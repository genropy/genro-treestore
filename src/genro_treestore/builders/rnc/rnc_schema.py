# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""RncBuilder - Dynamic builder generated from RNC (RELAX NG Compact) schema.

Creates a builder class dynamically by parsing a RELAX NG Compact (.rnc)
schema file. The resulting builder has methods for all elements defined
in the schema, with validation based on the schema's content model.

Note: For XSD schemas, use XsdBuilder from genro_treestore.builders.xsd

Example:
    >>> from genro_treestore.builders.schema import RncBuilder
    >>> from genro_treestore import TreeStore
    >>>
    >>> # Load schema from RNC file
    >>> builder = RncBuilder.from_rnc_file('html5.rnc')
    >>>
    >>> # Use with TreeStore
    >>> store = TreeStore(builder=builder)
    >>> html = store.html()
    >>> html.head().title(value='My Page')
    >>> html.body().div(id='main').p(value='Hello')
    >>>
    >>> # Or from RNC string
    >>> builder = RncBuilder.from_rnc('''
    ...     start = html
    ...     html = element html { head, body }
    ...     head = element head { title? }
    ...     title = element title { text }
    ...     body = element body { block* }
    ...     block = div | p
    ...     div = element div { inline* }
    ...     p = element p { inline* }
    ...     inline = text
    ... ''')
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from genro_treestore.builders.base import BuilderBase

if TYPE_CHECKING:
    from genro_treestore import TreeStore, TreeStoreNode


class RncBuilder(BuilderBase):
    """Builder dynamically generated from RNC (RELAX NG Compact) schema.

    This builder reads an RNC schema and creates methods for all defined
    elements. The schema's content model is used for validation.

    Attributes:
        _schema: Dict mapping element names to their specs (children, leaf, etc.)
        _elements: Set of all valid element names from the schema
        _void_elements: Set of elements that are void (no children, e.g., <br>)
        _definitions: Raw definitions from the parsed RNC TreeStore
    """

    def __init__(
        self,
        schema_store: TreeStore | None = None,
        void_elements: set[str] | None = None,
    ):
        """Initialize builder from a parsed RNC schema TreeStore.

        Args:
            schema_store: TreeStore from parse_rnc() or parse_rnc_file().
            void_elements: Optional set of element names that are void
                (self-closing, no content). If None, detected from schema.
        """
        self._definitions: TreeStore | None = schema_store
        self._elements: set[str] = set()
        self._void_elements: set[str] = void_elements or set()
        self._schema: dict[str, dict] = {}
        self._children_map: dict[str, set[str]] = {}

        if schema_store is not None:
            self._build_schema(schema_store)

    def _build_schema(self, schema_store: TreeStore) -> None:
        """Build _schema dict from parsed RNC TreeStore.

        Extracts element definitions and their content models from the
        RNC schema structure.

        Args:
            schema_store: TreeStore from parse_rnc().
        """
        # First pass: collect all element definitions
        for node in schema_store.nodes():
            label = node.label
            attr = node.attr

            # Skip namespace/datatype declarations
            if label.startswith('_'):
                continue

            # Check if this is an element definition
            if attr.get('_type') == 'element':
                tag_name = attr.get('_tag', label)
                self._elements.add(tag_name)

                # Build spec for this element
                spec = self._build_element_spec(node)
                self._schema[tag_name] = spec

            # Also check for reference definitions that resolve to elements
            elif attr.get('_type') == 'ref':
                # This is a reference to another definition
                # We'll resolve these in a second pass
                pass
            else:
                # Could be a pattern definition (e.g., flow = div | p | ...)
                # Extract element names from it
                self._extract_elements_from_pattern(node)

        # Second pass: resolve references and build children maps
        self._resolve_references(schema_store)

    def _build_element_spec(self, node: TreeStoreNode) -> dict:
        """Build a spec dict for an element node.

        Args:
            node: TreeStoreNode representing an element definition.

        Returns:
            Spec dict with 'children', 'leaf', 'attrs' keys.
        """
        attr = node.attr
        tag_name = attr.get('_tag', node.label)
        spec: dict[str, Any] = {}

        # Check if void element (empty content)
        if tag_name in self._void_elements:
            spec['leaf'] = True
            return spec

        # Analyze content model
        if node.is_branch:
            children = self._extract_children_from_content(node.value)
            if children:
                spec['children'] = children
        else:
            # Leaf element (text content or empty)
            value = node.value
            if value == 'empty' or attr.get('_type') == 'empty':
                spec['leaf'] = True
            elif value == 'text' or attr.get('_type') == 'text':
                # Text content - not a leaf, but no element children
                pass

        return spec

    def _extract_children_from_content(self, content: TreeStore) -> set[str] | None:
        """Extract allowed child element names from content model.

        Args:
            content: TreeStore representing element content.

        Returns:
            Set of allowed child tag names, or None if any element allowed.
        """
        children: set[str] = set()

        for node in content.nodes():
            attr = node.attr
            node_type = attr.get('_type')
            combinator = attr.get('_combinator')

            if node_type == 'element':
                # Direct element child
                tag = attr.get('_tag', node.label)
                children.add(tag)

            elif node_type == 'ref':
                # Reference to another definition - store for resolution
                ref_name = node.value if isinstance(node.value, str) else node.label
                # Mark as reference to resolve later
                children.add(f'={ref_name}')

            elif node_type == 'text':
                # Text is allowed, but doesn't add element children
                pass

            elif combinator in ('choice', 'sequence', 'interleave'):
                # Recurse into combinator children
                if node.is_branch:
                    sub_children = self._extract_children_from_content(node.value)
                    if sub_children:
                        children.update(sub_children)

            elif node.is_branch:
                # Other branch - recurse
                sub_children = self._extract_children_from_content(node.value)
                if sub_children:
                    children.update(sub_children)

        return children if children else None

    def _extract_elements_from_pattern(self, node: TreeStoreNode) -> None:
        """Extract element names from a pattern definition.

        Pattern definitions like `block = div | p | span` define
        groups of elements that can be used as content models.

        Args:
            node: TreeStoreNode representing a pattern definition.
        """
        attr = node.attr
        combinator = attr.get('_combinator')

        if combinator in ('choice', 'interleave', 'sequence'):
            # This is a choice/sequence pattern
            if node.is_branch:
                elements = set()
                for child in node.value.nodes():
                    child_type = child.attr.get('_type')
                    if child_type == 'element':
                        tag = child.attr.get('_tag', child.label)
                        elements.add(tag)
                        self._elements.add(tag)
                    elif child_type == 'ref':
                        # Reference - will be resolved later
                        ref = child.value if isinstance(child.value, str) else child.label
                        elements.add(f'={ref}')

                if elements:
                    self._children_map[node.label] = elements

    def _resolve_references(self, schema_store: TreeStore) -> None:
        """Resolve =ref references in children specs.

        Args:
            schema_store: The original schema TreeStore.
        """
        # Build a map of definition name -> child elements
        def_map: dict[str, set[str]] = {}

        for node in schema_store.nodes():
            if node.label.startswith('_'):
                continue

            attr = node.attr
            if attr.get('_type') == 'element':
                tag = attr.get('_tag', node.label)
                if tag in self._schema and 'children' in self._schema[tag]:
                    children = self._schema[tag]['children']
                    if isinstance(children, set):
                        def_map[node.label] = children

            elif attr.get('_combinator'):
                # Pattern definition
                if node.label in self._children_map:
                    def_map[node.label] = self._children_map[node.label]

        # Now resolve references in _schema
        for tag, spec in self._schema.items():
            if 'children' not in spec:
                continue

            children = spec['children']
            if not isinstance(children, set):
                continue

            resolved: set[str] = set()
            for child in children:
                if isinstance(child, str) and child.startswith('='):
                    ref_name = child[1:]
                    if ref_name in def_map:
                        resolved.update(def_map[ref_name])
                    elif ref_name in self._elements:
                        resolved.add(ref_name)
                else:
                    resolved.add(child)

            spec['children'] = resolved

    @classmethod
    def from_rnc(
        cls,
        content: str,
        void_elements: set[str] | None = None,
    ) -> 'RncBuilder':
        """Create builder from RNC content string.

        Args:
            content: RNC schema as string.
            void_elements: Optional set of void element names.

        Returns:
            RncBuilder instance.

        Example:
            >>> builder = RncBuilder.from_rnc('''
            ...     start = html
            ...     html = element html { head, body }
            ...     head = element head { title }
            ...     title = element title { text }
            ...     body = element body { div* }
            ...     div = element div { text }
            ... ''')
        """
        from .rnc_parser import parse_rnc
        schema_store = parse_rnc(content)
        return cls(schema_store, void_elements)

    @classmethod
    def from_rnc_file(
        cls,
        filepath: str | Path,
        void_elements: set[str] | None = None,
    ) -> 'RncBuilder':
        """Create builder from RNC file.

        Args:
            filepath: Path to .rnc file.
            void_elements: Optional set of void element names.

        Returns:
            RncBuilder instance.

        Example:
            >>> builder = RncBuilder.from_rnc_file('html5.rnc')
        """
        from .rnc_parser import parse_rnc_file
        schema_store = parse_rnc_file(filepath)
        return cls(schema_store, void_elements)

    @classmethod
    def from_resolver(
        cls,
        resolver: 'RncDirectoryResolver',
        void_elements: set[str] | None = None,
    ) -> 'RncBuilder':
        """Create builder from RNC directory resolver with lazy loading.

        Loads schema files on demand as elements are used. This is useful
        for large schemas like HTML5 that are split across multiple files.

        Args:
            resolver: RncDirectoryResolver pointing to schema directory.
            void_elements: Optional set of void element names.

        Returns:
            RncBuilder instance with lazy loading support.

        Example:
            >>> from genro_treestore.resolvers import html5_schema_resolver
            >>> builder = RncBuilder.from_resolver(html5_schema_resolver())
        """
        return LazyRncBuilder(resolver, void_elements)

    @classmethod
    def html5(cls, void_elements: set[str] | None = None) -> 'RncBuilder':
        """Create builder for HTML5 schema from W3C validator.

        Convenience method that creates a builder with the HTML5 schema
        from the W3C validator project, loaded lazily.

        Args:
            void_elements: Optional override for void elements.
                If None, uses standard HTML5 void elements.

        Returns:
            RncBuilder for HTML5.

        Example:
            >>> builder = RncBuilder.html5()
            >>> store = TreeStore(builder=builder)
            >>> store.html().head().title(value='My Page')
        """
        try:
            from .rnc_resolver import html5_schema_resolver
        except ImportError:
            from rnc_resolver import html5_schema_resolver

        if void_elements is None:
            # Standard HTML5 void elements
            void_elements = {
                'area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                'input', 'link', 'meta', 'param', 'source', 'track', 'wbr',
            }

        return cls.from_resolver(html5_schema_resolver(), void_elements)

    def __getattr__(self, name: str) -> Callable[..., TreeStore | TreeStoreNode]:
        """Dynamic method for any element in the schema.

        Args:
            name: Element name.

        Returns:
            Callable that creates a child with that element type.

        Raises:
            AttributeError: If name is not a valid element in the schema.
        """
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if it's a known element
        if name in self._elements:
            return self._make_element_method(name)

        # Check _schema (includes base class lookup)
        if name in self._schema:
            return self._make_schema_handler(name, self._schema[name])

        raise AttributeError(
            f"'{name}' is not a valid element in this schema. "
            f"Valid elements: {', '.join(sorted(self._elements)[:10])}..."
        )

    def _make_element_method(self, name: str) -> Callable[..., TreeStore | TreeStoreNode]:
        """Create a method for a specific element.

        Args:
            name: Element name.

        Returns:
            Callable that creates a child node.
        """
        is_void = name in self._void_elements
        spec = self._schema.get(name, {})
        is_leaf = spec.get('leaf', False)

        def element_method(
            target: TreeStore,
            tag: str = name,
            value: Any = None,
            **attr: Any
        ) -> TreeStore | TreeStoreNode:
            # Void/leaf elements get empty string value
            if (is_void or is_leaf) and value is None:
                value = ''
            return self.child(target, tag, value=value, **attr)

        return element_method

    def _resolve_ref(self, value: Any) -> Any:
        """Resolve =ref references using schema definitions.

        Overrides BuilderBase._resolve_ref to look up references
        in the schema's children_map and elements set.

        Args:
            value: The value to resolve.

        Returns:
            The resolved value.
        """
        # Handle sets/frozensets containing references
        if isinstance(value, (set, frozenset)):
            resolved = set()
            for item in value:
                resolved_item = self._resolve_ref(item)
                if isinstance(resolved_item, (set, frozenset)):
                    resolved.update(resolved_item)
                elif isinstance(resolved_item, str):
                    # Could be comma-separated string
                    resolved.update(t.strip() for t in resolved_item.split(',') if t.strip())
                else:
                    resolved.add(resolved_item)
            return frozenset(resolved) if isinstance(value, frozenset) else resolved

        if not isinstance(value, str):
            return value

        # If string contains comma, split and resolve each part recursively
        if ',' in value:
            parts = [p.strip() for p in value.split(',') if p.strip()]
            resolved_parts = []
            for part in parts:
                resolved_part = self._resolve_ref(part)
                if isinstance(resolved_part, (set, frozenset)):
                    resolved_parts.extend(resolved_part)
                elif isinstance(resolved_part, str):
                    resolved_parts.append(resolved_part)
                else:
                    resolved_parts.append(str(resolved_part))
            return ', '.join(resolved_parts)

        # Single value - check if it's a reference
        if value.startswith('='):
            ref_name = value[1:]  # '=flow' → 'flow'

            # First check if it's a known element
            if ref_name in self._elements:
                return ref_name

            # Then check if it's in children_map (pattern definition)
            if ref_name in self._children_map:
                # Recursively resolve the children
                return self._resolve_ref(self._children_map[ref_name])

            # Try parent class _ref_ properties
            prop_name = f'_ref_{ref_name}'
            if hasattr(self, prop_name):
                resolved = getattr(self, prop_name)
                return self._resolve_ref(resolved)

            # If not found, just return the ref name (might be a valid element)
            return ref_name

        return value

    @property
    def elements(self) -> frozenset[str]:
        """Return all valid element names in the schema."""
        return frozenset(self._elements)

    @property
    def void_elements(self) -> frozenset[str]:
        """Return void element names."""
        return frozenset(self._void_elements)

    def get_children(self, element: str) -> frozenset[str] | None:
        """Get allowed children for an element.

        Args:
            element: Element name.

        Returns:
            Frozenset of allowed child element names, or None if any allowed.
        """
        spec = self._schema.get(element, {})
        children = spec.get('children')
        if isinstance(children, (set, frozenset)):
            return frozenset(children)
        return None


class LazyRncBuilder(RncBuilder):
    """RncBuilder with lazy loading from RNC directory resolver.

    This builder loads schema files on demand as elements are accessed.
    Useful for large schemas like HTML5 split across multiple files.

    The builder maintains a TreeStore with resolvers for each schema file.
    When an unknown element is requested, it searches loaded schemas and
    potentially loads new ones to find the element definition.
    """

    def __init__(
        self,
        resolver: 'RncDirectoryResolver',
        void_elements: set[str] | None = None,
    ):
        """Initialize lazy schema builder.

        Args:
            resolver: RncDirectoryResolver for the schema directory.
            void_elements: Optional set of void element names.
        """
        # Don't call super().__init__ with schema - we'll load lazily
        self._definitions = None
        self._elements: set[str] = set()
        self._void_elements: set[str] = void_elements or set()
        self._schema: dict[str, dict] = {}
        self._children_map: dict[str, set[str]] = {}

        self._resolver = resolver
        self._schema_store: TreeStore | None = None
        self._loaded_files: set[str] = set()

    def _ensure_schema_store(self) -> TreeStore:
        """Ensure schema directory is loaded.

        Returns:
            TreeStore containing schema file nodes with resolvers.
        """
        if self._schema_store is None:
            from genro_treestore import TreeStore
            self._schema_store = TreeStore()
            self._schema_store.set_item('_root')
            self._schema_store.set_resolver('_root', self._resolver)
            # Trigger directory load
            _ = self._schema_store['_root']
        return self._schema_store

    def _load_schema_file(self, name: str) -> bool:
        """Load a specific schema file and extract elements.

        Args:
            name: Schema file name (without .rnc extension).

        Returns:
            True if file was loaded successfully.
        """
        if name in self._loaded_files:
            return True

        store = self._ensure_schema_store()
        try:
            # Access triggers RncResolver.load()
            schema = store[f'_root.{name}']
            if schema is not None:
                self._build_schema(schema)
                self._loaded_files.add(name)
                return True
        except (KeyError, FileNotFoundError, OSError):
            pass
        return False

    def _try_find_element(self, name: str) -> bool:
        """Try to find element by loading schema files.

        Searches through available schema files to find the element.

        Args:
            name: Element name to find.

        Returns:
            True if element was found after loading.
        """
        if name in self._elements:
            return True

        store = self._ensure_schema_store()
        root = store.get_node('_root')

        if root is None or not root.is_branch:
            return False

        # Try each schema file that hasn't been loaded
        for node in root.value.nodes():
            if node.label in self._loaded_files:
                continue
            if self._load_schema_file(node.label):
                if name in self._elements:
                    return True

        return name in self._elements

    def __getattr__(self, name: str) -> Callable[..., 'TreeStore | TreeStoreNode']:
        """Dynamic method for any element, with lazy loading.

        Args:
            name: Element name.

        Returns:
            Callable that creates a child with that element type.

        Raises:
            AttributeError: If name is not found in any schema file.
        """
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if already known
        if name in self._elements:
            return self._make_element_method(name)

        if name in self._schema:
            return self._make_schema_handler(name, self._schema[name])

        # Try to find in unloaded schemas
        if self._try_find_element(name):
            if name in self._elements:
                return self._make_element_method(name)
            if name in self._schema:
                return self._make_schema_handler(name, self._schema[name])

        raise AttributeError(
            f"'{name}' is not a valid element in this schema. "
            f"Loaded: {', '.join(sorted(self._loaded_files))}. "
            f"Known elements: {', '.join(sorted(self._elements)[:10])}..."
        )

    @property
    def elements(self) -> frozenset[str]:
        """Return currently known element names.

        Note: This may not include all elements if not all schema files
        have been loaded yet.
        """
        return frozenset(self._elements)

    def load_all(self) -> None:
        """Force load all schema files.

        Useful when you need access to all elements upfront.
        """
        store = self._ensure_schema_store()
        root = store.get_node('_root')

        if root is None or not root.is_branch:
            return

        for node in root.value.nodes():
            self._load_schema_file(node.label)
