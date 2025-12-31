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
    Grammar,
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

    def test_get_attr(self):
        """Test get_attr method."""
        node = TreeStoreNode('item', {'color': 'red', 'size': 10})
        assert node.get_attr('color') == 'red'
        assert node.get_attr('size') == 10
        assert node.get_attr('missing') is None
        assert node.get_attr('missing', 'default') == 'default'
        assert node.get_attr() == {'color': 'red', 'size': 10}

    def test_set_attr(self):
        """Test set_attr method."""
        node = TreeStoreNode('item')
        node.set_attr({'color': 'red'}, size=10)
        assert node.attr == {'color': 'red', 'size': 10}
        node.set_attr(color='blue')
        assert node.attr['color'] == 'blue'


class TestTreeStoreSource:
    """Tests for TreeStore source parameter."""

    def test_source_from_simple_dict(self):
        """Test creating TreeStore from simple dict."""
        store = TreeStore({'a': 1, 'b': 2, 'c': 'hello'})
        assert store['a'] == 1
        assert store['b'] == 2
        assert store['c'] == 'hello'

    def test_source_from_nested_dict(self):
        """Test creating TreeStore from nested dict."""
        store = TreeStore({
            'config': {
                'database': {
                    'host': 'localhost',
                    'port': 5432,
                }
            }
        })
        assert store['config.database.host'] == 'localhost'
        assert store['config.database.port'] == 5432

    def test_source_from_dict_with_attributes(self):
        """Test creating TreeStore from dict with _attr keys."""
        store = TreeStore({
            'item': {
                '_color': 'red',
                '_size': 10,
                '_value': 'hello',
            }
        })
        assert store['item'] == 'hello'
        assert store['item?color'] == 'red'
        assert store['item?size'] == 10

    def test_source_from_dict_with_children_and_attributes(self):
        """Test dict with both children and attributes."""
        store = TreeStore({
            'div': {
                '_class': 'container',
                'span': 'text',
            }
        })
        assert store['div?class'] == 'container'
        assert store['div.span'] == 'text'

    def test_source_from_treestore(self):
        """Test copying from another TreeStore."""
        original = TreeStore()
        original.set_item('a', 1, color='red')
        original.set_item('b.c', 2)

        copy = TreeStore(original)

        assert copy['a'] == 1
        assert copy['a?color'] == 'red'
        assert copy['b.c'] == 2

        # Verify it's a copy, not a reference
        original['a'] = 999
        assert copy['a'] == 1

    def test_source_from_list_simple(self):
        """Test creating TreeStore from list of tuples."""
        store = TreeStore([
            ('a', 1),
            ('b', 2),
            ('c', 'hello'),
        ])
        assert store['a'] == 1
        assert store['b'] == 2
        assert store['c'] == 'hello'

    def test_source_from_list_with_attributes(self):
        """Test list of tuples with attributes."""
        store = TreeStore([
            ('item1', 'value1', {'color': 'red'}),
            ('item2', 'value2', {'color': 'blue', 'size': 10}),
        ])
        assert store['item1'] == 'value1'
        assert store['item1?color'] == 'red'
        assert store['item2?color'] == 'blue'
        assert store['item2?size'] == 10

    def test_source_from_list_with_nested_dict(self):
        """Test list with nested dict values."""
        store = TreeStore([
            ('config', {'host': 'localhost', 'port': 5432}),
        ])
        assert store['config.host'] == 'localhost'
        assert store['config.port'] == 5432

    def test_source_from_list_with_nested_list(self):
        """Test list with nested list of tuples."""
        store = TreeStore([
            ('parent', [
                ('child1', 'a'),
                ('child2', 'b'),
            ]),
        ])
        assert store['parent.child1'] == 'a'
        assert store['parent.child2'] == 'b'

    def test_source_invalid_type_raises(self):
        """Test that invalid source type raises TypeError."""
        with pytest.raises(TypeError, match="must be dict, list, or TreeStore"):
            TreeStore("invalid")

    def test_source_list_invalid_tuple_raises(self):
        """Test that invalid tuple length raises ValueError."""
        with pytest.raises(ValueError, match="must be .* got 4 elements"):
            TreeStore([('a', 1, {}, 'extra')])


class TestTreeStoreBasic:
    """Basic tests for TreeStore."""

    def test_create_empty_store(self):
        """Test creating an empty store."""
        store = TreeStore()
        assert len(store) == 0
        assert store.parent is None

    def test_set_item_creates_branch(self):
        """Test set_item creates a branch node when no value."""
        store = TreeStore()
        result = store.set_item('div', color='red')
        assert isinstance(result, TreeStore)
        assert 'div' in store
        assert store.get_attr('div', 'color') == 'red'

    def test_set_item_creates_leaf_with_value(self):
        """Test set_item creates leaf when value is provided."""
        store = TreeStore()
        result = store.set_item('name', 'Alice')
        assert isinstance(result, TreeStore)  # Returns parent for chaining
        assert result is store
        assert store['name'] == 'Alice'

    def test_set_item_autocreate_path(self):
        """Test set_item creates intermediate nodes."""
        store = TreeStore()
        store.set_item('html.body.div', color='red')
        assert 'html' in store
        assert store['html.body.div?color'] == 'red'

    def test_set_item_fluent_chaining_branches(self):
        """Test fluent chaining with branches."""
        store = TreeStore()
        store.set_item('html').set_item('body').set_item('div', color='red')
        assert store['html.body.div?color'] == 'red'

    def test_set_item_fluent_chaining_leaves(self):
        """Test fluent chaining with leaves returns parent."""
        store = TreeStore()
        ul = store.set_item('ul')
        ul.set_item('li', 'Item 1').set_item('li2', 'Item 2').set_item('li3', 'Item 3')
        assert store['ul.li'] == 'Item 1'
        assert store['ul.li2'] == 'Item 2'
        assert store['ul.li3'] == 'Item 3'

    def test_get_item_returns_value(self):
        """Test get_item returns value."""
        store = TreeStore()
        store.set_item('name', 'Alice')
        assert store.get_item('name') == 'Alice'

    def test_get_item_with_default(self):
        """Test get_item returns default for missing path."""
        store = TreeStore()
        assert store.get_item('missing') is None
        assert store.get_item('missing', 'default') == 'default'

    def test_get_item_attribute_access(self):
        """Test get_item with ?attr syntax."""
        store = TreeStore()
        store.set_item('div', color='red')
        assert store.get_item('div?color') == 'red'

    def test_getitem_returns_value(self):
        """Test __getitem__ returns value."""
        store = TreeStore()
        store.set_item('name', 'Alice')
        assert store['name'] == 'Alice'

    def test_getitem_attribute_access(self):
        """Test __getitem__ with ?attr syntax."""
        store = TreeStore()
        store.set_item('div', color='red')
        assert store['div?color'] == 'red'

    def test_setitem_sets_value(self):
        """Test __setitem__ sets value with autocreate."""
        store = TreeStore()
        store['html.body.div'] = 'text'
        assert store['html.body.div'] == 'text'

    def test_setitem_sets_attribute(self):
        """Test __setitem__ sets attribute with ?attr syntax."""
        store = TreeStore()
        store.set_item('div')
        store['div?color'] = 'red'
        assert store['div?color'] == 'red'

    def test_get_node(self):
        """Test get_node returns TreeStoreNode."""
        store = TreeStore()
        store.set_item('div', color='red')
        node = store.get_node('div')
        assert isinstance(node, TreeStoreNode)
        assert node.label == 'div'
        assert node.attr['color'] == 'red'

    def test_get_attr(self):
        """Test get_attr on store."""
        store = TreeStore()
        store.set_item('div', color='red', size=10)
        assert store.get_attr('div', 'color') == 'red'
        assert store.get_attr('div', 'size') == 10
        assert store.get_attr('div') == {'color': 'red', 'size': 10}

    def test_set_attr(self):
        """Test set_attr on store."""
        store = TreeStore()
        store.set_item('div')
        store.set_attr('div', color='red', size=10)
        assert store['div?color'] == 'red'
        assert store['div?size'] == 10

    def test_del_item(self):
        """Test del_item removes node."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        node = store.del_item('a')
        assert node.label == 'a'
        assert 'a' not in store
        assert 'b' in store

    def test_pop(self):
        """Test pop removes and returns value."""
        store = TreeStore()
        store.set_item('name', 'Alice')
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
        store.set_item('a', 1)
        store.set_item('b', 2)
        nodes = list(store)
        assert len(nodes) == 2
        assert all(isinstance(n, TreeStoreNode) for n in nodes)

    def test_keys(self):
        """Test keys() returns labels."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.keys() == ['a', 'b']

    def test_values(self):
        """Test values() returns values."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.values() == [1, 2]

    def test_items(self):
        """Test items() returns (label, value) pairs."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.items() == [('a', 1), ('b', 2)]

    def test_nodes(self):
        """Test nodes() returns list of nodes."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        nodes = store.nodes()
        assert len(nodes) == 2
        assert all(isinstance(n, TreeStoreNode) for n in nodes)

    def test_get_nodes(self):
        """Test get_nodes at path."""
        store = TreeStore()
        store.set_item('div.span', 'text')
        store.set_item('div.p', 'para')
        nodes = store.get_nodes('div')
        assert len(nodes) == 2


class TestTreeStoreDigest:
    """Tests for digest functionality."""

    def test_digest_keys(self):
        """Test digest #k returns labels."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.digest('#k') == ['a', 'b']

    def test_digest_values(self):
        """Test digest #v returns values."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.digest('#v') == [1, 2]

    def test_digest_attributes(self):
        """Test digest #a returns all attributes."""
        store = TreeStore()
        store.set_item('a', 1, color='red')
        store.set_item('b', 2, color='blue')
        attrs = store.digest('#a')
        assert attrs[0]['color'] == 'red'
        assert attrs[1]['color'] == 'blue'

    def test_digest_specific_attribute(self):
        """Test digest #a.attrname returns specific attribute."""
        store = TreeStore()
        store.set_item('a', 1, color='red')
        store.set_item('b', 2, color='blue')
        assert store.digest('#a.color') == ['red', 'blue']

    def test_digest_multiple(self):
        """Test digest with multiple specifiers."""
        store = TreeStore()
        store.set_item('a', 1, color='red')
        store.set_item('b', 2, color='blue')
        result = store.digest('#k,#v,#a.color')
        assert result == [('a', 1, 'red'), ('b', 2, 'blue')]


class TestTreeStoreWalk:
    """Tests for walk functionality."""

    def test_walk_generator(self):
        """Test walk as generator."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        paths = [(p, n.value) for p, n in store.walk()]
        assert ('a', 1) in paths
        assert ('b', 2) in paths

    def test_walk_nested(self):
        """Test walk with nested structure."""
        store = TreeStore()
        store.set_item('div.span', 'text')
        paths = [p for p, _ in store.walk()]
        assert 'div' in paths
        assert 'div.span' in paths

    def test_walk_callback(self):
        """Test walk with callback."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        labels = []
        store.walk(lambda n: labels.append(n.label))
        assert labels == ['a', 'b']


class TestTreeStoreNavigation:
    """Tests for navigation properties."""

    def test_root_property(self):
        """Test root property."""
        store = TreeStore()
        div = store.set_item('div')
        span = div.set_item('span')
        assert store.root is store
        assert div.root is store
        assert span.root is store

    def test_depth_property(self):
        """Test depth property."""
        store = TreeStore()
        assert store.depth == 0
        div = store.set_item('div')
        assert div.depth == 1
        span = div.set_item('span')
        assert span.depth == 2

    def test_parent_node(self):
        """Test parent_node property."""
        store = TreeStore()
        div = store.set_item('div')
        assert store.parent_node is None
        assert div.parent_node is not None
        assert div.parent_node.label == 'div'


class TestTreeStorePathAccess:
    """Tests for path access with positional and attribute syntax."""

    def test_positional_access(self):
        """Test #N positional access."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        assert store['#0'] == 1
        assert store['#1'] == 2
        assert store['#2'] == 3

    def test_positional_negative(self):
        """Test negative positional access."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store['#-1'] == 2
        assert store['#-2'] == 1

    def test_positional_in_path(self):
        """Test positional access in dotted path."""
        store = TreeStore()
        store.set_item('div.span', 'text')
        assert store['#0.#0'] == 'text'

    def test_mixed_path_access(self):
        """Test mixed positional and label access."""
        store = TreeStore()
        store.set_item('div.span', 'text')
        assert store['div.#0'] == 'text'
        assert store['#0.span'] == 'text'

    def test_attribute_access_in_path(self):
        """Test ?attr in dotted path."""
        store = TreeStore()
        store.set_item('div.span', color='red')
        assert store['div.span?color'] == 'red'


class TestTreeStoreConversion:
    """Tests for conversion methods."""

    def test_as_dict_simple(self):
        """Test as_dict with simple values."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        assert store.as_dict() == {'a': 1, 'b': 2}

    def test_as_dict_nested(self):
        """Test as_dict with nested structure."""
        store = TreeStore()
        store.set_item('div.span', 'text')
        result = store.as_dict()
        assert 'div' in result
        assert result['div']['span'] == 'text'

    def test_as_dict_with_attributes(self):
        """Test as_dict preserves attributes."""
        store = TreeStore()
        store.set_item('item', 'value', color='red')
        result = store.as_dict()
        assert result['item']['_value'] == 'value'
        assert result['item']['color'] == 'red'

    def test_clear(self):
        """Test clear removes all nodes."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.clear()
        assert len(store) == 0


class TestTreeStoreUpdate:
    """Tests for TreeStore.update() method."""

    def test_update_simple_values(self):
        """Test update replaces simple values."""
        store = TreeStore({'a': 1, 'b': 2})
        store.update({'b': 3, 'c': 4})
        assert store['a'] == 1  # preserved
        assert store['b'] == 3  # updated
        assert store['c'] == 4  # added

    def test_update_recursive_branches(self):
        """Test update merges branches recursively."""
        store = TreeStore({
            'config': {
                'database': {'host': 'localhost', 'port': 5432},
                'cache': {'enabled': True},
            }
        })
        store.update({
            'config': {
                'database': {'port': 3306, 'user': 'admin'},
            }
        })

        # Original values preserved
        assert store['config.database.host'] == 'localhost'
        assert store['config.cache.enabled'] is True

        # Updated value
        assert store['config.database.port'] == 3306

        # New value added
        assert store['config.database.user'] == 'admin'

    def test_update_attributes(self):
        """Test update merges attributes."""
        store = TreeStore()
        store.set_item('item', 'value1', color='red', size=10)

        other = TreeStore()
        other.set_item('item', 'value2', color='blue', weight=5)

        store.update(other)

        assert store['item'] == 'value2'  # value updated
        assert store['item?color'] == 'blue'  # attr updated
        assert store['item?size'] == 10  # attr preserved
        assert store['item?weight'] == 5  # attr added

    def test_update_from_dict(self):
        """Test update accepts dict source."""
        store = TreeStore({'a': 1})
        store.update({'a': 2, 'b': 3})
        assert store['a'] == 2
        assert store['b'] == 3

    def test_update_from_list(self):
        """Test update accepts list of tuples."""
        store = TreeStore({'a': 1})
        store.update([('a', 2), ('b', 3, {'color': 'red'})])
        assert store['a'] == 2
        assert store['b'] == 3
        assert store['b?color'] == 'red'

    def test_update_from_treestore(self):
        """Test update accepts TreeStore."""
        store = TreeStore({'a': 1})
        other = TreeStore({'a': 2, 'b': 3})
        store.update(other)
        assert store['a'] == 2
        assert store['b'] == 3

    def test_update_ignore_none(self):
        """Test update with ignore_none=True."""
        store = TreeStore({'a': 1, 'b': 2})
        store.update({'a': None, 'b': 3}, ignore_none=True)
        assert store['a'] == 1  # None ignored
        assert store['b'] == 3  # updated

    def test_update_branch_replaces_leaf(self):
        """Test update replaces leaf with branch."""
        store = TreeStore({'config': 'simple'})
        store.update({'config': {'host': 'localhost'}})
        # Branch replaces the leaf value
        assert store['config.host'] == 'localhost'

    def test_update_leaf_replaces_branch(self):
        """Test update replaces branch with leaf."""
        store = TreeStore({'config': {'host': 'localhost'}})
        store.update({'config': 'simple'})
        assert store['config'] == 'simple'

    def test_update_invalid_type_raises(self):
        """Test update with invalid type raises TypeError."""
        store = TreeStore()
        with pytest.raises(TypeError, match="must be dict, list, or TreeStore"):
            store.update("invalid")


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
        assert builder.get_node('div_0').tag == 'div'
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
        assert builder.get_node('main').tag == 'div'

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
        """Test that invalid children are rejected on validate()."""
        class HtmlGrammar(Grammar):
            @property
            def list(self):
                return dict(tag='ul', valid_children={'li': '*'})

            @property
            def item(self):
                return dict(tag='li')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        ul = builder.ul()
        ul.li(value='item')  # OK
        ul.child('div')  # No error at insertion

        with pytest.raises(InvalidChildError, match="div.*not valid"):
            builder.validate()

    def test_max_children_enforcement(self):
        """Test max children count enforcement on validate()."""
        class LimitedGrammar(Grammar):
            @property
            def container(self):
                return dict(tag='container', valid_children={'item': '0-2'})

            @property
            def item(self):
                return dict(tag='item')

        builder = TreeStoreBuilder(grammar=LimitedGrammar)
        cont = builder.container()
        cont.item(value='first')
        cont.item(value='second')
        cont.item(value='third')  # No error at insertion

        with pytest.raises(TooManyChildrenError, match="at most 2"):
            builder.validate()

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

    def test_hierarchical_structure(self):
        """Test building hierarchical structure."""
        store = TreeStore()

        # Build with set_item
        store.set_item('config.database.host', 'localhost')
        store.set_item('config.database.port', 5432)
        store.set_item('config.cache.enabled', True)

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
            .set_item('html')
            .set_item('body')
            .set_item('div', id='main'))

        assert store['html.body.div?id'] == 'main'

        # Chain leaves (returns parent)
        ul = store.set_item('html.body.ul')
        ul.set_item('li1', 'A').set_item('li2', 'B').set_item('li3', 'C')

        assert store['html.body.ul.li1'] == 'A'
        assert store['html.body.ul.li2'] == 'B'
        assert store['html.body.ul.li3'] == 'C'


class TestPositionParameter:
    """Tests for _position parameter in set_item and child()."""

    def test_set_item_position_append_default(self):
        """Test set_item appends by default."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        assert store.keys() == ['a', 'b', 'c']

    def test_set_item_position_prepend(self):
        """Test set_item with _position='<' inserts at beginning."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('first', 0, _position='<')
        assert store.keys() == ['first', 'a', 'b']
        assert store['#0'] == 0
        assert store['#1'] == 1

    def test_set_item_position_before_label(self):
        """Test set_item with _position='<label' inserts before label."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='<b')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99
        assert store['#2'] == 2

    def test_set_item_position_after_label(self):
        """Test set_item with _position='>label' inserts after label."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='>a')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#0'] == 1
        assert store['#1'] == 99

    def test_set_item_position_before_index(self):
        """Test set_item with _position='<#N' inserts before position N."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='<#1')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_set_item_position_after_index(self):
        """Test set_item with _position='>#N' inserts after position N."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='>#0')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_set_item_position_at_index(self):
        """Test set_item with _position='#N' inserts at exact position N."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='#1')
        assert store.keys() == ['a', 'inserted', 'b', 'c']
        assert store['#1'] == 99

    def test_set_item_position_negative_index(self):
        """Test set_item with negative position index."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        store.set_item('inserted', 99, _position='<#-1')  # before last
        assert store.keys() == ['a', 'b', 'inserted', 'c']

    def test_set_item_position_branch(self):
        """Test _position works for branch nodes too."""
        store = TreeStore()
        store.set_item('first')
        store.set_item('last')
        store.set_item('middle', _position='<last')
        assert store.keys() == ['first', 'middle', 'last']

    def test_builder_child_position_prepend(self):
        """Test child() with _position='<' inserts at beginning."""
        builder = TreeStoreBuilder()
        builder.child('div')
        builder.child('div')
        builder.child('div', _position='<')
        assert builder.keys() == ['div_2', 'div_0', 'div_1']
        assert builder['#0?'] is None  # div_2 is first
        assert builder.get_node('#0').tag == 'div'

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
        store.set_item('container.a', 1)
        store.set_item('container.b', 2)
        store.set_item('container.c', 3)
        store.set_item('container.inserted', 99, _position='<b')
        container = store.get_node('container').value
        assert container.keys() == ['a', 'inserted', 'b', 'c']


# ==================== Grammar System Tests ====================

from genro_treestore import Grammar, element, InvalidParentError
from genro_treestore.treestore import _parse_cardinality_symbol


class TestParseCardinalitySymbol:
    """Tests for _parse_cardinality_symbol."""

    def test_star_zero_or_more(self):
        """Test '*' parses to (0, None)."""
        assert _parse_cardinality_symbol('*') == (0, None)

    def test_plus_one_or_more(self):
        """Test '+' parses to (1, None)."""
        assert _parse_cardinality_symbol('+') == (1, None)

    def test_question_zero_or_one(self):
        """Test '?' parses to (0, 1)."""
        assert _parse_cardinality_symbol('?') == (0, 1)

    def test_single_number(self):
        """Test single number parses to exact count."""
        assert _parse_cardinality_symbol('1') == (1, 1)
        assert _parse_cardinality_symbol('3') == (3, 3)

    def test_range_with_dash(self):
        """Test range with dash notation."""
        assert _parse_cardinality_symbol('1-3') == (1, 3)
        assert _parse_cardinality_symbol('0-5') == (0, 5)

    def test_range_with_colon(self):
        """Test range with colon notation."""
        assert _parse_cardinality_symbol('1:3') == (1, 3)
        assert _parse_cardinality_symbol('0:') == (0, None)
        assert _parse_cardinality_symbol('1:') == (1, None)


class TestGrammarBasic:
    """Tests for Grammar class."""

    def test_grammar_from_property(self):
        """Test grammar defined via property."""
        class SimpleGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div,span')

        grammar = SimpleGrammar()
        assert 'div' in grammar.get_all_tags()
        assert 'span' in grammar.get_all_tags()

    def test_grammar_from_element_decorator(self):
        """Test grammar defined via @element decorator."""
        class SimpleGrammar(Grammar):
            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, **attr):
                return node

        grammar = SimpleGrammar()
        assert 'ul' in grammar.get_all_tags()
        assert 'ol' in grammar.get_all_tags()

        config = grammar.get_config('ul')
        assert config is not None
        assert config['valid_children'] == {'li': (1, None)}

    def test_grammar_method_name_as_default_tag(self):
        """Test @element uses method name as default tag."""
        class SimpleGrammar(Grammar):
            @element(valid_children={'span': '*'})
            def div(self, node, **attr):
                return node

        grammar = SimpleGrammar()
        assert 'div' in grammar.get_all_tags()

    def test_grammar_valid_children_string(self):
        """Test valid_children as comma-separated string."""
        class SimpleGrammar(Grammar):
            @property
            def container(self):
                return dict(tag='div', valid_children='span,p,a')

        grammar = SimpleGrammar()
        config = grammar.get_config('div')
        assert config['valid_children'] == {
            'span': (0, None),
            'p': (0, None),
            'a': (0, None),
        }

    def test_grammar_get_method(self):
        """Test getting custom method from grammar."""
        class SimpleGrammar(Grammar):
            @element(tag='ul')
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.child('li', value=item)
                return node

        grammar = SimpleGrammar()
        method = grammar.get_method('ul')
        assert method is not None
        assert callable(method)


class TestBuilderWithGrammar:
    """Tests for TreeStoreBuilder with grammar parameter."""

    def test_builder_with_grammar_class(self):
        """Test passing Grammar class to TreeStoreBuilder."""
        class HtmlGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div,section')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        assert builder.grammar is not None

    def test_builder_with_grammar_instance(self):
        """Test passing Grammar instance to TreeStoreBuilder."""
        class HtmlGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div')

        grammar = HtmlGrammar()
        builder = TreeStoreBuilder(grammar=grammar)
        assert builder.grammar is grammar

    def test_dynamic_tag_method(self):
        """Test dynamic tag access via __getattr__."""
        class HtmlGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div,span')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        div = builder.div(id='main')
        assert builder['div_0?id'] == 'main'
        assert builder.get_node('div_0').tag == 'div'

    def test_dynamic_tag_method_with_value(self):
        """Test dynamic tag method creating leaf node."""
        class HtmlGrammar(Grammar):
            @property
            def inline(self):
                return dict(tag='span')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        builder.span(value='Hello')
        assert builder['span_0'] == 'Hello'

    def test_grammar_propagates_to_children(self):
        """Test grammar is passed to child builders."""
        class HtmlGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div,span')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        div = builder.div()
        assert div.grammar is builder.grammar

        # Child can also use dynamic tags
        span = div.span()
        assert builder['div_0.span_0'] is span

    def test_real_methods_take_precedence(self):
        """Test that real TreeStore methods take precedence over grammar tags."""
        class BadGrammar(Grammar):
            @property
            def collisions(self):
                return dict(tag='keys,values,items')

        builder = TreeStoreBuilder(grammar=BadGrammar)
        # keys() should return list, not create a tag
        assert builder.keys() == []

        # Access via child() still works
        builder.child('keys', value='test')
        assert builder['keys_0'] == 'test'

    def test_attribute_error_for_unknown_tag(self):
        """Test AttributeError for undefined tags."""
        class HtmlGrammar(Grammar):
            @property
            def block(self):
                return dict(tag='div')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        with pytest.raises(AttributeError):
            builder.unknown_tag()


class TestGrammarValidation:
    """Tests for grammar-based validation via validate() method."""

    def test_valid_children_from_grammar(self):
        """Test valid_children validation using grammar."""
        class HtmlGrammar(Grammar):
            @property
            def list(self):
                return dict(tag='ul', valid_children={'li': '*'})

            @property
            def list_item(self):
                return dict(tag='li')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        ul = builder.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')

        # Validation passes
        builder.validate()

        assert builder['ul_0.li_0'] == 'Item 1'
        assert builder['ul_0.li_1'] == 'Item 2'

    def test_valid_children_rejects_invalid_tag(self):
        """Test valid_children rejects invalid child tags on validate()."""
        class HtmlGrammar(Grammar):
            @property
            def list(self):
                return dict(tag='ul', valid_children={'li': '*'})

            @property
            def block(self):
                return dict(tag='div')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        ul = builder.ul()
        ul.div()  # No error at insertion time

        # Error raised at validation time
        with pytest.raises(InvalidChildError):
            builder.validate()

    def test_valid_children_cardinality_max(self):
        """Test valid_children max cardinality on validate()."""
        class HtmlGrammar(Grammar):
            @property
            def document(self):
                return dict(tag='html', valid_children={'head': '?', 'body': '1'})

            @property
            def parts(self):
                return dict(tag='head,body')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        html = builder.html()
        html.head()
        html.head()  # No error at insertion time

        # Error raised at validation time (too many head elements)
        with pytest.raises(TooManyChildrenError):
            builder.validate()

    def test_valid_children_cardinality_min(self):
        """Test valid_children min cardinality on validate()."""
        class HtmlGrammar(Grammar):
            @property
            def document(self):
                return dict(tag='html', valid_children={'body': '+'})

            @property
            def parts(self):
                return dict(tag='body')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        builder.html()  # html with no body

        # Error raised at validation time (missing body)
        with pytest.raises(MissingChildError):
            builder.validate()

    def test_valid_parent_constraint(self):
        """Test valid_parent validation on validate()."""
        class HtmlGrammar(Grammar):
            @property
            def list(self):
                return dict(tag='ul,ol')

            @property
            def list_item(self):
                return dict(tag='li', valid_parent='ul,ol')

            @property
            def block(self):
                return dict(tag='div')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)

        # li under ul is valid
        ul = builder.ul()
        ul.li(value='OK')

        # li under div - no error at insertion time
        div = builder.div()
        div.li(value='Error')

        # Error raised at validation time
        with pytest.raises(InvalidParentError):
            builder.validate()

    def test_validate_without_grammar_raises(self):
        """Test validate() raises if no grammar defined."""
        builder = TreeStoreBuilder()
        builder.child('div')

        with pytest.raises(ValueError, match="no grammar defined"):
            builder.validate()

    def test_validate_passes_for_valid_tree(self):
        """Test validate() passes silently for valid tree."""
        class HtmlGrammar(Grammar):
            @property
            def document(self):
                return dict(tag='html', valid_children={'head': '?', 'body': '1'})

            @property
            def head(self):
                return dict(tag='head', valid_children={'title': '1'})

            @property
            def body(self):
                return dict(tag='body', valid_children={'div': '*'})

            @property
            def parts(self):
                return dict(tag='title,div')

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        html = builder.html()
        head = html.head()
        head.title(value='Page')
        body = html.body()
        body.div()
        body.div()

        # Should not raise
        builder.validate()


class TestElementDecoratorWithLogic:
    """Tests for @element decorator with custom logic."""

    def test_element_with_custom_method(self):
        """Test @element decorator with custom initialization logic."""
        class HtmlGrammar(Grammar):
            @property
            def list_item(self):
                return dict(tag='li')

            @element(tag='ul', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        builder.ul(items=['A', 'B', 'C'])

        assert builder['ul_0.li_0'] == 'A'
        assert builder['ul_0.li_1'] == 'B'
        assert builder['ul_0.li_2'] == 'C'

    def test_element_aliases(self):
        """Test @element with multiple tags (aliases)."""
        class HtmlGrammar(Grammar):
            @property
            def list_item(self):
                return dict(tag='li')

            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node

        builder = TreeStoreBuilder(grammar=HtmlGrammar)

        # Both ul and ol share the same behavior
        builder.ul(items=['A', 'B'])
        builder.ol(items=['1', '2'])

        assert builder['ul_0.li_0'] == 'A'
        assert builder['ol_0.li_0'] == '1'


class TestGrammarWithGroups:
    """Tests for grammar groups referencing other groups."""

    def test_group_reference_in_valid_children(self):
        """Test referencing a group in valid_children using string name."""
        class HtmlGrammar(Grammar):
            @property
            def inline(self):
                return dict(tag='span,a,em,strong')

            @property
            def block(self):
                return dict(
                    tag='div,p',
                    valid_children={'inline': '*'},  # group name as string
                )

        grammar = HtmlGrammar()

        # Group name is stored as-is
        config = grammar.get_config('div')
        assert 'inline' in config['valid_children']

        # Expansion happens at validate() time
        expanded = grammar.expand_name('inline')
        assert 'span' in expanded
        assert 'a' in expanded
        assert 'em' in expanded
        assert 'strong' in expanded

    def test_group_reference_in_valid_parent(self):
        """Test referencing a group in valid_parent using string."""
        class HtmlGrammar(Grammar):
            @property
            def list(self):
                return dict(tag='ul,ol')

            @property
            def list_item(self):
                return dict(
                    tag='li',
                    valid_parent='ul,ol',  # direct tag list
                )

        grammar = HtmlGrammar()

        config = grammar.get_config('li')
        assert 'ul' in config['valid_parent']
        assert 'ol' in config['valid_parent']

    def test_validation_with_group_expansion(self):
        """Test that validation correctly expands group names."""
        class HtmlGrammar(Grammar):
            @property
            def inline(self):
                return dict(tag='span,a,em')

            @property
            def block(self):
                return dict(
                    tag='div',
                    valid_children={'inline': '*'},  # group name
                )

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        div = builder.div()
        div.span(value='text')
        div.a(value='link')
        div.em(value='emphasis')

        # Should pass - all inline elements are valid
        builder.validate()

        # Add invalid child
        div.child('p')

        # Should fail - p is not in 'inline' group
        with pytest.raises(InvalidChildError):
            builder.validate()

    def test_combined_groups_in_valid_children(self):
        """Test combining multiple groups with comma: 'inline,block'."""
        class HtmlGrammar(Grammar):
            @property
            def inline(self):
                return dict(tag='span,em')

            @property
            def block(self):
                return dict(tag='div,p')

            @property
            def container(self):
                return dict(
                    tag='section',
                    valid_children={'inline,block': '*'},  # combined groups
                )

        builder = TreeStoreBuilder(grammar=HtmlGrammar)
        section = builder.section()
        section.span(value='inline')
        section.div()  # block element

        # All should be valid
        builder.validate()
