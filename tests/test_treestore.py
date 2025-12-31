# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for TreeStore, TreeStoreNode, and TreeStoreBuilder."""

import pytest

from genro_treestore import (
    TreeStore,
    TreeStoreNode,
    TreeStoreBuilder,
    valid_children,
    InvalidChildError,
    MissingChildError,
    TooManyChildrenError,
)
from genro_treestore.treestore import _parse_cardinality


class TestTreeStoreNode:
    """Tests for TreeStoreNode."""

    def test_create_simple_node(self):
        """Test creating a simple node with scalar value."""
        node = TreeStoreNode('name_0', {'_tag': 'name', 'id': 1}, 'Alice')
        assert node.label == 'name_0'
        assert node.tag == 'name'
        assert node.attr == {'_tag': 'name', 'id': 1}
        assert node.value == 'Alice'
        assert node.parent is None

    def test_create_node_defaults(self):
        """Test node creation with default values."""
        node = TreeStoreNode('empty_0')
        assert node.label == 'empty_0'
        assert node.tag is None
        assert node.attr == {}
        assert node.value is None
        assert node.parent is None

    def test_create_node_with_tag(self):
        """Test node creation with tag in attr."""
        node = TreeStoreNode('item_0', {'_tag': 'item'})
        assert node.label == 'item_0'
        assert node.tag == 'item'

    def test_is_leaf(self):
        """Test is_leaf property for scalar values."""
        node = TreeStoreNode('name_0', {'_tag': 'name'}, value='Alice')
        assert node.is_leaf is True
        assert node.is_branch is False

    def test_is_branch(self):
        """Test is_branch property for TreeStore values."""
        store = TreeStore()
        node = TreeStoreNode('container_0', {'_tag': 'container'}, value=store)
        assert node.is_branch is True
        assert node.is_leaf is False

    def test_repr_with_tag(self):
        """Test string representation with tag."""
        node = TreeStoreNode('name_0', {'_tag': 'name', 'id': 1}, 'Alice')
        repr_str = repr(node)
        assert 'name_0' in repr_str
        assert 'name' in repr_str
        assert 'Alice' in repr_str

    def test_repr_without_tag(self):
        """Test string representation without tag."""
        node = TreeStoreNode('item_0', {'id': 1}, 'value')
        repr_str = repr(node)
        assert 'item_0' in repr_str
        assert 'value' in repr_str

    def test_underscore_property_returns_parent(self):
        """Test ._ returns parent TreeStore."""
        store = TreeStore()
        node = TreeStoreNode('item_0', value='test', parent=store)
        assert node._ is store

    def test_underscore_property_no_parent_raises(self):
        """Test ._ raises when no parent."""
        node = TreeStoreNode('orphan_0')
        with pytest.raises(ValueError, match="no parent"):
            _ = node._


class TestTreeStore:
    """Tests for TreeStore."""

    def test_create_empty_store(self):
        """Test creating an empty store."""
        store = TreeStore()
        assert len(store) == 0
        assert store.parent is None

    def test_child_creates_branch(self):
        """Test child() creates a branch node."""
        store = TreeStore()
        div = store.child('div', color='red')
        assert isinstance(div, TreeStore)
        assert 'div_0' in store
        assert store['div_0'].tag == 'div'
        assert store['div_0'].attr == {'_tag': 'div', 'color': 'red'}

    def test_child_creates_leaf_with_value(self):
        """Test child() creates leaf when value is provided."""
        store = TreeStore()
        node = store.child('li', value='Hello')
        assert isinstance(node, TreeStoreNode)
        assert node.value == 'Hello'
        assert node.tag == 'li'
        assert node.is_leaf

    def test_child_with_explicit_label(self):
        """Test child() with explicit label."""
        store = TreeStore()
        div = store.child('div', label='main', color='red')
        assert 'main' in store
        assert store['main'].tag == 'div'

    def test_child_with_explicit_label_and_value(self):
        """Test child() with explicit label and value."""
        store = TreeStore()
        node = store.child('li', label='myitem', value='Hello')
        assert 'myitem' in store
        assert store['myitem'].value == 'Hello'
        assert store['myitem'].tag == 'li'

    def test_child_with_attributes_dict(self):
        """Test child() with attributes dict."""
        store = TreeStore()
        attrs = {'color': 'red', 'size': 10}
        div = store.child('div', attributes=attrs)
        assert store['div_0'].attr == {'_tag': 'div', 'color': 'red', 'size': 10}

    def test_child_attributes_dict_merged_with_kwargs(self):
        """Test attributes dict is merged with kwargs."""
        store = TreeStore()
        attrs = {'color': 'red'}
        div = store.child('div', attributes=attrs, size=10, color='blue')
        # kwargs override attributes dict
        assert store['div_0'].attr == {'_tag': 'div', 'color': 'blue', 'size': 10}

    def test_auto_label_increments(self):
        """Test auto-generated labels increment."""
        store = TreeStore()
        store.child('div')
        store.child('div')
        store.child('div')
        assert 'div_0' in store
        assert 'div_1' in store
        assert 'div_2' in store

    def test_auto_label_per_tag(self):
        """Test auto-generated labels are per tag."""
        store = TreeStore()
        store.child('div')
        store.child('span')
        store.child('div')
        assert 'div_0' in store
        assert 'span_0' in store
        assert 'div_1' in store

    def test_nested_structure(self):
        """Test building nested structure."""
        store = TreeStore()
        div = store.child('div', color='red')
        ul = div.child('ul')
        ul.child('li', value='first')
        ul.child('li', value='second')

        assert 'div_0' in store
        assert 'ul_0' in store['div_0'].value
        assert 'li_0' in store['div_0'].value['ul_0'].value
        assert 'li_1' in store['div_0'].value['ul_0'].value

    def test_underscore_chain(self):
        """Test ._ chaining for leaf nodes."""
        store = TreeStore()
        ul = store.child('ul')
        # Chain: create li, go back to ul with ._, create another li
        ul.child('li', value='first')._.child('li', value='second')

        assert 'li_0' in ul
        assert 'li_1' in ul
        assert ul['li_0'].value == 'first'
        assert ul['li_1'].value == 'second'

    def test_iteration(self):
        """Test iterating over store."""
        store = TreeStore()
        store.child('a', value=1)
        store.child('b', value=2)
        assert list(store) == ['a_0', 'b_0']
        assert list(store.keys()) == ['a_0', 'b_0']

    def test_get_with_default(self):
        """Test get method with default value."""
        store = TreeStore()
        assert store.get('missing') is None
        assert store.get('missing', 'default') == 'default'

    def test_root_property(self):
        """Test root property navigation."""
        root = TreeStore()
        div = root.child('div')
        ul = div.child('ul')

        assert root.root is root
        assert div.root is root
        assert ul.root is root

    def test_depth_property(self):
        """Test depth calculation."""
        root = TreeStore()
        assert root.depth == 0

        div = root.child('div')
        assert div.depth == 1

        ul = div.child('ul')
        assert ul.depth == 2

    def test_by_tag(self):
        """Test by_tag returns nodes with given tag."""
        store = TreeStore()
        store.child('div')
        store.child('span')
        store.child('div')

        divs = store.by_tag('div')
        assert len(divs) == 2
        assert all(n.tag == 'div' for n in divs)

    def test_pop_removes_node(self):
        """Test pop removes and returns node."""
        store = TreeStore()
        store.child('div')
        store.child('div')
        store.child('div')

        node = store.pop('div_1')
        assert node.label == 'div_1'
        assert 'div_1' not in store
        assert 'div_0' in store
        assert 'div_2' in store


class TestReindex:
    """Tests for reindex functionality."""

    def test_reindex_removes_gaps(self):
        """Test reindex removes gaps in auto-labels."""
        store = TreeStore()
        store.child('div')  # div_0
        store.child('div')  # div_1
        store.child('div')  # div_2

        store.pop('div_1')
        assert list(store) == ['div_0', 'div_2']

        store.reindex()
        assert list(store) == ['div_0', 'div_1']

    def test_reindex_preserves_explicit_labels(self):
        """Test reindex preserves explicit labels."""
        store = TreeStore()
        store.child('div', label='main')
        store.child('div')  # div_0
        store.child('div')  # div_1

        store.pop('div_0')
        store.reindex()

        assert 'main' in store
        assert 'div_0' in store
        assert len(store) == 2

    def test_reindex_recursive(self):
        """Test reindex works recursively."""
        store = TreeStore()
        div = store.child('div')
        div.child('span')  # span_0
        div.child('span')  # span_1
        div.child('span')  # span_2
        div.pop('span_1')

        store.reindex()
        assert list(div) == ['span_0', 'span_1']

    def test_reindex_preserves_order(self):
        """Test reindex preserves original order."""
        store = TreeStore()
        store.child('div')  # div_0
        store.child('div')  # div_1
        store.child('div')  # div_2
        store.child('div')  # div_3

        store.pop('div_1')
        store.pop('div_2')
        store.reindex()

        # div_0 stays div_0, div_3 becomes div_1
        nodes = [store[k] for k in sorted(store.keys())]
        assert nodes[0].label == 'div_0'
        assert nodes[1].label == 'div_1'


class TestAsDict:
    """Tests for as_dict functionality."""

    def test_as_dict_simple_leaves(self):
        """Test as_dict with simple leaf values."""
        store = TreeStore()
        store.child('name', value='Alice')
        store.child('age', value=30)

        result = store.as_dict()
        assert result['name_0'] == 'Alice'
        assert result['age_0'] == 30

    def test_as_dict_with_branches(self):
        """Test as_dict with nested branches."""
        store = TreeStore()
        div = store.child('div', color='red')
        div.child('text', value='Hello')

        result = store.as_dict()
        assert result['div_0']['_tag'] == 'div'
        assert result['div_0']['color'] == 'red'
        assert result['div_0']['text_0'] == 'Hello'

    def test_as_dict_leaf_with_attr(self):
        """Test as_dict for leaf with attributes."""
        store = TreeStore()
        store.child('item', value='test_value', style='bold')

        result = store.as_dict()
        assert result['item_0']['_tag'] == 'item'
        assert result['item_0']['_value'] == 'test_value'
        assert result['item_0']['style'] == 'bold'


class TestWalk:
    """Tests for walk functionality."""

    def test_walk_flat(self):
        """Test walking flat structure."""
        store = TreeStore()
        store.child('a', value=1)
        store.child('b', value=2)

        paths = [(p, n.value) for p, n in store.walk()]
        assert ('a_0', 1) in paths
        assert ('b_0', 2) in paths

    def test_walk_nested(self):
        """Test walking nested structure."""
        store = TreeStore()
        div = store.child('div')
        div.child('span', value='text')

        paths = [p for p, _ in store.walk()]
        assert 'div_0' in paths
        assert 'div_0.span_0' in paths


class TestParseCardinality:
    """Tests for cardinality parsing."""

    def test_parse_true(self):
        assert _parse_cardinality(True) == (0, None)

    def test_parse_int(self):
        assert _parse_cardinality(3) == (3, 3)

    def test_parse_exact_string(self):
        assert _parse_cardinality('1') == (1, 1)
        assert _parse_cardinality('5') == (5, 5)

    def test_parse_range(self):
        assert _parse_cardinality('0:') == (0, None)
        assert _parse_cardinality('1:') == (1, None)
        assert _parse_cardinality('1:3') == (1, 3)
        assert _parse_cardinality(':5') == (0, 5)


class TestValidChildrenDecorator:
    """Tests for @valid_children decorator."""

    def test_simple_allowed_tags(self):
        @valid_children('div', 'span')
        def method():
            pass

        assert method._valid_children == {
            'div': (0, None),
            'span': (0, None),
        }

    def test_with_constraints(self):
        @valid_children(title='1', item='1:5')
        def method():
            pass

        assert method._valid_children == {
            'title': (1, 1),
            'item': (1, 5),
        }

    def test_mixed_args_and_kwargs(self):
        @valid_children('div', 'span', title='1')
        def method():
            pass

        assert method._valid_children == {
            'div': (0, None),
            'span': (0, None),
            'title': (1, 1),
        }


class TestTypedBuilder:
    """Tests for typed builders with validation."""

    def test_html_builder_example(self):
        """Test a simple HTML-like builder."""
        class HtmlBuilder(TreeStoreBuilder):
            def div(self, label: str = None, **attr) -> TreeStore:
                return self.child('div', label=label, **attr)

            @valid_children('li')
            def ul(self, label: str = None, **attr) -> TreeStore:
                return self.child('ul', label=label, **attr)

            def li(self, value: str = None, label: str = None, **attr) -> TreeStoreNode:
                return self.child('li', label=label, value=value, **attr)

        body = HtmlBuilder()
        box = body.div(color='red')
        ul = box.ul()
        ul.li('pino')
        ul.li('gino')
        box2 = body.div(color='green')

        assert 'div_0' in body
        assert 'div_1' in body
        assert body['div_0'].attr == {'_tag': 'div', 'color': 'red'}
        assert body['div_1'].attr == {'_tag': 'div', 'color': 'green'}

        ul_store = body['div_0'].value['ul_0'].value
        assert 'li_0' in ul_store
        assert 'li_1' in ul_store
        assert ul_store['li_0'].value == 'pino'
        assert ul_store['li_1'].value == 'gino'

    def test_valid_children_enforcement(self):
        """Test that invalid children are rejected."""
        class HtmlBuilder(TreeStoreBuilder):
            @valid_children('li')
            def ul(self, label: str = None, **attr) -> TreeStore:
                return self.child('ul', label=label, **attr)

            def li(self, value: str = None, **attr) -> TreeStoreNode:
                return self.child('li', value=value, **attr)

            def div(self, **attr) -> TreeStore:
                return self.child('div', **attr)

        builder = HtmlBuilder()
        ul = builder.ul()
        ul.li('item')  # OK

        with pytest.raises(InvalidChildError, match="div.*not valid"):
            ul.child('div')  # div not allowed in ul

    def test_max_children_enforcement(self):
        """Test that max children count is enforced."""
        class LimitedBuilder(TreeStoreBuilder):
            @valid_children(item='0:2')
            def container(self, **attr) -> TreeStore:
                return self.child('container', **attr)

            def item(self, value: str, **attr) -> TreeStoreNode:
                return self.child('item', value=value, **attr)

        builder = LimitedBuilder()
        cont = builder.container()
        cont.item('first')
        cont.item('second')

        with pytest.raises(TooManyChildrenError, match="Maximum 2"):
            cont.item('third')

    def test_child_store_inherits_builder_class(self):
        """Test that child stores maintain builder methods."""
        class HtmlBuilder(TreeStoreBuilder):
            def div(self, **attr) -> TreeStore:
                return self.child('div', **attr)

            def span(self, value: str = None, **attr) -> TreeStoreNode:
                return self.child('span', value=value, **attr)

        builder = HtmlBuilder()
        div = builder.div()
        # div should be an HtmlBuilder instance, not plain TreeStore
        assert isinstance(div, HtmlBuilder)
        # So it should have the div method
        inner_div = div.div()
        assert isinstance(inner_div, HtmlBuilder)


class TestDottedPathAccess:
    """Tests for dotted path access in __getitem__."""

    def test_single_label_access(self):
        """Test that single label access still works."""
        store = TreeStore()
        store.child('div')
        assert store['div_0'].tag == 'div'

    def test_dotted_path_two_levels(self):
        """Test dotted path with two levels."""
        store = TreeStore()
        div = store.child('div')
        div.child('span', value='text')

        node = store['div_0.span_0']
        assert node.tag == 'span'
        assert node.value == 'text'

    def test_dotted_path_three_levels(self):
        """Test dotted path with three levels."""
        store = TreeStore()
        div = store.child('div')
        ul = div.child('ul')
        ul.child('li', value='first')

        node = store['div_0.ul_0.li_0']
        assert node.tag == 'li'
        assert node.value == 'first'

    def test_dotted_path_keyerror_missing_intermediate(self):
        """Test KeyError for missing intermediate node."""
        store = TreeStore()
        store.child('div')

        with pytest.raises(KeyError):
            _ = store['div_0.nonexistent.child']

    def test_dotted_path_keyerror_on_leaf(self):
        """Test KeyError when path goes through leaf node."""
        store = TreeStore()
        div = store.child('div')
        div.child('text', value='Hello')

        with pytest.raises(KeyError, match="not a branch"):
            _ = store['div_0.text_0.child']

    def test_dotted_path_with_explicit_labels(self):
        """Test dotted path with explicit labels."""
        store = TreeStore()
        div = store.child('div', label='main')
        ul = div.child('ul', label='menu')
        ul.child('li', label='home', value='Home')

        node = store['main.menu.home']
        assert node.value == 'Home'

    def test_positional_access_simple(self):
        """Test positional access with #N syntax."""
        store = TreeStore()
        store.child('div')
        store.child('span')
        store.child('p')

        assert store['#0'].tag == 'div'
        assert store['#1'].tag == 'span'
        assert store['#2'].tag == 'p'

    def test_positional_access_out_of_range(self):
        """Test KeyError for out of range position."""
        store = TreeStore()
        store.child('div')

        with pytest.raises(KeyError, match="out of range"):
            _ = store['#5']

    def test_positional_access_in_path(self):
        """Test positional access in dotted path."""
        store = TreeStore()
        div = store.child('div')
        ul = div.child('ul')
        ul.child('li', value='first')
        ul.child('li', value='second')
        ul.child('li', value='third')
        ul.child('li', value='fourth')

        # Access: first child (div_0) -> ul_0 -> fourth item (#3)
        node = store['#0.ul_0.#3']
        assert node.value == 'fourth'

    def test_mixed_positional_and_label_access(self):
        """Test mixing positional and label access."""
        store = TreeStore()
        div = store.child('div', label='main')
        ul = div.child('ul')
        ul.child('li', value='item1')
        ul.child('li', value='item2')

        # main -> first child (ul_0) -> second item (#1)
        node = store['main.#0.#1']
        assert node.value == 'item2'


class TestAttributeAccess:
    """Tests for attribute access with ?attr syntax."""

    def test_get_attribute_simple(self):
        """Test getting attribute with ?attr syntax."""
        store = TreeStore()
        store.child('div', color='red', size=10)

        assert store['div_0?color'] == 'red'
        assert store['div_0?size'] == 10

    def test_get_attribute_missing_returns_none(self):
        """Test getting missing attribute returns None."""
        store = TreeStore()
        store.child('div', color='red')

        assert store['div_0?missing'] is None

    def test_get_attribute_in_path(self):
        """Test getting attribute in dotted path."""
        store = TreeStore()
        div = store.child('div')
        div.child('ul', class_='menu', id='nav')

        assert store['div_0.ul_0?class_'] == 'menu'
        assert store['div_0.ul_0?id'] == 'nav'

    def test_get_attribute_with_positional(self):
        """Test getting attribute with positional access."""
        store = TreeStore()
        store.child('div', color='red')
        store.child('span', color='blue')

        assert store['#0?color'] == 'red'
        assert store['#1?color'] == 'blue'

    def test_set_attribute_simple(self):
        """Test setting attribute with ?attr syntax."""
        store = TreeStore()
        store.child('div')

        store['div_0?color'] = 'red'
        assert store['div_0'].attr['color'] == 'red'

    def test_set_attribute_in_path(self):
        """Test setting attribute in dotted path."""
        store = TreeStore()
        div = store.child('div')
        div.child('ul')

        store['div_0.ul_0?class'] = 'active'
        assert store['div_0.ul_0'].attr['class'] == 'active'

    def test_set_attribute_with_positional(self):
        """Test setting attribute with positional access."""
        store = TreeStore()
        div = store.child('div')
        ul = div.child('ul')
        ul.child('li', value='first')
        ul.child('li', value='second')
        ul.child('li', value='third')
        ul.child('li', value='fourth')

        store['#0.ul_0.#3?highlight'] = True
        assert store['div_0.ul_0.li_3'].attr['highlight'] is True

    def test_set_without_attr_raises(self):
        """Test that setting without ?attr raises KeyError."""
        store = TreeStore()
        store.child('div')

        with pytest.raises(KeyError, match="use .attr syntax"):
            store['div_0'] = 'something'


class TestIntegration:
    """Integration tests."""

    def test_complete_html_structure(self):
        """Test building a complete HTML-like structure."""
        store = TreeStore()

        # Build structure
        html = store.child('html')
        head = html.child('head')
        head.child('title', value='My Page')

        body = html.child('body')
        div = body.child('div', label='container', class_='main')
        div.child('h1', value='Welcome')

        ul = div.child('ul')
        ul.child('li', value='Item 1')._.child('li', value='Item 2')._.child('li', value='Item 3')

        # Verify structure
        assert 'html_0' in store
        html_store = store['html_0'].value
        assert 'head_0' in html_store
        assert 'body_0' in html_store

        body_store = html_store['body_0'].value
        assert 'container' in body_store

        ul_store = body_store['container'].value['ul_0'].value
        assert len(ul_store) == 3
        assert ul_store['li_0'].value == 'Item 1'
        assert ul_store['li_1'].value == 'Item 2'
        assert ul_store['li_2'].value == 'Item 3'
