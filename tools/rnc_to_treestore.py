#!/usr/bin/env python
# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Demo script for RNC parser.

This script demonstrates parsing RelaxNG Compact files into TreeStore.
The actual parser is in genro_treestore.parsers.rnc module.

Usage:
    python tools/rnc_to_treestore.py [url_or_file]

Examples:
    # Parse tables.rnc from W3C Validator
    python tools/rnc_to_treestore.py

    # Parse local file
    python tools/rnc_to_treestore.py schema/my_schema.rnc

    # Parse from URL
    python tools/rnc_to_treestore.py https://example.com/schema.rnc
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from genro_treestore.parsers import parse_rnc, parse_rnc_file


def demo(source: str | None = None):
    """Demo parsing RNC content.

    Args:
        source: URL, file path, or None for default tables.rnc
    """
    import urllib.request

    if source is None:
        # Default: fetch tables.rnc from W3C Validator
        url = 'https://raw.githubusercontent.com/validator/validator/main/schema/html5/tables.rnc'
        print(f"Fetching {url}...")
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
        store = parse_rnc(content)
    elif source.startswith(('http://', 'https://')):
        print(f"Fetching {source}...")
        with urllib.request.urlopen(source) as response:
            content = response.read().decode('utf-8')
        store = parse_rnc(content)
    else:
        print(f"Parsing {source}...")
        store = parse_rnc_file(source)

    print("\n" + "=" * 60)
    print("Top-level definitions:")
    print("=" * 60)

    # Show top-level nodes
    for node in store.nodes():
        tag = node.tag or node.label
        type_attr = node.attr.get('_type', '')
        tag_attr = node.attr.get('_tag', '')

        if type_attr == 'element':
            print(f"  {tag}: element <{tag_attr}>")
        elif type_attr == 'attribute':
            print(f"  {tag}: attribute @{tag_attr}")
        elif type_attr == 'ref':
            print(f"  {tag}: → {node.value}")
        elif tag.startswith('_'):
            continue  # Skip meta
        else:
            print(f"  {tag}: {type_attr or node.value}")

    print("\n" + "=" * 60)
    print("Sample access examples:")
    print("=" * 60)

    # Try to access some common paths
    test_names = ['table.elem', 'table.attrs', 'td.elem', 'td.attrs.colspan',
                  'tables.attrs.scope', 'start']

    for name in test_names:
        try:
            node = store.get_node(name)
            if node:
                attrs = {k: v for k, v in node.attr.items() if not k.startswith('_')}
                meta = {k: v for k, v in node.attr.items() if k.startswith('_')}
                print(f"\nstore['{name}']:")
                print(f"  value: {node.value if node.is_leaf else '<branch>'}")
                if meta:
                    print(f"  meta: {meta}")
                if attrs:
                    print(f"  attrs: {attrs}")
        except Exception as e:
            print(f"\nstore['{name}']: not found ({e})")

    return store


if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else None
    demo(source)
