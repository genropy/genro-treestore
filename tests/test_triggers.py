# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for TreeStore trigger/subscription system."""

import pytest

from genro_treestore import TreeStore, TreeStoreNode


class TestStoreSubscribeInsert:
    """Tests for store-level insert triggers."""

    def test_subscribe_insert_single_node(self):
        """Insert event fires when adding a node."""
        store = TreeStore()
        events = []

        def on_insert(node, path, index, evt, reason):
            events.append({'node': node, 'path': path, 'index': index, 'evt': evt, 'reason': reason})

        store.subscribe('test', insert=on_insert)
        store.set_item('child', 'value')

        assert len(events) == 1
        assert events[0]['evt'] == 'ins'
        assert events[0]['path'] == 'child'
        assert events[0]['index'] == 0

    def test_subscribe_insert_multiple_nodes(self):
        """Insert events fire for each new node."""
        store = TreeStore()
        events = []

        def on_insert(node, path, index, evt, reason):
            events.append({'path': path, 'index': index})

        store.subscribe('test', insert=on_insert)
        store.set_item('a', 1)
        store.set_item('b', 2)
        store.set_item('c', 3)

        assert len(events) == 3
        assert events[0]['path'] == 'a'
        assert events[1]['path'] == 'b'
        assert events[2]['path'] == 'c'
        assert events[0]['index'] == 0
        assert events[1]['index'] == 1
        assert events[2]['index'] == 2

    def test_subscribe_insert_nested_path(self):
        """Insert event shows full path from subscriber's store."""
        store = TreeStore()
        events = []

        def on_insert(node, path, index, evt, reason):
            events.append({'path': path})

        store.subscribe('test', insert=on_insert)
        store.set_item('parent.child.grandchild', 'value')

        # Three inserts: parent, child, grandchild
        assert len(events) == 3
        paths = [e['path'] for e in events]
        assert 'parent' in paths
        assert 'parent.child' in paths
        assert 'parent.child.grandchild' in paths

    def test_subscribe_insert_propagates_to_root(self):
        """Insert events propagate up the hierarchy."""
        store = TreeStore()
        root_events = []
        child_events = []

        def on_root_insert(node, path, index, evt, reason):
            root_events.append({'path': path})

        store.subscribe('root', insert=on_root_insert)

        # Create branch and subscribe to it
        child_store = store.set_item('parent')

        def on_child_insert(node, path, index, evt, reason):
            child_events.append({'path': path})

        child_store.subscribe('child', insert=on_child_insert)

        # Add to child
        child_store.set_item('leaf', 'value')

        # Child sees just 'leaf'
        assert len(child_events) == 1
        assert child_events[0]['path'] == 'leaf'

        # Root sees 'parent' (initial) + 'parent.leaf'
        assert len(root_events) == 2
        assert root_events[1]['path'] == 'parent.leaf'


class TestStoreSubscribeDelete:
    """Tests for store-level delete triggers."""

    def test_subscribe_delete_single_node(self):
        """Delete event fires when removing a node."""
        store = TreeStore({'a': 1, 'b': 2})
        events = []

        def on_delete(node, path, index, evt, reason):
            events.append({'path': path, 'index': index, 'evt': evt})

        store.subscribe('test', delete=on_delete)
        store.del_item('a')

        assert len(events) == 1
        assert events[0]['evt'] == 'del'
        assert events[0]['path'] == 'a'
        assert events[0]['index'] == 0

    def test_subscribe_delete_propagates(self):
        """Delete events propagate up the hierarchy."""
        store = TreeStore()
        events = []

        def on_delete(node, path, index, evt, reason):
            events.append({'path': path})

        store.subscribe('test', delete=on_delete)
        store.set_item('parent.child', 'value')

        # Delete child from parent
        parent_store = store['parent']
        parent_store.del_item('child')

        assert len(events) == 1
        assert events[0]['path'] == 'parent.child'


class TestStoreSubscribeUpdate:
    """Tests for store-level update triggers."""

    def test_subscribe_update_value_change(self):
        """Update event fires when changing a value."""
        store = TreeStore({'item': 'old'})
        events = []

        def on_update(node, path, evt, oldvalue, reason):
            events.append({'path': path, 'evt': evt, 'oldvalue': oldvalue})

        store.subscribe('test', update=on_update)
        store['item'] = 'new'

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_value'
        assert events[0]['path'] == 'item'
        assert events[0]['oldvalue'] == 'old'

    def test_subscribe_update_attr_change(self):
        """Update event fires when changing attributes."""
        store = TreeStore()
        store.set_item('item', 'value', color='red')
        events = []

        def on_update(node, path, evt, oldvalue, reason):
            events.append({'path': path, 'evt': evt})

        store.subscribe('test', update=on_update)
        store.set_attr('item', color='blue')

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_attr'
        assert events[0]['path'] == 'item'

    def test_subscribe_update_no_change_no_event(self):
        """No event when setting same value."""
        store = TreeStore({'item': 'value'})
        events = []

        def on_update(node, path, evt, oldvalue, reason):
            events.append({'path': path})

        store.subscribe('test', update=on_update)
        store['item'] = 'value'  # Same value

        assert len(events) == 0

    def test_subscribe_update_propagates(self):
        """Update events propagate up the hierarchy."""
        store = TreeStore()
        events = []

        def on_update(node, path, evt, oldvalue, reason):
            events.append({'path': path, 'oldvalue': oldvalue})

        store.subscribe('test', update=on_update)
        store.set_item('parent.child', 'old')
        store['parent.child'] = 'new'

        assert len(events) == 1
        assert events[0]['path'] == 'parent.child'
        assert events[0]['oldvalue'] == 'old'


class TestStoreSubscribeAny:
    """Tests for 'any' subscription."""

    def test_subscribe_any_receives_all_events(self):
        """'any' callback receives insert, update, and delete."""
        store = TreeStore()
        events = []

        def on_any(**kwargs):
            events.append(kwargs['evt'])

        store.subscribe('test', any=on_any)

        store.set_item('item', 'value')  # insert
        store['item'] = 'new'            # update
        store.del_item('item')           # delete

        assert 'ins' in events
        assert 'upd_value' in events
        assert 'del' in events


class TestStoreUnsubscribe:
    """Tests for unsubscribe functionality."""

    def test_unsubscribe_stops_events(self):
        """Unsubscribed callback no longer receives events."""
        store = TreeStore()
        events = []

        def on_insert(node, path, index, evt, reason):
            events.append(path)

        store.subscribe('test', insert=on_insert)
        store.set_item('first', 1)

        store.unsubscribe('test', any=True)
        store.set_item('second', 2)

        assert events == ['first']

    def test_unsubscribe_specific_event(self):
        """Can unsubscribe from specific event types."""
        store = TreeStore()
        insert_events = []
        delete_events = []

        def on_insert(node, path, index, evt, reason):
            insert_events.append(path)

        def on_delete(node, path, index, evt, reason):
            delete_events.append(path)

        store.subscribe('test', insert=on_insert, delete=on_delete)
        store.set_item('a', 1)
        store.del_item('a')

        assert len(insert_events) == 1
        assert len(delete_events) == 1

        # Unsubscribe only from insert
        store.unsubscribe('test', insert=True)
        store.set_item('b', 2)
        store.del_item('b')

        # No new insert events, but delete still works
        assert len(insert_events) == 1
        assert len(delete_events) == 2


class TestStoreSubscribeReason:
    """Tests for reason parameter in triggers."""

    def test_reason_passed_to_callback(self):
        """Reason is passed to subscriber callback."""
        store = TreeStore()
        events = []

        def on_update(node, path, evt, oldvalue, reason):
            events.append({'reason': reason})

        store.subscribe('test', update=on_update)

        node = store.get_node('item') if 'item' in store else None
        store.set_item('item', 'old')
        store.get_node('item').set_value('new', reason='my_renderer')

        assert len(events) == 1
        assert events[0]['reason'] == 'my_renderer'

    def test_reason_for_avoiding_cycles(self):
        """Reason can be used to detect self-triggered events."""
        store = TreeStore()
        store.set_item('counter', 0)
        updates = []

        def on_update(node, path, evt, oldvalue, reason):
            updates.append(reason)
            if reason != 'auto':
                # Auto-increment, but mark with reason to avoid loop
                node.set_value(node.value + 1, reason='auto')

        store.subscribe('test', update=on_update)
        store.get_node('counter').set_value(10, reason='user')

        # First update from user, second from auto
        assert updates == ['user', 'auto']


class TestNodeSubscribe:
    """Tests for node-level triggers."""

    def test_node_subscribe_value_change(self):
        """Node subscriber receives value change events."""
        store = TreeStore({'item': 'old'})
        node = store.get_node('item')
        events = []

        def on_change(node, info, evt):
            events.append({'info': info, 'evt': evt})

        node.subscribe('test', on_change)
        node.value = 'new'

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_value'
        assert events[0]['info'] == 'old'  # oldvalue

    def test_node_subscribe_attr_change(self):
        """Node subscriber receives attribute change events."""
        store = TreeStore()
        store.set_item('item', 'value', color='red')
        node = store.get_node('item')
        events = []

        def on_change(node, info, evt):
            events.append({'info': info, 'evt': evt})

        node.subscribe('test', on_change)
        node.set_attr(color='blue', size='large')

        assert len(events) == 1
        assert events[0]['evt'] == 'upd_attr'
        assert 'color' in events[0]['info']  # changed attrs
        assert 'size' in events[0]['info']

    def test_node_unsubscribe(self):
        """Node unsubscribe stops events."""
        store = TreeStore({'item': 0})
        node = store.get_node('item')
        events = []

        def on_change(node, info, evt):
            events.append(info)

        node.subscribe('test', on_change)
        node.value = 1
        node.unsubscribe('test')
        node.value = 2

        assert events == [0]  # Only first change


class TestTriggerDuringLoad:
    """Tests that loading data doesn't trigger events."""

    def test_source_dict_no_triggers(self):
        """Loading from dict doesn't trigger events."""
        events = []

        def on_any(**kwargs):
            events.append(kwargs)

        store = TreeStore({'a': 1, 'b': {'c': 2}})
        store.subscribe('test', any=on_any)

        # Events should be empty - loading happened before subscribe
        assert len(events) == 0

        # But now changes should trigger
        store.set_item('d', 4)
        assert len(events) == 1

    def test_source_treestore_no_triggers(self):
        """Copying from TreeStore doesn't trigger events."""
        source = TreeStore({'x': 1})
        events = []

        store = TreeStore(source)

        def on_any(**kwargs):
            events.append(kwargs)

        store.subscribe('test', any=on_any)
        assert len(events) == 0


class TestMultipleSubscribers:
    """Tests for multiple subscribers on same store."""

    def test_multiple_subscribers_all_notified(self):
        """All subscribers receive events."""
        store = TreeStore()
        events_a = []
        events_b = []

        def on_a(node, path, index, evt, reason):
            events_a.append(path)

        def on_b(node, path, index, evt, reason):
            events_b.append(path)

        store.subscribe('a', insert=on_a)
        store.subscribe('b', insert=on_b)

        store.set_item('item', 'value')

        assert events_a == ['item']
        assert events_b == ['item']

    def test_subscriber_id_uniqueness(self):
        """Same ID replaces previous subscription."""
        store = TreeStore()
        events = []

        def on_first(node, path, index, evt, reason):
            events.append('first')

        def on_second(node, path, index, evt, reason):
            events.append('second')

        store.subscribe('same_id', insert=on_first)
        store.subscribe('same_id', insert=on_second)

        store.set_item('item', 'value')

        # Only second callback should fire
        assert events == ['second']
