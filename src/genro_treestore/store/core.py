# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore - A lightweight hierarchical data structure.

This module provides the TreeStore class, the core container for hierarchical
data in the genro-treestore library. TreeStore offers O(1) lookup performance,
path-based navigation, and reactive subscriptions for change detection.

Key Features:
    - **Hierarchical storage**: Nested TreeStoreNode instances forming a tree
    - **O(1) lookup**: Internal dict-based storage for fast access by label
    - **Path navigation**: Dotted paths ('a.b.c') and positional syntax ('#0.#1')
    - **Builder pattern**: Optional builder for domain-specific fluent APIs
    - **Reactive subscriptions**: Event notifications on data changes
    - **Lazy resolution**: Support for resolvers that compute values on demand

Path Syntax:
    - Dotted paths: 'parent.child.grandchild'
    - Positional: '#0' (first child), '#-1' (last child)
    - Attribute access: 'node?attribute'
    - Combined: 'parent.#0?color'

Example:
    Basic usage::

        store = TreeStore()
        store.set_item('config.database.host', 'localhost')
        store.set_item('config.database.port', 5432)

        print(store['config.database.host'])  # 'localhost'

        # With attributes
        store.set_item('config.debug', True, level='verbose')
        print(store['config.debug?level'])  # 'verbose'

    With builder::

        store = TreeStore(builder=HtmlBuilder())
        body = store.body()
        body.div(id='main').p('Hello World')
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, TYPE_CHECKING

from .node import TreeStoreNode
from .subscription import SubscriptionMixin, SubscriberCallback
from .loading import load_from_dict, load_from_list, load_from_treestore

if TYPE_CHECKING:
    pass


class TreeStore(SubscriptionMixin):
    """A hierarchical data container with O(1) lookup.

    TreeStore provides:
    - set_item(path, value, **attr): Create/update nodes with autocreate
    - get_item(path) / store[path]: Get values
    - get_attr(path, attr) / set_attr(path, **attr): Attribute access
    - digest(what): Extract data with #k, #v, #a syntax

    The internal storage uses dict for O(1) lookup performance.

    Attributes:
        parent: The TreeStoreNode that contains this store as its value,
            or None if this is a root store.

    Example:
        >>> store = TreeStore()
        >>> store.set_item('html.body.div', color='red')
        >>> store['html.body.div?color']
        'red'
    """

    __slots__ = (
        '_nodes', '_order', 'parent', '_builder',
        '_upd_subscribers', '_ins_subscribers', '_del_subscribers',
        '_raise_on_error', '_validator',
    )

    def __init__(
        self,
        source: dict | list | TreeStore | None = None,
        parent: TreeStoreNode | None = None,
        builder: Any | None = None,
        raise_on_error: bool = True,
    ) -> None:
        """Initialize a TreeStore.

        Args:
            source: Optional initial data. Can be:
                - dict: Nested dict converted to nodes. Keys with '_' prefix
                  are treated as attributes (e.g., {'_color': 'red', 'child': ...})
                - TreeStore: Copy from another TreeStore
                - list: List of tuples (label, value) or (label, value, attr)
            parent: The TreeStoreNode that contains this store as its value.
            builder: Optional builder object that provides domain-specific methods.
                When set, attribute access delegates to the builder, enabling
                fluent API like store.div(), store.meta(), etc.
            raise_on_error: If True (default), raises ValueError on hard errors
                (invalid attributes, invalid child tags, too many children).
                Soft errors (missing required children) are always collected
                in node._invalid_reasons without raising.
                If False, all errors are collected without raising.

        Example:
            >>> TreeStore({'a': 1, 'b': {'c': 2}})
            >>> TreeStore([('x', 1), ('y', 2, {'color': 'red'})])
            >>> TreeStore(other_store)  # copy
            >>> TreeStore(builder=HtmlBodyBuilder())  # with builder
            >>> TreeStore(builder=HtmlBuilder(), raise_on_error=False)  # permissive mode
        """
        self._nodes: dict[str, TreeStoreNode] = {}
        self._order: list[TreeStoreNode] = []
        self.parent = parent
        self._builder = builder
        self._upd_subscribers: dict[str, SubscriberCallback] = {}
        self._ins_subscribers: dict[str, SubscriberCallback] = {}
        self._del_subscribers: dict[str, SubscriberCallback] = {}
        self._raise_on_error = raise_on_error
        self._validator = None

        # Auto-register validation subscriber if builder is set
        if builder is not None and parent is None:
            from ..validation import ValidationSubscriber
            self._validator = ValidationSubscriber(self)

        if source is not None:
            self._load_source(source)

    def _load_source(
        self, source: dict | list | TreeStore
    ) -> None:
        """Load data from source into this TreeStore.

        Delegates to the appropriate loading function based on source type.

        Args:
            source: Data to load (dict, list, or TreeStore).

        Raises:
            TypeError: If source is not dict, list, or TreeStore.
        """
        if isinstance(source, dict):
            load_from_dict(self, source)
        elif isinstance(source, TreeStore):
            load_from_treestore(self, source)
        elif isinstance(source, list):
            load_from_list(self, source)
        else:
            raise TypeError(
                f"source must be dict, list, or TreeStore, not {type(source).__name__}"
            )

    # ==================== Special Methods ====================

    def __repr__(self) -> str:
        """Return string representation showing node labels."""
        return f"TreeStore({list(self._nodes.keys())})"

    def __len__(self) -> int:
        """Return the number of direct children in this store."""
        return len(self._nodes)

    def __iter__(self) -> Iterator[TreeStoreNode]:
        """Iterate over direct child nodes in insertion order."""
        return iter(self._order)

    def __contains__(self, label: str) -> bool:
        """Check if a label exists at root level or as a path.

        Args:
            label: Label or dotted path to check.

        Returns:
            True if the label/path exists, False otherwise.
        """
        if '.' not in label:
            return label in self._nodes
        try:
            self.get_node(label)
            return True
        except KeyError:
            return False

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to builder if present.

        If a builder is set and has a method matching the name,
        returns a callable that invokes the builder method with
        this store as the target.

        Args:
            name: Attribute name (e.g., 'div', 'meta', 'span')

        Returns:
            Callable that creates a child via the builder.

        Raises:
            AttributeError: If no builder or builder has no such method.
        """
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        if self._builder is not None:
            # Let the builder raise its own AttributeError with a descriptive message
            handler = getattr(self._builder, name)
            if callable(handler):
                return lambda _nodelabel=None, **attr: handler(self, tag=name, label=_nodelabel, **attr)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    @property
    def builder(self) -> Any:
        """Access the builder instance."""
        return self._builder

    # ==================== Path Utilities ====================

    def _parse_path_segment(self, segment: str) -> tuple[bool, int | str]:
        """Parse a path segment, detecting positional index (#N) syntax.

        Args:
            segment: A single path segment (e.g., 'child' or '#0').

        Returns:
            Tuple of (is_positional, index_or_label) where:
            - is_positional: True if segment uses #N syntax
            - index_or_label: Integer index if positional, string label otherwise
        """
        if segment.startswith('#'):
            rest = segment[1:]
            if rest.lstrip('-').isdigit():
                return True, int(rest)
        return False, segment

    def _get_node_by_position(self, index: int) -> TreeStoreNode:
        """Get node by positional index (O(1) via _order list).

        Args:
            index: Position index (supports negative indexing).

        Returns:
            TreeStoreNode at the specified position.

        Raises:
            KeyError: If index is out of range.
        """
        if index < 0:
            index = len(self._order) + index
        if index < 0 or index >= len(self._order):
            raise KeyError(f"Position #{index} out of range (0-{len(self._order)-1})")
        return self._order[index]

    def _index_of(self, label: str) -> int:
        """Get the position index of a node by its label.

        Args:
            label: The label to search for.

        Returns:
            Integer position index in _order list.

        Raises:
            KeyError: If label not found.
        """
        for i, node in enumerate(self._order):
            if node.label == label:
                return i
        raise KeyError(f"Label '{label}' not found")

    def _insert_node(
        self,
        node: TreeStoreNode,
        position: str | None = None,
        trigger: bool = True,
        reason: str | None = None,
    ) -> None:
        """Insert a node into both _nodes dict and _order list.

        Args:
            node: The node to insert.
            position: Position specifier:
                - None or '>': append to end (default)
                - '<': insert at beginning
                - '<label': insert before label
                - '>label': insert after label
                - '<#N': insert before position N
                - '>#N': insert after position N
                - '#N': insert at exact position N
            trigger: If True, notify subscribers of the insertion.
            reason: Optional reason string for the trigger.
        """
        self._nodes[node.label] = node

        if position is None or position == '>':
            idx = len(self._order)
            self._order.append(node)
        elif position == '<':
            idx = 0
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
            idx = len(self._order)
            self._order.append(node)

        if trigger:
            self._on_node_inserted(node, idx, reason=reason)

    def _remove_node(
        self,
        label: str,
        trigger: bool = True,
        reason: str | None = None,
    ) -> TreeStoreNode:
        """Remove a node from both _nodes dict and _order list.

        Args:
            label: The label of the node to remove.
            trigger: If True, notify subscribers of the deletion.
            reason: Optional reason string for the trigger.

        Returns:
            The removed node.

        Raises:
            KeyError: If label not found.
        """
        node = self._nodes.pop(label)
        idx = self._order.index(node)
        self._order.remove(node)

        if trigger:
            self._on_node_deleted(node, idx, reason=reason)

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

        Raises:
            KeyError: If path segment not found and autocreate is False.
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
                        child_store = TreeStore(builder=current._builder)
                        node = TreeStoreNode(key, {}, value=child_store, parent=current)
                        child_store.parent = node
                        current._insert_node(node)
                    else:
                        raise KeyError(f"Path segment '{key}' not found")
                node = current._nodes[key]

            # If node has a resolver, resolve it to populate node._value
            if node._resolver is not None:
                resolver = node._resolver
                # Check cache first
                if resolver.cache_time != 0 and not resolver.expired:
                    resolved = resolver._cache
                else:
                    resolved = resolver.load()  # smartasync handles sync/async
                    if resolver.cache_time != 0:
                        resolver._update_cache(resolved)
                # Always populate node._value for traversal
                node._value = resolved

            if not node.is_branch:
                if autocreate:
                    # Convert leaf to branch
                    child_store = TreeStore(builder=current._builder)
                    child_store.parent = node
                    node._value = child_store
                else:
                    remaining = '.'.join(parts[i+1:])
                    raise KeyError(f"'{part}' is a leaf, cannot access '{remaining}'")

            # Use _value directly to avoid re-triggering resolver
            current = node._value

        return current, parts[-1]

    # ==================== Core API ====================

    def set_item(
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
            _position: Position specifier:
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
            >>> store.set_item('html').set_item('body').set_item('div', color='red')
            >>> store.set_item('ul').set_item('li', 'Item 1').set_item('li', 'Item 2')
            >>> store.set_item('first', 'value', _position='<')  # insert at beginning
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
            child_store = TreeStore(builder=parent_store._builder)
            node = TreeStoreNode(label, final_attr, value=child_store, parent=parent_store)
            child_store.parent = node
            parent_store._insert_node(node, _position)
            return child_store  # Return child store for chaining children

    def get_item(self, path: str, default: Any = None) -> Any:
        """Get the value at the given path.

        Args:
            path: Dotted path, optionally with ?attr suffix.
            default: Default value if path not found.

        Returns:
            The value at the path, attribute value, or default.

        Example:
            >>> store.get_item('html.body.div')  # returns value
            >>> store.get_item('html.body.div?color')  # returns attribute
        """
        try:
            # Check for attribute access
            attr_name = None
            if '?' in path:
                path, attr_name = path.rsplit('?', 1)

            node = self.get_node(path)

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

        Raises:
            KeyError: If path not found.

        Example:
            >>> store['html.body.div']  # value
            >>> store['html.body.div?color']  # attribute
            >>> store['#0.#1']  # positional access
        """
        # Check for attribute access
        attr_name = None
        if '?' in path:
            path, attr_name = path.rsplit('?', 1)

        node = self.get_node(path)

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
            node = self.get_node(node_path)
            node.attr[attr_name] = value
        else:
            # Set value (with autocreate)
            self.set_item(path, value)

    def get_node(self, path: str) -> TreeStoreNode:
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

    def get_attr(self, path: str, attr: str | None = None, default: Any = None) -> Any:
        """Get attribute(s) from node at path.

        Args:
            path: Path to the node.
            attr: Attribute name. If None, returns all attributes.
            default: Default value if attribute not found.

        Returns:
            Attribute value, all attributes dict, or default.
        """
        try:
            node = self.get_node(path)
            return node.get_attr(attr, default)
        except KeyError:
            return default

    def set_attr(
        self, path: str, _attributes: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Set attributes on node at path.

        Args:
            path: Path to the node.
            _attributes: Dictionary of attributes.
            **kwargs: Additional attributes as keyword arguments.
        """
        node = self.get_node(path)
        node.set_attr(_attributes, **kwargs)

    def set_resolver(self, path: str, resolver: Any) -> None:
        """Set a resolver on the node at the given path.

        Args:
            path: Path to the node.
            resolver: The resolver to set.
        """
        node = self.get_node(path)
        node.resolver = resolver

    def get_resolver(self, path: str) -> Any:
        """Get the resolver from the node at the given path.

        Args:
            path: Path to the node.

        Returns:
            The resolver, or None if no resolver is set.
        """
        node = self.get_node(path)
        return node.resolver

    def del_item(self, path: str) -> TreeStoreNode:
        """Delete and return node at path.

        Args:
            path: Path to the node.

        Returns:
            The removed TreeStoreNode.

        Raises:
            KeyError: If path not found.
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
            node = self.del_item(path)
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

    def get_nodes(self, path: str = '') -> list[TreeStoreNode]:
        """Get nodes at path (or root if empty).

        Args:
            path: Optional path to get nodes from.

        Returns:
            List of TreeStoreNode at the specified level in insertion order.
        """
        if not path:
            return list(self._order)

        node = self.get_node(path)
        if node.is_branch:
            return list(node.value._order)
        return []

    # ==================== Digest ====================

    def iter_digest(self, what: str = '#k,#v') -> Iterator[Any]:
        """Yield data from nodes using digest syntax.

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
        """Extract data from nodes using digest syntax.

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
            # Callback mode
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
    def parent_node(self) -> TreeStoreNode | None:
        """Get the parent node (alias for self.parent)."""
        return self.parent

    # ==================== Conversion ====================

    def as_dict(self) -> dict[str, Any]:
        """Convert to plain dict (recursive).

        Branch nodes become nested dicts with their attributes and children.
        Leaf nodes become their value directly (or dict with _value if has attrs).

        Returns:
            Nested dictionary representation of the tree.
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
        """Remove all nodes from this store.

        Does not trigger deletion events for individual nodes.
        """
        self._nodes.clear()
        self._order.clear()

    def update(
        self,
        other: dict | list | TreeStore,
        ignore_none: bool = False,
    ) -> None:
        """Update this TreeStore with data from another source.

        For each item in other:
        - If label exists: updates attributes, and if both are branches,
          recursively updates children; otherwise replaces value
        - If label doesn't exist: adds the new node

        Args:
            other: Source data (dict, list of tuples, or TreeStore)
            ignore_none: If True, don't update values that are None

        Example:
            >>> store = TreeStore({'config': {'a': 1, 'b': 2}})
            >>> store.update({'config': {'b': 3, 'c': 4}})
            >>> store['config.a']  # 1 (preserved)
            >>> store['config.b']  # 3 (updated)
            >>> store['config.c']  # 4 (added)
        """
        # Convert source to TreeStore if needed
        if isinstance(other, dict):
            other_store = TreeStore(other)
        elif isinstance(other, list):
            other_store = TreeStore(other)
        elif isinstance(other, TreeStore):
            other_store = other
        else:
            raise TypeError(
                f"other must be dict, list, or TreeStore, not {type(other).__name__}"
            )

        self._update_from_treestore(other_store, ignore_none)

    def _update_from_treestore(
        self,
        other: TreeStore,
        ignore_none: bool = False,
    ) -> None:
        """Update this TreeStore from another TreeStore.

        Internal method that performs the actual merge operation.

        Args:
            other: Source TreeStore to merge from.
            ignore_none: If True, skip None values.
        """
        for other_node in other._order:
            label = other_node.label
            other_value = other_node.value

            if label in self._nodes:
                # Node exists - update it
                curr_node = self._nodes[label]

                # Update attributes
                curr_node.attr.update(other_node.attr)

                # Handle value
                if isinstance(other_value, TreeStore) and curr_node.is_branch:
                    # Both are branches - recursive update
                    curr_node.value._update_from_treestore(other_value, ignore_none)
                else:
                    # Replace value (unless ignore_none and value is None)
                    if not ignore_none or other_value is not None:
                        curr_node.value = other_value
            else:
                # Node doesn't exist - add it
                if other_node.is_branch:
                    # Deep copy the branch
                    child_store = TreeStore(builder=self._builder)
                    node = TreeStoreNode(
                        label,
                        dict(other_node.attr),
                        value=child_store,
                        parent=self,
                    )
                    child_store.parent = node
                    load_from_treestore(child_store, other_value)
                    self._insert_node(node)
                else:
                    # Copy leaf
                    node = TreeStoreNode(
                        label,
                        dict(other_node.attr),
                        value=other_value,
                        parent=self,
                    )
                    self._insert_node(node)

    def get(self, label: str, default: Any = None) -> TreeStoreNode | None:
        """Get node by label at this level, with default.

        Unlike get_node(), this only looks at direct children (no path traversal).

        Args:
            label: Node label to find.
            default: Value to return if not found.

        Returns:
            TreeStoreNode if found, default otherwise.
        """
        return self._nodes.get(label, default)

    # ==================== Validation ====================

    @property
    def is_valid(self) -> bool:
        """True if all nodes in this store are valid.

        Recursively checks all nodes in the tree for validation errors.

        Returns:
            True if no node has validation errors, False otherwise.

        Example:
            >>> store = TreeStore(builder=HtmlBuilder())
            >>> thead = store.thead()
            >>> store.is_valid
            False  # thead requires at least 1 tr
            >>> thead.tr()
            >>> store.is_valid
            True
        """
        walk_result = self.walk()
        if walk_result is None:
            return True
        for path, node in walk_result:
            if not node.is_valid:
                return False
        return True

    def validation_errors(self) -> dict[str, list[str]]:
        """Return all validation errors in the tree.

        Returns:
            Dictionary mapping node paths to their error lists.
            Only includes nodes with errors.

        Example:
            >>> store = TreeStore(builder=HtmlBuilder())
            >>> thead = store.thead()
            >>> store.validation_errors()
            {'thead_0': ["requires at least 1 'tr', has 0"]}
        """
        errors: dict[str, list[str]] = {}
        walk_result = self.walk()
        if walk_result is None:
            return errors
        for path, node in walk_result:
            if node._invalid_reasons:
                errors[path] = list(node._invalid_reasons)
        return errors
