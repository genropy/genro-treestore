# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Reactive validation for TreeStore with builder rules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .store import TreeStore
    from .store import TreeStoreNode
    from .builders.base import BuilderBase


class ValidationSubscriber:
    """Subscriber that handles reactive validation for TreeStore.

    When attached to a TreeStore with a builder, this subscriber listens
    to all change events (insert, delete, update) and reactively validates
    nodes, accumulating errors in node._invalid_reasons.

    The validation is incremental: only the affected node and its parent's
    children constraints are revalidated on each event.

    Error handling depends on store._raise_on_error:
    - Hard errors (invalid attributes, invalid child tag, too many children):
      Raise ValueError if raise_on_error=True, otherwise just collect.
    - Soft errors (missing required children / min not reached):
      Never raise - always just collect. User can add children later.

    Example:
        >>> store = TreeStore(builder=HtmlBuilder())
        >>> # ValidationSubscriber is auto-registered
        >>> thead = store.thead()
        >>> thead.parent._invalid_reasons
        ["requires at least 1 'tr', has 0"]
        >>> thead.tr()
        >>> thead.parent._invalid_reasons
        []  # Automatically cleared
    """

    __slots__ = ("store", "builder", "_raise_on_error")

    def __init__(self, store: TreeStore) -> None:
        """Initialize the validation subscriber.

        Args:
            store: The TreeStore to validate. Must have a builder set.
        """
        self.store = store
        self.builder: BuilderBase | None = store._builder
        self._raise_on_error: bool = getattr(store, "_raise_on_error", True)
        store.subscribe("_validator", any=self._on_change)

    def _on_change(
        self,
        node: TreeStoreNode,
        path: str,
        evt: str,
        **kw: Any,
    ) -> None:
        """Handle change events and trigger revalidation.

        Args:
            node: The affected node.
            path: Path from the subscribed store to the node.
            evt: Event type ('ins', 'del', 'upd_value', 'upd_attr').
            **kw: Additional event data (oldvalue, reason, index).
        """
        if evt == "del":
            # Node deleted → revalidate parent's children constraints
            # The node.parent is the TreeStore that contained the deleted node
            parent_store = node.parent
            if parent_store is not None:
                self._validate_children_constraints(parent_store)
        else:
            # ins, upd_value, upd_attr → revalidate the node
            self._validate_node(node)
            # And revalidate parent's children constraints
            if node.parent is not None:
                self._validate_children_constraints(node.parent)
            # For new branch nodes, also validate their own children constraints
            # (they start with 0 children, which may violate min constraints)
            if evt == "ins" and node.is_branch:
                self._validate_children_constraints(node.value)

    def _validate_node(self, node: TreeStoreNode) -> None:
        """Validate a node's attributes and populate _invalid_reasons.

        Hard errors (invalid attributes) raise if _raise_on_error is True.

        Args:
            node: The node to validate.
        """
        # Clear previous attribute errors (keep cardinality errors on parent)
        node._invalid_reasons = [
            e for e in node._invalid_reasons if e.startswith("requires ") or e.startswith("allows ")
        ]

        if self.builder is None:
            return

        tag = node.tag
        if tag is None:
            return

        # Validate attributes using builder's _validate_attrs
        # This is a HARD error - raise if raise_on_error is True
        attr_errors = self.builder._validate_attrs(
            tag, node.attr, raise_on_error=self._raise_on_error
        )
        node._invalid_reasons.extend(attr_errors)

    def _validate_children_constraints(self, store: TreeStore) -> None:
        """Validate children constraints and update parent node's _invalid_reasons.

        - Too many children (max exceeded): HARD error, raises if _raise_on_error
        - Missing children (min not reached): SOFT error, never raises

        Args:
            store: The TreeStore whose children constraints to validate.
        """
        parent_node = store.parent
        if parent_node is None:
            return

        if self.builder is None:
            return

        parent_tag = parent_node.tag
        if parent_tag is None:
            return

        valid_children, cardinality = self.builder._get_validation_rules(parent_tag)

        # Count children by tag
        child_counts: dict[str, int] = {}
        for node in store.nodes():
            child_tag = node.tag or node.label
            child_counts[child_tag] = child_counts.get(child_tag, 0) + 1

        # Check cardinality constraints
        cardinality_errors: list[str] = []
        hard_errors: list[str] = []

        for tag, (min_count, max_count) in cardinality.items():
            actual = child_counts.get(tag, 0)
            # SOFT error: missing children - never raise
            if min_count > 0 and actual < min_count:
                cardinality_errors.append(f"requires at least {min_count} '{tag}', has {actual}")
            # HARD error: too many children - raise if raise_on_error
            if max_count is not None and actual > max_count:
                error_msg = f"allows at most {max_count} '{tag}', has {actual}"
                cardinality_errors.append(error_msg)
                hard_errors.append(error_msg)

        # Update parent_node._invalid_reasons:
        # Remove old cardinality errors, add new ones
        parent_node._invalid_reasons = [
            e
            for e in parent_node._invalid_reasons
            if not e.startswith("requires ") and not e.startswith("allows ")
        ] + cardinality_errors

        # Raise for hard errors if raise_on_error is True
        if hard_errors and self._raise_on_error:
            raise ValueError(
                f"Cardinality constraint violated for '{parent_tag}': " + "; ".join(hard_errors)
            )
