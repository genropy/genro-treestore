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
    in a TreeStore. Use the @element decorator to define tags:

    1. Single tag (method name used):
        @element(children='item')
        def menu(self, target, tag, **attr):
            return self.child(target, tag, **attr)

    2. Multiple tags pointing to same method:
        @element(tags='fridge, oven, sink')
        def appliance(self, target, tag, **attr):
            return self.child(target, tag, value='', **attr)

    The class automatically builds a _element_tags dict mapping
    tag names to methods via __init_subclass__.

    Usage:
        >>> store = TreeStore(builder=MyBuilder())
        >>> store.fridge()  # calls appliance() with tag='fridge'
    """

    # Class-level dict mapping tag -> method name
    _element_tags: dict[str, str]

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
        """Look up tag in _element_tags and return the bound method."""
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        element_tags = getattr(type(self), '_element_tags', {})
        if name in element_tags:
            method_name = element_tags[name]
            return getattr(self, method_name)

        raise AttributeError(
            f"'{type(self).__name__}' has no element '{name}'"
        )

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
        """Get validation rules for a tag from decorated methods.

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

        method = getattr(self, tag, None)
        if method is None:
            return None, {}

        valid = getattr(method, '_valid_children', None)
        cardinality = getattr(method, '_child_cardinality', {})
        return valid, cardinality

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
