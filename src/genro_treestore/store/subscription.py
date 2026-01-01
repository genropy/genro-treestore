# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore subscription and event notification system.

This module provides the event subscription mechanism for TreeStore,
enabling reactive programming patterns. Subscribers can listen to
node changes (value/attribute updates), insertions, and deletions.

Events propagate up the hierarchy: a subscriber on the root TreeStore
receives events from all descendants, with the path indicating where
the change occurred.

Event Types:
    - 'upd_value': Node value changed
    - 'upd_attr': Node attributes changed
    - 'ins': Node inserted
    - 'del': Node deleted

Callback Signature::

    def callback(node, path, evt, oldvalue=None, index=None, reason=None):
        '''
        Args:
            node: The affected TreeStoreNode
            path: Dot-separated path from the subscribed store to the node
            evt: Event type ('upd_value', 'upd_attr', 'ins', 'del')
            oldvalue: Previous value (for 'upd_value' events)
            index: Position index (for 'ins' and 'del' events)
            reason: Optional string identifying the change source
        '''

Example:
    >>> def on_change(node, path, evt, **kw):
    ...     print(f"{evt} at {path}: {node.value}")
    >>> store.subscribe('logger', any=on_change)
    >>> store.set_item('config.debug', True)
    ins at config.debug: True
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import TreeStoreNode

# Type alias for subscriber callbacks
SubscriberCallback = Callable[..., None]


class SubscriptionMixin:
    """Mixin class providing subscription functionality for TreeStore.

    This mixin adds subscribe/unsubscribe methods and event notification
    to TreeStore. It requires the host class to have:
    - _upd_subscribers: dict[str, SubscriberCallback]
    - _ins_subscribers: dict[str, SubscriberCallback]
    - _del_subscribers: dict[str, SubscriberCallback]
    - parent: TreeStoreNode | None
    """

    _upd_subscribers: dict[str, SubscriberCallback]
    _ins_subscribers: dict[str, SubscriberCallback]
    _del_subscribers: dict[str, SubscriberCallback]
    parent: TreeStoreNode | None

    def subscribe(
        self,
        subscriber_id: str,
        update: SubscriberCallback | None = None,
        insert: SubscriberCallback | None = None,
        delete: SubscriberCallback | None = None,
        any: SubscriberCallback | None = None,
    ) -> None:
        """Subscribe to change events on this store.

        Events propagate up the hierarchy: a subscriber on the root
        receives events from all descendants, with the path indicating
        where the change occurred.

        Args:
            subscriber_id: Unique identifier for this subscription.
            update: Callback for value/attribute changes.
            insert: Callback for node insertions.
            delete: Callback for node deletions.
            any: Callback for all events (shorthand for update+insert+delete).

        Callback Signature::

            def callback(node, path, evt, oldvalue=None, index=None, reason=None):
                '''
                Args:
                    node: The affected TreeStoreNode
                    path: Dot-separated path from this store to the node
                    evt: Event type ('upd_value', 'upd_attr', 'ins', 'del')
                    oldvalue: Previous value (for 'upd_value' events)
                    index: Position index (for 'ins' and 'del' events)
                    reason: Optional string identifying the change source
                '''

        Example:
            >>> def on_change(node, path, evt, **kw):
            ...     print(f"{evt} at {path}")
            >>> store.subscribe('renderer', any=on_change)
        """
        if update or any:
            self._upd_subscribers[subscriber_id] = update or any
        if insert or any:
            self._ins_subscribers[subscriber_id] = insert or any
        if delete or any:
            self._del_subscribers[subscriber_id] = delete or any

    def unsubscribe(
        self,
        subscriber_id: str,
        update: bool = False,
        insert: bool = False,
        delete: bool = False,
        any: bool = False,
    ) -> None:
        """Unsubscribe from change events.

        Args:
            subscriber_id: The subscription identifier to remove.
            update: Unsubscribe from update events.
            insert: Unsubscribe from insert events.
            delete: Unsubscribe from delete events.
            any: Unsubscribe from all events.
        """
        if update or any:
            self._upd_subscribers.pop(subscriber_id, None)
        if insert or any:
            self._ins_subscribers.pop(subscriber_id, None)
        if delete or any:
            self._del_subscribers.pop(subscriber_id, None)

    def _on_node_changed(
        self,
        node: TreeStoreNode,
        pathlist: list[str],
        evt: str,
        oldvalue: Any = None,
        reason: str | None = None,
    ) -> None:
        """Notify subscribers of a node change and propagate to parent.

        Called when a node's value or attributes change. Notifies all
        update subscribers and propagates the event up the tree hierarchy.

        Args:
            node: The node that changed.
            pathlist: Path components from this store to the node.
            evt: Event type ('upd_value' or 'upd_attr').
            oldvalue: Previous value.
            reason: Optional reason string.
        """
        path = ".".join(pathlist)
        for callback in self._upd_subscribers.values():
            callback(node=node, path=path, evt=evt, oldvalue=oldvalue, reason=reason)

        if self.parent is not None:
            parent_store = self.parent.parent
            if parent_store is not None:
                parent_store._on_node_changed(
                    node, [self.parent.label] + pathlist, evt, oldvalue, reason
                )

    def _on_node_inserted(
        self,
        node: TreeStoreNode,
        index: int,
        pathlist: list[str] | None = None,
        reason: str | None = None,
    ) -> None:
        """Notify subscribers of a node insertion and propagate to parent.

        Called when a new node is added to the store. Notifies all insert
        subscribers and propagates the event up the tree hierarchy.

        Args:
            node: The inserted node.
            index: Position where node was inserted.
            pathlist: Path components from this store to the node.
            reason: Optional reason string.
        """
        if pathlist is None:
            pathlist = []
        path = ".".join(pathlist) if pathlist else node.label

        for callback in self._ins_subscribers.values():
            callback(node=node, path=path, index=index, evt="ins", reason=reason)

        if self.parent is not None:
            parent_store = self.parent.parent
            if parent_store is not None:
                parent_store._on_node_inserted(
                    node,
                    index,
                    [self.parent.label] + (pathlist or [node.label]),
                    reason,
                )

    def _on_node_deleted(
        self,
        node: TreeStoreNode,
        index: int,
        pathlist: list[str] | None = None,
        reason: str | None = None,
    ) -> None:
        """Notify subscribers of a node deletion and propagate to parent.

        Called when a node is removed from the store. Notifies all delete
        subscribers and propagates the event up the tree hierarchy.

        Args:
            node: The deleted node.
            index: Position where node was removed from.
            pathlist: Path components from this store to the node.
            reason: Optional reason string.
        """
        if pathlist is None:
            pathlist = []
        path = ".".join(pathlist) if pathlist else node.label

        for callback in self._del_subscribers.values():
            callback(node=node, path=path, index=index, evt="del", reason=reason)

        if self.parent is not None:
            parent_store = self.parent.parent
            if parent_store is not None:
                parent_store._on_node_deleted(
                    node,
                    index,
                    [self.parent.label] + (pathlist or [node.label]),
                    reason,
                )
