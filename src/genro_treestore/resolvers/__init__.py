# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore resolvers - Lazy/dynamic value resolution system.

This package provides resolvers for lazy evaluation and dynamic value
computation in TreeStore nodes. Resolvers allow a node's value to be
computed on-demand rather than stored statically.

Resolver Types:
    - **TreeStoreResolver**: Base class for all resolvers
    - **CallbackResolver**: Simple resolver that invokes a callback function
    - **DirectoryResolver**: Loads directory contents lazily
    - **TxtDocResolver**: Loads text file contents

Key Features:
    - Sync/async transparency via @smartasync
    - TTL-based caching (cache_time parameter)
    - Serialization support for persistence
    - Traversal resolvers for hierarchical data
    - Leaf resolvers for dynamic scalar values

Example:
    >>> from genro_treestore.resolvers import CallbackResolver, DirectoryResolver
    >>>
    >>> # Callback resolver for computed values
    >>> def compute_total(node):
    ...     store = node.parent
    ...     return store['price'] * store['quantity']
    >>> store.set_resolver('total', CallbackResolver(compute_total))
    >>>
    >>> # Directory resolver for lazy file loading
    >>> store.set_resolver('docs', DirectoryResolver('/path/to/docs'))
"""

from .base import TreeStoreResolver, CallbackResolver
from .directory import DirectoryResolver, TxtDocResolver

__all__ = [
    "TreeStoreResolver",
    "CallbackResolver",
    "DirectoryResolver",
    "TxtDocResolver",
]
