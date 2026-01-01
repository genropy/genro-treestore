# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Builders for TreeStore - typed APIs with structural validation.

Builders provide domain-specific fluent APIs for constructing TreeStore
hierarchies with compile-time-like validation. They enforce structural
rules, validate attributes, and ensure well-formed output.

Builder Types:
    - **BuilderBase**: Abstract base class for custom builders
    - **HtmlBuilder**: HTML5 document builder with element validation
    - **RncBuilder**: Dynamic builder from RELAX NG Compact schemas
    - **XsdBuilder**: Dynamic builder from XML Schema (XSD) files

Decorators:
    - **@element**: Define an element handler with validation rules
    - **@valid_children**: Specify allowed child tags with cardinality

Creating Custom Builders:
    Extend BuilderBase and use decorators or _schema dict::

        from genro_treestore.builders import BuilderBase, element, valid_children

        class MyBuilder(BuilderBase):
            @element
            @valid_children('item[1:]')  # At least one item required
            def container(self, store, parent, **attrs):
                pass

            @element
            def item(self, store, parent, value=None, **attrs):
                pass

Dynamic Schema Builders:
    Load structure from external schema files::

        from genro_treestore.builders import RncBuilder, XsdBuilder

        # From RELAX NG Compact
        html_builder = RncBuilder.from_rnc_file('html5.rnc')

        # From XML Schema
        invoice_builder = XsdBuilder(TreeStore.from_xml(xsd_content))

Example:
    Using HtmlBuilder for type-safe HTML generation::

        from genro_treestore import TreeStore
        from genro_treestore.builders import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder())
        body = store.body()
        div = body.div(id='main', class_='container')
        div.h1(value='Hello World')
        div.p(value='Welcome to TreeStore builders.')

See Also:
    - :mod:`genro_treestore.builders.base` - BuilderBase implementation
    - :mod:`genro_treestore.builders.html` - HTML5 builder
    - :mod:`genro_treestore.builders.rnc` - RNC schema builder
    - :mod:`genro_treestore.builders.xsd` - XSD schema builder
"""

from .base import BuilderBase
from .decorators import element, valid_children
from .html import HtmlBuilder, HtmlHeadBuilder, HtmlBodyBuilder, HtmlPage
from .rnc import RncBuilder, LazyRncBuilder
from .xsd import XsdBuilder

__all__ = [
    "BuilderBase",
    "element",
    "valid_children",
    "HtmlBuilder",
    "HtmlHeadBuilder",
    "HtmlBodyBuilder",
    "HtmlPage",
    "RncBuilder",
    "LazyRncBuilder",
    "XsdBuilder",
]
