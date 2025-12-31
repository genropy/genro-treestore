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

    def __init__(self, parent: TreeStoreNode | None = None) -> None:
        """Initialize a TreeStore.

        Args:
            parent: The TreeStoreNode that contains this store as its value.
        """
        self._nodes: dict[str, TreeStoreNode] = {}
        self._order: list[TreeStoreNode] = []  # Maintains insertion order for positional access
        self.parent = parent

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


class TreeStoreBuilder(TreeStore):
    """Builder pattern for TreeStore with auto-labeling and validation.

    Use child() to create nodes with auto-generated labels (tag_N pattern).
    Subclass to create domain-specific builders with @valid_children.

    Example:
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
    """

    __slots__ = ('_tag_counters',)

    node_factory: type[TreeStoreNode] = BuilderNode

    def __init__(self, parent: TreeStoreNode | None = None) -> None:
        """Initialize a TreeStoreBuilder."""
        super().__init__(parent)
        self._tag_counters: dict[str, int] = {}

    @property
    def store(self) -> TreeStore:
        """Access the underlying TreeStore."""
        return self

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

    def _get_valid_children(self) -> dict[str, tuple[int, int | None]] | None:
        """Get valid children from the method that created this context."""
        if self.parent is None:
            return None

        tag = self.parent.tag
        if tag is None:
            return None

        # Find the method for this tag on the builder class
        method = getattr(self.__class__, tag, None)
        if method is None:
            # Try on root builder if we're a child store
            root = self.root
            if root is not self:
                method = getattr(root.__class__, tag, None)

        if method is None:
            return None

        return getattr(method, '_valid_children', None)

    def _validate_child(self, tag: str) -> None:
        """Validate that a child tag is allowed."""
        valid = self._get_valid_children()
        if valid is None:
            return

        if tag not in valid:
            raise InvalidChildError(
                f"Tag '{tag}' is not valid here. Allowed: {list(valid.keys())}"
            )

        # Check max count
        min_count, max_count = valid[tag]
        current_count = sum(1 for n in self._nodes.values() if n.tag == tag)
        if max_count is not None and current_count >= max_count:
            raise TooManyChildrenError(
                f"Maximum {max_count} '{tag}' children allowed, "
                f"already have {current_count}"
            )

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

        # Validate child if constraints exist
        self._validate_child(tag)

        if value is not None:
            # Create leaf node
            node = self.node_factory(label, final_attr, value, parent=self, tag=tag)
            self._insert_node(node, _position)
            return node
        else:
            # Create branch node with new Builder instance
            child_builder = self.__class__()
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
