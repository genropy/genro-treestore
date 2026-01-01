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

from typing import Any, Callable, Iterator, Literal, TYPE_CHECKING

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

    def flattened(
        self,
        path_registry: dict[int, str] | None = None,
    ) -> Iterator[tuple[str | int | None, str, str | None, Any, dict[str, Any]]]:
        """Yield flat tuples representing the tree in depth-first order.

        Converts the hierarchical tree structure into a flat sequence of tuples,
        suitable for serialization. Each tuple contains all information needed
        to reconstruct a node: its parent reference, label, tag, value, and
        attributes.

        This method is the foundation for TYTX serialization (see to_tytx()).

        Output Modes:
            **Normal mode** (path_registry=None):
                Parent references are full path strings. More readable and
                compresses very well with gzip due to repetitive patterns.

            **Compact mode** (path_registry=dict):
                Parent references are sequential numeric codes (0, 1, 2...).
                The provided dict is populated with {code: path} mappings.
                Produces smaller output without compression (~32% smaller),
                but gzip actually compresses normal mode better.

        Args:
            path_registry: Optional dict to enable compact mode.
                - If None: parent is emitted as path string (normal mode)
                - If dict: parent is emitted as numeric code, and the dict
                  is populated with {code: full_path} mappings for branches

        Yields:
            tuple: (parent, label, tag, value, attr) where:
                - **parent**: Reference to parent node
                    - Normal mode: path string ('' for root-level nodes)
                    - Compact mode: int code (None for root-level nodes)
                - **label**: Node's unique key within its parent (e.g., 'floor_0')
                - **tag**: Node type from builder (e.g., 'floor') or None
                - **value**: Node value
                    - None for branch nodes (nodes with children)
                    - Actual value for leaf nodes (scalar values)
                - **attr**: Dict of node attributes (always a copy)

        Note:
            - Iteration order is depth-first (parent before children)
            - Branch nodes have value=None because their "value" is the child store
            - The path_registry dict is modified in place during iteration
            - Uses walk() internally for tree traversal

        Example:
            Normal mode (path strings)::

                >>> store = TreeStore(builder=BuildingBuilder())
                >>> b = store.building(name='Casa Mia')
                >>> b.floor(number=1).room(name='Kitchen')
                >>>
                >>> for row in store.flattened():
                ...     parent, label, tag, value, attr = row
                ...     print(f"{parent!r:20} {label:15} {tag}")
                ''                   building_0      building
                'building_0'         floor_0         floor
                'building_0.floor_0' room_0          room

            Compact mode (numeric codes)::

                >>> paths = {}
                >>> for row in store.flattened(path_registry=paths):
                ...     parent, label, tag, value, attr = row
                ...     print(f"{parent!r:5} {label:15} {tag}")
                None  building_0      building
                0     floor_0         floor
                1     room_0          room
                >>>
                >>> paths
                {0: 'building_0', 1: 'building_0.floor_0'}

        See Also:
            - to_tytx(): Serializes using this method
            - walk(): The underlying tree traversal method
        """
        if path_registry is not None:
            path_to_code: dict[str, int] = {}
            code_counter = 0

        walk_result = self.walk()
        if walk_result is None:
            return

        for path, node in walk_result:
            parent_path = path.rsplit('.', 1)[0] if '.' in path else ''
            value = None if node.is_branch else node._value
            attr = dict(node.attr)

            if path_registry is not None:
                # Emit numeric code for parent
                parent_code = path_to_code.get(parent_path) if parent_path else None
                yield (parent_code, node.label, node.tag, value, attr)

                # Register this path if it's a branch (has children)
                if node.is_branch:
                    path_to_code[path] = code_counter
                    path_registry[code_counter] = path
                    code_counter += 1
            else:
                # Emit path string for parent
                yield (parent_path, node.label, node.tag, value, attr)

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

    # ==================== Serialization ====================

    def to_tytx(
        self,
        transport: Literal['json', 'msgpack'] | None = None,
        compact: bool = False,
    ) -> str | bytes:
        """Serialize TreeStore to TYTX format with type preservation.

        TYTX (Typed Transport) preserves Python types (Decimal, date, datetime,
        time) in the serialized format, eliminating manual type conversion when
        deserializing.

        The tree is serialized as a flat list of row tuples in depth-first order.
        Each row contains: (parent, label, tag, value, attr).

        Args:
            transport: Output format:
                - None or 'json': JSON string (default). Human-readable,
                  compresses very well with gzip.
                - 'msgpack': Binary MessagePack bytes. ~30% smaller than JSON
                  before compression.
            compact: Serialization mode:
                - False (default): Parent as path strings ('a.b.c').
                  Recommended with gzip compression.
                - True: Parent as numeric codes (0, 1, 2...).
                  ~32% smaller without compression, but gzip prefers normal.

        Returns:
            str: If transport is None or 'json'
            bytes: If transport is 'msgpack'

        Raises:
            ImportError: If genro-tytx package is not installed.

        Example:
            >>> from decimal import Decimal
            >>> from datetime import date
            >>>
            >>> store = TreeStore()
            >>> store.set_item('invoice.amount', Decimal('1234.56'))
            >>> store.set_item('invoice.date', date(2025, 1, 15))
            >>>
            >>> # Default JSON format
            >>> json_data = store.to_tytx()
            >>>
            >>> # Binary MessagePack (smaller)
            >>> msgpack_data = store.to_tytx(transport='msgpack')
            >>>
            >>> # Compact mode (for uncompressed transmission)
            >>> compact_data = store.to_tytx(compact=True)

        See Also:
            - from_tytx(): Deserialize back to TreeStore
            - flattened(): The underlying flat representation
        """
        from .serialization import to_tytx as serialize
        return serialize(self, transport=transport, compact=compact)

    @classmethod
    def from_tytx(
        cls,
        data: str | bytes,
        transport: Literal['json', 'msgpack'] | None = None,
        builder: Any | None = None,
    ) -> 'TreeStore':
        """Deserialize TreeStore from TYTX format with type preservation.

        Reconstructs a TreeStore from TYTX-serialized data. Automatically
        detects normal vs compact format. Types (Decimal, date, datetime, time)
        are preserved exactly as they were before serialization.

        Args:
            data: Serialized data from to_tytx().
                - str: If transport is None or 'json'
                - bytes: If transport is 'msgpack'
            transport: Input format (must match serialization):
                - None or 'json': Parse as JSON string (default)
                - 'msgpack': Parse as MessagePack bytes
            builder: Optional builder for the reconstructed store.
                Enables builder methods (e.g., store.div()) on the result.

        Returns:
            TreeStore: Fully reconstructed tree with:
                - Complete node hierarchy
                - All values with original types preserved
                - All node attributes restored

        Raises:
            ImportError: If genro-tytx package is not installed.

        Example:
            >>> # Basic round-trip
            >>> original = TreeStore()
            >>> original.set_item('config.price', Decimal('99.99'))
            >>> data = original.to_tytx()
            >>>
            >>> restored = TreeStore.from_tytx(data)
            >>> restored['config.price']  # Decimal('99.99'), not float
            >>>
            >>> # With MessagePack
            >>> data = original.to_tytx(transport='msgpack')
            >>> restored = TreeStore.from_tytx(data, transport='msgpack')
            >>>
            >>> # With builder
            >>> restored = TreeStore.from_tytx(data, builder=HtmlBuilder())

        See Also:
            - to_tytx(): Serialize TreeStore to TYTX format
        """
        from .serialization import from_tytx as deserialize
        return deserialize(data, transport=transport, builder=builder)

    @classmethod
    def from_xml(
        cls,
        data: str,
        builder: Any | None = None,
    ) -> 'TreeStore':
        """Load TreeStore from XML string.

        Each XML element becomes a node with:

        - **label**: tag name with counter suffix (element_0, element_1, etc.)
        - **value**: text content (leaf) or child TreeStore (branch)
        - **attr**: XML attributes, plus '_tag' with namespace prefix if present

        Namespace Handling:
            XML namespaces are processed as follows:

            - Namespace declarations (xmlns:prefix="uri") are extracted
            - Element tags with namespaces store the prefixed form in '_tag'
            - The label uses only the local name (without namespace)
            - Namespaced attributes are filtered out (not preserved)

            Example with namespaces::

                xml = '''<root xmlns:ns="http://example.com">
                    <ns:item>value</ns:item>
                </root>'''
                store = TreeStore.from_xml(xml)
                # Label: 'item_0', attr['_tag']: 'ns:item'

        Args:
            data: XML string to parse.
            builder: Optional builder for the resulting store.

        Returns:
            TreeStore with XML structure. The root element becomes
            the first (and typically only) top-level node.

        Example:
            Simple XML::

                >>> xml = '<html><head><title>Hello</title></head></html>'
                >>> store = TreeStore.from_xml(xml)
                >>> store['html_0.head_0.title_0']
                'Hello'

            Accessing tag and attributes::

                >>> xml = '<div class="main"><span id="x">text</span></div>'
                >>> store = TreeStore.from_xml(xml)
                >>> node = store.get_node('div_0.span_0')
                >>> node.attr['id']
                'x'
                >>> node.value
                'text'

        See Also:
            - :meth:`to_xml` - Convert TreeStore back to XML
        """
        import xml.etree.ElementTree as ET
        import re

        # Extract namespace prefixes from XML
        ns_decls = re.findall(r'xmlns:(\w+)=["\']([^"\']+)["\']', data)
        uri_to_prefix = {uri: prefix for prefix, uri in ns_decls}
        ns_pattern = re.compile(r'\{([^}]+)\}(.+)')

        def clean_tag(tag: str) -> tuple[str, str | None]:
            """Return (local_name, prefixed_tag or None)."""
            match = ns_pattern.match(tag)
            if match:
                uri, local = match.groups()
                prefix = uri_to_prefix.get(uri)
                if prefix:
                    return local, f'{prefix}:{local}'
                return local, None
            return tag, None

        def load_element(element: ET.Element, store: 'TreeStore') -> None:
            """Recursively load XML element into store."""
            local, prefixed = clean_tag(element.tag)
            existing = [n.label for n in store.nodes() if n.label.startswith(f'{local}_')]
            label = f'{local}_{len(existing)}'

            attribs = {k: v for k, v in element.attrib.items() if not k.startswith('{')}
            if prefixed:
                attribs['_tag'] = prefixed

            children = list(element)
            if children:
                child_store = cls(builder=builder)
                for child in children:
                    load_element(child, child_store)
                store.set_item(label, child_store, _attributes=attribs)
            else:
                value = element.text.strip() if element.text else ''
                store.set_item(label, value, _attributes=attribs)

        root_elem = ET.fromstring(data)
        store = cls(builder=builder)
        load_element(root_elem, store)
        return store

    def to_xml(self, root_tag: str | None = None) -> str:
        """Serialize TreeStore to XML string.

        Converts the TreeStore hierarchy into an XML document. Each node
        becomes an XML element with:

        - **tag**: from node's '_tag' attribute, or label without suffix
        - **attributes**: node's attr dict (excluding internal _* keys)
        - **content**: text value (if leaf) or child elements (if branch)

        Root Element Handling:
            The root element is determined as follows:

            - If ``root_tag`` is provided, it wraps all content
            - If store has exactly one top-level node and no ``root_tag``,
              that node becomes the root element directly
            - If store has multiple top-level nodes and no ``root_tag``,
              they are wrapped in a ``<root>`` element

        Tag Resolution:
            For each node, the XML tag is resolved in order:

            1. ``node.attr['_tag']`` - Explicit tag (may include namespace prefix)
            2. ``node.label.rsplit('_', 1)[0]`` - Label without counter suffix

            This allows round-trip preservation when loading from XML.

        Args:
            root_tag: Optional root element tag. If None and store has
                exactly one root node, uses that node's tag. If None and
                store has multiple nodes, defaults to 'root'.

        Returns:
            XML string representation without XML declaration.

        Example:
            Single root node::

                >>> store = TreeStore()
                >>> store.set_item('html.head.title', 'Hello')
                >>> print(store.to_xml())
                <html><head><title>Hello</title></head></html>

            Multiple top-level nodes::

                >>> store = TreeStore()
                >>> store.set_item('item', 'first')
                >>> store.set_item('item', 'second')
                >>> print(store.to_xml())
                <root><item>first</item><item>second</item></root>

            With explicit root tag::

                >>> store = TreeStore()
                >>> store.set_item('item', 'value')
                >>> print(store.to_xml(root_tag='items'))
                <items><item>value</item></items>

        See Also:
            - :meth:`from_xml` - Load TreeStore from XML
        """
        import xml.etree.ElementTree as ET

        def store_to_element(store: 'TreeStore', tag: str) -> ET.Element:
            """Convert store to XML element."""
            element = ET.Element(tag)

            for node in store.nodes():
                # Get tag from attr or strip suffix from label
                node_tag = node.attr.get('_tag') or node.label.rsplit('_', 1)[0]

                # Copy non-internal attributes
                attribs = {k: str(v) for k, v in node.attr.items() if not k.startswith('_')}

                if node.is_branch:
                    # Recurse into child store
                    child_elem = store_to_element(node.value, node_tag)
                    child_elem.attrib.update(attribs)
                    element.append(child_elem)
                else:
                    # Leaf node
                    child_elem = ET.SubElement(element, node_tag, attribs)
                    if node.value is not None and node.value != '':
                        child_elem.text = str(node.value)

            return element

        nodes = list(self.nodes())
        if not nodes:
            tag = root_tag or 'root'
            return f'<{tag}/>'

        if len(nodes) == 1 and root_tag is None:
            # Single root node - use it directly
            node = nodes[0]
            tag = node.attr.get('_tag') or node.label.rsplit('_', 1)[0]
            attribs = {k: str(v) for k, v in node.attr.items() if not k.startswith('_')}

            if node.is_branch:
                root = store_to_element(node.value, tag)
                root.attrib.update(attribs)
            else:
                root = ET.Element(tag, attribs)
                if node.value is not None and node.value != '':
                    root.text = str(node.value)
        else:
            # Multiple root nodes - wrap in container
            tag = root_tag or 'root'
            root = store_to_element(self, tag)

        return ET.tostring(root, encoding='unicode')
