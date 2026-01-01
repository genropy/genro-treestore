# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore node classes."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import TreeStore

# Type alias for node subscriber callbacks
NodeSubscriberCallback = Callable[..., None]


class TreeStoreNode:
    """A node in a TreeStore hierarchy.

    Each node has:
    - label: The node's unique name/key within its parent
    - attr: Dictionary of attributes
    - value: Either a scalar value or a TreeStore (for children)
    - parent: Reference to the containing TreeStore
    - tag: Optional type/tag for the node (used by builders)

    Example:
        >>> node = TreeStoreNode('user', {'id': 1}, 'Alice')
        >>> node.label
        'user'
        >>> node.value
        'Alice'
    """

    __slots__ = ('label', 'attr', '_value', 'parent', 'tag', '_node_subscribers')

    def __init__(
        self,
        label: str,
        attr: dict[str, Any] | None = None,
        value: Any = None,
        parent: TreeStore | None = None,
        tag: str | None = None,
    ) -> None:
        """Initialize a TreeStoreNode.

        Args:
            label: The node's unique name/key.
            attr: Optional dictionary of attributes.
            value: The node's value (scalar or TreeStore for children).
            parent: The TreeStore containing this node.
            tag: Optional type/tag for the node (used by builders).
        """
        self.label = label
        self.attr = attr or {}
        self._value = value
        self.parent = parent
        self.tag = tag
        self._node_subscribers: dict[str, NodeSubscriberCallback] = {}

    def __repr__(self) -> str:
        from .store import TreeStore
        value_repr = (
            f"TreeStore({len(self._value)})"
            if isinstance(self._value, TreeStore)
            else repr(self._value)
        )
        return f"TreeStoreNode({self.label!r}, value={value_repr})"

    @property
    def value(self) -> Any:
        """Get the node's value."""
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the node's value with trigger."""
        self.set_value(new_value)

    def set_value(
        self,
        value: Any,
        trigger: bool = True,
        reason: str | None = None,
    ) -> None:
        """Set the node's value, optionally triggering events.

        Args:
            value: The new value.
            trigger: If True, notify subscribers of the change.
            reason: Optional reason string for the trigger.
        """
        oldvalue = self._value
        if value == oldvalue:
            return  # No change

        self._value = value

        if trigger:
            # Notify node subscribers
            for callback in self._node_subscribers.values():
                callback(node=self, info=oldvalue, evt='upd_value')

            # Notify parent store
            if self.parent is not None:
                self.parent._on_node_changed(
                    self, [self.label], 'upd_value', oldvalue, reason
                )

    @property
    def is_branch(self) -> bool:
        """True if this node contains a TreeStore (has children)."""
        from .store import TreeStore
        return isinstance(self._value, TreeStore)

    @property
    def is_leaf(self) -> bool:
        """True if this node contains a scalar value."""
        from .store import TreeStore
        return not isinstance(self._value, TreeStore)

    @property
    def _(self) -> TreeStore:
        """Return parent TreeStore for navigation/chaining.

        Example:
            >>> node._.set_item('sibling', 'value')  # add sibling
        """
        if self.parent is None:
            raise ValueError("Node has no parent")
        return self.parent

    def get_attr(self, attr: str | None = None, default: Any = None) -> Any:
        """Get attribute value or all attributes.

        Args:
            attr: Attribute name. If None, returns all attributes.
            default: Default value if attribute not found.

        Returns:
            Attribute value, default, or dict of all attributes.
        """
        if attr is None:
            return self.attr
        return self.attr.get(attr, default)

    def set_attr(
        self,
        _attr: dict[str, Any] | None = None,
        trigger: bool = True,
        reason: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Set attributes on the node.

        Args:
            _attr: Dictionary of attributes to set.
            trigger: If True, notify subscribers of the change.
            reason: Optional reason string for the trigger.
            **kwargs: Additional attributes as keyword arguments.
        """
        if trigger and self._node_subscribers:
            oldattr = dict(self.attr)

        if _attr:
            self.attr.update(_attr)
        self.attr.update(kwargs)

        if trigger:
            # Notify node subscribers
            if self._node_subscribers:
                changed_attrs = [
                    k for k in self.attr
                    if k not in oldattr or self.attr[k] != oldattr[k]
                ]
                for callback in self._node_subscribers.values():
                    callback(node=self, info=changed_attrs, evt='upd_attr')

            # Notify parent store
            if self.parent is not None:
                self.parent._on_node_changed(
                    self, [self.label], 'upd_attr', reason=reason
                )

    def subscribe(self, subscriber_id: str, callback: NodeSubscriberCallback) -> None:
        """Subscribe to changes on this specific node.

        Args:
            subscriber_id: Unique identifier for this subscription.
            callback: Function to call on changes.

        Callback signature:
            callback(node, info, evt)
            - node: This TreeStoreNode
            - info: oldvalue (for 'upd_value') or list of changed attrs (for 'upd_attr')
            - evt: Event type ('upd_value' or 'upd_attr')

        Example:
            >>> def on_change(node, info, evt):
            ...     print(f"{evt}: {info}")
            >>> node.subscribe('watcher', on_change)
        """
        self._node_subscribers[subscriber_id] = callback

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from changes on this node.

        Args:
            subscriber_id: The subscription identifier to remove.
        """
        self._node_subscribers.pop(subscriber_id, None)


