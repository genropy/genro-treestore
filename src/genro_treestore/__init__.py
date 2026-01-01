# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Genro-TreeStore - Hierarchical data structures with builder pattern support.

A lightweight library providing tree-based data structures for the Genro
ecosystem (Genro Kyō), with support for lazy value resolution.

Core Features:
    - TreeStore: Hierarchical container with O(1) lookup
    - TreeStoreNode: Individual nodes with attributes and values
    - Resolver system: Lazy/dynamic value computation with caching
    - Builder pattern: Domain-specific fluent APIs

Resolver System:
    Resolvers enable lazy evaluation of node values. See the resolver
    module documentation for details on:

    - Traversal resolvers (load hierarchical data on demand)
    - Leaf resolvers (compute dynamic values like sensor readings)
    - Sync/async transparency via @smartasync
    - Caching with TTL support

Parsers are available in the `parsers` subpackage:
    >>> from genro_treestore.parsers import parse_rnc, parse_rnc_file

Example:
    Basic usage::

        from genro_treestore import TreeStore, CallbackResolver

        store = TreeStore()
        store.set_item('config.name', 'MyApp')
        store.set_item('config.version', '1.0')

        # Lazy computed value
        def get_full_name(node):
            s = node.parent
            return f"{s.get_item('name')} v{s.get_item('version')}"

        store.set_item('config.full_name')
        store.set_resolver('config.full_name', CallbackResolver(get_full_name))

        print(store['config.full_name'])  # "MyApp v1.0"
"""

__version__ = "0.1.0"

from .builders import BuilderBase, HtmlBuilder, HtmlHeadBuilder, HtmlBodyBuilder, HtmlPage
from .exceptions import (
    InvalidChildError,
    InvalidParentError,
    MissingChildError,
    TooManyChildrenError,
    TreeStoreError,
)
from .directory_resolver import DirectoryResolver, TxtDocResolver
from .node import TreeStoreNode
from .resolver import CallbackResolver, TreeStoreResolver
from .store import TreeStore

__all__ = [
    # Core classes
    "TreeStore",
    "TreeStoreNode",
    # Resolver classes
    "TreeStoreResolver",
    "CallbackResolver",
    "DirectoryResolver",
    "TxtDocResolver",
    # Builder classes
    "BuilderBase",
    "HtmlBuilder",
    "HtmlHeadBuilder",
    "HtmlBodyBuilder",
    "HtmlPage",
    # Exceptions
    "TreeStoreError",
    "InvalidChildError",
    "MissingChildError",
    "TooManyChildrenError",
    "InvalidParentError",
]
