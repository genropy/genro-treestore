# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""XsdBuilder - Dynamic builder generated from XSD schema.

Creates a builder class dynamically by parsing an XSD schema file.
The resulting builder has methods for all elements defined in the schema.

Example:
    >>> from genro_treestore.builders import XsdBuilder
    >>> from genro_treestore import TreeStore
    >>>
    >>> # Load XSD from file
    >>> xsd_content = open('fatturapa_v1.2.2.xsd').read()
    >>> schema = TreeStore.from_xml(xsd_content)
    >>> builder = XsdBuilder(schema)
    >>>
    >>> # Use with TreeStore
    >>> fattura = TreeStore(builder=builder)
    >>> fe = fattura.FatturaElettronica(versione='FPR12')
    >>> header = fe.FatturaElettronicaHeader()
    >>> # ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from genro_treestore.builders.base import BuilderBase

if TYPE_CHECKING:
    from genro_treestore import TreeStore, TreeStoreNode


class XsdBuilder(BuilderBase):
    """Builder dynamically generated from XSD schema.

    Creates methods for all elements defined in an XSD schema.
    Pass the schema TreeStore (from TreeStore.from_xml()) to __init__.

    Example:
        >>> xsd = open('fatturapa.xsd').read()
        >>> schema = TreeStore.from_xml(xsd)
        >>> builder = XsdBuilder(schema)
        >>>
        >>> fattura = TreeStore(builder=builder)
        >>> fattura.FatturaElettronica(versione='FPR12')
    """

    def __init__(self, schema_store: "TreeStore"):
        """Initialize builder from XSD schema TreeStore.

        Args:
            schema_store: TreeStore from TreeStore.from_xml(xsd_string).
        """
        self._schema_store = schema_store
        self._elements: dict[str, dict] = {}  # name -> spec
        self._types: dict[str, dict] = {}  # type name -> spec
        self._build_schema()

    def _build_schema(self) -> None:
        """Extract elements and types from XSD TreeStore."""
        # Find schema root (xs:schema)
        schema_node = None
        for node in self._schema_store.nodes():
            if node.attr.get("_tag", "").endswith(":schema") or node.label.startswith(
                "schema"
            ):
                schema_node = node
                break

        if schema_node is None or not schema_node.is_branch:
            return

        # First pass: collect all types
        self._collect_types(schema_node.value)

        # Second pass: collect elements
        self._collect_elements(schema_node.value)

        # Third pass: resolve type references to get children
        self._resolve_types()

    def _collect_types(self, store: "TreeStore") -> None:
        """Collect complexType and simpleType definitions."""
        for node in store.nodes():
            tag = node.attr.get("_tag", node.label.rsplit("_", 1)[0])
            name = node.attr.get("name")

            if "complexType" in tag and name:
                self._types[name] = self._parse_complex_type(node)
            elif "simpleType" in tag and name:
                self._types[name] = self._parse_simple_type(node)

    def _collect_elements(self, store: "TreeStore") -> None:
        """Collect element definitions."""
        for node in store.nodes():
            tag = node.attr.get("_tag", node.label.rsplit("_", 1)[0])
            name = node.attr.get("name")

            if "element" in tag and name:
                self._elements[name] = self._parse_element(node)

    def _parse_element(self, node: "TreeStoreNode") -> dict:
        """Parse an xs:element into a spec dict."""
        spec: dict[str, Any] = {}
        attr = node.attr

        # Get type reference
        type_ref = attr.get("type")
        if type_ref:
            # Strip namespace prefix
            type_name = type_ref.split(":")[-1] if ":" in type_ref else type_ref
            spec["type"] = type_name

        # Check for inline complexType
        if node.is_branch:
            for child in node.value.nodes():
                child_tag = child.attr.get("_tag", child.label.rsplit("_", 1)[0])
                if "complexType" in child_tag:
                    spec["children"] = self._extract_children(child)
                    break

        # If has type reference, get children from type
        if "type" in spec and spec["type"] in self._types:
            type_spec = self._types[spec["type"]]
            if "children" in type_spec:
                spec["children"] = type_spec["children"]

        return spec

    def _parse_complex_type(self, node: "TreeStoreNode") -> dict:
        """Parse a complexType definition."""
        spec: dict[str, Any] = {}

        if node.is_branch:
            spec["children"] = self._extract_children(node)

        return spec

    def _parse_simple_type(self, node: "TreeStoreNode") -> dict:
        """Parse a simpleType definition."""
        return {"leaf": True}

    def _resolve_types(self) -> None:
        """Resolve type references in elements to get children from types."""
        for elem_name, spec in self._elements.items():
            if "children" not in spec and "type" in spec:
                type_name = spec["type"]
                if type_name in self._types:
                    type_spec = self._types[type_name]
                    if "children" in type_spec:
                        spec["children"] = type_spec["children"]

    def _extract_children(self, node: "TreeStoreNode") -> set[str]:
        """Extract allowed child element names from complexType.

        Also registers discovered elements in self._elements.
        """
        children: set[str] = set()

        if not node.is_branch:
            return children

        for child in node.value.nodes():
            child_tag = child.attr.get("_tag", child.label.rsplit("_", 1)[0])

            if "element" in child_tag:
                # Direct element or reference
                name = child.attr.get("name")
                ref = child.attr.get("ref")
                type_ref = child.attr.get("type")

                elem_name = name or ref
                if elem_name:
                    # Strip namespace prefix
                    elem_name = (
                        elem_name.split(":")[-1] if ":" in elem_name else elem_name
                    )
                    children.add(elem_name)

                    # Register element if not already known
                    if elem_name not in self._elements:
                        spec: dict[str, Any] = {}
                        if type_ref:
                            type_name = (
                                type_ref.split(":")[-1] if ":" in type_ref else type_ref
                            )
                            spec["type"] = type_name
                        # Check for inline complexType
                        if child.is_branch:
                            spec["children"] = self._extract_children(child)
                        self._elements[elem_name] = spec

            elif "sequence" in child_tag or "choice" in child_tag or "all" in child_tag:
                # Recurse into compositor
                if child.is_branch:
                    children.update(self._extract_children(child))

            elif "complexType" in child_tag:
                # Inline type
                if child.is_branch:
                    children.update(self._extract_children(child))

        return children

    def __getattr__(self, name: str) -> Callable[..., "TreeStore | TreeStoreNode"]:
        """Dynamic method for any element in the schema."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        if name in self._elements:
            return self._make_element_method(name)

        raise AttributeError(
            f"'{name}' is not a valid element in this schema. "
            f"Valid elements: {', '.join(sorted(self._elements.keys())[:10])}..."
        )

    def _make_element_method(
        self, name: str
    ) -> Callable[..., "TreeStore | TreeStoreNode"]:
        """Create a method for a specific element."""
        spec = self._elements.get(name, {})
        children = spec.get("children", set())
        is_leaf = not children and "type" in spec

        def element_method(
            target: "TreeStore", tag: str = name, value: Any = None, **attr: Any
        ) -> "TreeStore | TreeStoreNode":
            if is_leaf and value is None:
                value = ""
            return self.child(target, tag, value=value, **attr)

        # Store children for validation
        element_method._valid_children = frozenset(children)
        element_method._child_cardinality = {}

        return element_method

    @property
    def elements(self) -> frozenset[str]:
        """Return all valid element names in the schema."""
        return frozenset(self._elements.keys())

    def get_children(self, element: str) -> frozenset[str] | None:
        """Get allowed children for an element."""
        spec = self._elements.get(element, {})
        children = spec.get("children")
        if children:
            return frozenset(children)
        return None
