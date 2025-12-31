# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Builders for TreeStore - base class and domain-specific implementations."""

from .base import BuilderBase
from .decorators import element, valid_children
from .html import HtmlBuilder, HtmlHeadBuilder, HtmlBodyBuilder, HtmlPage

__all__ = [
    'BuilderBase',
    'element',
    'valid_children',  # alias for backwards compatibility
    'HtmlBuilder',
    'HtmlHeadBuilder',
    'HtmlBodyBuilder',
    'HtmlPage',
]
