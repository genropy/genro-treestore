# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore serialization - TYTX format support.

This module provides functions to serialize and deserialize TreeStore
hierarchies to/from TYTX format. TYTX preserves Python types (Decimal,
date, datetime, time) across serialization, eliminating manual type
conversion on both ends.

Wire Format:
    The serialized format is a dict with:
    - 'rows': List of tuples, one per node in depth-first order
    - 'paths': (optional, compact mode only) Registry mapping codes to paths

    Each row tuple contains:
    (parent, label, tag, value, attr)
    - parent: Parent path string (e.g., 'a.b') or numeric code if compact
    - label: Node's unique key within its parent (e.g., 'div_0')
    - tag: Node type from builder (e.g., 'div') or None
    - value: Node value (None for branches, actual value for leaves)
    - attr: Dict of node attributes

Two Serialization Modes:
    Normal mode (compact=False, default):
        Parent references are full path strings. More readable, compresses
        well with gzip due to repetitive path patterns.

    Compact mode (compact=True):
        Parent references are numeric codes (0, 1, 2...). Smaller without
        compression, but gzip actually makes it larger than normal mode.

    Recommendation:
        - Use normal mode (default) if you'll compress the data
        - Use compact mode only for uncompressed transmission

Datetime Handling:
    TYTX serializes all datetimes as UTC with millisecond precision.
    Naive datetimes are treated as UTC on serialization. On deserialization,
    datetimes are always returned as timezone-aware (UTC).

    For roundtrip comparison, use ``genro_tytx.utils.tytx_equivalent()``
    which handles naive vs aware UTC equivalence.

Requirements:
    Requires the genro-tytx package for type-preserving encoding/decoding.
    Install with: pip install genro-tytx

Example:
    >>> from genro_treestore import TreeStore
    >>> from decimal import Decimal
    >>>
    >>> store = TreeStore()
    >>> store.set_item('invoice.amount', Decimal('1234.56'))
    >>> store.set_item('invoice.paid', False)
    >>>
    >>> # Serialize
    >>> data = store.to_tytx()
    >>>
    >>> # Deserialize - types are preserved
    >>> restored = TreeStore.from_tytx(data)
    >>> restored['invoice.amount']  # Decimal('1234.56'), not string
"""

from __future__ import annotations

from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import TreeStore


def to_tytx(
    store: TreeStore,
    transport: Literal['json', 'msgpack'] | None = None,
    compact: bool = False,
) -> str | bytes:
    """Serialize a TreeStore to TYTX format.

    Converts the entire tree hierarchy into a flat list of row tuples,
    then encodes it using TYTX which preserves Python types (Decimal,
    date, datetime, time) in the wire format.

    Args:
        store: The TreeStore to serialize.
        transport: Output format:
            - None or 'json': JSON string (default). Human-readable,
              compresses very well with gzip.
            - 'msgpack': Binary MessagePack bytes. ~30% smaller than JSON
              before compression, good for bandwidth-constrained scenarios.
        compact: Serialization mode:
            - False (default): Parent paths as full strings ('a.b.c').
              Recommended when using gzip compression.
            - True: Parent paths as numeric codes (0, 1, 2...).
              ~30% smaller uncompressed, but larger after gzip.

    Returns:
        str if transport is None or 'json', bytes if 'msgpack'.

    Raises:
        ImportError: If genro-tytx package is not installed.

    Output Format:
        Normal mode::

            {"rows": [
                ["", "root", "div", null, {"id": "main"}],
                ["root", "child_0", "span", "text", {}],
                ...
            ]}

        Compact mode::

            {"rows": [
                [null, "root", "div", null, {"id": "main"}],
                [0, "child_0", "span", "text", {}],
                ...
            ], "paths": {"0": "root", ...}}

    Example:
        >>> store = TreeStore()
        >>> store.set_item('config.timeout', 30)
        >>> store.set_item('config.retry', True)
        >>>
        >>> # Default JSON
        >>> json_data = to_tytx(store)
        >>>
        >>> # Binary MessagePack
        >>> msgpack_data = to_tytx(store, transport='msgpack')
        >>>
        >>> # Compact mode (smaller without gzip)
        >>> compact_data = to_tytx(store, compact=True)
    """
    try:
        from genro_tytx import to_tytx as tytx_encode
    except ImportError as e:
        raise ImportError("genro-tytx package required for serialization") from e

    if compact:
        paths: dict[int, str] = {}
        rows = list(store.flattened(path_registry=paths))
        # Convert int keys to str for JSON compatibility
        paths_str = {str(k): v for k, v in paths.items()}
        return tytx_encode({'rows': rows, 'paths': paths_str}, transport=transport)
    else:
        rows = list(store.flattened())
        return tytx_encode({'rows': rows}, transport=transport)


def from_tytx(
    data: str | bytes,
    transport: Literal['json', 'msgpack'] | None = None,
    builder: Any | None = None,
) -> TreeStore:
    """Deserialize TreeStore from TYTX format.

    Reconstructs a complete TreeStore hierarchy from TYTX-encoded data.
    Automatically detects whether the data uses normal or compact format
    by checking for the presence of a 'paths' registry.

    The reconstruction algorithm:
        1. Decode TYTX data to get rows and optional path registry
        2. For each row in depth-first order:
           - Resolve parent reference (path string or numeric code)
           - Create TreeStoreNode with label, tag, value, and attributes
           - If value is None, create child TreeStore (branch node)
           - Insert node into parent store

    Args:
        data: Serialized data from to_tytx().
            - str: If transport is None or 'json'
            - bytes: If transport is 'msgpack'
        transport: Input format matching how data was serialized:
            - None or 'json': Parse as JSON string (default)
            - 'msgpack': Parse as MessagePack bytes
        builder: Optional builder instance for the reconstructed store.
            If provided, enables builder pattern methods on the result.

    Returns:
        TreeStore: Fully reconstructed tree with:
            - All nodes in correct hierarchy
            - Original values with types preserved (Decimal, date, etc.)
            - All node attributes restored
            - Parent-child relationships established

    Raises:
        ImportError: If genro-tytx package is not installed.
        ValueError: If data format is invalid or corrupted.

    Format Detection:
        The function automatically handles both serialization modes:

        Normal mode (no 'paths' key)::

            {"rows": [["", "root", "div", null, {}], ...]}

        Compact mode (has 'paths' key)::

            {"rows": [[null, "root", "div", null, {}], ...],
             "paths": {"0": "root", ...}}

    Example:
        >>> # Basic deserialization
        >>> store = from_tytx(json_data)
        >>> store['config.timeout']
        30

        >>> # With MessagePack
        >>> store = from_tytx(msgpack_data, transport='msgpack')

        >>> # With builder for DOM-like API
        >>> store = from_tytx(data, builder=HtmlBuilder())
        >>> store.div()  # Builder methods available

        >>> # Round-trip preserves types
        >>> original = TreeStore()
        >>> original.set_item('price', Decimal('99.99'))
        >>> data = to_tytx(original)
        >>> restored = from_tytx(data)
        >>> restored['price']  # Decimal('99.99'), not float
    """
    try:
        from genro_tytx import from_tytx as tytx_decode
    except ImportError as e:
        raise ImportError("genro-tytx package required for deserialization") from e

    from .core import TreeStore
    from .node import TreeStoreNode

    parsed = tytx_decode(data, transport=transport)
    rows = parsed['rows']
    # Check if compact format (has 'paths' registry)
    paths_raw = parsed.get('paths')
    # Convert str keys back to int if present
    code_to_path: dict[int, str] | None = (
        {int(k): v for k, v in paths_raw.items()} if paths_raw else None
    )

    store = TreeStore(builder=builder)

    # Registry to track created branch stores by path
    path_to_store: dict[str, TreeStore] = {'': store}

    for row in rows:
        parent_ref, label, tag, value, attr = row

        # Resolve parent path from code if compact format
        if code_to_path is not None:
            parent_path = code_to_path.get(parent_ref, '') if parent_ref is not None else ''
        else:
            parent_path = parent_ref

        # Get parent store from registry
        parent_store = path_to_store.get(parent_path, store)

        # Build full path for this node
        full_path = f"{parent_path}.{label}" if parent_path else label

        # Create node with attributes
        node = TreeStoreNode(label, attr, value=value, tag=tag)

        # If value is None, this is a branch - create child store
        if value is None:
            child_store = TreeStore(builder=builder)
            node._value = child_store
            child_store.parent = node
            # Register this branch for children
            path_to_store[full_path] = child_store

        node.parent = parent_store
        parent_store._insert_node(node, trigger=False)

    return store
