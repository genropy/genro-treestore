# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""HtmlBuilder - HTML5 element builder with content model validation.

This module provides builders for generating HTML5 documents with
structural validation based on the WHATWG HTML Living Standard.

Content Categories:
    HTML5 defines several content categories that determine where
    elements can appear and what they can contain:

    - **Metadata content**: Elements for document metadata (head section)
    - **Flow content**: Most elements that can appear in body
    - **Phrasing content**: Text-level semantics (inline elements)
    - **Heading content**: Section headings (h1-h6, hgroup)
    - **Sectioning content**: Document outline elements
    - **Embedded content**: External resources (img, video, etc.)
    - **Interactive content**: User interaction elements

References:
    - WHATWG HTML Standard: https://html.spec.whatwg.org/
    - Content categories: https://html.spec.whatwg.org/dev/dom.html

Example:
    Creating an HTML document::

        from genro_treestore import TreeStore
        from genro_treestore.builders import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder())
        body = store.body()
        div = body.div(id='main', class_='container')
        div.h1(value='Welcome')
        div.p(value='Hello, World!')
        ul = div.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from .base import BuilderBase

if TYPE_CHECKING:
    from ..store import TreeStore
    from ..store import TreeStoreNode


# =============================================================================
# HTML5 Content Categories
# Based on WHATWG HTML Standard: https://html.spec.whatwg.org/dev/dom.html
# =============================================================================

# Void elements - self-closing, cannot have children or text content
VOID_ELEMENTS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'source', 'track', 'wbr'
})

# Metadata content - elements for document metadata (in <head>)
METADATA_CONTENT = frozenset({
    'base', 'link', 'meta', 'noscript', 'script', 'style', 'template', 'title'
})

# Flow content - most elements allowed in <body>
# This is the largest category, containing block and inline elements
FLOW_CONTENT = frozenset({
    'a', 'abbr', 'address', 'article', 'aside', 'audio', 'b', 'bdi', 'bdo',
    'blockquote', 'br', 'button', 'canvas', 'cite', 'code', 'data', 'datalist',
    'del', 'details', 'dfn', 'dialog', 'div', 'dl', 'em', 'embed', 'fieldset',
    'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
    'hgroup', 'hr', 'i', 'iframe', 'img', 'input', 'ins', 'kbd', 'label',
    'main', 'map', 'mark', 'math', 'menu', 'meter', 'nav', 'noscript',
    'object', 'ol', 'output', 'p', 'picture', 'pre', 'progress', 'q', 'ruby',
    's', 'samp', 'script', 'search', 'section', 'select', 'slot', 'small',
    'span', 'strong', 'sub', 'sup', 'svg', 'table', 'template', 'textarea',
    'time', 'u', 'ul', 'var', 'video', 'wbr'
})

# Phrasing content - text-level semantics (roughly: inline elements)
PHRASING_CONTENT = frozenset({
    'a', 'abbr', 'audio', 'b', 'bdi', 'bdo', 'br', 'button', 'canvas', 'cite',
    'code', 'data', 'datalist', 'del', 'dfn', 'em', 'embed', 'i', 'iframe',
    'img', 'input', 'ins', 'kbd', 'label', 'map', 'mark', 'math', 'meter',
    'noscript', 'object', 'output', 'picture', 'progress', 'q', 'ruby', 's',
    'samp', 'script', 'select', 'slot', 'small', 'span', 'strong', 'sub',
    'sup', 'svg', 'template', 'textarea', 'time', 'u', 'var', 'video', 'wbr'
})

# Heading content - section headings
HEADING_CONTENT = frozenset({'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hgroup'})

# Sectioning content - elements that define document outline
SECTIONING_CONTENT = frozenset({'article', 'aside', 'nav', 'section'})

# Embedded content - external resources
EMBEDDED_CONTENT = frozenset({
    'audio', 'canvas', 'embed', 'iframe', 'img', 'math', 'object', 'picture',
    'svg', 'video'
})

# Interactive content - elements for user interaction
INTERACTIVE_CONTENT = frozenset({
    'a', 'audio', 'button', 'details', 'embed', 'iframe', 'img', 'input',
    'label', 'select', 'textarea', 'video'
})

# =============================================================================
# Element-specific child constraints
# Maps parent elements to their allowed children
# =============================================================================

ELEMENT_CHILDREN = {
    # Document structure
    'html': {'head', 'body'},
    'head': METADATA_CONTENT,
    'body': FLOW_CONTENT,

    # Lists
    'ul': {'li'},
    'ol': {'li'},
    'dl': {'dt', 'dd', 'div'},
    'menu': {'li'},

    # Tables
    'table': {'caption', 'colgroup', 'thead', 'tbody', 'tfoot', 'tr'},
    'thead': {'tr'},
    'tbody': {'tr'},
    'tfoot': {'tr'},
    'tr': {'th', 'td'},
    'colgroup': {'col'},

    # Forms
    'select': {'option', 'optgroup'},
    'optgroup': {'option'},
    'datalist': {'option'},
    'fieldset': {'legend'} | FLOW_CONTENT,

    # Grouping with special first child
    'figure': {'figcaption'} | FLOW_CONTENT,
    'details': {'summary'} | FLOW_CONTENT,

    # Media
    'picture': {'source', 'img'},
    'audio': {'source', 'track'} | FLOW_CONTENT,
    'video': {'source', 'track'} | FLOW_CONTENT,

    # Other
    'map': {'area'} | FLOW_CONTENT,
    'ruby': {'rt', 'rp'} | PHRASING_CONTENT,
}

# All known HTML5 tags (union of all categories plus structural elements)
ALL_TAGS = (
    METADATA_CONTENT | FLOW_CONTENT | VOID_ELEMENTS |
    {'html', 'head', 'body', 'li', 'dt', 'dd', 'caption', 'colgroup', 'col',
     'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'option', 'optgroup',
     'legend', 'figcaption', 'summary', 'source', 'track', 'area', 'rt', 'rp'}
)


class HtmlBuilder(BuilderBase):
    """Builder for HTML elements.

    Provides dynamic methods for all HTML tags via __getattr__.
    Void elements (meta, br, img, etc.) automatically use empty string value.

    Usage:
        >>> store = TreeStore(builder=HtmlBuilder())
        >>> store.div(id='main').p(value='Hello')
        >>> store.ul().li(value='Item 1')

    Categories available as class attributes for reference:
        - VOID_ELEMENTS
        - FLOW_CONTENT
        - PHRASING_CONTENT
        - etc.
    """

    # Expose categories as class attributes
    VOID_ELEMENTS = VOID_ELEMENTS
    METADATA_CONTENT = METADATA_CONTENT
    FLOW_CONTENT = FLOW_CONTENT
    PHRASING_CONTENT = PHRASING_CONTENT
    HEADING_CONTENT = HEADING_CONTENT
    SECTIONING_CONTENT = SECTIONING_CONTENT
    EMBEDDED_CONTENT = EMBEDDED_CONTENT
    INTERACTIVE_CONTENT = INTERACTIVE_CONTENT
    ELEMENT_CHILDREN = ELEMENT_CHILDREN
    ALL_TAGS = ALL_TAGS

    def __getattr__(self, name: str) -> Callable[..., TreeStore | TreeStoreNode]:
        """Dynamic method for any HTML tag.

        Args:
            name: Tag name (e.g., 'div', 'span', 'meta')

        Returns:
            Callable that creates a child with that tag.

        Raises:
            AttributeError: If name is not a valid HTML tag.
        """
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        if name in ALL_TAGS:
            return self._make_tag_method(name)

        raise AttributeError(f"'{name}' is not a valid HTML tag")

    def _make_tag_method(self, name: str) -> Callable[..., TreeStore | TreeStoreNode]:
        """Create a method for a specific tag."""
        is_void = name in VOID_ELEMENTS

        def tag_method(
            target: TreeStore,
            tag: str = name,
            value: Any = None,
            **attr: Any
        ) -> TreeStore | TreeStoreNode:
            # Void elements get empty string value (self-closing)
            if is_void and value is None:
                value = ''
            return self.child(target, tag, value=value, **attr)

        return tag_method


class HtmlHeadBuilder(HtmlBuilder):
    """Builder for HTML head section.

    Allows all HTML tags but semantically intended for head content
    (meta, title, link, style, script, etc.)
    """
    pass


class HtmlBodyBuilder(HtmlBuilder):
    """Builder for HTML body section.

    Allows all HTML tags for body content generation.
    """
    pass


class HtmlPage:
    """HTML page with separate head and body TreeStores.

    Creates a complete HTML document structure with:
    - html root TreeStore
    - head TreeStore with HtmlHeadBuilder (metadata only)
    - body TreeStore with HtmlBodyBuilder (flow content)

    Usage:
        >>> page = HtmlPage()
        >>> page.head.title(value='My Page')
        >>> page.head.meta(charset='utf-8')
        >>> page.body.div(id='main').p(value='Hello World')
        >>> html = page.to_html()
    """

    def __init__(self):
        """Initialize the page with head and body."""
        from ..store import TreeStore

        self.html = TreeStore()
        self.head = TreeStore(builder=HtmlHeadBuilder())
        self.body = TreeStore(builder=HtmlBodyBuilder())
        self.html.set_item('head', self.head)
        self.html.set_item('body', self.body)

    def _node_to_html(self, node: TreeStoreNode, indent: int = 0) -> str:
        """Recursively convert a node to HTML."""
        tag = node.tag or node.label
        attrs = ' '.join(
            f'{k}="{v}"' for k, v in node.attr.items()
            if not k.startswith('_')
        )
        attrs_str = f' {attrs}' if attrs else ''
        spaces = '  ' * indent

        if node.is_leaf:
            if node.value == '':
                return f'{spaces}<{tag}{attrs_str}>'
            return f'{spaces}<{tag}{attrs_str}>{node.value}</{tag}>'

        lines = [f'{spaces}<{tag}{attrs_str}>']
        for child in node.value.nodes():
            lines.append(self._node_to_html(child, indent + 1))
        lines.append(f'{spaces}</{tag}>')
        return '\n'.join(lines)

    def _store_to_html(self, store: TreeStore, tag: str, indent: int = 0) -> str:
        """Convert a TreeStore to HTML with a wrapper tag."""
        spaces = '  ' * indent
        lines = [f'{spaces}<{tag}>']
        for node in store.nodes():
            lines.append(self._node_to_html(node, indent + 1))
        lines.append(f'{spaces}</{tag}>')
        return '\n'.join(lines)

    def to_html(self, filename: str | None = None, output_dir: str | None = None) -> str:
        """Generate complete HTML.

        Args:
            filename: If provided, save to output_dir/filename
            output_dir: Directory to save to (default: current directory)

        Returns:
            HTML string, or path if filename was provided
        """
        from pathlib import Path

        html_lines = [
            '<!DOCTYPE html>',
            '<html>',
            self._store_to_html(self.head, 'head', indent=0),
            self._store_to_html(self.body, 'body', indent=0),
            '</html>'
        ]
        html_content = '\n'.join(html_lines)

        if filename:
            if output_dir is None:
                output_dir = Path.cwd()
            else:
                output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / filename
            output_path.write_text(html_content)
            return str(output_path)

        return html_content

    def print_tree(self):
        """Print the tree structure for debugging."""
        print("=" * 60)
        print("HEAD")
        print("=" * 60)
        for path, node in self.head.walk():
            indent_level = "  " * path.count('.')
            tag = node.tag or node.label
            value_str = ''
            if node.is_leaf and node.value:
                val = str(node.value)
                value_str = f': "{val[:30]}..."' if len(val) > 30 else f': "{val}"'
            print(f"{indent_level}<{tag}>{value_str}")

        print("\n" + "=" * 60)
        print("BODY")
        print("=" * 60)
        for path, node in self.body.walk():
            indent_level = "  " * path.count('.')
            tag = node.tag or node.label
            value_str = f': "{node.value}"' if node.is_leaf and node.value else ''
            attrs = ' '.join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith('_'))
            attrs_str = f' [{attrs}]' if attrs else ''
            print(f"{indent_level}<{tag}{attrs_str}>{value_str}")
