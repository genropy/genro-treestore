# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore - A lightweight hierarchical data structure inspired by Genro Bag.

This module provides:
- TreeStoreNode: A node with label, attributes, and value
- TreeStore: A Bag-like container with setItem/getItem API
- TreeStoreBuilder: Builder pattern with auto-labeling and validation
- valid_children: Decorator for child validation in typed builders
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self


class TreeStoreNode:
    """A node in a TreeStore hierarchy.

    Each node has:
    - label: The node's unique name/key within its parent
    - attr: Dictionary of attributes
    - value: Either a scalar value or a TreeStore (for children)
    - parent: Reference to the containing TreeStore

    Example:
        >>> node = TreeStoreNode('user', {'id': 1}, 'Alice')
        >>> node.label
        'user'
        >>> node.value
        'Alice'
    """

    __slots__ = ('label', 'attr', 'value', 'parent')

    def __init__(
        self,
        label: str,
        attr: dict[str, Any] | None = None,
        value: Any | TreeStore = None,
        parent: TreeStore | None = None,
    ) -> None:
        """Initialize a TreeStoreNode.

        Args:
            label: The node's unique name/key.
            attr: Optional dictionary of attributes.
            value: The node's value (scalar or TreeStore for children).
            parent: The TreeStore containing this node.
        """
        self.label = label
        self.attr = attr or {}
        self.value = value
        self.parent = parent

    @property
    def tag(self) -> str | None:
        """Get the node's tag (type) from attr['_tag'] if present."""
        return self.attr.get('_tag')

    def __repr__(self) -> str:
        value_repr = (
            f"TreeStore({len(self.value)})"
            if isinstance(self.value, TreeStore)
            else repr(self.value)
        )
        return f"TreeStoreNode({self.label!r}, value={value_repr})"

    @property
    def is_branch(self) -> bool:
        """True if this node contains a TreeStore (has children)."""
        return isinstance(self.value, TreeStore)

    @property
    def is_leaf(self) -> bool:
        """True if this node contains a scalar value."""
        return not isinstance(self.value, TreeStore)

    @property
    def _(self) -> TreeStore:
        """Return parent TreeStore for navigation/chaining.

        Example:
            >>> node._.setItem('sibling', 'value')  # add sibling
        """
        if self.parent is None:
            raise ValueError("Node has no parent")
        return self.parent

    def getAttr(self, attr: str | None = None, default: Any = None) -> Any:
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

    def setAttr(self, _attr: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Set attributes on the node.

        Args:
            _attr: Dictionary of attributes to set.
            **kwargs: Additional attributes as keyword arguments.
        """
        if _attr:
            self.attr.update(_attr)
        self.attr.update(kwargs)


class BuilderNode(TreeStoreNode):
    """A node with tag support for TreeStoreBuilder.

    Extends TreeStoreNode with a separate tag attribute (not in attr dict).
    """

    __slots__ = ('_tag',)

    def __init__(
        self,
        label: str,
        attr: dict[str, Any] | None = None,
        value: Any = None,
        parent: TreeStore | None = None,
        tag: str | None = None,
    ) -> None:
        super().__init__(label, attr, value, parent)
        self._tag = tag

    @property
    def tag(self) -> str | None:
        """Get the node's tag (type)."""
        return self._tag


class TreeStore:
    """A Bag-like hierarchical data container with O(1) lookup.

    TreeStore provides a familiar API similar to Genro Bag:
    - setItem(path, value, **attr): Create/update nodes with autocreate
    - getItem(path) / store[path]: Get values
    - getAttr(path, attr) / setAttr(path, **attr): Attribute access
    - digest(what): Extract data with #k, #v, #a syntax

    The internal storage uses dict for O(1) lookup performance.

    Example:
        >>> store = TreeStore()
        >>> store.setItem('html.body.div', color='red')
        >>> store['html.body.div?color']
        'red'
    """

    __slots__ = ('_nodes', '_order', 'parent')

    def __init__(
        self,
        source: dict | list | TreeStore | None = None,
        parent: TreeStoreNode | None = None,
    ) -> None:
        """Initialize a TreeStore.

        Args:
            source: Optional initial data. Can be:
                - dict: Nested dict converted to nodes. Keys with '_' prefix
                  are treated as attributes (e.g., {'_color': 'red', 'child': ...})
                - TreeStore: Copy from another TreeStore
                - list: List of tuples (label, value) or (label, value, attr)
            parent: The TreeStoreNode that contains this store as its value.

        Example:
            >>> TreeStore({'a': 1, 'b': {'c': 2}})
            >>> TreeStore([('x', 1), ('y', 2, {'color': 'red'})])
            >>> TreeStore(other_store)  # copy
        """
        self._nodes: dict[str, TreeStoreNode] = {}
        self._order: list[TreeStoreNode] = []
        self.parent = parent

        if source is not None:
            self._load_source(source)

    def _load_source(
        self, source: dict | list | TreeStore
    ) -> None:
        """Load data from source into this TreeStore."""
        if isinstance(source, dict):
            self._load_from_dict(source)
        elif isinstance(source, TreeStore):
            self._load_from_treestore(source)
        elif isinstance(source, list):
            self._load_from_list(source)
        else:
            raise TypeError(
                f"source must be dict, list, or TreeStore, not {type(source).__name__}"
            )

    def _load_from_dict(self, data: dict[str, Any]) -> None:
        """Load data from a nested dict.

        Keys starting with '_' are treated as attributes for the parent node.
        Other keys become child nodes.
        """
        for key, value in data.items():
            if key.startswith('_'):
                # Skip attribute keys at root level (no parent to attach to)
                continue

            if isinstance(value, dict):
                # Check for attributes in the dict
                attr = {}
                children = {}
                node_value = None

                for k, v in value.items():
                    if k.startswith('_'):
                        if k == '_value':
                            node_value = v
                        else:
                            attr[k[1:]] = v  # Remove '_' prefix
                    else:
                        children[k] = v

                if children:
                    # Branch node with children
                    child_store = TreeStore()
                    node = TreeStoreNode(key, attr, value=child_store, parent=self)
                    child_store.parent = node
                    child_store._load_from_dict(children)
                    self._insert_node(node)
                else:
                    # Leaf node (only _value and attributes)
                    node = TreeStoreNode(key, attr, value=node_value, parent=self)
                    self._insert_node(node)
            else:
                # Simple value
                node = TreeStoreNode(key, {}, value=value, parent=self)
                self._insert_node(node)

    def _load_from_treestore(self, source: TreeStore) -> None:
        """Copy data from another TreeStore."""
        for src_node in source._order:
            if src_node.is_branch:
                # Recursively copy branch
                child_store = TreeStore()
                node = TreeStoreNode(
                    src_node.label,
                    dict(src_node.attr),  # Copy attributes
                    value=child_store,
                    parent=self,
                )
                child_store.parent = node
                child_store._load_from_treestore(src_node.value)
                self._insert_node(node)
            else:
                # Copy leaf
                node = TreeStoreNode(
                    src_node.label,
                    dict(src_node.attr),
                    value=src_node.value,
                    parent=self,
                )
                self._insert_node(node)

    def _load_from_list(self, items: list) -> None:
        """Load data from a list of tuples.

        Each tuple can be:
            - (label, value)
            - (label, value, attr_dict)
        """
        for item in items:
            if len(item) == 2:
                label, value = item
                attr = {}
            elif len(item) == 3:
                label, value, attr = item
                attr = dict(attr)  # Copy
            else:
                raise ValueError(
                    f"List items must be (label, value) or (label, value, attr), "
                    f"got {len(item)} elements"
                )

            if isinstance(value, dict):
                # Nested dict becomes branch
                child_store = TreeStore()
                node = TreeStoreNode(label, attr, value=child_store, parent=self)
                child_store.parent = node
                child_store._load_from_dict(value)
                self._insert_node(node)
            elif isinstance(value, list) and value and isinstance(value[0], tuple):
                # Nested list of tuples becomes branch
                child_store = TreeStore()
                node = TreeStoreNode(label, attr, value=child_store, parent=self)
                child_store.parent = node
                child_store._load_from_list(value)
                self._insert_node(node)
            else:
                # Simple value
                node = TreeStoreNode(label, attr, value=value, parent=self)
                self._insert_node(node)

    def __repr__(self) -> str:
        return f"TreeStore({list(self._nodes.keys())})"

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self) -> Iterator[TreeStoreNode]:
        """Iterate over nodes in insertion order."""
        return iter(self._order)

    def __contains__(self, label: str) -> bool:
        """Check if a label exists at root level or as a path."""
        if '.' not in label:
            return label in self._nodes
        try:
            self.getNode(label)
            return True
        except KeyError:
            return False

    # ==================== Path Utilities ====================

    def _parse_path_segment(self, segment: str) -> tuple[bool, int | str]:
        """Parse a path segment, detecting positional index (#N) syntax.

        Returns:
            Tuple of (is_positional, index_or_label)
        """
        if segment.startswith('#'):
            rest = segment[1:]
            if rest.lstrip('-').isdigit():
                return True, int(rest)
        return False, segment

    def _get_node_by_position(self, index: int) -> TreeStoreNode:
        """Get node by positional index (O(1) via _order list)."""
        if index < 0:
            index = len(self._order) + index
        if index < 0 or index >= len(self._order):
            raise KeyError(f"Position #{index} out of range (0-{len(self._order)-1})")
        return self._order[index]

    def _index_of(self, label: str) -> int:
        """Get the position index of a label (O(n))."""
        for i, node in enumerate(self._order):
            if node.label == label:
                return i
        raise KeyError(f"Label '{label}' not found")

    def _insert_node(self, node: TreeStoreNode, position: str | None = None) -> None:
        """Insert a node into both _nodes dict and _order list.

        Args:
            node: The node to insert.
            position: Position specifier (Bag-style):
                - None or '>': append to end (default)
                - '<': insert at beginning
                - '<label': insert before label
                - '>label': insert after label
                - '<#N': insert before position N
                - '>#N': insert after position N
                - '#N': insert at exact position N
        """
        self._nodes[node.label] = node

        if position is None or position == '>':
            self._order.append(node)
        elif position == '<':
            self._order.insert(0, node)
        elif position.startswith('<#'):
            idx = int(position[2:])
            if idx < 0:
                idx = len(self._order) + idx
            self._order.insert(idx, node)
        elif position.startswith('>#'):
            idx = int(position[2:]) + 1
            if idx < 0:
                idx = len(self._order) + idx + 1
            self._order.insert(idx, node)
        elif position.startswith('<'):
            label = position[1:]
            idx = self._index_of(label)
            self._order.insert(idx, node)
        elif position.startswith('>'):
            label = position[1:]
            idx = self._index_of(label) + 1
            self._order.insert(idx, node)
        elif position.startswith('#'):
            idx = int(position[1:])
            if idx < 0:
                idx = len(self._order) + idx
            self._order.insert(idx, node)
        else:
            # Unknown position, append to end
            self._order.append(node)

    def _remove_node(self, label: str) -> TreeStoreNode:
        """Remove a node from both _nodes dict and _order list.

        Args:
            label: The label of the node to remove.

        Returns:
            The removed node.
        """
        node = self._nodes.pop(label)
        self._order.remove(node)
        return node

    def _htraverse(
        self, path: str, autocreate: bool = False
    ) -> tuple[TreeStore, str]:
        """Traverse path, optionally creating intermediate nodes.

        Args:
            path: Dotted path string.
            autocreate: If True, create missing intermediate nodes.

        Returns:
            Tuple of (parent_store, final_label)
        """
        if not path:
            return self, ''

        parts = path.split('.')
        current = self

        for i, part in enumerate(parts[:-1]):
            is_pos, key = self._parse_path_segment(part)

            if is_pos:
                try:
                    node = current._get_node_by_position(key)
                except KeyError:
                    if autocreate:
                        raise KeyError(f"Cannot autocreate with positional syntax #{key}")
                    raise
            else:
                if key not in current._nodes:
                    if autocreate:
                        # Create intermediate branch node
                        child_store = TreeStore()
                        node = TreeStoreNode(key, {}, value=child_store, parent=current)
                        child_store.parent = node
                        current._insert_node(node)
                    else:
                        raise KeyError(f"Path segment '{key}' not found")
                node = current._nodes[key]

            if not node.is_branch:
                if autocreate:
                    # Convert leaf to branch
                    child_store = TreeStore()
                    child_store.parent = node
                    node.value = child_store
                else:
                    remaining = '.'.join(parts[i+1:])
                    raise KeyError(f"'{part}' is a leaf, cannot access '{remaining}'")

            current = node.value

        return current, parts[-1]

    # ==================== Core API (Bag-like) ====================

    def setItem(
        self,
        path: str,
        value: Any = None,
        _attributes: dict[str, Any] | None = None,
        _position: str | None = None,
        **kwargs: Any
    ) -> TreeStore:
        """Set an item at the given path, creating intermediate nodes as needed.

        Args:
            path: Dotted path to the item (e.g., 'html.body.div').
            value: The value to store. If None, creates a branch node.
            _attributes: Dictionary of attributes.
            _position: Position specifier (Bag-style):
                - None or '>': append to end (default)
                - '<': insert at beginning
                - '<label': insert before label
                - '>label': insert after label
                - '<#N': insert before position N
                - '>#N': insert after position N
                - '#N': insert at exact position N
            **kwargs: Additional attributes as keyword arguments.

        Returns:
            TreeStore for fluent chaining:
            - If branch created: returns the new branch's TreeStore
            - If leaf created: returns the parent TreeStore

        Example:
            >>> store.setItem('html').setItem('body').setItem('div', color='red')
            >>> store.setItem('ul').setItem('li', 'Item 1').setItem('li', 'Item 2')
            >>> store.setItem('first', 'value', _position='<')  # insert at beginning
        """
        parent_store, label = self._htraverse(path, autocreate=True)

        # Merge attributes
        final_attr: dict[str, Any] = {}
        if _attributes:
            final_attr.update(_attributes)
        final_attr.update(kwargs)

        # Check if node exists
        if label in parent_store._nodes:
            node = parent_store._nodes[label]
            if value is not None:
                node.value = value
            if final_attr:
                node.attr.update(final_attr)
            # Return appropriate store for chaining
            if node.is_branch:
                return node.value
            return parent_store

        # Create new node
        if value is not None:
            # Leaf node
            node = TreeStoreNode(label, final_attr, value, parent=parent_store)
            parent_store._insert_node(node, _position)
            return parent_store  # Return parent for chaining siblings
        else:
            # Branch node
            child_store = TreeStore()
            node = TreeStoreNode(label, final_attr, value=child_store, parent=parent_store)
            child_store.parent = node
            parent_store._insert_node(node, _position)
            return child_store  # Return child store for chaining children

    def getItem(self, path: str, default: Any = None) -> Any:
        """Get the value at the given path.

        Args:
            path: Dotted path, optionally with ?attr suffix.
            default: Default value if path not found.

        Returns:
            The value at the path, attribute value, or default.

        Example:
            >>> store.getItem('html.body.div')  # returns value
            >>> store.getItem('html.body.div?color')  # returns attribute
        """
        try:
            # Check for attribute access
            attr_name = None
            if '?' in path:
                path, attr_name = path.rsplit('?', 1)

            node = self.getNode(path)

            if attr_name is not None:
                return node.attr.get(attr_name, default)

            return node.value
        except KeyError:
            return default

    def __getitem__(self, path: str) -> Any:
        """Get value or attribute by path.

        Args:
            path: Dotted path, with optional ?attr or positional #N syntax.

        Returns:
            Value at path, or attribute if ?attr used.

        Example:
            >>> store['html.body.div']  # value
            >>> store['html.body.div?color']  # attribute
            >>> store['#0.#1']  # positional access
        """
        # Check for attribute access
        attr_name = None
        if '?' in path:
            path, attr_name = path.rsplit('?', 1)

        node = self.getNode(path)

        if attr_name is not None:
            return node.attr.get(attr_name)

        return node.value

    def __setitem__(self, path: str, value: Any) -> None:
        """Set value or attribute by path.

        Args:
            path: Dotted path. Use ?attr suffix to set attribute.
            value: Value to set.

        Example:
            >>> store['html.body.div'] = 'text'  # set value
            >>> store['html.body.div?color'] = 'red'  # set attribute
        """
        if '?' in path:
            # Set attribute
            node_path, attr_name = path.rsplit('?', 1)
            node = self.getNode(node_path)
            node.attr[attr_name] = value
        else:
            # Set value (with autocreate)
            self.setItem(path, value)

    def getNode(self, path: str) -> TreeStoreNode:
        """Get node at the given path.

        Args:
            path: Dotted path to the node.

        Returns:
            TreeStoreNode at the path.

        Raises:
            KeyError: If path not found.
        """
        if not path:
            raise KeyError("Empty path")

        if '.' not in path:
            is_pos, key = self._parse_path_segment(path)
            if is_pos:
                return self._get_node_by_position(key)
            return self._nodes[path]

        parent_store, label = self._htraverse(path, autocreate=False)
        is_pos, key = self._parse_path_segment(label)
        if is_pos:
            return parent_store._get_node_by_position(key)
        return parent_store._nodes[label]

    def getAttr(self, path: str, attr: str | None = None, default: Any = None) -> Any:
        """Get attribute(s) from node at path.

        Args:
            path: Path to the node.
            attr: Attribute name. If None, returns all attributes.
            default: Default value if attribute not found.

        Returns:
            Attribute value, all attributes dict, or default.
        """
        try:
            node = self.getNode(path)
            return node.getAttr(attr, default)
        except KeyError:
            return default

    def setAttr(
        self, path: str, _attributes: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Set attributes on node at path.

        Args:
            path: Path to the node.
            _attributes: Dictionary of attributes.
            **kwargs: Additional attributes as keyword arguments.
        """
        node = self.getNode(path)
        node.setAttr(_attributes, **kwargs)

    def delItem(self, path: str) -> TreeStoreNode:
        """Delete and return node at path.

        Args:
            path: Path to the node.

        Returns:
            The removed TreeStoreNode.
        """
        if '.' not in path:
            return self._remove_node(path)

        parent_store, label = self._htraverse(path, autocreate=False)
        return parent_store._remove_node(label)

    def pop(self, path: str, default: Any = None) -> Any:
        """Remove and return value at path.

        Args:
            path: Path to the node.
            default: Default value if path not found.

        Returns:
            The value of the removed node, or default.
        """
        try:
            node = self.delItem(path)
            return node.value
        except KeyError:
            return default

    # ==================== Iteration ====================

    def iter_keys(self) -> Iterator[str]:
        """Yield labels at this level in insertion order."""
        for n in self._order:
            yield n.label

    def iter_values(self) -> Iterator[Any]:
        """Yield values at this level in insertion order."""
        for n in self._order:
            yield n.value

    def iter_items(self) -> Iterator[tuple[str, Any]]:
        """Yield (label, value) pairs in insertion order."""
        for n in self._order:
            yield n.label, n.value

    def iter_nodes(self) -> Iterator[TreeStoreNode]:
        """Yield nodes at this level in insertion order."""
        yield from self._order

    def keys(self) -> list[str]:
        """Return list of labels at this level in insertion order."""
        return list(self.iter_keys())

    def values(self) -> list[Any]:
        """Return list of values at this level in insertion order."""
        return list(self.iter_values())

    def items(self) -> list[tuple[str, Any]]:
        """Return list of (label, value) pairs in insertion order."""
        return list(self.iter_items())

    def nodes(self) -> list[TreeStoreNode]:
        """Return list of nodes at this level in insertion order."""
        return list(self.iter_nodes())

    def getNodes(self, path: str = '') -> list[TreeStoreNode]:
        """Get nodes at path (or root if empty).

        Args:
            path: Optional path to get nodes from.

        Returns:
            List of TreeStoreNode at the specified level in insertion order.
        """
        if not path:
            return list(self._order)

        node = self.getNode(path)
        if node.is_branch:
            return list(node.value._order)
        return []

    # ==================== Digest ====================

    def iter_digest(self, what: str = '#k,#v') -> Iterator[Any]:
        """Yield data from nodes using Bag-style digest syntax.

        Args:
            what: Comma-separated specifiers:
                - #k: labels
                - #v: values
                - #a: all attributes (dict)
                - #a.attrname: specific attribute

        Yields:
            Values, or tuples if multiple specifiers.

        Example:
            >>> for label in store.iter_digest('#k'):
            ...     print(label)
        """
        specs = [s.strip() for s in what.split(',')]

        def _extract(node: TreeStoreNode, spec: str) -> Any:
            if spec == '#k':
                return node.label
            elif spec == '#v':
                return node.value
            elif spec == '#a':
                return node.attr
            elif spec.startswith('#a.'):
                return node.attr.get(spec[3:])
            else:
                raise ValueError(f"Unknown digest specifier: {spec}")

        if len(specs) == 1:
            spec = specs[0]
            for node in self._order:
                yield _extract(node, spec)
        else:
            for node in self._order:
                yield tuple(_extract(node, spec) for spec in specs)

    def digest(self, what: str = '#k,#v') -> list[Any]:
        """Extract data from nodes using Bag-style digest syntax.

        Args:
            what: Comma-separated specifiers:
                - #k: labels
                - #v: values
                - #a: all attributes (dict)
                - #a.attrname: specific attribute

        Returns:
            List of values, or list of tuples if multiple specifiers.

        Example:
            >>> store.digest('#k')  # ['label1', 'label2']
            >>> store.digest('#v')  # [value1, value2]
            >>> store.digest('#k,#v')  # [('label1', val1), ('label2', val2)]
            >>> store.digest('#a.color')  # ['red', 'blue']
        """
        return list(self.iter_digest(what))

    # ==================== Walk ====================

    def walk(
        self,
        callback: Callable[[TreeStoreNode], Any] | None = None,
        _prefix: str = ""
    ) -> Iterator[tuple[str, TreeStoreNode]] | None:
        """Walk the tree, optionally calling a callback on each node.

        Args:
            callback: Optional function to call on each node.
                      If provided, walk returns None.
            _prefix: Internal use for path building.

        Yields:
            Tuples of (path, node) if no callback provided.

        Example:
            >>> for path, node in store.walk():
            ...     print(path, node.value)

            >>> store.walk(lambda n: print(n.label))
        """
        if callback is not None:
            # Callback mode (like Bag)
            for node in self._order:
                callback(node)
                if node.is_branch:
                    node.value.walk(callback)
            return None

        # Generator mode
        def _walk_gen(store: TreeStore, prefix: str) -> Iterator[tuple[str, TreeStoreNode]]:
            for node in store._order:
                path = f"{prefix}.{node.label}" if prefix else node.label
                yield path, node
                if node.is_branch:
                    yield from _walk_gen(node.value, path)

        return _walk_gen(self, _prefix)

    # ==================== Navigation ====================

    @property
    def root(self) -> TreeStore:
        """Get the root TreeStore of this hierarchy."""
        if self.parent is None:
            return self
        return self.parent.parent.root if self.parent.parent else self

    @property
    def depth(self) -> int:
        """Get the depth of this store in the hierarchy (root=0)."""
        if self.parent is None:
            return 0
        return self.parent.parent.depth + 1 if self.parent.parent else 1

    @property
    def parentNode(self) -> TreeStoreNode | None:
        """Get the parent node (alias for self.parent)."""
        return self.parent

    # ==================== Conversion ====================

    def as_dict(self) -> dict[str, Any]:
        """Convert to plain dict (recursive).

        Branch nodes become nested dicts with their attributes and children.
        Leaf nodes become their value directly (or dict with _value if has attrs).
        """
        result: dict[str, Any] = {}
        for node in self._order:
            label = node.label
            if node.is_branch:
                child_dict = node.value.as_dict()
                if node.attr:
                    node_dict = dict(node.attr)
                    node_dict.update(child_dict)
                    result[label] = node_dict
                else:
                    result[label] = child_dict
            else:
                if node.attr:
                    result[label] = {'_value': node.value, **node.attr}
                else:
                    result[label] = node.value
        return result

    def clear(self) -> None:
        """Remove all nodes."""
        self._nodes.clear()
        self._order.clear()

    def get(self, label: str, default: Any = None) -> TreeStoreNode | None:
        """Get node by label at this level, with default."""
        return self._nodes.get(label, default)


# ==================== Builder Pattern ====================


def valid_children(*allowed: str, **constraints: str) -> Callable:
    """Decorator to specify valid children for a builder method.

    Can be used in two ways:

    1. Simple list of allowed tags:
        @valid_children('div', 'span', 'p')

    2. With cardinality constraints:
        @valid_children(div='0:', span='1:3', title='1')

    Cardinality format: 'min:max'
        - '0:' = zero or more (optional, unlimited)
        - '1:' = one or more (mandatory, unlimited)
        - '1' or '1:1' = exactly one (mandatory)
        - '0:3' = zero to three

    Args:
        *allowed: Tag names that are valid children (implies '0:').
        **constraints: Tag names with cardinality constraints.

    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        parsed: dict[str, tuple[int, int | None]] = {}

        for tag in allowed:
            parsed[tag] = (0, None)

        for tag, constraint in constraints.items():
            parsed[tag] = _parse_cardinality(constraint)

        func._valid_children = parsed  # type: ignore
        return func

    return decorator


def _parse_cardinality(spec: str | int | bool) -> tuple[int, int | None]:
    """Parse a cardinality specification."""
    if spec is True:
        return (0, None)
    if isinstance(spec, int):
        return (spec, spec)
    if not isinstance(spec, str):
        raise ValueError(f"Invalid cardinality spec: {spec}")

    if ':' not in spec:
        n = int(spec)
        return (n, n)

    parts = spec.split(':')
    min_val = int(parts[0]) if parts[0] else 0
    max_val = int(parts[1]) if parts[1] else None
    return (min_val, max_val)


class InvalidChildError(Exception):
    """Raised when an invalid child tag is used."""
    pass


class MissingChildError(Exception):
    """Raised when a mandatory child is missing."""
    pass


class TooManyChildrenError(Exception):
    """Raised when too many children of a type are added."""
    pass


class InvalidParentError(Exception):
    """Raised when a tag is used under an invalid parent."""
    pass


# ==================== Grammar System ====================


def element(
    tag: str | None = None,
    valid_children: dict[str, str] | str | None = None,
    valid_parent: str | None = None,
) -> Callable:
    """Decorator for grammar element methods with custom logic.

    Used to define elements in a Grammar class that have custom behavior
    (components). The method receives the builder node as first argument.

    Args:
        tag: Tag name(s), comma-separated for aliases. If None, uses method name.
        valid_children: Dict of {tag: cardinality} or comma-separated tag string.
        valid_parent: Comma-separated string of valid parent tags.

    Cardinality format:
        - '*' = zero or more (0:)
        - '+' = one or more (1:)
        - '?' = zero or one (0:1)
        - '1' = exactly one (1:1)
        - '1-3' or '1:3' = range

    Example:
        class HtmlGrammar(Grammar):
            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._element_config = {
            'tag': tag,
            'valid_children': valid_children,
            'valid_parent': valid_parent,
            'method': func,
        }
        return func

    return decorator


def _parse_cardinality_symbol(spec: str) -> tuple[int, int | None]:
    """Parse a cardinality specification with symbolic notation.

    Supports:
        - '*' = zero or more (0, None)
        - '+' = one or more (1, None)
        - '?' = zero or one (0, 1)
        - '1' = exactly one (1, 1)
        - '1-3' or '1:3' = range (1, 3)
        - '0:' = zero or more (0, None)
        - '1:' = one or more (1, None)
    """
    if spec == '*':
        return (0, None)
    if spec == '+':
        return (1, None)
    if spec == '?':
        return (0, 1)

    # Try range with dash
    if '-' in spec and ':' not in spec:
        parts = spec.split('-')
        return (int(parts[0]), int(parts[1]))

    # Fall back to original format with colon
    return _parse_cardinality(spec)


class Grammar:
    """Base class for defining builder grammars.

    Grammars define valid elements and their relationships using:
    - Properties that return dicts for groups of similar elements
    - @element decorated methods for elements with custom logic

    Groups can reference other groups via self.other_group.

    Example:
        class HtmlGrammar(Grammar):
            @property
            def flow(self):
                return dict(
                    tag='div,span,p',
                    valid_children={self.inline: '*'},
                )

            @property
            def inline(self):
                return dict(
                    tag='span,a,em,strong',
                )

            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node
    """

    def __init__(self) -> None:
        self._resolved: dict[str, dict[str, Any]] = {}
        self._tag_to_config: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, dict[str, Any]] = {}
        self._resolve_all()

    def _resolve_all(self) -> None:
        """Resolve all grammar definitions from properties and decorated methods."""
        # First pass: collect all definitions
        for name in dir(self):
            if name.startswith('_'):
                continue

            attr = getattr(self.__class__, name, None)

            # Check for @element decorated methods
            if callable(attr) and hasattr(attr, '_element_config'):
                config = attr._element_config.copy()
                tags = config.get('tag') or name
                config['_method_name'] = name
                self._store_config(tags, config)
                continue

            # Check for properties returning dicts
            if isinstance(attr, property):
                try:
                    value = getattr(self, name)
                    if isinstance(value, dict) and 'tag' in value:
                        config = value.copy()
                        config['_group_name'] = name
                        # Store group for later expansion
                        self._groups[name] = config
                        self._store_config(config['tag'], config)
                except Exception:
                    pass

    def _store_config(self, tags: str, config: dict[str, Any]) -> None:
        """Store configuration for one or more tags."""
        tag_list = [t.strip() for t in tags.split(',')]

        # Resolve valid_children references to other groups
        valid_children = config.get('valid_children')
        if valid_children:
            config['valid_children'] = self._resolve_children(valid_children)

        # Resolve valid_parent references
        valid_parent = config.get('valid_parent')
        if valid_parent:
            config['valid_parent'] = self._resolve_parent(valid_parent)

        # Store for each tag
        for tag in tag_list:
            self._tag_to_config[tag] = config

    def _resolve_children(
        self, valid_children: dict | str
    ) -> dict[str, tuple[int, int | None]]:
        """Store valid_children as {key: (min, max)}.

        Keys are stored as-is (can be tags or group names).
        Expansion to actual tags happens at validate() time.
        """
        result: dict[str, tuple[int, int | None]] = {}

        if isinstance(valid_children, str):
            # Simple comma-separated list, implies '*'
            for name in valid_children.split(','):
                result[name.strip()] = (0, None)
            return result

        for key, cardinality in valid_children.items():
            parsed = _parse_cardinality_symbol(cardinality)
            result[key] = parsed

        return result

    def _resolve_parent(self, valid_parent: str | dict) -> set[str]:
        """Resolve valid_parent to a set of tag names."""
        if isinstance(valid_parent, dict) and 'tag' in valid_parent:
            return set(t.strip() for t in valid_parent['tag'].split(','))
        if isinstance(valid_parent, str):
            return set(t.strip() for t in valid_parent.split(','))
        return set()

    def get_config(self, tag: str) -> dict[str, Any] | None:
        """Get configuration for a tag."""
        return self._tag_to_config.get(tag)

    def get_method(self, tag: str) -> Callable | None:
        """Get the custom method for a tag, if any."""
        config = self._tag_to_config.get(tag)
        if config and 'method' in config:
            return config['method']
        return None

    def get_all_tags(self) -> list[str]:
        """Get all defined tags."""
        return list(self._tag_to_config.keys())

    def expand_name(self, name: str) -> list[str]:
        """Expand a name (tag or group) to a list of tags.

        Args:
            name: A tag name, group name, or comma-separated list of both.

        Returns:
            List of tag names. If name is a tag, returns [name].
            If name is a group, returns all tags in the group.
            Comma-separated names are expanded individually.
        """
        result: list[str] = []
        for part in name.split(','):
            part = part.strip()
            # Check if it's a known tag
            if part in self._tag_to_config:
                result.append(part)
            else:
                # Try as a group name (property that returns dict with 'tag')
                group_config = self._groups.get(part)
                if group_config and 'tag' in group_config:
                    for tag in group_config['tag'].split(','):
                        result.append(tag.strip())
                else:
                    # Unknown name, treat as literal tag
                    result.append(part)
        return result


class TreeStoreBuilder(TreeStore):
    """Builder pattern for TreeStore with auto-labeling and validation.

    Use child() to create nodes with auto-generated labels (tag_N pattern).

    Can be used in two ways:

    1. Subclass to create domain-specific builders with @valid_children:

        >>> class HtmlBuilder(TreeStoreBuilder):
        ...     @valid_children('li')
        ...     def ul(self, **attr):
        ...         return self.child('ul', **attr)
        ...
        ...     def li(self, value=None, **attr):
        ...         return self.child('li', value=value, **attr)
        ...
        >>> builder = HtmlBuilder()
        >>> ul = builder.ul()
        >>> ul.li('Item 1')
        >>> ul.li('Item 2')

    2. Pass a Grammar class for dynamic tag methods:

        >>> class HtmlGrammar(Grammar):
        ...     @property
        ...     def block(self):
        ...         return dict(tag='div,section', valid_children={'div,span': '*'})
        ...
        ...     @element(tag='ul,ol', valid_children={'li': '+'})
        ...     def ul(self, node, items=None, **attr):
        ...         if items:
        ...             for item in items:
        ...                 node.li(value=item)
        ...         return node
        ...
        >>> builder = TreeStoreBuilder(grammar=HtmlGrammar)
        >>> builder.div(id='main')     # from grammar property
        >>> builder.ul(items=['a','b']) # from @element method
    """

    __slots__ = ('_tag_counters', '_grammar')

    node_factory: type[TreeStoreNode] = BuilderNode

    def __init__(
        self,
        parent: TreeStoreNode | None = None,
        grammar: type[Grammar] | Grammar | None = None,
    ) -> None:
        """Initialize a TreeStoreBuilder.

        Args:
            parent: The TreeStoreNode that contains this store as its value.
            grammar: A Grammar class or instance defining valid tags and rules.
        """
        super().__init__(parent)
        self._tag_counters: dict[str, int] = {}

        # Handle grammar parameter
        if grammar is None:
            self._grammar: Grammar | None = None
        elif isinstance(grammar, type):
            # Grammar class passed, instantiate it
            self._grammar = grammar()
        else:
            # Grammar instance passed
            self._grammar = grammar

    @property
    def store(self) -> TreeStore:
        """Access the underlying TreeStore."""
        return self

    @property
    def grammar(self) -> Grammar | None:
        """Access the grammar instance.

        Use this to access tag methods when they clash with TreeStore methods.
        Example: builder.grammar.keys instead of builder.keys
        """
        return self._grammar

    def __getattr__(self, name: str) -> Any:
        """Dynamic tag method access via grammar.

        If a grammar is defined and the name matches a tag, returns a callable
        that creates a child node with that tag.

        Real methods on TreeStoreBuilder take precedence (e.g., keys(), values()).
        For clashing names, use builder.grammar.tagname or builder.child('tagname').
        """
        # Check if we have a grammar and this name is a valid tag
        if self._grammar is not None:
            config = self._grammar.get_config(name)
            if config is not None:
                # Return a callable that creates a child with this tag
                return self._make_tag_method(name, config)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def _make_tag_method(
        self, tag: str, config: dict[str, Any]
    ) -> Callable[..., TreeStoreBuilder | BuilderNode]:
        """Create a tag method for dynamic grammar access."""
        custom_method = config.get('method')

        def tag_method(
            value: Any = None,
            _position: str | None = None,
            **attr: Any
        ) -> TreeStoreBuilder | BuilderNode:
            # Create the child node
            child = self.child(tag, value=value, _position=_position, **attr)

            # If there's a custom method, call it with the node
            if custom_method is not None:
                result = custom_method(self._grammar, child, **attr)
                if result is not None:
                    return result

            return child

        return tag_method

    def _generate_label(self, tag: str) -> str:
        """Generate a unique label for a tag.

        Uses pattern: tag_0, tag_1, tag_2, ...
        Counter always increments (never reuses numbers).
        """
        n = self._tag_counters.get(tag, 0)
        self._tag_counters[tag] = n + 1
        return f"{tag}_{n}"

    def _is_auto_label(self, label: str, tag: str) -> bool:
        """Check if a label was auto-generated."""
        pattern = f"^{re.escape(tag)}_\\d+$"
        return bool(re.match(pattern, label))

    def child(
        self,
        tag: str,
        label: str | None = None,
        value: Any = None,
        attributes: dict[str, Any] | None = None,
        _position: str | None = None,
        **attr: Any
    ) -> TreeStoreBuilder | BuilderNode:
        """Create a child node with auto-generated label.

        Args:
            tag: The node's type (e.g., 'div', 'ul').
            label: Explicit label (optional, auto-generated if None).
            value: If provided, creates a leaf node; otherwise creates a branch.
            attributes: Dict of attributes (merged with **attr).
            _position: Position specifier (Bag-style):
                - None or '>': append to end (default)
                - '<': insert at beginning
                - '<label': insert before label
                - '>label': insert after label
                - '<#N': insert before position N
                - '>#N': insert after position N
                - '#N': insert at exact position N
            **attr: Node attributes as kwargs.

        Returns:
            TreeStoreBuilder if branch (for adding children), BuilderNode if leaf.

        Examples:
            >>> div = builder.child('div', color='red')  # branch, label='div_0'
            >>> builder.child('li', value='Hello')       # leaf, label='li_0'
            >>> builder.child('li', value='First', _position='<')  # insert at beginning
        """
        # Merge attributes
        final_attr: dict[str, Any] = {}
        if attributes:
            final_attr.update(attributes)
        final_attr.update(attr)

        # Generate label if not provided
        if label is None:
            label = self._generate_label(tag)

        # Note: validation is now explicit via validate() method

        if value is not None:
            # Create leaf node
            node = self.node_factory(label, final_attr, value, parent=self, tag=tag)
            self._insert_node(node, _position)
            return node
        else:
            # Create branch node with new Builder instance
            # Propagate grammar to child builder
            child_builder = self.__class__(grammar=self._grammar)
            node = self.node_factory(label, final_attr, value=child_builder, parent=self, tag=tag)
            child_builder.parent = node
            self._insert_node(node, _position)
            return child_builder

    def reindex(self) -> None:
        """Renumber auto-generated labels to remove gaps.

        Only affects labels matching pattern {tag}_{number}.
        Explicit labels are left unchanged.

        Example:
            Before: div_0, div_3, div_7, main
            After:  div_0, div_1, div_2, main
        """
        # Group nodes by tag
        by_tag: dict[str, list[tuple[str, TreeStoreNode]]] = {}
        for label, node in list(self._nodes.items()):
            if node.tag and self._is_auto_label(label, node.tag):
                by_tag.setdefault(node.tag, []).append((label, node))

        # Renumber each tag group
        for tag, tag_nodes in by_tag.items():
            # Sort by current number to preserve order
            tag_nodes.sort(key=lambda x: int(x[0].rsplit('_', 1)[1]))

            # Remove old labels
            for old_label, _ in tag_nodes:
                del self._nodes[old_label]

            # Add with new labels
            for i, (_, node) in enumerate(tag_nodes):
                new_label = f"{tag}_{i}"
                node.label = new_label
                self._nodes[new_label] = node

            # Reset counter
            self._tag_counters[tag] = len(tag_nodes)

        # Recursively reindex children
        for node in self._nodes.values():
            if node.is_branch and isinstance(node.value, TreeStoreBuilder):
                node.value.reindex()

    def by_tag(self, tag: str) -> list[TreeStoreNode]:
        """Get all nodes with the given tag."""
        return [n for n in self._nodes.values() if n.tag == tag]

    def validate(self) -> None:
        """Validate the tree against the grammar.

        Checks:
        - valid_children: each node's children are allowed
        - valid_parent: each node is under an allowed parent
        - cardinality: min/max counts for children

        Raises:
            InvalidChildError: If a child tag is not allowed.
            InvalidParentError: If a node is under an invalid parent.
            MissingChildError: If a mandatory child is missing.
            TooManyChildrenError: If too many children of a type exist.
            ValueError: If no grammar is defined.
        """
        if self._grammar is None:
            raise ValueError("Cannot validate: no grammar defined")

        self._validate_node(self, parent_tag=None)

    def _validate_node(
        self, store: TreeStore, parent_tag: str | None
    ) -> None:
        """Recursively validate a store and its children."""
        # Get valid_children for this parent and expand group names
        valid_children_raw: dict[str, tuple[int, int | None]] | None = None
        valid_children_expanded: dict[str, tuple[int, int | None]] | None = None
        if parent_tag is not None and self._grammar is not None:
            config = self._grammar.get_config(parent_tag)
            if config is not None:
                valid_children_raw = config.get('valid_children')
                if valid_children_raw is not None:
                    # Expand group names to actual tags
                    valid_children_expanded = {}
                    for key, cardinality in valid_children_raw.items():
                        expanded_tags = self._grammar.expand_name(key)
                        for tag in expanded_tags:
                            valid_children_expanded[tag] = cardinality

        # Count children by tag
        child_counts: dict[str, int] = {}

        for node in store._order:
            tag = node.tag
            if tag is None:
                continue

            # Check valid_parent constraint
            if self._grammar is not None:
                node_config = self._grammar.get_config(tag)
                if node_config is not None:
                    valid_parent = node_config.get('valid_parent')
                    if valid_parent is not None and parent_tag is not None:
                        if parent_tag not in valid_parent:
                            raise InvalidParentError(
                                f"Tag '{tag}' cannot be a child of '{parent_tag}'. "
                                f"Valid parents: {list(valid_parent)}"
                            )

            # Check valid_children constraint
            if valid_children_expanded is not None:
                if tag not in valid_children_expanded:
                    raise InvalidChildError(
                        f"Tag '{tag}' is not valid under '{parent_tag}'. "
                        f"Allowed: {list(valid_children_expanded.keys())}"
                    )

            # Count this tag
            child_counts[tag] = child_counts.get(tag, 0) + 1

            # Recursively validate children
            if node.is_branch and isinstance(node.value, TreeStore):
                self._validate_node(node.value, parent_tag=tag)

        # Check cardinality constraints
        if valid_children_expanded is not None:
            for tag, (min_count, max_count) in valid_children_expanded.items():
                count = child_counts.get(tag, 0)

                if count < min_count:
                    raise MissingChildError(
                        f"Tag '{parent_tag}' requires at least {min_count} "
                        f"'{tag}' children, found {count}"
                    )

                if max_count is not None and count > max_count:
                    raise TooManyChildrenError(
                        f"Tag '{parent_tag}' allows at most {max_count} "
                        f"'{tag}' children, found {count}"
                    )
