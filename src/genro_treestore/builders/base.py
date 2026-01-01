# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""BuilderBase - Abstract base class for TreeStore builders."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..store import TreeStore
    from ..store import TreeStoreNode


class BuilderBase(ABC):
    """Abstract base class for TreeStore builders.

    A builder provides domain-specific methods for creating nodes
    in a TreeStore. There are two ways to define elements:

    1. Using @element decorator on methods:
        @element(children='item')
        def menu(self, target, tag, **attr):
            return self.child(target, tag, **attr)

        @element(tags='fridge, oven, sink')
        def appliance(self, target, tag, **attr):
            return self.child(target, tag, value='', **attr)

    2. Using _schema dict for external/dynamic definitions:
        class HtmlBuilder(BuilderBase):
            _schema = {
                'div': {'children': '=flow'},
                'br': {'leaf': True},
                'td': {
                    'children': '=flow',
                    'attrs': {
                        'colspan': {'type': 'int', 'min': 1, 'default': 1},
                        'rowspan': {'type': 'int', 'min': 0, 'default': 1},
                        'scope': {'type': 'enum', 'values': ['row', 'col']},
                    }
                },
            }

    Schema keys:
        - children: str or set of allowed child tags (supports =ref)
        - leaf: True if element has no children (value='')
        - attrs: dict of attribute specs for validation
            - type: 'int', 'string', 'uri', 'bool', 'enum', 'idrefs'
            - required: True/False (default: False)
            - min/max: numeric constraints for int type
            - default: default value
            - values: list of valid values for enum type

    The lookup order is: decorated methods first, then _schema.
    Attribute validation is performed with pure Python (no dependencies).

    Usage:
        >>> store = TreeStore(builder=MyBuilder())
        >>> store.fridge()  # calls appliance() with tag='fridge'
    """

    # Class-level dict mapping tag -> method name (from @element decorator)
    _element_tags: dict[str, str]

    # Schema dict for external element definitions (optional)
    _schema: dict[str, dict] = {}

    def _validate_attrs(
        self, tag: str, attrs: dict[str, Any], raise_on_error: bool = True
    ) -> list[str]:
        """Validate attributes against schema specification (pure Python).

        Args:
            tag: The tag name to get attrs spec for.
            attrs: Dict of attribute values to validate.
            raise_on_error: If True, raises ValueError on validation failure.
                If False, returns list of error messages.

        Returns:
            List of error messages (empty if valid).

        Raises:
            ValueError: If validation fails and raise_on_error is True.
        """
        schema = getattr(self, '_schema', {})
        spec = schema.get(tag, {})
        attrs_spec = spec.get('attrs')

        if not attrs_spec:
            return []

        errors = []

        for attr_name, attr_spec in attrs_spec.items():
            value = attrs.get(attr_name)
            required = attr_spec.get('required', False)
            type_name = attr_spec.get('type', 'string')

            # Check required
            if required and value is None:
                errors.append(f"'{attr_name}' is required for '{tag}'")
                continue

            # Skip validation if value not provided
            if value is None:
                continue

            # Type validation
            if type_name == 'int':
                if not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        errors.append(
                            f"'{attr_name}' must be an integer, got {type(value).__name__}"
                        )
                        continue

                # Range constraints
                min_val = attr_spec.get('min')
                max_val = attr_spec.get('max')
                if min_val is not None and value < min_val:
                    errors.append(
                        f"'{attr_name}' must be >= {min_val}, got {value}"
                    )
                if max_val is not None and value > max_val:
                    errors.append(
                        f"'{attr_name}' must be <= {max_val}, got {value}"
                    )

            elif type_name == 'bool':
                if not isinstance(value, bool):
                    if isinstance(value, str):
                        if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                            errors.append(
                                f"'{attr_name}' must be a boolean, got '{value}'"
                            )
                    else:
                        errors.append(
                            f"'{attr_name}' must be a boolean, got {type(value).__name__}"
                        )

            elif type_name == 'enum':
                values = attr_spec.get('values', [])
                if values and value not in values:
                    errors.append(
                        f"'{attr_name}' must be one of {values}, got '{value}'"
                    )

            # string, uri, idrefs, idref, color - accept any string
            elif type_name in ('string', 'uri', 'idrefs', 'idref', 'color'):
                if not isinstance(value, str):
                    # Allow conversion to string
                    pass

        if errors and raise_on_error:
            raise ValueError(f"Attribute validation failed for '{tag}': " + "; ".join(errors))

        return errors

    def _resolve_ref(self, value: Any) -> Any:
        """Resolve =ref references by looking up _ref_<name> properties.

        References use the = prefix convention (static pointer in Genropy):
        - '=flow' → looks up self._ref_flow property
        - '=phrasing' → looks up self._ref_phrasing property

        Handles comma-separated strings with mixed refs and literals:
        - '=appliances, sink' → split, resolve '=appliances', keep 'sink', rejoin

        This allows:
        - Override in subclasses (properties can be overridden)
        - Computed/lazy values (property getter is called each time)
        - Use in both _schema dict and @element decorator

        Args:
            value: The value to resolve. Can be:
                   - '=ref' → single reference
                   - '=ref, tag, =other' → mixed refs and literals
                   - set/frozenset containing references

        Returns:
            The resolved value, or the original value if not a reference.

        Raises:
            ValueError: If reference property not found on builder.

        Example:
            >>> class MyBuilder(BuilderBase):
            ...     @property
            ...     def _ref_flow(self):
            ...         return 'div, p, span, a'
            ...
            ...     _schema = {
            ...         'section': {'children': '=flow'},
            ...         'kitchen': {'children': '=appliances, sink'},
            ...     }
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
                    # Convert set to comma-separated string
                    resolved_parts.extend(resolved_part)
                elif isinstance(resolved_part, str):
                    resolved_parts.append(resolved_part)
                else:
                    resolved_parts.append(str(resolved_part))
            return ', '.join(resolved_parts)

        # Single value - check if it's a reference
        if value.startswith('='):
            ref_name = value[1:]  # '=flow' → 'flow'
            prop_name = f'_ref_{ref_name}'

            # Check if property exists on this instance
            if hasattr(self, prop_name):
                resolved = getattr(self, prop_name)
                # Recursively resolve in case the property returns another ref
                return self._resolve_ref(resolved)

            raise ValueError(
                f"Reference '{value}' not found: "
                f"no '{prop_name}' property on {type(self).__name__}"
            )

        return value

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build the _element_tags dict from @element decorated methods."""
        super().__init_subclass__(**kwargs)

        # Start with parent's tags if any
        cls._element_tags = {}
        for base in cls.__mro__[1:]:
            if hasattr(base, '_element_tags'):
                cls._element_tags.update(base._element_tags)
                break

        # Scan class methods for @element decorated ones
        for name, method in cls.__dict__.items():
            if name.startswith('_'):
                continue
            if not callable(method):
                continue

            element_tags = getattr(method, '_element_tags', None)
            if element_tags is None and hasattr(method, '_valid_children'):
                # No explicit tags, use method name
                cls._element_tags[name] = name
            elif element_tags:
                # Explicit tags specified
                for tag in element_tags:
                    cls._element_tags[tag] = name

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _element_tags or _schema and return handler."""
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        # First, check decorated methods
        element_tags = getattr(type(self), '_element_tags', {})
        if name in element_tags:
            method_name = element_tags[name]
            return getattr(self, method_name)

        # Then, check _schema
        schema = getattr(self, '_schema', {})
        if name in schema:
            return self._make_schema_handler(name, schema[name])

        raise AttributeError(
            f"'{type(self).__name__}' has no element '{name}'"
        )

    def _make_schema_handler(self, tag: str, spec: dict):
        """Create a handler function for a schema-defined element.

        Args:
            tag: The tag name.
            spec: Schema spec dict with keys:
                - children: str or set of allowed child tags
                - leaf: True if element has no children
                - attrs: dict for attribute validation

        Returns:
            A callable that creates the element.
        """
        is_leaf = spec.get('leaf', False)

        # Capture self for closure
        builder = self

        def handler(target, tag: str = tag, label: str | None = None, value=None, **attr):
            # Validation is handled by ValidationSubscriber after node creation
            # Determine value: user-provided > leaf default > branch (None)
            if value is None and is_leaf:
                value = ''
            return builder.child(target, tag, label=label, value=value, **attr)

        # Store validation rules on the handler for check() to find
        # Note: children_spec is resolved at validation time, not here
        children_spec = spec.get('children')
        if children_spec is not None:
            # Store raw spec - will be resolved in _parse_children_spec
            handler._raw_children_spec = children_spec
            handler._valid_children, handler._child_cardinality = \
                self._parse_children_spec(children_spec)
        else:
            # No children spec = leaf element (no children allowed)
            handler._valid_children = frozenset()
            handler._child_cardinality = {}

        return handler

    def _parse_children_spec(
        self, spec: str | set | frozenset
    ) -> tuple[frozenset[str], dict[str, tuple[int, int | None]]]:
        """Parse a children spec into validation rules.

        Args:
            spec: Can be:
                - str: 'tag1, tag2[:1], tag3[1:]' or '=ref' or '=ref, tag'
                - set/frozenset: {'tag1', 'tag2', '=ref'}

        Returns:
            Tuple of (valid_children frozenset, cardinality dict).
        """
        from .decorators import _parse_tag_spec

        # First, resolve any =references (handles split and recursion)
        resolved_spec = self._resolve_ref(spec)

        if isinstance(resolved_spec, (set, frozenset)):
            # Simple set of tags, no cardinality
            return frozenset(resolved_spec), {}

        # Parse string spec with cardinality
        parsed: dict[str, tuple[int, int | None]] = {}
        specs = [s.strip() for s in resolved_spec.split(',') if s.strip()]
        for tag_spec in specs:
            tag, min_c, max_c = _parse_tag_spec(tag_spec)
            parsed[tag] = (min_c, max_c)

        return frozenset(parsed.keys()), parsed

    def child(
        self,
        target: TreeStore,
        tag: str,
        label: str | None = None,
        value: Any = None,
        _position: str | None = None,
        _builder: BuilderBase | None = None,
        **attr: Any
    ) -> TreeStore | TreeStoreNode:
        """Create a child node in the target TreeStore.

        Args:
            target: The TreeStore to add the child to.
            tag: The node's type (stored in node.tag).
            label: Explicit label. If None, auto-generated as tag_N.
            value: If provided, creates a leaf node; otherwise creates a branch.
            _position: Position specifier (see TreeStore.set_item for syntax).
            _builder: Override builder for this branch and its descendants.
                     If None, inherits from target.
            **attr: Node attributes.

        Returns:
            TreeStore if branch (for adding children), TreeStoreNode if leaf.

        Example:
            >>> builder.child(store, 'div', id='main')
            >>> builder.child(store, 'meta', value='', charset='utf-8')  # void
            >>> builder.child(store, 'svg', _builder=SvgBuilder())
        """
        # Import here to avoid circular dependency
        from ..store import TreeStore
        from ..store import TreeStoreNode

        # Auto-generate label if not provided
        if label is None:
            n = 0
            while f"{tag}_{n}" in target._nodes:
                n += 1
            label = f"{tag}_{n}"

        # Determine builder for child
        child_builder = _builder if _builder is not None else target._builder

        if value is not None:
            # Leaf node
            node = TreeStoreNode(label, attr, value, parent=target, tag=tag)
            target._insert_node(node, _position)
            return node
        else:
            # Branch node
            child_store = TreeStore(builder=child_builder)
            node = TreeStoreNode(label, attr, value=child_store, parent=target, tag=tag)
            child_store.parent = node
            target._insert_node(node, _position)
            return child_store

    def _get_validation_rules(
        self, tag: str | None
    ) -> tuple[frozenset[str] | None, dict[str, tuple[int, int | None]]]:
        """Get validation rules for a tag from decorated methods or schema.

        Args:
            tag: The tag name to look up. None means root level.

        Returns:
            Tuple of (valid_children, child_cardinality).
            - valid_children: frozenset of allowed child tag names, or None if no rules
            - child_cardinality: dict mapping tag -> (min, max) for each child type
            Returns (None, {}) if no rules defined or tag is None.
        """
        if tag is None:
            return None, {}

        # First, check decorated methods
        element_tags = getattr(type(self), '_element_tags', {})
        if tag in element_tags:
            method_name = element_tags[tag]
            method = getattr(self, method_name, None)
            if method is not None:
                # Check for raw children spec (needs dynamic resolution)
                raw_spec = getattr(method, '_raw_children_spec', None)
                if raw_spec is not None:
                    # Re-parse with current instance for =ref resolution
                    return self._parse_children_spec(raw_spec)
                # Otherwise use pre-computed values
                valid = getattr(method, '_valid_children', None)
                cardinality = getattr(method, '_child_cardinality', {})
                return valid, cardinality

        # Then, check _schema
        schema = getattr(self, '_schema', {})
        if tag in schema:
            spec = schema[tag]
            children_spec = spec.get('children')
            if children_spec is not None:
                return self._parse_children_spec(children_spec)
            else:
                # No children spec = leaf element
                return frozenset(), {}

        return None, {}

    def check(
        self,
        store: TreeStore,
        parent_tag: str | None = None,
        path: str = ''
    ) -> list[str]:
        """Check the TreeStore structure against this builder's rules.

        Checks structure rules defined via @element(children=...) decorator:
        - valid_children: which tags can be children of this tag
        - cardinality: per-tag min/max constraints using slice syntax

        Args:
            store: The TreeStore to check.
            parent_tag: The tag of the parent node (for context).
            path: Current path in the tree (for error messages).

        Returns:
            List of error messages (empty if valid).
        """
        errors = []

        # Get rules for parent tag
        valid_children, cardinality = self._get_validation_rules(parent_tag)

        # Count children by tag
        child_counts: dict[str, int] = {}
        for node in store.nodes():
            child_tag = node.tag or node.label
            child_counts[child_tag] = child_counts.get(child_tag, 0) + 1

        # Check each child
        for node in store.nodes():
            child_tag = node.tag or node.label
            node_path = f"{path}.{node.label}" if path else node.label

            # Check if child tag is valid for parent
            if valid_children is not None and child_tag not in valid_children:
                if valid_children:
                    errors.append(
                        f"'{child_tag}' is not a valid child of '{parent_tag}'. "
                        f"Valid children: {', '.join(sorted(valid_children))}"
                    )
                else:
                    errors.append(
                        f"'{child_tag}' is not a valid child of '{parent_tag}'. "
                        f"'{parent_tag}' cannot have children"
                    )

            # Recursively check branch children
            if not node.is_leaf:
                child_errors = self.check(node.value, parent_tag=child_tag, path=node_path)
                errors.extend(child_errors)

        # Check per-tag cardinality constraints
        for tag, (min_count, max_count) in cardinality.items():
            actual = child_counts.get(tag, 0)

            if min_count > 0 and actual < min_count:
                errors.append(
                    f"'{parent_tag}' requires at least {min_count} '{tag}', "
                    f"but has {actual}"
                )
            if max_count is not None and actual > max_count:
                errors.append(
                    f"'{parent_tag}' allows at most {max_count} '{tag}', "
                    f"but has {actual}"
                )

        return errors
