# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore node classes."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import TreeStore


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

    __slots__ = ('label', 'attr', 'value', 'parent', 'tag')

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
        self.value = value
        self.parent = parent
        self.tag = tag

    def __repr__(self) -> str:
        from .store import TreeStore
        value_repr = (
            f"TreeStore({len(self.value)})"
            if isinstance(self.value, TreeStore)
            else repr(self.value)
        )
        return f"TreeStoreNode({self.label!r}, value={value_repr})"

    @property
    def is_branch(self) -> bool:
        """True if this node contains a TreeStore (has children)."""
        from .store import TreeStore
        return isinstance(self.value, TreeStore)

    @property
    def is_leaf(self) -> bool:
        """True if this node contains a scalar value."""
        from .store import TreeStore
        return not isinstance(self.value, TreeStore)

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

    def set_attr(self, _attr: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Set attributes on the node.

        Args:
            _attr: Dictionary of attributes to set.
            **kwargs: Additional attributes as keyword arguments.
        """
        if _attr:
            self.attr.update(_attr)
        self.attr.update(kwargs)


