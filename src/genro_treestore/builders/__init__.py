# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Builders for TreeStore - typed APIs with structural validation.

Builders provide domain-specific fluent APIs for constructing TreeStore
hierarchies with compile-time-like validation. They enforce structural
rules, validate attributes, and ensure well-formed output.

Builder Types:
    - **BuilderBase**: Abstract base class for custom builders
    - **HtmlBuilder**: HTML5 document builder with element validation
    - **XsdBuilder**: Dynamic builder from XML Schema (XSD) files

Decorators:
    - **@element**: Define an element handler with validation rules

Creating Custom Builders:
    Extend BuilderBase and use the @element decorator::

        from genro_treestore.builders import BuilderBase, element

        class MyBuilder(BuilderBase):
            @element(children='item[1:]')  # At least one item required
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def item(self, target, tag, value=None, **attr):
                return self.child(target, tag, value=value, **attr)

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
    - :mod:`genro_treestore.builders.xsd` - XSD schema builder
"""

from .base import BuilderBase
from .decorators import element
from .html import HtmlBuilder, HtmlHeadBuilder, HtmlBodyBuilder, HtmlPage
from .xsd import XsdBuilder

__all__ = [
    "BuilderBase",
    "element",
    "HtmlBuilder",
    "HtmlHeadBuilder",
    "HtmlBodyBuilder",
    "HtmlPage",
    "XsdBuilder",
]
