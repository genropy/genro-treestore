# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore loading functions.

This module provides functions for populating a TreeStore from various
data sources: dictionaries, lists of tuples, or other TreeStore instances.

These functions are called internally by TreeStore.__init__ when a source
argument is provided. They can also be used directly for more control over
the loading process.

Data Formats:
    **Dict format**: Nested dictionaries where keys starting with '_' are
    treated as attributes (e.g., '_color': 'red'), and '_value' holds the
    node's value for leaf nodes with attributes.

    **List format**: List of tuples, each being either (label, value) or
    (label, value, attr_dict). Nested lists/dicts create branch nodes.

    **TreeStore format**: Deep copy from another TreeStore instance.

Example:
    >>> from genro_treestore.store.loading import load_from_dict
    >>> store = TreeStore()
    >>> load_from_dict(store, {'config': {'_color': 'red', 'name': 'App'}})
    >>> store['config.name']
    'App'
    >>> store['config?color']
    'red'
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import TreeStore
    from .node import TreeStoreNode


def load_from_dict(
    store: TreeStore,
    data: dict[str, Any],
    trigger: bool = False,
) -> None:
    """Load data from a nested dictionary into the TreeStore.

    Keys starting with '_' are treated as attributes for the parent node.
    The special key '_value' holds the node's scalar value when a leaf node
    also has attributes.

    Args:
        store: The TreeStore to populate.
        data: Nested dictionary of data to load.
        trigger: If True, fire insertion events for each node.

    Example:
        >>> load_from_dict(store, {
        ...     'user': {
        ...         '_id': 123,           # attribute
        ...         'name': 'Alice',      # child node
        ...         'status': {
        ...             '_value': 'active',  # value with attributes
        ...             '_color': 'green'    # attribute
        ...         }
        ...     }
        ... })
    """
    from .core import TreeStore
    from .node import TreeStoreNode

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
                child_store = TreeStore(builder=store._builder)
                node = TreeStoreNode(key, attr, value=child_store, parent=store)
                child_store.parent = node
                load_from_dict(child_store, children, trigger=trigger)
                store._insert_node(node, trigger=trigger)
            else:
                # Leaf node (only _value and attributes)
                node = TreeStoreNode(key, attr, value=node_value, parent=store)
                store._insert_node(node, trigger=trigger)
        else:
            # Simple value
            node = TreeStoreNode(key, {}, value=value, parent=store)
            store._insert_node(node, trigger=trigger)


def load_from_list(
    store: TreeStore,
    items: list,
    trigger: bool = False,
) -> None:
    """Load data from a list of tuples into the TreeStore.

    Each tuple can be:
    - (label, value): Creates a node with label and value
    - (label, value, attr_dict): Creates a node with label, value, and attributes

    Nested dicts or lists of tuples in the value position create branch nodes.

    Args:
        store: The TreeStore to populate.
        items: List of tuples to load.
        trigger: If True, fire insertion events for each node.

    Raises:
        ValueError: If a tuple has invalid length (not 2 or 3 elements).

    Example:
        >>> load_from_list(store, [
        ...     ('name', 'Alice'),
        ...     ('age', 30, {'unit': 'years'}),
        ...     ('address', {'city': 'Rome', 'country': 'Italy'})
        ... ])
    """
    from .core import TreeStore
    from .node import TreeStoreNode

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
            child_store = TreeStore(builder=store._builder)
            node = TreeStoreNode(label, attr, value=child_store, parent=store)
            child_store.parent = node
            load_from_dict(child_store, value, trigger=trigger)
            store._insert_node(node, trigger=trigger)
        elif isinstance(value, list) and value and isinstance(value[0], tuple):
            # Nested list of tuples becomes branch
            child_store = TreeStore(builder=store._builder)
            node = TreeStoreNode(label, attr, value=child_store, parent=store)
            child_store.parent = node
            load_from_list(child_store, value, trigger=trigger)
            store._insert_node(node, trigger=trigger)
        else:
            # Simple value
            node = TreeStoreNode(label, attr, value=value, parent=store)
            store._insert_node(node, trigger=trigger)


def load_from_treestore(
    store: TreeStore,
    source: TreeStore,
    trigger: bool = False,
) -> None:
    """Copy data from another TreeStore (deep copy).

    Creates new TreeStoreNode instances for each node in the source,
    preserving the hierarchical structure, labels, attributes, and values.

    Args:
        store: The TreeStore to populate.
        source: The source TreeStore to copy from.
        trigger: If True, fire insertion events for each node.

    Example:
        >>> original = TreeStore({'config': {'debug': True}})
        >>> copy = TreeStore()
        >>> load_from_treestore(copy, original)
        >>> copy['config.debug']
        True
    """
    from .core import TreeStore
    from .node import TreeStoreNode

    for src_node in source._order:
        if src_node.is_branch:
            # Recursively copy branch
            child_store = TreeStore(builder=store._builder)
            node = TreeStoreNode(
                src_node.label,
                dict(src_node.attr),  # Copy attributes
                value=child_store,
                parent=store,
            )
            child_store.parent = node
            load_from_treestore(child_store, src_node.value, trigger=trigger)
            store._insert_node(node, trigger=trigger)
        else:
            # Copy leaf
            node = TreeStoreNode(
                src_node.label,
                dict(src_node.attr),
                value=src_node.value,
                parent=store,
            )
            store._insert_node(node, trigger=trigger)
