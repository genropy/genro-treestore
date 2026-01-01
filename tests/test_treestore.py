# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for TreeStore, TreeStoreNode, and Builders."""

import pytest

from genro_treestore import (
    TreeStore,
    TreeStoreNode,
    BuilderBase,
    HtmlBuilder,
)


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
        """Test node creation with tag parameter."""
        node = TreeStoreNode('item', tag='div')
        assert node.label == 'item'
        assert node.tag == 'div'

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


# ==================== Builder Tests ====================


class TestHtmlBuilder:
    """Tests for HtmlBuilder."""

    def test_create_store_with_builder(self):
        """Test creating TreeStore with HtmlBuilder."""
        store = TreeStore(builder=HtmlBuilder())
        assert store.builder is not None
        assert isinstance(store.builder, HtmlBuilder)

    def test_html_builder_creates_div(self):
        """Test HtmlBuilder creates div element."""
        store = TreeStore(builder=HtmlBuilder())
        div = store.div(id='main')
        assert isinstance(div, TreeStore)
        assert 'div_0' in store
        node = store.get_node('div_0')
        assert node.tag == 'div'
        assert node.attr['id'] == 'main'

    def test_html_builder_creates_nested_elements(self):
        """Test HtmlBuilder creates nested structure."""
        store = TreeStore(builder=HtmlBuilder())
        div = store.div(id='container')
        div.span(value='Hello')
        div.span(value='World')

        assert store['div_0.span_0'] == 'Hello'
        assert store['div_0.span_1'] == 'World'

    def test_html_builder_void_elements(self):
        """Test void elements (meta, br, img) get empty string value."""
        store = TreeStore(builder=HtmlBuilder())
        store.meta(charset='utf-8')
        store.br()
        store.img(src='image.png')

        meta_node = store.get_node('meta_0')
        assert meta_node.value == ''
        assert meta_node.tag == 'meta'
        assert meta_node.attr['charset'] == 'utf-8'

        br_node = store.get_node('br_0')
        assert br_node.value == ''

    def test_html_builder_table_structure(self):
        """Test building table with HtmlBuilder."""
        store = TreeStore(builder=HtmlBuilder())
        table = store.table()
        thead = table.thead()
        tr = thead.tr()
        tr.th(value='Name')
        tr.th(value='Age')

        tbody = table.tbody()
        row = tbody.tr()
        row.td(value='Alice')
        row.td(value='30')

        assert store['table_0.thead_0.tr_0.th_0'] == 'Name'
        assert store['table_0.tbody_0.tr_0.td_0'] == 'Alice'

    def test_html_builder_invalid_tag_raises(self):
        """Test invalid tag raises AttributeError."""
        store = TreeStore(builder=HtmlBuilder())
        with pytest.raises(AttributeError):
            store.invalidtag()

    def test_html_builder_all_flow_content_tags(self):
        """Test common flow content tags work."""
        store = TreeStore(builder=HtmlBuilder())
        store.div()
        store.p()
        store.article()
        store.section()
        store.header()
        store.footer()
        store.nav()
        store.aside()

        assert len(store) == 8

    def test_html_builder_list_elements(self):
        """Test list elements ul, ol, li."""
        store = TreeStore(builder=HtmlBuilder())
        ul = store.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')
        ul.li(value='Item 3')

        assert store['ul_0.li_0'] == 'Item 1'
        assert store['ul_0.li_1'] == 'Item 2'
        assert store['ul_0.li_2'] == 'Item 3'

    def test_html_builder_headings(self):
        """Test heading elements h1-h6."""
        store = TreeStore(builder=HtmlBuilder())
        store.h1(value='Title')
        store.h2(value='Subtitle')
        store.h3(value='Section')

        assert store['h1_0'] == 'Title'
        assert store['h2_0'] == 'Subtitle'
        assert store['h3_0'] == 'Section'


class TestBuilderInheritance:
    """Tests for builder inheritance to child stores."""

    def test_child_inherits_builder(self):
        """Test child TreeStore inherits builder from parent."""
        store = TreeStore(builder=HtmlBuilder())
        div = store.div()

        # Child store should have the same builder
        assert div.builder is store.builder

    def test_nested_children_inherit_builder(self):
        """Test deeply nested children inherit builder."""
        store = TreeStore(builder=HtmlBuilder())
        div = store.div()
        span = div.span()
        a = span.a()

        assert a.builder is store.builder


class TestBuilderBase:
    """Tests for BuilderBase abstract class."""

    def test_custom_builder(self):
        """Test creating custom builder subclass."""
        class MyBuilder(BuilderBase):
            def custom_tag(self, target, tag, value=None, **attr):
                return self.child(target, tag, value=value, **attr)

        store = TreeStore(builder=MyBuilder())
        store.custom_tag(value='test', data='123')

        node = store.get_node('custom_tag_0')
        assert node.tag == 'custom_tag'
        assert node.value == 'test'
        assert node.attr['data'] == '123'


class TestPositionParameter:
    """Tests for _position parameter in set_item."""

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

    def test_position_with_path(self):
        """Test _position works with nested paths."""
        store = TreeStore()
        store.set_item('container.a', 1)
        store.set_item('container.b', 2)
        store.set_item('container.c', 3)
        store.set_item('container.inserted', 99, _position='<b')
        container = store.get_node('container').value
        assert container.keys() == ['a', 'inserted', 'b', 'c']


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

    def test_builder_html_page(self):
        """Test building HTML page structure with HtmlBuilder."""
        store = TreeStore(builder=HtmlBuilder())

        # Create structure
        html = store.div(id='page')

        head = html.div(id='header')
        head.h1(value='My Page')

        body = html.div(id='content')
        ul = body.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')
        ul.li(value='Item 3')

        # Verify structure
        assert store['div_0.div_0.h1_0'] == 'My Page'
        assert store['div_0.div_0?id'] == 'header'
        assert store['div_0.div_1.ul_0.li_0'] == 'Item 1'
        assert store['div_0.div_1.ul_0.li_2'] == 'Item 3'

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


class TestTreeStoreCoreEdgeCases:
    """Tests for edge cases in core.py to achieve 100% coverage."""

    def test_repr(self):
        """Test __repr__ method."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        repr_str = repr(store)
        assert "TreeStore" in repr_str
        assert "'a'" in repr_str
        assert "'b'" in repr_str

    def test_getattr_private_attribute_raises(self):
        """Test __getattr__ raises for underscore attributes."""
        store = TreeStore()
        with pytest.raises(AttributeError, match="no attribute '_private'"):
            _ = store._private

    def test_getattr_no_builder_raises(self):
        """Test __getattr__ raises when no builder and unknown attribute."""
        store = TreeStore()  # No builder
        with pytest.raises(AttributeError, match="no attribute 'unknown'"):
            _ = store.unknown

    def test_get_node_by_position_out_of_range(self):
        """Test _get_node_by_position raises for out of range index."""
        store = TreeStore()
        store.set_item('a', 1)
        with pytest.raises(KeyError, match="Position #5 out of range"):
            store['#5']

    def test_get_node_empty_path_raises(self):
        """Test get_node raises for empty path."""
        store = TreeStore()
        with pytest.raises(KeyError, match="Empty path"):
            store.get_node('')

    def test_insert_node_unknown_position_appends(self):
        """Test _insert_node with unknown position falls back to append."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        # Unknown position format should append
        store.set_item('c', 3, _position='unknown_format')
        assert store.keys() == ['a', 'b', 'c']

    def test_insert_node_negative_position_after(self):
        """Test _insert_node with >#-N negative position."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        # Insert after position -2 (which is 'b')
        store.set_item('inserted', 99, _position='>#-2')
        # Position -2 in [a,b,c] is 'b' (index 1), so after index 1 means index 2
        assert 'inserted' in store.keys()

    def test_insert_node_negative_position_exact(self):
        """Test _insert_node with #-N negative position."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)
        # Insert at negative position
        store.set_item('inserted', 99, _position='#-1')
        assert 'inserted' in store.keys()

    def test_htraverse_empty_path(self):
        """Test _htraverse with empty path returns self."""
        store = TreeStore()
        parent, label = store._htraverse('')
        assert parent is store
        assert label == ''

    def test_htraverse_autocreate_positional_raises(self):
        """Test _htraverse with autocreate and positional raises."""
        store = TreeStore()
        with pytest.raises(KeyError, match="Cannot autocreate with positional"):
            store._htraverse('#0.child', autocreate=True)

    def test_htraverse_leaf_in_path_raises(self):
        """Test _htraverse raises when encountering leaf in middle of path."""
        store = TreeStore()
        store.set_item('leaf', 'value')  # This is a leaf
        with pytest.raises(KeyError, match="is a leaf"):
            store['leaf.child']

    def test_htraverse_leaf_to_branch_autocreate(self):
        """Test _htraverse converts leaf to branch when autocreating."""
        store = TreeStore()
        store.set_item('node', 'value')  # Start as leaf
        # Now set a child path - should convert to branch
        store.set_item('node.child', 'child_value')
        assert store['node.child'] == 'child_value'

    def test_get_attr_missing_path_returns_default(self):
        """Test get_attr returns default for missing path."""
        store = TreeStore()
        assert store.get_attr('missing', 'attr') is None
        assert store.get_attr('missing', 'attr', 'default') == 'default'

    def test_del_item_with_path(self):
        """Test del_item with dotted path."""
        store = TreeStore()
        store.set_item('parent.child', 'value')
        node = store.del_item('parent.child')
        assert node.label == 'child'
        assert 'child' not in store.get_node('parent').value

    def test_get_nodes_empty_path(self):
        """Test get_nodes with empty path returns root nodes."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b', 2)
        nodes = store.get_nodes('')
        assert len(nodes) == 2

    def test_get_nodes_leaf_returns_empty(self):
        """Test get_nodes on leaf node returns empty list."""
        store = TreeStore()
        store.set_item('leaf', 'value')
        nodes = store.get_nodes('leaf')
        assert nodes == []

    def test_iter_digest_unknown_specifier_raises(self):
        """Test iter_digest raises for unknown specifier."""
        store = TreeStore()
        store.set_item('a', 1)
        with pytest.raises(ValueError, match="Unknown digest specifier"):
            list(store.iter_digest('#unknown'))

    def test_as_dict_branch_with_attributes(self):
        """Test as_dict with branch node that has attributes."""
        store = TreeStore()
        store.set_item('parent', color='red')  # Branch with attribute
        parent = store.get_node('parent').value
        parent.set_item('child', 'value')

        result = store.as_dict()
        assert 'parent' in result
        assert result['parent']['color'] == 'red'
        assert result['parent']['child'] == 'value'

    def test_get_method(self):
        """Test get() method for direct children lookup."""
        store = TreeStore()
        store.set_item('existing', 'value')

        node = store.get('existing')
        assert node is not None
        assert node.value == 'value'

        missing = store.get('missing')
        assert missing is None

        default = store.get('missing', 'default')
        assert default == 'default'

    def test_update_add_branch_from_other(self):
        """Test update adds new branch from other TreeStore."""
        store = TreeStore({'a': 1})
        other = TreeStore({'b': {'c': 2, 'd': 3}})
        store.update(other)
        assert store['a'] == 1
        assert store['b.c'] == 2
        assert store['b.d'] == 3


class TestTreeStoreXml:
    """Tests for XML serialization in core.py."""

    def test_from_xml_simple(self):
        """Test from_xml with simple XML."""
        xml = '<root><item>value</item></root>'
        store = TreeStore.from_xml(xml)
        assert store['root_0.item_0'] == 'value'

    def test_from_xml_with_attributes(self):
        """Test from_xml preserves XML attributes."""
        xml = '<div class="container"><span id="x">text</span></div>'
        store = TreeStore.from_xml(xml)
        assert store['div_0.span_0'] == 'text'
        assert store['div_0.span_0?id'] == 'x'

    def test_from_xml_with_namespace(self):
        """Test from_xml handles namespaces."""
        xml = '''<root xmlns:ns="http://example.com">
            <ns:item>value</ns:item>
        </root>'''
        store = TreeStore.from_xml(xml)
        # Namespace prefix should be in _tag attribute
        node = store.get_node('root_0.item_0')
        assert node.attr.get('_tag') == 'ns:item'

    def test_from_xml_empty_element(self):
        """Test from_xml with empty element."""
        xml = '<root><empty></empty></root>'
        store = TreeStore.from_xml(xml)
        assert store['root_0.empty_0'] == ''

    def test_from_xml_multiple_same_tags(self):
        """Test from_xml with multiple elements of same tag."""
        xml = '<root><item>first</item><item>second</item></root>'
        store = TreeStore.from_xml(xml)
        assert store['root_0.item_0'] == 'first'
        assert store['root_0.item_1'] == 'second'

    def test_to_xml_simple(self):
        """Test to_xml with simple structure."""
        store = TreeStore()
        store.set_item('item', 'value')
        xml = store.to_xml()
        assert '<item>value</item>' in xml

    def test_to_xml_empty_store(self):
        """Test to_xml with empty store."""
        store = TreeStore()
        xml = store.to_xml()
        assert xml == '<root/>'

    def test_to_xml_empty_store_with_root_tag(self):
        """Test to_xml with empty store and custom root tag."""
        store = TreeStore()
        xml = store.to_xml(root_tag='items')
        assert xml == '<items/>'

    def test_to_xml_single_leaf_node(self):
        """Test to_xml with single leaf node (no root wrapper needed)."""
        store = TreeStore()
        store.set_item('item', 'value')
        xml = store.to_xml()
        assert '<item>value</item>' in xml

    def test_to_xml_single_branch_node(self):
        """Test to_xml with single branch node."""
        store = TreeStore()
        store.set_item('parent.child', 'value')
        xml = store.to_xml()
        assert '<parent>' in xml
        assert '<child>value</child>' in xml

    def test_to_xml_multiple_root_nodes(self):
        """Test to_xml with multiple root nodes wraps in root."""
        store = TreeStore()
        store.set_item('item1', 'first')
        store.set_item('item2', 'second')
        xml = store.to_xml()
        assert '<root>' in xml
        assert '<item1>first</item1>' in xml
        assert '<item2>second</item2>' in xml

    def test_to_xml_with_attributes(self):
        """Test to_xml preserves attributes."""
        store = TreeStore()
        store.set_item('div', color='red')
        div = store.get_node('div').value
        div.set_item('span', 'text')
        xml = store.to_xml()
        assert 'color="red"' in xml
        assert '<span>text</span>' in xml

    def test_to_xml_with_root_tag(self):
        """Test to_xml with explicit root_tag."""
        store = TreeStore()
        store.set_item('item', 'value')
        xml = store.to_xml(root_tag='items')
        assert '<items>' in xml
        assert '</items>' in xml

    def test_to_xml_with_tag_attribute(self):
        """Test to_xml uses _tag attribute for element name."""
        store = TreeStore()
        store.set_item('item_0', 'value', _tag='custom')
        xml = store.to_xml()
        assert '<custom>value</custom>' in xml

    def test_to_xml_empty_value(self):
        """Test to_xml with empty string value."""
        store = TreeStore()
        store.set_item('empty', '')
        xml = store.to_xml()
        assert '<empty' in xml

    def test_to_xml_none_value(self):
        """Test to_xml with None value (branch node)."""
        store = TreeStore()
        store.set_item('parent')  # None value = branch
        xml = store.to_xml()
        assert '<parent' in xml

    def test_xml_roundtrip(self):
        """Test XML roundtrip preserves structure."""
        original = TreeStore()
        original.set_item('root.child1', 'value1', attr='a')
        original.set_item('root.child2', 'value2', attr='b')

        xml = original.to_xml()
        restored = TreeStore.from_xml(xml)

        # Check structure preserved (labels have _0 suffix from from_xml)
        assert 'root_0' in restored
        assert restored['root_0.child1_0'] == 'value1'
        assert restored['root_0.child2_0'] == 'value2'


class TestTreeStoreValidation:
    """Tests for validation methods to complete coverage."""

    def test_is_valid_empty_store(self):
        """Test is_valid on empty store returns True."""
        store = TreeStore()
        assert store.is_valid is True

    def test_validation_errors_empty_store(self):
        """Test validation_errors on empty store returns empty dict."""
        store = TreeStore()
        assert store.validation_errors() == {}

    def test_flattened_empty_walk(self):
        """Test flattened handles empty walk result."""
        store = TreeStore()
        # Empty store should yield nothing
        result = list(store.flattened())
        assert result == []


class TestTreeStoreCoreAdditionalCoverage:
    """Additional tests for remaining uncovered lines in core.py."""

    def test_contains_with_path(self):
        """Test __contains__ with dotted path returns False for missing."""
        store = TreeStore()
        store.set_item('a.b', 1)
        assert 'a.b' in store
        assert 'a.b.c' not in store  # This path doesn't exist

    def test_index_of_not_found(self):
        """Test _index_of raises KeyError when label not found."""
        store = TreeStore()
        store.set_item('a', 1)
        with pytest.raises(KeyError, match="Label 'nonexistent' not found"):
            store._index_of('nonexistent')

    def test_htraverse_positional_not_found_no_autocreate(self):
        """Test _htraverse raises KeyError for positional not found without autocreate."""
        store = TreeStore()
        with pytest.raises(KeyError):
            store._htraverse('#0.child', autocreate=False)

    def test_htraverse_path_segment_not_found(self):
        """Test _htraverse raises KeyError for missing path segment."""
        store = TreeStore()
        store.set_item('a', 1)
        with pytest.raises(KeyError, match="Path segment 'b' not found"):
            store._htraverse('b.c', autocreate=False)

    def test_set_item_update_existing_branch_no_value(self):
        """Test set_item updates existing branch node attributes without changing value."""
        store = TreeStore()
        store.set_item('branch', color='red')
        # Update attributes on existing branch
        result = store.set_item('branch', color='blue', size=10)
        assert store['branch?color'] == 'blue'
        assert store['branch?size'] == 10
        # Should return the branch store
        assert isinstance(result, TreeStore)

    def test_set_item_update_existing_branch_with_value(self):
        """Test set_item updates existing branch node value."""
        store = TreeStore()
        store.set_item('branch')  # Create branch
        branch = store.get_node('branch').value
        branch.set_item('child', 'value')
        # Now update the branch with a new value - this replaces the branch
        store.set_item('branch', 'new_value')
        assert store['branch'] == 'new_value'

    def test_walk_with_nested_callback(self):
        """Test walk with callback on nested structure."""
        store = TreeStore()
        store.set_item('parent.child1', 1)
        store.set_item('parent.child2', 2)

        visited = []
        store.walk(lambda n: visited.append(n.label))
        assert 'parent' in visited
        assert 'child1' in visited
        assert 'child2' in visited

    def test_from_xml_namespace_without_declared_prefix(self):
        """Test from_xml with namespace URI that has no declared prefix."""
        # This XML has a namespace URI but no prefix declaration for it
        xml = '''<root xmlns="http://default.ns">
            <item>value</item>
        </root>'''
        store = TreeStore.from_xml(xml)
        # Should still parse, local name extracted
        assert 'root_0' in store

    def test_to_xml_branch_with_attributes(self):
        """Test to_xml with branch node that has attributes."""
        store = TreeStore()
        store.set_item('parent', color='red')
        parent = store.get_node('parent').value
        parent.set_item('child', 'value')

        xml = store.to_xml()
        assert 'color="red"' in xml
        assert '<child>value</child>' in xml

    def test_to_xml_single_leaf_with_attributes(self):
        """Test to_xml with single leaf node with attributes."""
        store = TreeStore()
        store.set_item('item', 'value', color='red', size='10')
        xml = store.to_xml()
        assert '<item' in xml
        assert 'color="red"' in xml
        assert 'size="10"' in xml
        assert '>value</item>' in xml

    def test_walk_callback_returns_none(self):
        """Test that walk with callback returns None."""
        store = TreeStore()
        store.set_item('a', 1)
        result = store.walk(lambda n: None)
        assert result is None

    def test_flattened_with_callback_walk_none(self):
        """Test flattened when walk returns generator (not None)."""
        store = TreeStore()
        store.set_item('a', 1)
        store.set_item('b.c', 2)
        result = list(store.flattened())
        assert len(result) == 3  # a, b, b.c

    def test_is_valid_with_nested_nodes(self):
        """Test is_valid iterates through nested nodes."""
        store = TreeStore()
        store.set_item('parent.child1', 1)
        store.set_item('parent.child2', 2)
        # Without builder, all nodes are valid
        assert store.is_valid is True

    def test_validation_errors_with_nested_nodes(self):
        """Test validation_errors iterates through nested nodes."""
        store = TreeStore()
        store.set_item('parent.child1', 1)
        store.set_item('parent.child2', 2)
        # Without builder/validator, no errors
        errors = store.validation_errors()
        assert errors == {}
