# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""RNC (RELAX NG Compact) schema builder for TreeStore.

This module provides:
- RncBuilder: Dynamic builder from RNC schema
- LazyRncBuilder: Lazy-loading variant for large schemas
- parse_rnc: Parse RNC content string
- parse_rnc_file: Parse RNC file

Example:
    >>> from genro_treestore.builders.rnc import RncBuilder, parse_rnc
    >>> builder = RncBuilder.from_rnc_file('schema.rnc')
"""

from .rnc_schema import RncBuilder, LazyRncBuilder
from .rnc_parser import parse_rnc, parse_rnc_file

__all__ = [
    "RncBuilder",
    "LazyRncBuilder",
    "parse_rnc",
    "parse_rnc_file",
]
