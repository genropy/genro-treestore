# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Genro-TreeStore - Hierarchical data structures with builder pattern support.

A lightweight, zero-dependency library providing tree-based data structures
for the Genro ecosystem (Genro Kyō).
"""

__version__ = "0.1.0"

from .treestore import (
    TreeStore,
    TreeStoreNode,
    BuilderNode,
    TreeStoreBuilder,
    valid_children,
    InvalidChildError,
    MissingChildError,
    TooManyChildrenError,
)

__all__ = [
    "TreeStore",
    "TreeStoreNode",
    "BuilderNode",
    "TreeStoreBuilder",
    "valid_children",
    "InvalidChildError",
    "MissingChildError",
    "TooManyChildrenError",
]
