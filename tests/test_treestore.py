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
        node = TreeStoreNode('user', {'id': 1}, 'Alice')
        assert node.label == 'user'
        assert node.attr == {'id': 1}
        assert node.value == 'Alice'
        assert node.parent is None

    def test_create_node_defaults(self):
        """Test node creation with default values."""
        node = TreeStoreNode('empty')
        assert node.label == 'empty'
        assert node.tag is None
        assert node.attr == {}
        assert node.value is None
        assert node.parent is None

    def test_create_node_with_tag(self):
        """Test node creation with tag in attr."""
        node = TreeStoreNode('item', {'_tag': 'item'})
        assert node.label == 'item'
        assert node.tag == 'item'

    def test_is_leaf(self):
        """Test is_leaf property for scalar values."""
        node = TreeStoreNode('name', value='Alice')
        assert node.is_leaf is True
        assert node.is_branch is False

    def test_is_branch(self):
        """Test is_branch property for TreeStore values."""
        store = TreeStore()
        node = TreeStoreNode('container', value=store)
        assert node.is_branch is True
        assert node.is_leaf is False

    def test_repr(self):
        """Test string representation."""
        node = TreeStoreNode('name', {'id': 1}, 'Alice')
        repr_str = repr(node)
        assert 'name' in repr_str
        assert 'Alice' in repr_str

    def test_underscore_property_returns_parent(self):
        """Test ._ returns parent TreeStore."""
        store = TreeStore()
        node = TreeStoreNode('item', value='test', parent=store)
        assert node._ is store

    def test_underscore_property_no_parent_raises(self):
        """Test ._ raises when no parent."""
        node = TreeStoreNode('orphan')
        with pytest.raises(ValueError, match="no parent"):
            _ = node._

    def test_getAttr(self):
        """Test getAttr method."""
        node = TreeStoreNode('item', {'color': 'red', 'size': 10})
        assert node.getAttr('color') == 'red'
        assert node.getAttr('size') == 10
        assert node.getAttr('missing') is None
        assert node.getAttr('missing', 'default') == 'default'
        assert node.getAttr() == {'color': 'red', 'size': 10}

    def test_setAttr(self):
        """Test setAttr method."""
        node = TreeStoreNode('item')
        node.setAttr({'color': 'red'}, size=10)
        assert node.attr == {'color': 'red', 'size': 10}
        node.setAttr(color='blue')
        assert node.attr['color'] == 'blue'


class TestTreeStoreBasic:
    """Basic tests for TreeStore."""

    def test_create_empty_store(self):
        """Test creating an empty store."""
        store = TreeStore()
        assert len(store) == 0
        assert store.parent is None

    def test_setItem_creates_branch(self):
        """Test setItem creates a branch node when no value."""
        store = TreeStore()
        result = store.setItem('div', color='red')
        assert isinstance(result, TreeStore)
        assert 'div' in store
        assert store.getAttr('div', 'color') == 'red'

    def test_setItem_creates_leaf_with_value(self):
        """Test setItem creates leaf when value is provided."""
        store = TreeStore()
        result = store.setItem('name', 'Alice')
        assert isinstance(result, TreeStore)  # Returns parent for chaining
        assert result is store
        assert store['name'] == 'Alice'

    def test_setItem_autocreate_path(self):
        """Test setItem creates intermediate nodes."""
        store = TreeStore()
        store.setItem('html.body.div', color='red')
        assert 'html' in store
        assert store['html.body.div?color'] == 'red'

    def test_setItem_fluent_chaining_branches(self):
        """Test fluent chaining with branches."""
        store = TreeStore()
        store.setItem('html').setItem('body').setItem('div', color='red')
        assert store['html.body.div?color'] == 'red'

    def test_setItem_fluent_chaining_leaves(self):
        """Test fluent chaining with leaves returns parent."""
        store = TreeStore()
        ul = store.setItem('ul')
        ul.setItem('li', 'Item 1').setItem('li2', 'Item 2').setItem('li3', 'Item 3')
        assert store['ul.li'] == 'Item 1'
        assert store['ul.li2'] == 'Item 2'
        assert store['ul.li3'] == 'Item 3'

    def test_getItem_returns_value(self):
        """Test getItem returns value."""
        store = TreeStore()
        store.setItem('name', 'Alice')
        assert store.getItem('name') == 'Alice'

    def test_getItem_with_default(self):
        """Test getItem returns default for missing path."""
        store = TreeStore()
        assert store.getItem('missing') is None
        assert store.getItem('missing', 'default') == 'default'

    def test_getItem_attribute_access(self):
        """Test getItem with ?attr syntax."""
        store = TreeStore()
        store.setItem('div', color='red')
        assert store.getItem('div?color') == 'red'

    def test_getitem_returns_value(self):
        """Test __getitem__ returns value."""
        store = TreeStore()
        store.setItem('name', 'Alice')
        assert store['name'] == 'Alice'

    def test_getitem_attribute_access(self):
        """Test __getitem__ with ?attr syntax."""
        store = TreeStore()
        store.setItem('div', color='red')
        assert store['div?color'] == 'red'

    def test_setitem_sets_value(self):
        """Test __setitem__ sets value with autocreate."""
        store = TreeStore()
        store['html.body.div'] = 'text'
        assert store['html.body.div'] == 'text'

    def test_setitem_sets_attribute(self):
        """Test __setitem__ sets attribute with ?attr syntax."""
        store = TreeStore()
        store.setItem('div')
        store['div?color'] = 'red'
        assert store['div?color'] == 'red'

    def test_getNode(self):
        """Test getNode returns TreeStoreNode."""
        store = TreeStore()
        store.setItem('div', color='red')
        node = store.getNode('div')
        assert isinstance(node, TreeStoreNode)
        assert node.label == 'div'
        assert node.attr['color'] == 'red'

    def test_getAttr(self):
        """Test getAttr on store."""
        store = TreeStore()
        store.setItem('div', color='red', size=10)
        assert store.getAttr('div', 'color') == 'red'
        assert store.getAttr('div', 'size') == 10
        assert store.getAttr('div') == {'color': 'red', 'size': 10}

    def test_setAttr(self):
        """Test setAttr on store."""
        store = TreeStore()
        store.setItem('div')
        store.setAttr('div', color='red', size=10)
        assert store['div?color'] == 'red'
        assert store['div?size'] == 10

    def test_delItem(self):
        """Test delItem removes node."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        node = store.delItem('a')
        assert node.label == 'a'
        assert 'a' not in store
        assert 'b' in store

    def test_pop(self):
        """Test pop removes and returns value."""
        store = TreeStore()
        store.setItem('name', 'Alice')
        value = store.pop('name')
        assert value == 'Alice'
        assert 'name' not in store

    def test_pop_with_default(self):
        """Test pop returns default for missing."""
        store = TreeStore()
        assert store.pop('missing') is None
        assert store.pop('missing', 'default') == 'default'


class TestTreeStoreIteration:
    """Tests for TreeStore iteration methods."""

    def test_iter_yields_nodes(self):
        """Test __iter__ yields nodes."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        nodes = list(store)
        assert len(nodes) == 2
        assert all(isinstance(n, TreeStoreNode) for n in nodes)

    def test_keys(self):
        """Test keys() returns labels."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.keys() == ['a', 'b']

    def test_values(self):
        """Test values() returns values."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.values() == [1, 2]

    def test_items(self):
        """Test items() returns (label, value) pairs."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.items() == [('a', 1), ('b', 2)]

    def test_nodes(self):
        """Test nodes() returns list of nodes."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        nodes = store.nodes()
        assert len(nodes) == 2
        assert all(isinstance(n, TreeStoreNode) for n in nodes)

    def test_getNodes(self):
        """Test getNodes at path."""
        store = TreeStore()
        store.setItem('div.span', 'text')
        store.setItem('div.p', 'para')
        nodes = store.getNodes('div')
        assert len(nodes) == 2


class TestTreeStoreDigest:
    """Tests for digest functionality."""

    def test_digest_keys(self):
        """Test digest #k returns labels."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.digest('#k') == ['a', 'b']

    def test_digest_values(self):
        """Test digest #v returns values."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.digest('#v') == [1, 2]

    def test_digest_attributes(self):
        """Test digest #a returns all attributes."""
        store = TreeStore()
        store.setItem('a', 1, color='red')
        store.setItem('b', 2, color='blue')
        attrs = store.digest('#a')
        assert attrs[0]['color'] == 'red'
        assert attrs[1]['color'] == 'blue'

    def test_digest_specific_attribute(self):
        """Test digest #a.attrname returns specific attribute."""
        store = TreeStore()
        store.setItem('a', 1, color='red')
        store.setItem('b', 2, color='blue')
        assert store.digest('#a.color') == ['red', 'blue']

    def test_digest_multiple(self):
        """Test digest with multiple specifiers."""
        store = TreeStore()
        store.setItem('a', 1, color='red')
        store.setItem('b', 2, color='blue')
        result = store.digest('#k,#v,#a.color')
        assert result == [('a', 1, 'red'), ('b', 2, 'blue')]


class TestTreeStoreWalk:
    """Tests for walk functionality."""

    def test_walk_generator(self):
        """Test walk as generator."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        paths = [(p, n.value) for p, n in store.walk()]
        assert ('a', 1) in paths
        assert ('b', 2) in paths

    def test_walk_nested(self):
        """Test walk with nested structure."""
        store = TreeStore()
        store.setItem('div.span', 'text')
        paths = [p for p, _ in store.walk()]
        assert 'div' in paths
        assert 'div.span' in paths

    def test_walk_callback(self):
        """Test walk with callback."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        labels = []
        store.walk(lambda n: labels.append(n.label))
        assert labels == ['a', 'b']


class TestTreeStoreNavigation:
    """Tests for navigation properties."""

    def test_root_property(self):
        """Test root property."""
        store = TreeStore()
        div = store.setItem('div')
        span = div.setItem('span')
        assert store.root is store
        assert div.root is store
        assert span.root is store

    def test_depth_property(self):
        """Test depth property."""
        store = TreeStore()
        assert store.depth == 0
        div = store.setItem('div')
        assert div.depth == 1
        span = div.setItem('span')
        assert span.depth == 2

    def test_parentNode(self):
        """Test parentNode property."""
        store = TreeStore()
        div = store.setItem('div')
        assert store.parentNode is None
        assert div.parentNode is not None
        assert div.parentNode.label == 'div'


class TestTreeStorePathAccess:
    """Tests for path access with positional and attribute syntax."""

    def test_positional_access(self):
        """Test #N positional access."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        assert store['#0'] == 1
        assert store['#1'] == 2
        assert store['#2'] == 3

    def test_positional_negative(self):
        """Test negative positional access."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store['#-1'] == 2
        assert store['#-2'] == 1

    def test_positional_in_path(self):
        """Test positional access in dotted path."""
        store = TreeStore()
        store.setItem('div.span', 'text')
        assert store['#0.#0'] == 'text'

    def test_mixed_path_access(self):
        """Test mixed positional and label access."""
        store = TreeStore()
        store.setItem('div.span', 'text')
        assert store['div.#0'] == 'text'
        assert store['#0.span'] == 'text'

    def test_attribute_access_in_path(self):
        """Test ?attr in dotted path."""
        store = TreeStore()
        store.setItem('div.span', color='red')
        assert store['div.span?color'] == 'red'


class TestTreeStoreConversion:
    """Tests for conversion methods."""

    def test_as_dict_simple(self):
        """Test as_dict with simple values."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        assert store.as_dict() == {'a': 1, 'b': 2}

    def test_as_dict_nested(self):
        """Test as_dict with nested structure."""
        store = TreeStore()
        store.setItem('div.span', 'text')
        result = store.as_dict()
        assert 'div' in result
        assert result['div']['span'] == 'text'

    def test_as_dict_with_attributes(self):
        """Test as_dict preserves attributes."""
        store = TreeStore()
        store.setItem('item', 'value', color='red')
        result = store.as_dict()
        assert result['item']['_value'] == 'value'
        assert result['item']['color'] == 'red'

    def test_clear(self):
        """Test clear removes all nodes."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.clear()
        assert len(store) == 0


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


class TestTreeStoreBuilder:
    """Tests for TreeStoreBuilder."""

    def test_child_creates_branch(self):
        """Test child() creates branch with auto-label."""
        builder = TreeStoreBuilder()
        div = builder.child('div', color='red')
        assert isinstance(div, TreeStoreBuilder)
        assert 'div_0' in builder
        assert builder.getNode('div_0').tag == 'div'
        assert builder['div_0?color'] == 'red'

    def test_child_creates_leaf(self):
        """Test child() creates leaf with auto-label."""
        builder = TreeStoreBuilder()
        node = builder.child('li', value='Hello')
        assert isinstance(node, TreeStoreNode)
        assert node.value == 'Hello'
        assert node.tag == 'li'

    def test_child_explicit_label(self):
        """Test child() with explicit label."""
        builder = TreeStoreBuilder()
        builder.child('div', label='main')
        assert 'main' in builder
        assert builder.getNode('main').tag == 'div'

    def test_auto_label_increments(self):
        """Test auto-labels increment per tag."""
        builder = TreeStoreBuilder()
        builder.child('div')
        builder.child('div')
        builder.child('span')
        builder.child('div')
        assert 'div_0' in builder
        assert 'div_1' in builder
        assert 'span_0' in builder
        assert 'div_2' in builder

    def test_html_builder_example(self):
        """Test a simple HTML-like builder."""
        class HtmlBuilder(TreeStoreBuilder):
            def div(self, label: str = None, **attr):
                return self.child('div', label=label, **attr)

            @valid_children('li')
            def ul(self, label: str = None, **attr):
                return self.child('ul', label=label, **attr)

            def li(self, value: str = None, label: str = None, **attr):
                return self.child('li', label=label, value=value, **attr)

        body = HtmlBuilder()
        box = body.div(color='red')
        ul = box.ul()
        ul.li('pino')
        ul.li('gino')
        body.div(color='green')

        assert 'div_0' in body
        assert 'div_1' in body
        assert body['div_0?color'] == 'red'
        assert body['div_1?color'] == 'green'

    def test_valid_children_enforcement(self):
        """Test that invalid children are rejected."""
        class HtmlBuilder(TreeStoreBuilder):
            @valid_children('li')
            def ul(self, **attr):
                return self.child('ul', **attr)

            def li(self, value: str = None, **attr):
                return self.child('li', value=value, **attr)

        builder = HtmlBuilder()
        ul = builder.ul()
        ul.li('item')  # OK

        with pytest.raises(InvalidChildError, match="div.*not valid"):
            ul.child('div')

    def test_max_children_enforcement(self):
        """Test max children count enforcement."""
        class LimitedBuilder(TreeStoreBuilder):
            @valid_children(item='0:2')
            def container(self, **attr):
                return self.child('container', **attr)

            def item(self, value: str, **attr):
                return self.child('item', value=value, **attr)

        builder = LimitedBuilder()
        cont = builder.container()
        cont.item('first')
        cont.item('second')

        with pytest.raises(TooManyChildrenError, match="Maximum 2"):
            cont.item('third')

    def test_child_inherits_builder_class(self):
        """Test child stores are same builder class."""
        class HtmlBuilder(TreeStoreBuilder):
            def div(self, **attr):
                return self.child('div', **attr)

        builder = HtmlBuilder()
        div = builder.div()
        assert isinstance(div, HtmlBuilder)
        inner = div.div()
        assert isinstance(inner, HtmlBuilder)

    def test_reindex(self):
        """Test reindex removes gaps."""
        builder = TreeStoreBuilder()
        builder.child('div')
        builder.child('div')
        builder.child('div')
        builder.pop('div_1')

        assert builder.keys() == ['div_0', 'div_2']
        builder.reindex()
        assert builder.keys() == ['div_0', 'div_1']

    def test_by_tag(self):
        """Test by_tag filters nodes."""
        builder = TreeStoreBuilder()
        builder.child('div')
        builder.child('span')
        builder.child('div')

        divs = builder.by_tag('div')
        assert len(divs) == 2
        assert all(n.tag == 'div' for n in divs)


class TestIntegration:
    """Integration tests."""

    def test_bag_like_structure(self):
        """Test building structure with Bag-like API."""
        store = TreeStore()

        # Build with setItem
        store.setItem('config.database.host', 'localhost')
        store.setItem('config.database.port', 5432)
        store.setItem('config.cache.enabled', True)

        # Access values
        assert store['config.database.host'] == 'localhost'
        assert store['config.database.port'] == 5432
        assert store['config.cache.enabled'] is True

        # Modify
        store['config.database.host'] = '192.168.1.1'
        assert store['config.database.host'] == '192.168.1.1'

    def test_builder_structure(self):
        """Test building structure with Builder API."""
        class HtmlBuilder(TreeStoreBuilder):
            def html(self, **attr):
                return self.child('html', **attr)

            def head(self, **attr):
                return self.child('head', **attr)

            def body(self, **attr):
                return self.child('body', **attr)

            def title(self, value, **attr):
                return self.child('title', value=value, **attr)

            def div(self, **attr):
                return self.child('div', **attr)

            @valid_children('li')
            def ul(self, **attr):
                return self.child('ul', **attr)

            def li(self, value, **attr):
                return self.child('li', value=value, **attr)

        builder = HtmlBuilder()
        html = builder.html()

        head = html.head()
        head.title('My Page')

        body = html.body()
        div = body.div(id='container')
        ul = div.ul()
        ul.li('Item 1')
        ul.li('Item 2')
        ul.li('Item 3')

        # Verify structure
        assert builder['html_0.head_0.title_0'] == 'My Page'
        assert builder['html_0.body_0.div_0?id'] == 'container'
        assert builder['html_0.body_0.div_0.ul_0.li_0'] == 'Item 1'
        assert builder['html_0.body_0.div_0.ul_0.li_2'] == 'Item 3'

    def test_fluent_chaining(self):
        """Test fluent API chaining."""
        store = TreeStore()

        # Chain branches
        (store
            .setItem('html')
            .setItem('body')
            .setItem('div', id='main'))

        assert store['html.body.div?id'] == 'main'

        # Chain leaves (returns parent)
        ul = store.setItem('html.body.ul')
        ul.setItem('li1', 'A').setItem('li2', 'B').setItem('li3', 'C')

        assert store['html.body.ul.li1'] == 'A'
        assert store['html.body.ul.li2'] == 'B'
        assert store['html.body.ul.li3'] == 'C'


class TestPositionParameter:
    """Tests for _position parameter in setItem and child()."""

    def test_setItem_position_append_default(self):
        """Test setItem appends by default."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        assert store.keys() == ['a', 'b', 'c']

    def test_setItem_position_prepend(self):
        """Test setItem with _position='<' inserts at beginning."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('first', 0, _position='<')
        assert store.keys() == ['first', 'a', 'b']
        assert store['#0'] == 0
        assert store['#1'] == 1

    def test_setItem_position_before_label(self):
        """Test setItem with _position='<label' inserts before label."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='<b')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99
        assert store['#2'] == 2

    def test_setItem_position_after_label(self):
        """Test setItem with _position='>label' inserts after label."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='>a')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#0'] == 1
        assert store['#1'] == 99

    def test_setItem_position_before_index(self):
        """Test setItem with _position='<#N' inserts before position N."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='<#1')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_setItem_position_after_index(self):
        """Test setItem with _position='>#N' inserts after position N."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='>#0')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_setItem_position_at_index(self):
        """Test setItem with _position='#N' inserts at exact position N."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='#1')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_setItem_position_negative_index(self):
        """Test setItem with negative position index."""
        store = TreeStore()
        store.setItem('a', 1)
        store.setItem('b', 2)
        store.setItem('c', 3)
        store.setItem('inserted', 99, _position='<#-1')  # before last
        assert store.keys() == ['a', 'b', 'inserted', 'c']

    def test_setItem_position_branch(self):
        """Test _position works for branch nodes too."""
        store = TreeStore()
        store.setItem('first')
        store.setItem('last')
        store.setItem('middle', _position='<last')
        assert store.keys() == ['first', 'middle', 'last']

    def test_builder_child_position_prepend(self):
        """Test child() with _position='<' inserts at beginning."""
        builder = TreeStoreBuilder()
        builder.child('div')
        builder.child('div')
        builder.child('div', _position='<')
        assert builder.keys() == ['div_2', 'div_0', 'div_1']
        assert builder['#0?'] is None  # div_2 is first
        assert builder.getNode('#0').tag == 'div'

    def test_builder_child_position_before_label(self):
        """Test child() with _position='<label' inserts before label."""
        builder = TreeStoreBuilder()
        builder.child('div', label='first')
        builder.child('div', label='last')
        builder.child('div', label='middle', _position='<last')
        assert builder.keys() == ['first', 'middle', 'last']

    def test_builder_child_position_at_index(self):
        """Test child() with _position='#N' inserts at position."""
        builder = TreeStoreBuilder()
        builder.child('li', value='A')
        builder.child('li', value='B')
        builder.child('li', value='C')
        builder.child('li', value='INSERTED', _position='#1')
        assert [builder[f'#{ i}'] for i in range(4)] == ['A', 'INSERTED', 'B', 'C']

    def test_position_with_path(self):
        """Test _position works with nested paths."""
        store = TreeStore()
        store.setItem('container.a', 1)
        store.setItem('container.b', 2)
        store.setItem('container.c', 3)
        store.setItem('container.inserted', 99, _position='<b')
        container = store.getNode('container').value
        assert container.keys() == ['a', 'inserted', 'b', 'c']
