# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore package - Hierarchical data container.

This package provides the TreeStore class, a hierarchical data structure
with O(1) lookup, builder pattern support, and reactive subscriptions.

The package is organized into:
- core: Main TreeStore class with path traversal, access, and iteration
- loading: Functions for loading data from dict, list, or TreeStore sources
- subscription: Event subscription and notification system

Example:
    >>> from genro_treestore import TreeStore
    >>> store = TreeStore()
    >>> store.set_item('config.name', 'MyApp')
    >>> store['config.name']
    'MyApp'
"""

from .core import TreeStore
from .node import TreeStoreNode

__all__ = ["TreeStore", "TreeStoreNode"]
