# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builder for TreeStore.

This module provides:
- XsdBuilder: Dynamic builder from XSD schema

Example:
    >>> from genro_treestore import TreeStore
    >>> from genro_treestore.builders.xsd import XsdBuilder
    >>>
    >>> xsd_content = open('schema.xsd').read()
    >>> schema = TreeStore.from_xml(xsd_content)
    >>> builder = XsdBuilder(schema)
"""

from .xsd_schema import XsdBuilder

__all__ = ["XsdBuilder"]
