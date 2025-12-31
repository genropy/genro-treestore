# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStoreBuilder - Builder pattern for TreeStore."""

from __future__ import annotations

import re
from typing import Any, Callable

from .exceptions import (
    InvalidChildError,
    InvalidParentError,
    MissingChildError,
    TooManyChildrenError,
)
from .grammar import Grammar
from .node import BuilderNode, TreeStoreNode
from .store import TreeStore


class TreeStoreBuilder(TreeStore):
    """Builder pattern for TreeStore with auto-labeling and validation.

    Use child() to create nodes with auto-generated labels (tag_N pattern).

    Can be used in two ways:

    1. Subclass to create domain-specific builders with @valid_children:

        >>> class HtmlBuilder(TreeStoreBuilder):
        ...     @valid_children('li')
        ...     def ul(self, **attr):
        ...         return self.child('ul', **attr)
        ...
        ...     def li(self, value=None, **attr):
        ...         return self.child('li', value=value, **attr)
        ...
        >>> builder = HtmlBuilder()
        >>> ul = builder.ul()
        >>> ul.li('Item 1')
        >>> ul.li('Item 2')

    2. Pass a Grammar class for dynamic tag methods:

        >>> class HtmlGrammar(Grammar):
        ...     @property
        ...     def block(self):
        ...         return dict(tag='div,section', valid_children={'div,span': '*'})
        ...
        ...     @element(tag='ul,ol', valid_children={'li': '+'})
        ...     def ul(self, node, items=None, **attr):
        ...         if items:
        ...             for item in items:
        ...                 node.li(value=item)
        ...         return node
        ...
        >>> builder = TreeStoreBuilder(grammar=HtmlGrammar)
        >>> builder.div(id='main')     # from grammar property
        >>> builder.ul(items=['a','b']) # from @element method
    """

    __slots__ = ('_tag_counters', '_grammar')

    node_factory: type[TreeStoreNode] = BuilderNode

    def __init__(
        self,
        parent: TreeStoreNode | None = None,
        grammar: type[Grammar] | Grammar | None = None,
    ) -> None:
        """Initialize a TreeStoreBuilder.

        Args:
            parent: The TreeStoreNode that contains this store as its value.
            grammar: A Grammar class or instance defining valid tags and rules.
        """
        super().__init__(parent=parent)
        self._tag_counters: dict[str, int] = {}

        # Handle grammar parameter
        if grammar is None:
            self._grammar: Grammar | None = None
        elif isinstance(grammar, type):
            # Grammar class passed, instantiate it
            self._grammar = grammar()
        else:
            # Grammar instance passed
            self._grammar = grammar

    @property
    def store(self) -> TreeStore:
        """Access the underlying TreeStore."""
        return self

    @property
    def grammar(self) -> Grammar | None:
        """Access the grammar instance.

        Use this to access tag methods when they clash with TreeStore methods.
        Example: builder.grammar.keys instead of builder.keys
        """
        return self._grammar

    def __getattr__(self, name: str) -> Any:
        """Dynamic tag method access via grammar.

        If a grammar is defined and the name matches a tag, returns a callable
        that creates a child node with that tag.

        Real methods on TreeStoreBuilder take precedence (e.g., keys(), values()).
        For clashing names, use builder.grammar.tagname or builder.child('tagname').
        """
        # Check if we have a grammar and this name is a valid tag
        if self._grammar is not None:
            config = self._grammar.get_config(name)
            if config is not None:
                # Return a callable that creates a child with this tag
                return self._make_tag_method(name, config)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def _make_tag_method(
        self, tag: str, config: dict[str, Any]
    ) -> Callable[..., TreeStoreBuilder | BuilderNode]:
        """Create a tag method for dynamic grammar access."""
        custom_method = config.get('method')

        def tag_method(
            value: Any = None,
            _position: str | None = None,
            **attr: Any
        ) -> TreeStoreBuilder | BuilderNode:
            # Create the child node
            child = self.child(tag, value=value, _position=_position, **attr)

            # If there's a custom method, call it with the node
            if custom_method is not None:
                result = custom_method(self._grammar, child, **attr)
                if result is not None:
                    return result

            return child

        return tag_method

    def _generate_label(self, tag: str) -> str:
        """Generate a unique label for a tag.

        Uses pattern: tag_0, tag_1, tag_2, ...
        Counter always increments (never reuses numbers).
        """
        n = self._tag_counters.get(tag, 0)
        self._tag_counters[tag] = n + 1
        return f"{tag}_{n}"

    def _is_auto_label(self, label: str, tag: str) -> bool:
        """Check if a label was auto-generated."""
        pattern = f"^{re.escape(tag)}_\\d+$"
        return bool(re.match(pattern, label))

    def child(
        self,
        tag: str,
        label: str | None = None,
        value: Any = None,
        attributes: dict[str, Any] | None = None,
        _position: str | None = None,
        **attr: Any
    ) -> TreeStoreBuilder | BuilderNode:
        """Create a child node with auto-generated label.

        Args:
            tag: The node's type (e.g., 'div', 'ul').
            label: Explicit label (optional, auto-generated if None).
            value: If provided, creates a leaf node; otherwise creates a branch.
            attributes: Dict of attributes (merged with **attr).
            _position: Position specifier:
                - None or '>': append to end (default)
                - '<': insert at beginning
                - '<label': insert before label
                - '>label': insert after label
                - '<#N': insert before position N
                - '>#N': insert after position N
                - '#N': insert at exact position N
            **attr: Node attributes as kwargs.

        Returns:
            TreeStoreBuilder if branch (for adding children), BuilderNode if leaf.

        Examples:
            >>> div = builder.child('div', color='red')  # branch, label='div_0'
            >>> builder.child('li', value='Hello')       # leaf, label='li_0'
            >>> builder.child('li', value='First', _position='<')  # insert at beginning
        """
        # Merge attributes
        final_attr: dict[str, Any] = {}
        if attributes:
            final_attr.update(attributes)
        final_attr.update(attr)

        # Generate label if not provided
        if label is None:
            label = self._generate_label(tag)

        # Note: validation is now explicit via validate() method

        if value is not None:
            # Create leaf node
            node = self.node_factory(label, final_attr, value, parent=self, tag=tag)
            self._insert_node(node, _position)
            return node
        else:
            # Create branch node with new Builder instance
            # Propagate grammar to child builder
            child_builder = self.__class__(grammar=self._grammar)
            node = self.node_factory(label, final_attr, value=child_builder, parent=self, tag=tag)
            child_builder.parent = node
            self._insert_node(node, _position)
            return child_builder

    def reindex(self) -> None:
        """Renumber auto-generated labels to remove gaps.

        Only affects labels matching pattern {tag}_{number}.
        Explicit labels are left unchanged.

        Example:
            Before: div_0, div_3, div_7, main
            After:  div_0, div_1, div_2, main
        """
        # Group nodes by tag
        by_tag: dict[str, list[tuple[str, TreeStoreNode]]] = {}
        for label, node in list(self._nodes.items()):
            if node.tag and self._is_auto_label(label, node.tag):
                by_tag.setdefault(node.tag, []).append((label, node))

        # Renumber each tag group
        for tag, tag_nodes in by_tag.items():
            # Sort by current number to preserve order
            tag_nodes.sort(key=lambda x: int(x[0].rsplit('_', 1)[1]))

            # Remove old labels
            for old_label, _ in tag_nodes:
                del self._nodes[old_label]

            # Add with new labels
            for i, (_, node) in enumerate(tag_nodes):
                new_label = f"{tag}_{i}"
                node.label = new_label
                self._nodes[new_label] = node

            # Reset counter
            self._tag_counters[tag] = len(tag_nodes)

        # Recursively reindex children
        for node in self._nodes.values():
            if node.is_branch and isinstance(node.value, TreeStoreBuilder):
                node.value.reindex()

    def by_tag(self, tag: str) -> list[TreeStoreNode]:
        """Get all nodes with the given tag."""
        return [n for n in self._nodes.values() if n.tag == tag]

    def validate(self) -> None:
        """Validate the tree against the grammar.

        Checks:
        - valid_children: each node's children are allowed
        - valid_parent: each node is under an allowed parent
        - cardinality: min/max counts for children

        Raises:
            InvalidChildError: If a child tag is not allowed.
            InvalidParentError: If a node is under an invalid parent.
            MissingChildError: If a mandatory child is missing.
            TooManyChildrenError: If too many children of a type exist.
            ValueError: If no grammar is defined.
        """
        if self._grammar is None:
            raise ValueError("Cannot validate: no grammar defined")

        self._validate_node(self, parent_tag=None)

    def _validate_node(
        self, store: TreeStore, parent_tag: str | None
    ) -> None:
        """Recursively validate a store and its children."""
        # Get valid_children for this parent and expand group names
        valid_children_raw: dict[str, tuple[int, int | None]] | None = None
        valid_children_expanded: dict[str, tuple[int, int | None]] | None = None
        if parent_tag is not None and self._grammar is not None:
            config = self._grammar.get_config(parent_tag)
            if config is not None:
                valid_children_raw = config.get('valid_children')
                if valid_children_raw is not None:
                    # Expand group names to actual tags
                    valid_children_expanded = {}
                    for key, cardinality in valid_children_raw.items():
                        expanded_tags = self._grammar.expand_name(key)
                        for tag in expanded_tags:
                            valid_children_expanded[tag] = cardinality

        # Count children by tag
        child_counts: dict[str, int] = {}

        for node in store._order:
            tag = node.tag
            if tag is None:
                continue

            # Check valid_parent constraint
            if self._grammar is not None:
                node_config = self._grammar.get_config(tag)
                if node_config is not None:
                    valid_parent = node_config.get('valid_parent')
                    if valid_parent is not None and parent_tag is not None:
                        if parent_tag not in valid_parent:
                            raise InvalidParentError(
                                f"Tag '{tag}' cannot be a child of '{parent_tag}'. "
                                f"Valid parents: {list(valid_parent)}"
                            )

            # Check valid_children constraint
            if valid_children_expanded is not None:
                if tag not in valid_children_expanded:
                    raise InvalidChildError(
                        f"Tag '{tag}' is not valid under '{parent_tag}'. "
                        f"Allowed: {list(valid_children_expanded.keys())}"
                    )

            # Count this tag
            child_counts[tag] = child_counts.get(tag, 0) + 1

            # Recursively validate children
            if node.is_branch and isinstance(node.value, TreeStore):
                self._validate_node(node.value, parent_tag=tag)

        # Check cardinality constraints
        if valid_children_expanded is not None:
            for tag, (min_count, max_count) in valid_children_expanded.items():
                count = child_counts.get(tag, 0)

                if count < min_count:
                    raise MissingChildError(
                        f"Tag '{parent_tag}' requires at least {min_count} "
                        f"'{tag}' children, found {count}"
                    )

                if max_count is not None and count > max_count:
                    raise TooManyChildrenError(
                        f"Tag '{parent_tag}' allows at most {max_count} "
                        f"'{tag}' children, found {count}"
                    )
