# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore - A hierarchical structure with builder pattern support.

This module provides:
- TreeStoreNode: A node with label, attributes, and value
- TreeStore: A container of TreeStoreNodes with builder methods
- TreeStoreBuilder: Base class for typed builders with tag support
- valid_children: Decorator for child validation in typed builders

The tag (node type) is stored in attr['_tag'] for builder use cases.
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
    - attr: Dictionary of attributes (may include '_tag' for typed builders)
    - value: Either a scalar value or a TreeStore (for children)
    - parent: Reference to the containing TreeStore

    Example:
        >>> node = TreeStoreNode('user_0', {'_tag': 'user', 'id': 1}, TreeStore())
        >>> node.label
        'user_0'
        >>> node.tag  # convenience property for attr.get('_tag')
        'user'
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
            attr: Optional dictionary of attributes (may include '_tag').
            value: The node's value (scalar or TreeStore for children).
            parent: The TreeStore containing this node.
        """
        self.label = label
        self.attr = attr or {}
        self.value = value
        self.parent = parent

    @property
    def tag(self) -> str | None:
        """Get the node's tag (type) from attr['_tag']."""
        return self.attr.get('_tag')

    def __repr__(self) -> str:
        value_repr = (
            f"TreeStore({len(self.value)})"
            if isinstance(self.value, TreeStore)
            else repr(self.value)
        )
        tag = self.tag
        if tag:
            return f"TreeStoreNode({self.label!r}, tag={tag!r}, value={value_repr})"
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
        """Return parent TreeStore for chaining after leaf operations.

        Example:
            >>> ul.li('pino')._.li('gino')  # chain on same parent
        """
        if self.parent is None:
            raise ValueError("Node has no parent")
        return self.parent

    @property
    def root(self) -> TreeStore:
        """Get the root TreeStore of this node's hierarchy."""
        if self.parent is None:
            raise ValueError("Node has no parent")
        return self.parent.root


class TreeStore:
    """A container of TreeStoreNodes with hierarchical navigation and builder methods.

    TreeStore maintains:
    - nodes: Dictionary of {label: TreeStoreNode}
    - parent: Reference to the TreeStoreNode that contains this store
    - _tag_counters: Counters for auto-generated labels per tag

    The dual relationship enables bidirectional traversal:
    - node.parent -> TreeStore containing the node
    - store.parent -> TreeStoreNode that has this store as value

    Example:
        >>> store = TreeStore()
        >>> div = store.child('div', color='red')
        >>> div.child('span', 'Hello')
    """

    __slots__ = ('nodes', 'parent', '_tag', '_tag_counters')

    def __init__(self, parent: TreeStoreNode | None = None) -> None:
        """Initialize a TreeStore.

        Args:
            parent: The TreeStoreNode that contains this store as its value.
        """
        self.nodes: dict[str, TreeStoreNode] = {}
        self.parent = parent
        self._tag: str | None = None  # Tag for validation context
        self._tag_counters: dict[str, int] = {}  # {tag: next_number}

    def __repr__(self) -> str:
        return f"TreeStore({list(self.nodes.keys())})"

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Iterator[str]:
        return iter(self.nodes)

    def __contains__(self, label: str) -> bool:
        return label in self.nodes

    def _parse_path_segment(self, segment: str) -> tuple[bool, int | str]:
        """Parse a path segment, detecting positional index (#N) syntax.

        Returns:
            Tuple of (is_positional, index_or_label)
        """
        if segment.startswith('#') and segment[1:].isdigit():
            return True, int(segment[1:])
        return False, segment

    def _get_node_by_position(self, index: int) -> TreeStoreNode:
        """Get node by positional index."""
        labels = list(self.nodes.keys())
        if index < 0 or index >= len(labels):
            raise KeyError(f"Position #{index} out of range (0-{len(labels)-1})")
        return self.nodes[labels[index]]

    def _resolve_path(self, path: str) -> tuple[TreeStoreNode, str | None]:
        """Resolve a path to a node and optional attribute name.

        Args:
            path: Path string, optionally ending with ?attr_name

        Returns:
            Tuple of (node, attr_name or None)
        """
        # Check for attribute access
        attr_name = None
        if '?' in path:
            path, attr_name = path.rsplit('?', 1)

        # Simple case: no dots
        if '.' not in path:
            is_pos, key = self._parse_path_segment(path)
            if is_pos:
                return self._get_node_by_position(key), attr_name
            return self.nodes[path], attr_name

        # Dotted path
        parts = path.split('.')
        current = self
        node = None
        for i, part in enumerate(parts):
            is_pos, key = self._parse_path_segment(part)
            if is_pos:
                node = current._get_node_by_position(key)
            else:
                node = current.nodes[key]

            if i < len(parts) - 1:
                # Not the last part, descend into branch
                if not node.is_branch:
                    raise KeyError(f"'{part}' is not a branch at path '{'.'.join(parts[:i+1])}'")
                current = node.value
        return node, attr_name

    def __getitem__(self, path: str) -> TreeStoreNode | Any:
        """Get node or attribute by path.

        Args:
            path: Single label, dotted path, or positional path.
                  Supports #N syntax for positional access.
                  Supports ?attr suffix for attribute access.

        Returns:
            TreeStoreNode at the specified path, or attribute value if ?attr is used.

        Example:
            >>> store['div_0']              # by label -> TreeStoreNode
            >>> store['#0']                 # first node (positional)
            >>> store['div_0.ul_0.li_0']    # dotted path by labels
            >>> store['#0.ul_0.#3']         # mixed: first child, then ul_0, then 4th child
            >>> store['div_0?color']        # get 'color' attribute of div_0
            >>> store['div_0.ul_0?class']   # get 'class' attribute of ul_0
        """
        node, attr_name = self._resolve_path(path)
        if attr_name is not None:
            return node.attr.get(attr_name)
        return node

    def __setitem__(self, path: str, value: Any) -> None:
        """Set attribute value by path.

        Args:
            path: Path with ?attr suffix for attribute access.
            value: Value to set.

        Example:
            >>> store['div_0?color'] = 'red'
            >>> store['div_0.ul_0.li_0?class'] = 'active'
        """
        node, attr_name = self._resolve_path(path)
        if attr_name is None:
            raise KeyError("Cannot set node directly, use ?attr syntax to set attributes")
        node.attr[attr_name] = value

    @property
    def _(self) -> TreeStore:
        """Return parent's parent TreeStore for navigation.

        Example:
            >>> child_store._.other_method()  # go up one level
        """
        if self.parent is None:
            raise ValueError("Already at root level")
        if self.parent.parent is None:
            raise ValueError("Already at root level")
        return self.parent.parent

    @property
    def root(self) -> TreeStore:
        """Get the root TreeStore of this hierarchy."""
        if self.parent is None:
            return self
        return self.parent.root

    @property
    def depth(self) -> int:
        """Get the depth of this store in the hierarchy (root=0)."""
        if self.parent is None:
            return 0
        return self.parent.parent.depth + 1 if self.parent.parent else 1

    def _generate_label(self, tag: str) -> str:
        """Generate a unique label for a tag.

        Uses pattern: tag_0, tag_1, tag_2, ...
        Counter always increments (never reuses numbers).
        """
        n = self._tag_counters.get(tag, 0)
        self._tag_counters[tag] = n + 1
        return f"{tag}_{n}"

    def _is_auto_label(self, label: str, tag: str) -> bool:
        """Check if a label was auto-generated.

        Auto labels match pattern: {tag}_{number}
        """
        pattern = f"^{re.escape(tag)}_\\d+$"
        return bool(re.match(pattern, label))

    def child(
        self,
        tag: str,
        label: str | None = None,
        value: Any = None,
        attributes: dict[str, Any] | None = None,
        **attr
    ) -> TreeStore | TreeStoreNode:
        """Create a child node.

        Args:
            tag: The node's type (e.g., 'div', 'ul').
            label: Explicit label (optional, auto-generated if None).
            value: If provided, creates a leaf node; otherwise creates a branch.
            attributes: Dict of attributes (merged with **attr).
            **attr: Node attributes as kwargs.

        Returns:
            TreeStore if branch (for adding children), TreeStoreNode if leaf.

        Examples:
            >>> div = store.child('div', color='red')  # branch, label='div_0'
            >>> store.child('div', label='main')       # branch, label='main'
            >>> store.child('li', value='Hello')       # leaf, label='li_0'
            >>> store.child('li', label='item1', value='Hello')  # leaf, label='item1'
        """
        # Merge attributes dict with kwargs, add _tag
        final_attr: dict[str, Any] = {'_tag': tag}
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
            node = TreeStoreNode(label, final_attr, value, parent=self)
            self.nodes[label] = node
            return node
        else:
            # Create branch node with TreeStore as value
            child_store = self.__class__.__new__(self.__class__)
            child_store.nodes = {}
            child_store.parent = None
            child_store._tag = None
            child_store._tag_counters = {}

            node = TreeStoreNode(label, final_attr, value=child_store, parent=self)
            child_store.parent = node  # Dual relationship
            child_store._tag = tag  # For validation context
            self.nodes[label] = node
            return child_store

    def _get_valid_children(self) -> dict[str, tuple[int, int | None]] | None:
        """Get valid children constraints for this store's context."""
        # This is overridden in typed builders
        return None

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
        current_count = sum(1 for n in self.nodes.values() if n.tag == tag)
        if max_count is not None and current_count >= max_count:
            raise TooManyChildrenError(
                f"Maximum {max_count} '{tag}' children allowed, "
                f"already have {current_count}"
            )

    def get(self, label: str, default: Any = None) -> TreeStoreNode | Any:
        """Get a node by label, with optional default."""
        return self.nodes.get(label, default)

    def keys(self) -> Iterator[str]:
        """Iterate over node labels."""
        return iter(self.nodes.keys())

    def values(self) -> Iterator[TreeStoreNode]:
        """Iterate over nodes."""
        return iter(self.nodes.values())

    def items(self) -> Iterator[tuple[str, TreeStoreNode]]:
        """Iterate over (label, node) pairs."""
        return iter(self.nodes.items())

    def by_tag(self, tag: str) -> list[TreeStoreNode]:
        """Get all nodes with the given tag."""
        return [n for n in self.nodes.values() if n.tag == tag]

    def pop(self, label: str) -> TreeStoreNode:
        """Remove and return a node by label."""
        return self.nodes.pop(label)

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
        for label, node in list(self.nodes.items()):
            if self._is_auto_label(label, node.tag):
                by_tag.setdefault(node.tag, []).append((label, node))

        # Renumber each tag group
        for tag, nodes in by_tag.items():
            # Sort by current number to preserve order
            nodes.sort(key=lambda x: int(x[0].rsplit('_', 1)[1]))

            # Remove old labels
            for old_label, _ in nodes:
                del self.nodes[old_label]

            # Add with new labels
            for i, (_, node) in enumerate(nodes):
                new_label = f"{tag}_{i}"
                node.label = new_label
                self.nodes[new_label] = node

            # Reset counter
            self._tag_counters[tag] = len(nodes)

        # Recursively reindex children
        for node in self.nodes.values():
            if node.is_branch:
                node.value.reindex()

    def as_dict(self) -> dict[str, Any]:
        """Convert to plain dict (recursive).

        Branch nodes become nested dicts with their attributes and children.
        Leaf nodes become their value directly (or dict with _value if has attrs).
        """
        result: dict[str, Any] = {}
        for label, node in self.nodes.items():
            if node.is_branch:
                child_dict = node.value.as_dict()
                # Start with attributes (includes _tag if set)
                node_dict = dict(node.attr)
                node_dict.update(child_dict)
                result[label] = node_dict
            else:
                # Leaf: check if has meaningful attrs beyond _tag
                other_attrs = {k: v for k, v in node.attr.items() if k != '_tag'}
                if other_attrs:
                    result[label] = {'_value': node.value, **node.attr}
                else:
                    result[label] = node.value
        return result

    def walk(
        self, _prefix: str = ""
    ) -> Iterator[tuple[str, TreeStoreNode]]:
        """Iterate over all paths and nodes.

        Yields:
            Tuples of (path, node) for each node in the tree.
        """
        for label, node in self.nodes.items():
            path = f"{_prefix}.{label}" if _prefix else label
            yield path, node
            if node.is_branch:
                yield from node.value.walk(_prefix=path)


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
    """Base class for typed builders with validation.

    Subclass this to create domain-specific builders (HTML, XML, etc.)
    with typed methods and @valid_children validation.

    Example:
        >>> class HtmlBuilder(TreeStoreBuilder):
        ...     @valid_children('li')
        ...     def ul(self, label: str = None, **attr) -> TreeStore:
        ...         return self.child('ul', label, **attr)
        ...
        ...     def li(self, value: str = None, label: str = None, **attr):
        ...         return self.child('li', label, value=value, **attr)
    """

    def _get_valid_children(self) -> dict[str, tuple[int, int | None]] | None:
        """Get valid children from the method that created this context."""
        if self._tag is None:
            return None

        # Find the method for this tag on the builder class
        method = getattr(self.__class__, self._tag, None)
        if method is None:
            # Try on root builder if we're a child store
            root = self.root
            if root is not self:
                method = getattr(root.__class__, self._tag, None)

        if method is None:
            return None

        return getattr(method, '_valid_children', None)
