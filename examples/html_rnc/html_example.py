# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""HTML RNC Example - Using RncBuilder with W3C HTML5 schema.

Demonstrates using RncBuilder to create a builder from RNC schema files.
Uses the HTML5 tables.rnc from W3C Validator as example.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from genro_treestore import TreeStore
from genro_treestore.builders.rnc import RncBuilder, parse_rnc

# W3C Validator HTML5 tables schema
RNC_URL = 'https://raw.githubusercontent.com/validator/validator/main/schema/html5/tables.rnc'
RNC_CACHE = Path(__file__).parent / 'tables.rnc'


def get_rnc_content() -> str:
    """Get RNC content, downloading if not cached."""
    if RNC_CACHE.exists():
        return RNC_CACHE.read_text()

    print(f"Downloading tables.rnc from {RNC_URL}...")
    with urllib.request.urlopen(RNC_URL) as response:
        content = response.read().decode('utf-8')

    RNC_CACHE.write_text(content)
    print(f"Cached to {RNC_CACHE}")
    return content


def example_from_string():
    """Example using RncBuilder with inline RNC schema."""
    print("\n1. RncBuilder from inline schema string")
    print("-" * 40)

    # Simple HTML-like schema
    builder = RncBuilder.from_rnc('''
        start = html
        html = element html { head, body }
        head = element head { title?, meta* }
        title = element title { text }
        meta = element meta { empty }
        body = element body { block* }
        block = div | p | table
        div = element div { (block | inline)* }
        p = element p { inline* }
        inline = text | span | a
        span = element span { inline* }
        a = element a { inline* }
        table = element table { tr+ }
        tr = element tr { (th | td)+ }
        th = element th { inline* }
        td = element td { inline* }
    ''')

    print(f"Elements in schema: {sorted(builder.elements)}")

    # Create HTML document
    store = TreeStore(builder=builder)
    html = store.html()

    head = html.head()
    head.title(value='My Page')
    head.meta(charset='utf-8')

    body = html.body()
    div = body.div(id='content')
    div.p(value='Hello, World!')

    table = body.table()
    tr1 = table.tr()
    tr1.th(value='Name')
    tr1.th(value='Value')
    tr2 = table.tr()
    tr2.td(value='foo')
    tr2.td(value='42')

    return store


def example_from_w3c():
    """Example using W3C HTML5 tables schema."""
    print("\n2. RncBuilder from W3C HTML5 tables.rnc")
    print("-" * 40)

    rnc_content = get_rnc_content()
    schema_store = parse_rnc(rnc_content)

    print(f"Schema definitions: {len(list(schema_store.nodes()))}")

    # Show some definitions
    print("\nSample definitions from tables.rnc:")
    for node in list(schema_store.nodes())[:5]:
        tag = node.tag or node.label
        type_attr = node.attr.get('_type', '')
        print(f"  {tag}: {type_attr}")

    return schema_store


def show_structure(store: TreeStore, indent: int = 0):
    """Display TreeStore structure as HTML-like output."""
    for node in store.nodes():
        prefix = '  ' * indent
        tag = node.tag or node.label
        attrs = ' '.join(f'{k}="{v}"' for k, v in node.attr.items()
                        if not k.startswith('_'))
        if node.is_branch:
            attr_str = f' {attrs}' if attrs else ''
            print(f'{prefix}<{tag}{attr_str}>')
            show_structure(node.value, indent + 1)
            print(f'{prefix}</{tag}>')
        else:
            attr_str = f' {attrs}' if attrs else ''
            if node.value:
                print(f'{prefix}<{tag}{attr_str}>{node.value}</{tag}>')
            else:
                print(f'{prefix}<{tag}{attr_str}/>')


if __name__ == '__main__':
    print("=" * 60)
    print("HTML RNC Example - RncBuilder")
    print("=" * 60)

    # Example 1: Inline schema
    store = example_from_string()
    print("\nGenerated HTML structure:")
    show_structure(store)

    # Example 2: W3C schema
    example_from_w3c()
