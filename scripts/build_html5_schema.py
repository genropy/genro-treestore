#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Build HTML5 schema MessagePack from W3C RNC files.

This script uses rnc2rng to parse the W3C HTML5 schema and converts
it to a TreeStore, then serializes it as MessagePack for fast loading.

Usage:
    python scripts/build_html5_schema.py

Output:
    src/genro_treestore/builders/rnc/schemas/html5_schema.msgpack

Requirements:
    pip install rnc2rng genro-tytx msgpack
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def convert_ast_to_treestore(ast_node, store, path: str = ""):
    """Recursively convert rnc2rng AST node to TreeStore.

    Args:
        ast_node: rnc2rng AST node
        store: TreeStore to populate
        path: Current path in store
    """
    from genro_treestore import TreeStore

    node_type = ast_node.type
    node_name = ast_node.name
    node_value = ast_node.value

    if node_type == "ROOT":
        # Process all children
        for child in node_value:
            convert_ast_to_treestore(child, store)
        return

    if node_type == "DEFAULT_NS":
        # Default namespace declaration
        uri = node_value[0] if node_value else ""
        prefix = node_name or ""
        store.set_item("_ns_default", uri, prefix=prefix)
        return

    if node_type == "NS":
        # Namespace declaration
        uri = node_value[0] if node_value else ""
        store.set_item(f"_ns_{node_name}", uri)
        return

    if node_type == "DATATYPES":
        # Datatype declaration
        uri = node_value[0] if node_value else ""
        store.set_item(f"_dt_{node_name}", uri)
        return

    if node_type == "DEFINE":
        # Definition: name = pattern
        def_name = node_name
        if not def_name:
            return

        # Get the ASSIGN node
        if node_value and len(node_value) > 0:
            assign_node = node_value[0]
            if hasattr(assign_node, "type") and assign_node.type == "ASSIGN":
                operator = assign_node.name  # "=" or "|=" or "&="
                pattern_nodes = assign_node.value

                # Convert pattern to TreeStore
                pattern_store = TreeStore()
                attrs = {}

                if operator in ("|=", "&="):
                    attrs["_combine"] = operator

                # Process pattern nodes
                for i, pnode in enumerate(pattern_nodes):
                    child_store, child_attrs = convert_pattern(pnode)
                    if child_store is not None:
                        if isinstance(child_store, TreeStore):
                            # Merge child store
                            for cnode in child_store.nodes():
                                pattern_store.set_item(cnode.label, cnode.value, **cnode.attr)
                        else:
                            pattern_store.set_item(f"item_{i}", child_store, **child_attrs)
                    elif child_attrs:
                        attrs.update(child_attrs)

                # Store definition
                if pattern_store.nodes():
                    store.set_item(def_name, pattern_store, **attrs)
                else:
                    # Leaf definition
                    value = ""
                    if pattern_nodes:
                        pn = pattern_nodes[0]
                        if hasattr(pn, "name") and pn.name:
                            value = pn.name
                    store.set_item(def_name, value, **attrs)
        return

    # Skip other node types at top level
    return


def convert_pattern(node) -> tuple:
    """Convert a pattern AST node to TreeStore value and attrs.

    Returns:
        Tuple of (value, attrs)
    """
    from genro_treestore import TreeStore

    if not hasattr(node, "type"):
        return None, {}

    node_type = node.type
    node_name = node.name
    node_value = node.value

    if node_type == "ELEM":
        # Element definition
        tag_name = None
        content_store = TreeStore()

        for child in node_value:
            if hasattr(child, "type"):
                if child.type == "NAME":
                    tag_name = child.name
                else:
                    child_val, child_attrs = convert_pattern(child)
                    if child_val is not None:
                        if isinstance(child_val, TreeStore):
                            for cnode in child_val.nodes():
                                content_store.set_item(cnode.label, cnode.value, **cnode.attr)
                        else:
                            content_store.set_item("content", child_val, **child_attrs)

        attrs = {"_type": "element"}
        if tag_name:
            attrs["_tag"] = tag_name

        if content_store.nodes():
            return content_store, attrs
        return "", attrs

    if node_type == "ATTR":
        # Attribute definition
        attr_name = None
        content = ""
        content_attrs = {}

        for child in node_value:
            if hasattr(child, "type"):
                if child.type == "NAME":
                    attr_name = child.name
                else:
                    content, content_attrs = convert_pattern(child)

        attrs = {"_type": "attribute"}
        if attr_name:
            attrs["_tag"] = attr_name
        attrs.update(content_attrs)

        return content if content else "", attrs

    if node_type == "REF":
        # Reference to another definition
        return node_name, {"_type": "ref"}

    if node_type == "TEXT":
        return "text", {"_type": "text"}

    if node_type == "EMPTY":
        return "empty", {"_type": "empty"}

    if node_type == "NOT_ALLOWED":
        return "notAllowed", {"_type": "notAllowed"}

    if node_type == "CHOICE":
        # Choice: a | b | c
        choice_store = TreeStore()
        for i, child in enumerate(node_value):
            child_val, child_attrs = convert_pattern(child)
            if child_val is not None:
                choice_store.set_item(f"choice_{i}", child_val, **child_attrs)
        return choice_store, {"_combinator": "choice"}

    if node_type == "INTERLEAVE":
        # Interleave: a & b & c
        items_store = TreeStore()
        for i, child in enumerate(node_value):
            child_val, child_attrs = convert_pattern(child)
            if child_val is not None:
                items_store.set_item(f"item_{i}", child_val, **child_attrs)
        return items_store, {"_combinator": "interleave"}

    if node_type == "SEQ":
        # Sequence: a, b, c
        items_store = TreeStore()
        for i, child in enumerate(node_value):
            child_val, child_attrs = convert_pattern(child)
            if child_val is not None:
                items_store.set_item(f"item_{i}", child_val, **child_attrs)
        return items_store, {"_combinator": "sequence"}

    if node_type == "MAYBE":
        # Optional: a?
        if node_value:
            child_val, child_attrs = convert_pattern(node_value[0])
            child_attrs["optional"] = True
            return child_val, child_attrs
        return None, {"optional": True}

    if node_type == "ANY":
        # Zero or more: a*
        if node_value:
            child_val, child_attrs = convert_pattern(node_value[0])
            child_attrs["multiple"] = True
            child_attrs["min"] = 0
            return child_val, child_attrs
        return None, {"multiple": True, "min": 0}

    if node_type == "SOME":
        # One or more: a+
        if node_value:
            child_val, child_attrs = convert_pattern(node_value[0])
            child_attrs["multiple"] = True
            child_attrs["min"] = 1
            return child_val, child_attrs
        return None, {"multiple": True, "min": 1}

    if node_type == "MIXED":
        # Mixed content
        if node_value:
            child_val, child_attrs = convert_pattern(node_value[0])
            child_attrs["_mixed"] = True
            return child_val, child_attrs
        return None, {"_mixed": True}

    if node_type == "LIST":
        # List
        if node_value:
            child_val, child_attrs = convert_pattern(node_value[0])
            child_attrs["_list"] = True
            return child_val, child_attrs
        return None, {"_list": True}

    if node_type == "GROUP":
        # Grouped pattern (parentheses)
        if node_value:
            # Process all children in group
            group_store = TreeStore()
            for i, child in enumerate(node_value):
                child_val, child_attrs = convert_pattern(child)
                if child_val is not None:
                    if isinstance(child_val, TreeStore):
                        for cnode in child_val.nodes():
                            group_store.set_item(cnode.label, cnode.value, **cnode.attr)
                    else:
                        group_store.set_item(f"item_{i}", child_val, **child_attrs)
            if group_store.nodes():
                return group_store, {}
        return None, {}

    if node_type == "DATATAG":
        # Datatype
        return node_name, {"_type": "datatype"}

    if node_type == "LITERAL":
        # Literal value
        return node_name, {"_type": "literal"}

    if node_type == "NAME":
        # Name (used in element/attribute names)
        return node_name, {}

    if node_type == "GRAMMAR":
        # Embedded grammar
        grammar_store = TreeStore()
        for child in node_value:
            convert_ast_to_treestore(child, grammar_store)
        return grammar_store, {"_type": "grammar"}

    if node_type == "DIV":
        # Division (grouping)
        div_store = TreeStore()
        for child in node_value:
            convert_ast_to_treestore(child, div_store)
        return div_store, {"_type": "div"}

    if node_type == "EXCEPT":
        # Exception pattern
        except_store = TreeStore()
        for i, child in enumerate(node_value):
            child_val, child_attrs = convert_pattern(child)
            if child_val is not None:
                except_store.set_item(f"except_{i}", child_val, **child_attrs)
        return except_store, {"_type": "except"}

    if node_type == "DOCUMENTATION":
        # Documentation comment
        doc_text = "\n".join(node_value) if node_value else ""
        return doc_text, {"_type": "doc"}

    # Unknown type - return as-is
    return node_name, {"_type": node_type.lower()}


def extract_elements_from_ast(ast_node, elements=None) -> set:
    """Extract all HTML element names directly from rnc2rng AST.

    Args:
        ast_node: rnc2rng AST node
        elements: Set to accumulate element names

    Returns:
        Set of element tag names.
    """
    if elements is None:
        elements = set()

    if not hasattr(ast_node, "type"):
        return elements

    if ast_node.type == "ELEM":
        # Get tag name from NAME child
        for child in ast_node.value:
            if hasattr(child, "type") and child.type == "NAME":
                tag = child.name
                # Skip wildcards and namespace prefixes
                if tag and tag != "*" and ":" not in tag:
                    elements.add(tag)
                break

    # Recurse into children
    for child in ast_node.value:
        if hasattr(child, "type"):
            extract_elements_from_ast(child, elements)

    return elements


def extract_elements(store) -> dict:
    """Extract all HTML elements from parsed schema.

    Returns:
        Dict mapping element tag names to their specs.
    """
    elements = {}

    def scan_node(node, path=""):
        # Check for element type
        if node.attr.get("_type") == "element":
            tag = node.attr.get("_tag", node.label)
            if tag and tag not in elements:
                elements[tag] = {
                    "path": path or node.label,
                    "attrs": dict(node.attr),
                }

        # Recurse into branches
        if node.is_branch:
            for child in node.value.nodes():
                child_path = f"{path}.{child.label}" if path else child.label
                scan_node(child, child_path)

    for node in store.nodes():
        scan_node(node)

    return elements


# HTML5 void elements (self-closing, no content)
# https://html.spec.whatwg.org/multipage/syntax.html#void-elements
HTML5_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",  # deprecated but still valid
    "source",
    "track",
    "wbr",
}


def get_void_elements(all_elements: set) -> set:
    """Get void elements from all elements.

    Uses the standard HTML5 void elements list.
    """
    return HTML5_VOID_ELEMENTS & all_elements


def build_html5_schema_store(ast) -> "TreeStore":
    """Build a simplified TreeStore with HTML5 schema info.

    Creates a TreeStore with:
    - _elements: all valid element names
    - _void_elements: void (self-closing) elements
    - Each element as a node with basic info
    """
    from genro_treestore import TreeStore

    store = TreeStore()

    # Extract all elements
    all_elements = extract_elements_from_ast(ast)

    # Get void elements from standard list
    void_elements = get_void_elements(all_elements)

    # Store element list
    store.set_item("_elements", sorted(all_elements))
    store.set_item("_void_elements", sorted(void_elements))

    # Create a node for each element
    for tag in sorted(all_elements):
        attrs = {"_type": "element"}
        if tag in void_elements:
            attrs["_void"] = True
        store.set_item(tag, "", **attrs)

    return store


def main():
    """Main entry point."""
    from rnc2rng.parser import parse
    from genro_treestore import TreeStore
    from genro_treestore.store.serialization import to_tytx

    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    schema_dir = project_root / "src/genro_treestore/builders/rnc/schemas/html5"
    output_file = schema_dir / "html5_schema.msgpack"

    # Check RNC files exist
    html5_rnc = schema_dir / "html5.rnc"
    if not html5_rnc.exists():
        print(f"ERROR: {html5_rnc} not found")
        print("Please download W3C HTML5 RNC schema first")
        sys.exit(1)

    print(f"Parsing {html5_rnc}...")

    # Parse with rnc2rng
    ast = parse(f=str(html5_rnc))

    # Extract elements directly from AST
    all_elements = extract_elements_from_ast(ast)
    print(f"HTML elements found: {len(all_elements)}")

    # Get void elements from standard list
    void_elements = get_void_elements(all_elements)
    print(f"Void elements: {len(void_elements)}")
    print(f"  {sorted(void_elements)}")

    # Build simplified schema store
    print(f"\nBuilding schema TreeStore...")
    store = build_html5_schema_store(ast)

    # Count nodes
    node_count = len(list(store.nodes()))
    print(f"Total nodes: {node_count}")

    # Show some elements
    print("\nSample elements:")
    for tag in sorted(all_elements)[:20]:
        void_marker = " (void)" if tag in void_elements else ""
        print(f"  {tag}{void_marker}")

    # Serialize to MessagePack
    print(f"\nSerializing to {output_file}...")

    msgpack_data = to_tytx(store, transport="msgpack")
    output_file.write_bytes(msgpack_data)

    # Stats
    size_kb = len(msgpack_data) / 1024
    print(f"Output size: {size_kb:.1f} KB")

    # Also save as JSON for inspection
    json_file = schema_dir / "html5_schema.json"
    json_data = to_tytx(store, transport="json")
    json_file.write_text(json_data)
    print(f"JSON output: {json_file}")

    print("\nDone!")


if __name__ == "__main__":
    main()
