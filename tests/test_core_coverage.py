# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Additional tests to achieve 100% coverage on core modules."""

import pytest
from genro_treestore import TreeStore, TreeStoreNode
from genro_treestore.store.loading import load_from_dict


class TestLoadingCoverage:
    """Tests for loading.py edge cases."""

    def test_load_from_dict_root_underscore_keys_skipped(self):
        """Test that root-level keys starting with _ are skipped."""
        store = TreeStore()
        # _attr at root level should be skipped
        load_from_dict(store, {
            '_should_skip': 'ignored',
            '_also_skip': 123,
            'valid_key': 'kept'
        })
        # Only valid_key should be present
        assert 'valid_key' in store
        assert len(store) == 1
        assert store['valid_key'] == 'kept'


class TestNodeCoverage:
    """Tests for node.py edge cases."""

    def test_node_set_value_no_change(self):
        """Test set_value when value doesn't change."""
        store = TreeStore()
        store.set_item('item', 'value')
        node = store.get_node('item')

        # Calling set_value with same value should do nothing
        node.set_value('value')
        assert node.value == 'value'

    def test_node_set_value_triggers_parent(self):
        """Test set_value triggers parent notification."""
        store = TreeStore()
        store.set_item('item', 'old_value')
        node = store.get_node('item')

        events = []
        store.subscribe('test', any=lambda node, path, evt, **kw: events.append((path, evt)))

        node.set_value('new_value')

        assert ('item', 'upd_value') in events

    def test_node_set_value_with_node_subscriber(self):
        """Test set_value triggers node-level subscriber."""
        store = TreeStore()
        store.set_item('item', 'old_value')
        node = store.get_node('item')

        events = []
        node.subscribe('watcher', lambda **kw: events.append(kw))

        node.set_value('new_value')

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_value'
        assert events[0]['info'] == 'old_value'

    def test_node_set_attr_with_node_subscriber(self):
        """Test set_attr triggers node-level subscriber."""
        store = TreeStore()
        store.set_item('item', 'value', color='red')
        node = store.get_node('item')

        events = []
        node.subscribe('watcher', lambda **kw: events.append(kw))

        node.set_attr(size=10)

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_attr'

    def test_node_set_attr_without_trigger(self):
        """Test set_attr with trigger=False doesn't fire events."""
        store = TreeStore()
        store.set_item('item', 'value')
        node = store.get_node('item')

        events = []
        store.subscribe('test', any=lambda node, path, evt, **kw: events.append(evt))

        node.set_attr(color='red', trigger=False)

        # No events should be triggered
        assert 'upd_attr' not in events


class TestSubscriptionCoverage:
    """Tests for subscription.py edge cases."""

    def test_subscribe_unsubscribe_insert(self):
        """Test subscribe/unsubscribe for insert event."""
        store = TreeStore()
        events = []

        store.subscribe('test', insert=lambda node, path, evt, **kw: events.append(evt))
        store.set_item('a', 1)
        assert 'ins' in events

        events.clear()
        store.unsubscribe('test', insert=True)
        store.set_item('b', 2)
        assert 'ins' not in events

    def test_subscribe_unsubscribe_delete(self):
        """Test subscribe/unsubscribe for delete event."""
        store = TreeStore()
        store.set_item('a', 1)
        events = []

        store.subscribe('test', delete=lambda node, path, evt, **kw: events.append(evt))
        store.del_item('a')
        assert 'del' in events

        events.clear()
        store.set_item('b', 2)
        store.unsubscribe('test', delete=True)
        store.del_item('b')
        assert 'del' not in events

    def test_subscribe_unsubscribe_update(self):
        """Test subscribe/unsubscribe for update event."""
        store = TreeStore()
        store.set_item('a', 1)
        events = []

        store.subscribe('test', update=lambda node, path, evt, **kw: events.append(evt))
        store.set_item('a', 2)
        assert 'upd_value' in events

        events.clear()
        store.unsubscribe('test', update=True)
        store.set_item('a', 3)
        assert 'upd_value' not in events


class TestValidationCoverage:
    """Tests for validation.py edge cases."""

    def test_validation_subscriber_node_without_tag(self):
        """Test validation skips nodes without tag."""
        from genro_treestore.validation import ValidationSubscriber

        store = TreeStore()
        # Create validator manually
        validator = ValidationSubscriber(store)

        store.set_item('item', 'value')  # No tag, no builder
        node = store.get_node('item')

        # Validation should do nothing for untagged nodes
        validator._validate_node(node)
        assert node._invalid_reasons == []

    def test_validation_children_constraints_no_parent_node(self):
        """Test _validate_children_constraints when parent_node is None."""
        from genro_treestore.validation import ValidationSubscriber

        store = TreeStore()
        validator = ValidationSubscriber(store)

        # Root store has no parent_node
        validator._validate_children_constraints(store)
        # Should not raise, just return

    def test_validation_children_constraints_no_builder(self):
        """Test _validate_children_constraints when builder is None."""
        from genro_treestore.validation import ValidationSubscriber

        store = TreeStore()
        store.set_item('parent')
        parent = store.get_node('parent').value

        validator = ValidationSubscriber(store)
        validator.builder = None  # Remove builder

        validator._validate_children_constraints(parent)
        # Should not raise, just return

    def test_validation_children_constraints_no_parent_tag(self):
        """Test _validate_children_constraints when parent has no tag."""
        from genro_treestore.validation import ValidationSubscriber

        store = TreeStore()
        store.set_item('parent')
        parent = store.get_node('parent').value
        parent.set_item('child', 'value')

        validator = ValidationSubscriber(store)

        # parent_node has no tag
        validator._validate_children_constraints(parent)
        # Should not raise, just return

    def test_validation_on_delete_event(self):
        """Test validation handles delete events correctly."""
        from genro_treestore import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder(), raise_on_error=False)
        ul = store.ul()
        ul.li(value='item1')
        ul.li(value='item2')

        # Delete an item
        ul.del_item('li_0')

        # Should still have one item
        assert len(ul) == 1

    def test_validation_hard_error_too_many_children(self):
        """Test that too many children raises ValueError when raise_on_error=True."""
        from genro_treestore.builders import BuilderBase
        from genro_treestore.builders.decorators import element

        class TestBuilder(BuilderBase):
            @element(children='item[0:2]')  # At most 2 items
            def container(self, target, tag, **attrs):
                return self.child(target, tag, **attrs)

            @element()
            def item(self, target, tag, value=None, **attrs):
                return self.child(target, tag, value=value, **attrs)

        store = TreeStore(builder=TestBuilder(), raise_on_error=True)
        container = store.container()
        container.item(value='first')
        container.item(value='second')

        # Third item should raise
        with pytest.raises(ValueError, match="allows at most 2"):
            container.item(value='third')

    def test_validation_soft_error_missing_children(self):
        """Test that missing required children doesn't raise, just collects."""
        from genro_treestore.builders import BuilderBase
        from genro_treestore.builders.decorators import element

        class TestBuilder(BuilderBase):
            @element(children='item[1:]')  # At least 1 item required
            def container(self, target, tag, **attrs):
                return self.child(target, tag, **attrs)

            @element()
            def item(self, target, tag, value=None, **attrs):
                return self.child(target, tag, value=value, **attrs)

        store = TreeStore(builder=TestBuilder(), raise_on_error=False)
        container = store.container()

        # Container with no items should have validation error
        container_node = store.get_node('container_0')
        assert not container_node.is_valid
        assert any("requires at least 1" in e for e in container_node._invalid_reasons)

        # Adding item should clear the error
        container.item(value='first')
        assert container_node.is_valid
