# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Grammar system for TreeStoreBuilder validation."""

from __future__ import annotations

from typing import Any, Callable


def valid_children(*allowed: str, **constraints: str) -> Callable:
    """Decorator to specify valid children for a builder method.

    Can be used in two ways:

    1. Simple list of allowed tags:
        @valid_children('div', 'span', 'p')

    2. With cardinality constraints:
        @valid_children(div='0:', span='1:3', title='1')

    Cardinality format: 'min:max'
        - '0:' = zero or more (optional, unlimited)
        - '1:' = one or more (mandatory, unlimited)
        - '1' or '1:1' = exactly one (mandatory)
        - '0:3' = zero to three

    Args:
        *allowed: Tag names that are valid children (implies '0:').
        **constraints: Tag names with cardinality constraints.

    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        parsed: dict[str, tuple[int, int | None]] = {}

        for tag in allowed:
            parsed[tag] = (0, None)

        for tag, constraint in constraints.items():
            parsed[tag] = _parse_cardinality(constraint)

        func._valid_children = parsed  # type: ignore
        return func

    return decorator


def _parse_cardinality(spec: str | int | bool) -> tuple[int, int | None]:
    """Parse a cardinality specification."""
    if spec is True:
        return (0, None)
    if isinstance(spec, int):
        return (spec, spec)
    if not isinstance(spec, str):
        raise ValueError(f"Invalid cardinality spec: {spec}")

    if ':' not in spec:
        n = int(spec)
        return (n, n)

    parts = spec.split(':')
    min_val = int(parts[0]) if parts[0] else 0
    max_val = int(parts[1]) if parts[1] else None
    return (min_val, max_val)


def element(
    tag: str | None = None,
    valid_children: dict[str, str] | str | None = None,
    valid_parent: str | None = None,
) -> Callable:
    """Decorator for grammar element methods with custom logic.

    Used to define elements in a Grammar class that have custom behavior
    (components). The method receives the builder node as first argument.

    Args:
        tag: Tag name(s), comma-separated for aliases. If None, uses method name.
        valid_children: Dict of {tag: cardinality} or comma-separated tag string.
        valid_parent: Comma-separated string of valid parent tags.

    Cardinality format:
        - '*' = zero or more (0:)
        - '+' = one or more (1:)
        - '?' = zero or one (0:1)
        - '1' = exactly one (1:1)
        - '1-3' or '1:3' = range

    Example:
        class HtmlGrammar(Grammar):
            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._element_config = {
            'tag': tag,
            'valid_children': valid_children,
            'valid_parent': valid_parent,
            'method': func,
        }
        return func

    return decorator


def _parse_cardinality_symbol(spec: str) -> tuple[int, int | None]:
    """Parse a cardinality specification with symbolic notation.

    Supports:
        - '*' = zero or more (0, None)
        - '+' = one or more (1, None)
        - '?' = zero or one (0, 1)
        - '1' = exactly one (1, 1)
        - '1-3' or '1:3' = range (1, 3)
        - '0:' = zero or more (0, None)
        - '1:' = one or more (1, None)
    """
    if spec == '*':
        return (0, None)
    if spec == '+':
        return (1, None)
    if spec == '?':
        return (0, 1)

    # Try range with dash
    if '-' in spec and ':' not in spec:
        parts = spec.split('-')
        return (int(parts[0]), int(parts[1]))

    # Fall back to original format with colon
    return _parse_cardinality(spec)


class Grammar:
    """Base class for defining builder grammars.

    Grammars define valid elements and their relationships using:
    - Properties that return dicts for groups of similar elements
    - @element decorated methods for elements with custom logic

    Groups can reference other groups via self.other_group.

    Example:
        class HtmlGrammar(Grammar):
            @property
            def flow(self):
                return dict(
                    tag='div,span,p',
                    valid_children={self.inline: '*'},
                )

            @property
            def inline(self):
                return dict(
                    tag='span,a,em,strong',
                )

            @element(tag='ul,ol', valid_children={'li': '+'})
            def ul(self, node, items=None, **attr):
                if items:
                    for item in items:
                        node.li(value=item)
                return node
    """

    def __init__(self) -> None:
        self._resolved: dict[str, dict[str, Any]] = {}
        self._tag_to_config: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, dict[str, Any]] = {}
        self._resolve_all()

    def _resolve_all(self) -> None:
        """Resolve all grammar definitions from properties and decorated methods."""
        # First pass: collect all definitions
        for name in dir(self):
            if name.startswith('_'):
                continue

            attr = getattr(self.__class__, name, None)

            # Check for @element decorated methods
            if callable(attr) and hasattr(attr, '_element_config'):
                config = attr._element_config.copy()
                tags = config.get('tag') or name
                config['_method_name'] = name
                self._store_config(tags, config)
                continue

            # Check for properties returning dicts
            if isinstance(attr, property):
                try:
                    value = getattr(self, name)
                    if isinstance(value, dict) and 'tag' in value:
                        config = value.copy()
                        config['_group_name'] = name
                        # Store group for later expansion
                        self._groups[name] = config
                        self._store_config(config['tag'], config)
                except Exception:
                    pass

    def _store_config(self, tags: str, config: dict[str, Any]) -> None:
        """Store configuration for one or more tags."""
        tag_list = [t.strip() for t in tags.split(',')]

        # Resolve valid_children references to other groups
        valid_children = config.get('valid_children')
        if valid_children:
            config['valid_children'] = self._resolve_children(valid_children)

        # Resolve valid_parent references
        valid_parent = config.get('valid_parent')
        if valid_parent:
            config['valid_parent'] = self._resolve_parent(valid_parent)

        # Store for each tag
        for tag in tag_list:
            self._tag_to_config[tag] = config

    def _resolve_children(
        self, valid_children: dict | str
    ) -> dict[str, tuple[int, int | None]]:
        """Store valid_children as {key: (min, max)}.

        Keys are stored as-is (can be tags or group names).
        Expansion to actual tags happens at validate() time.
        """
        result: dict[str, tuple[int, int | None]] = {}

        if isinstance(valid_children, str):
            # Simple comma-separated list, implies '*'
            for name in valid_children.split(','):
                result[name.strip()] = (0, None)
            return result

        for key, cardinality in valid_children.items():
            parsed = _parse_cardinality_symbol(cardinality)
            result[key] = parsed

        return result

    def _resolve_parent(self, valid_parent: str | dict) -> set[str]:
        """Resolve valid_parent to a set of tag names."""
        if isinstance(valid_parent, dict) and 'tag' in valid_parent:
            return set(t.strip() for t in valid_parent['tag'].split(','))
        if isinstance(valid_parent, str):
            return set(t.strip() for t in valid_parent.split(','))
        return set()

    def get_config(self, tag: str) -> dict[str, Any] | None:
        """Get configuration for a tag."""
        return self._tag_to_config.get(tag)

    def get_method(self, tag: str) -> Callable | None:
        """Get the custom method for a tag, if any."""
        config = self._tag_to_config.get(tag)
        if config and 'method' in config:
            return config['method']
        return None

    def get_all_tags(self) -> list[str]:
        """Get all defined tags."""
        return list(self._tag_to_config.keys())

    def expand_name(self, name: str) -> list[str]:
        """Expand a name (tag or group) to a list of tags.

        Args:
            name: A tag name, group name, or comma-separated list of both.

        Returns:
            List of tag names. If name is a tag, returns [name].
            If name is a group, returns all tags in the group.
            Comma-separated names are expanded individually.
        """
        result: list[str] = []
        for part in name.split(','):
            part = part.strip()
            # Check if it's a known tag
            if part in self._tag_to_config:
                result.append(part)
            else:
                # Try as a group name (property that returns dict with 'tag')
                group_config = self._groups.get(part)
                if group_config and 'tag' in group_config:
                    for tag in group_config['tag'].split(','):
                        result.append(tag.strip())
                else:
                    # Unknown name, treat as literal tag
                    result.append(part)
        return result
