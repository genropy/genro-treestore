# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""BuilderBase - Abstract base class for TreeStore builders."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..store import TreeStore
    from ..node import TreeStoreNode


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
                'div': {'children': FLOW_CONTENT},
                'br': {'leaf': True},
                'img': {'leaf': True, 'model': ImgModel},
            }

    Schema keys:
        - children: str or set of allowed child tags
        - leaf: True if element has no children (value='')
        - model: Pydantic model for attribute validation

    The lookup order is: decorated methods first, then _schema.

    Usage:
        >>> store = TreeStore(builder=MyBuilder())
        >>> store.fridge()  # calls appliance() with tag='fridge'
    """

    # Class-level dict mapping tag -> method name (from @element decorator)
    _element_tags: dict[str, str]

    # Schema dict for external element definitions (optional)
    _schema: dict[str, dict] = {}

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
            spec: Schema spec dict with keys: children, leaf, model.

        Returns:
            A callable that creates the element.
        """
        is_leaf = spec.get('leaf', False)
        model = spec.get('model')

        def handler(target, tag: str = tag, label: str | None = None, value=None, **attr):
            # Validate attributes with Pydantic model if specified
            if model is not None:
                try:
                    from pydantic import BaseModel
                    if isinstance(model, type) and issubclass(model, BaseModel):
                        model_fields = set(model.model_fields.keys())
                        attrs_to_validate = {
                            k: v for k, v in attr.items()
                            if k in model_fields
                        }
                        model(**attrs_to_validate)
                except ImportError:
                    pass  # Pydantic not available

            # Determine value: user-provided > leaf default > branch (None)
            if value is None and is_leaf:
                value = ''
            return self.child(target, tag, label=label, value=value, **attr)

        # Store validation rules on the handler for check() to find
        children_spec = spec.get('children')
        if children_spec is not None:
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
                - str: 'tag1, tag2[:1], tag3[1:]'
                - set/frozenset: {'tag1', 'tag2', 'tag3'}

        Returns:
            Tuple of (valid_children frozenset, cardinality dict).
        """
        from .decorators import _parse_tag_spec

        if isinstance(spec, (set, frozenset)):
            # Simple set of tags, no cardinality
            return frozenset(spec), {}

        # Parse string spec with cardinality
        parsed: dict[str, tuple[int, int | None]] = {}
        specs = [s.strip() for s in spec.split(',') if s.strip()]
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
        from ..node import TreeStoreNode

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
