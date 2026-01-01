# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Parsers for populating TreeStore from various schema formats.

Available parsers:
- rnc: RelaxNG Compact syntax (.rnc files)

Example:
    >>> from genro_treestore.parsers import parse_rnc, parse_rnc_file
    >>> store = parse_rnc_file('schema.rnc')
    >>> store['element.attrs.name']
"""

from .rnc import parse_rnc, parse_rnc_file, RncLexer, RncParser

__all__ = [
    'parse_rnc',
    'parse_rnc_file',
    'RncLexer',
    'RncParser',
]
