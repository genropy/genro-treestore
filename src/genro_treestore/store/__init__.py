# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore package - Hierarchical data container with O(1) lookup.

This package provides the core TreeStore data structure, a hierarchical
container optimized for path-based access with constant-time lookup.

Architecture:
    TreeStore uses a dual-reference pattern where:

    - **TreeStore** is a container of TreeStoreNode children
    - **TreeStoreNode** wraps a value (leaf) or another TreeStore (branch)
    - Each node maintains a reference to its parent TreeStore
    - Each TreeStore maintains a reference to its parent node (if any)

    This enables bidirectional navigation and efficient path resolution.

Modules:
    - **core**: TreeStore class with path traversal, CRUD operations,
      iteration, serialization (TYTX, XML), and builder integration
    - **node**: TreeStoreNode class representing individual tree nodes
      with attributes, values, resolvers, and subscription support
    - **loading**: Functions for populating TreeStore from various sources
      (dict, list, another TreeStore)
    - **subscription**: Reactive event system for change notifications
      with hierarchical propagation
    - **serialization**: TYTX format serialization for type-preserving
      round-trip storage

Path Syntax:
    TreeStore supports a rich path syntax for navigation::

        store['config.database.host']     # Dotted path
        store['users.#0.name']            # Positional index
        store['users.#-1']                # Negative index (last)
        store['config.?timeout']          # Attribute access
        store['items.*.price']            # Wildcard (iteration)

Example:
    Basic usage with nested data::

        from genro_treestore import TreeStore

        store = TreeStore()
        store.set_item('app.name', 'MyApp')
        store.set_item('app.version', '1.0.0')
        store.set_item('app.settings.debug', True)

        # Path access
        print(store['app.name'])              # 'MyApp'
        print(store['app.settings.debug'])    # True

        # Iteration
        for key, value in store['app'].items():
            print(f"{key}: {value}")

    With builder pattern::

        from genro_treestore import TreeStore
        from genro_treestore.builders import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder())
        body = store.body()
        body.div(id='main').p(value='Hello!')

See Also:
    - :class:`~genro_treestore.store.core.TreeStore`
    - :class:`~genro_treestore.store.node.TreeStoreNode`
    - :mod:`~genro_treestore.resolvers` - Lazy value resolution
    - :mod:`~genro_treestore.builders` - Typed builder APIs
"""

from .core import TreeStore
from .node import TreeStoreNode

__all__ = ["TreeStore", "TreeStoreNode"]
