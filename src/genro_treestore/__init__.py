# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Genro-TreeStore - Hierarchical data structures with builder pattern support.

A lightweight, zero-dependency library providing tree-based data structures
for the Genro ecosystem (Genro Kyō).
"""

__version__ = "0.1.0"

from .builder import TreeStoreBuilder
from .exceptions import (
    InvalidChildError,
    InvalidParentError,
    MissingChildError,
    TooManyChildrenError,
    TreeStoreError,
)
from .grammar import Grammar, element, valid_children
from .node import BuilderNode, TreeStoreNode
from .store import TreeStore

__all__ = [
    # Core classes
    "TreeStore",
    "TreeStoreNode",
    # Builder classes
    "BuilderNode",
    "TreeStoreBuilder",
    # Grammar
    "Grammar",
    "element",
    "valid_children",
    # Exceptions
    "TreeStoreError",
    "InvalidChildError",
    "MissingChildError",
    "TooManyChildrenError",
    "InvalidParentError",
]
