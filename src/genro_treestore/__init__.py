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

Schema Builders:
    Build TreeStore hierarchies from external schema definitions:

    - **HtmlBuilder**: HTML5 elements with W3C schema validation
    - **XsdBuilder**: From XML Schema (.xsd) files

Example:
    Basic usage with path access::

        from genro_treestore import TreeStore

        store = TreeStore()
        store.set_item('config.name', 'MyApp')
        store.set_item('config.version', '1.0')
        store.set_item('config.debug', True)

        print(store['config.name'])      # 'MyApp'
        print(store['config.debug'])     # True

    With lazy computed values::

        from genro_treestore import TreeStore, CallbackResolver

        store = TreeStore()
        store.set_item('config.name', 'MyApp')
        store.set_item('config.version', '1.0')

        def get_full_name(node):
            s = node.parent
            return f"{s.get_item('name')} v{s.get_item('version')}"

        store.set_item('config.full_name')
        store.set_resolver('config.full_name', CallbackResolver(get_full_name))

        print(store['config.full_name'])  # "MyApp v1.0"

    With builder pattern (HTML)::

        from genro_treestore import TreeStore
        from genro_treestore.builders import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder())
        body = store.body()
        body.div(id='main').p(value='Hello World!')
"""

__version__ = "0.2.0"

from .builders import (
    BuilderBase,
    HtmlBuilder,
    HtmlHeadBuilder,
    HtmlBodyBuilder,
    HtmlPage,
    XsdBuilder,
    element,
    valid_children,
)
from .exceptions import (
    InvalidChildError,
    InvalidParentError,
    MissingChildError,
    TooManyChildrenError,
    TreeStoreError,
)
from .resolvers import (
    CallbackResolver,
    TreeStoreResolver,
    DirectoryResolver,
    TxtDocResolver,
)
from .store import TreeStore, TreeStoreNode
from .store.subscription import SubscriberCallback
from .validation import ValidationSubscriber

__all__ = [
    # Core classes
    "TreeStore",
    "TreeStoreNode",
    # Resolver classes
    "TreeStoreResolver",
    "CallbackResolver",
    "DirectoryResolver",
    "TxtDocResolver",
    # Validation
    "ValidationSubscriber",
    # Builder classes
    "BuilderBase",
    "HtmlBuilder",
    "HtmlHeadBuilder",
    "HtmlBodyBuilder",
    "HtmlPage",
    "XsdBuilder",
    # Builder decorators
    "element",
    "valid_children",
    # Subscription types
    "SubscriberCallback",
    # Exceptions
    "TreeStoreError",
    "InvalidChildError",
    "MissingChildError",
    "TooManyChildrenError",
    "InvalidParentError",
]
