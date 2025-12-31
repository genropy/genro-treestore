# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Decorators for builder methods validation rules."""

from __future__ import annotations

import re
from functools import wraps
from typing import Callable, Any


# Pattern for tag with optional cardinality: tag, tag[n], tag[n:], tag[:m], tag[n:m]
_TAG_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\[(\d*):?(\d*)\])?$')


def _parse_tag_spec(spec: str) -> tuple[str, int, int | None]:
    """Parse a tag specification with optional cardinality.

    Args:
        spec: Tag spec like 'foo', 'foo[1]', 'foo[1:]', 'foo[:2]', 'foo[1:3]'

    Returns:
        Tuple of (tag_name, min_count, max_count)

    Raises:
        ValueError: If spec format is invalid.

    Examples:
        >>> _parse_tag_spec('foo')
        ('foo', 0, None)
        >>> _parse_tag_spec('foo[1]')
        ('foo', 1, 1)
        >>> _parse_tag_spec('foo[2:]')
        ('foo', 2, None)
        >>> _parse_tag_spec('foo[:3]')
        ('foo', 0, 3)
        >>> _parse_tag_spec('foo[1:3]')
        ('foo', 1, 3)
    """
    match = _TAG_PATTERN.match(spec.strip())
    if not match:
        raise ValueError(f"Invalid tag specification: '{spec}'")

    tag = match.group(1)
    min_str = match.group(2)
    max_str = match.group(3)

    # No brackets: unlimited (0..∞)
    if min_str is None and max_str is None:
        return tag, 0, None

    # Check if there was a colon in the original spec
    has_colon = ':' in spec

    if not has_colon:
        # tag[n] - exactly n
        n = int(min_str) if min_str else 0
        return tag, n, n

    # Has colon: slice syntax
    min_count = int(min_str) if min_str else 0
    max_count = int(max_str) if max_str else None

    return tag, min_count, max_count


def element(children: tuple[str, ...] = ()) -> Callable:
    """Decorator to specify valid children tags for a builder method.

    The decorated method's name is used as the parent tag.
    The validation rules are stored on the method for later use by validate().

    Args:
        children: Tuple of valid child tag specs. Each can be:
            - 'tag' - allowed, no cardinality constraint (0..∞)
            - 'tag[n]' - exactly n required
            - 'tag[n:]' - at least n required
            - 'tag[:m]' - at most m allowed
            - 'tag[n:m]' - between n and m (inclusive)
            Empty tuple means no children allowed (leaf node).

    Example:
        >>> class MyBuilder(BuilderBase):
        ...     @element(children=('section', 'item[1:]'))  # item required
        ...     def menu(self, target, **attr):
        ...         return self.child(target, 'menu', **attr)
        ...
        ...     @element(children=('fridge[:1]', 'oven[:2]', 'sink', 'table', 'chair'))
        ...     def kitchen(self, target, **attr):
        ...         return self.child(target, 'kitchen', **attr)
        ...
        ...     @element()  # No children allowed (leaf)
        ...     def item(self, target, **attr):
        ...         return self.child(target, 'item', value='', **attr)
    """
    # Parse all tag specs
    parsed: dict[str, tuple[int, int | None]] = {}
    for spec in children:
        tag, min_c, max_c = _parse_tag_spec(spec)
        parsed[tag] = (min_c, max_c)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Store validation rules on the function
        # _valid_children: set of allowed tag names
        # _child_cardinality: dict mapping tag -> (min, max)
        wrapper._valid_children = frozenset(parsed.keys())
        wrapper._child_cardinality = parsed

        return wrapper

    return decorator


# Alias for backwards compatibility
valid_children = element
