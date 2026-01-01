# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Decorators for builder methods validation rules."""

from __future__ import annotations

import inspect
import re
from functools import wraps
from typing import Callable, Any, TYPE_CHECKING

# Try to import Pydantic (optional dependency)
try:
    from pydantic import BaseModel, ValidationError, create_model
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None  # type: ignore
    ValidationError = None  # type: ignore
    create_model = None  # type: ignore

if TYPE_CHECKING:
    from pydantic import BaseModel as BaseModelType

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


def _create_model_from_signature(func: Callable, model_name: str) -> type | None:
    """Create a Pydantic model from function signature.

    Extracts typed parameters (excluding self, target, tag, **kwargs)
    and creates a dynamic Pydantic model for validation.

    Returns None if no typed parameters found or Pydantic not available.
    """
    if not PYDANTIC_AVAILABLE:
        return None

    sig = inspect.signature(func)
    fields: dict[str, Any] = {}

    # Skip these parameters - they're not user attributes
    skip_params = {'self', 'target', 'tag'}

    for name, param in sig.parameters.items():
        if name in skip_params:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            # **kwargs - skip
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            # *args - skip
            continue

        # Get annotation and default
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            # No type annotation, skip
            continue

        if param.default is inspect.Parameter.empty:
            # Required field
            fields[name] = (annotation, ...)
        else:
            # Optional field with default
            fields[name] = (annotation, param.default)

    if not fields:
        return None

    return create_model(model_name, **fields)


def _parse_tags_with_models(
    tags: str | tuple
) -> tuple[list[str], dict[str, type]]:
    """Parse tags parameter, extracting any per-tag models.

    Args:
        tags: Can be:
            - str: 'fridge, oven, sink'
            - tuple[str, ...]: ('fridge', 'oven', 'sink')
            - tuple[tuple[str, type], ...]: (('fridge', FridgeModel), ('oven', OvenModel))

    Returns:
        Tuple of (tag_list, tag_models_dict)
    """
    tag_list: list[str] = []
    tag_models: dict[str, type] = {}

    if isinstance(tags, str):
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    elif isinstance(tags, tuple) and tags:
        # Check if it's tuple of tuples (tag, model) or tuple of strings
        first = tags[0]
        if isinstance(first, tuple):
            # Tuple of (tag, model) pairs
            for item in tags:
                tag_name, model = item
                tag_list.append(tag_name)
                tag_models[tag_name] = model
        else:
            # Tuple of strings
            tag_list = list(tags)

    return tag_list, tag_models


def element(
    tags: str | tuple[str, ...] | tuple[tuple[str, type], ...] = '',
    children: str | tuple[str, ...] = '',
    model: bool | type = False
) -> Callable:
    """Decorator to define element tags and validation rules for a builder method.

    The decorator registers the method as handler for the specified tags.
    If no tags are specified, the method name is used as the tag.

    Args:
        tags: Tag names this method handles. Can be:
            - A comma-separated string: 'fridge, oven, sink'
            - A tuple of strings: ('fridge', 'oven', 'sink')
            - A tuple of (tag, Model) pairs for per-tag attribute validation:
              (('fridge', FridgeModel), ('oven', OvenModel))
            If empty, the method name is used as the single tag.

        children: Valid child tag specs for structure validation. Can be:
            - A comma-separated string: 'tag1, tag2[:1], tag3[1:]'
            - A tuple of strings: ('tag1', 'tag2[:1]', 'tag3[1:]')

            Each spec can be:
            - 'tag' - allowed, no cardinality constraint (0..∞)
            - 'tag[n]' - exactly n required
            - 'tag[n:]' - at least n required
            - 'tag[:m]' - at most m allowed
            - 'tag[n:m]' - between n and m (inclusive)
            Empty string or empty tuple means no children allowed (leaf node).

        model: Pydantic model for attribute validation (requires pydantic installed):
            - False: no validation (default)
            - True: auto-create model from function signature
            - BaseModel subclass: use that model for all tags
            Per-tag models can also be specified via tags parameter.

    Example:
        >>> class MyBuilder(BuilderBase):
        ...     # Multiple tags pointing to same method
        ...     @element(tags='fridge, oven, sink')
        ...     def appliance(self, target, tag, **attr):
        ...         return self.child(target, tag, value='', **attr)
        ...
        ...     # Structure validation with children
        ...     @element(children='section, item[1:]')
        ...     def menu(self, target, tag, **attr):
        ...         return self.child(target, tag, **attr)
        ...
        ...     @element()  # No children allowed (leaf)
        ...     def item(self, target, tag, **attr):
        ...         return self.child(target, tag, value='', **attr)
        ...
        ...     # Attribute validation from signature
        ...     @element(model=True)
        ...     def floor(self, target, tag, number: int = 0, **attr):
        ...         return self.child(target, tag, number=number, **attr)
        ...
        ...     # Explicit Pydantic model for attributes
        ...     @element(model=ApartmentModel)
        ...     def apartment(self, target, tag, **attr):
        ...         return self.child(target, tag, **attr)
        ...
        ...     # Per-tag attribute models
        ...     @element(tags=(('fridge', FridgeModel), ('oven', OvenModel)))
        ...     def appliance(self, target, tag, **attr):
        ...         return self.child(target, tag, value='', **attr)
    """
    # Parse tags - handle string, tuple of strings, or tuple of (tag, model) pairs
    tag_list, tag_models = _parse_tags_with_models(tags)

    # Check if children spec contains =references (need runtime resolution)
    children_str = children if isinstance(children, str) else ','.join(children)
    has_refs = '=' in children_str

    # Parse children specs - accept both string and tuple
    # Skip parsing if there are references (will be resolved at runtime)
    parsed_children: dict[str, tuple[int, int | None]] = {}

    if not has_refs:
        if isinstance(children, str):
            specs = [s.strip() for s in children.split(',') if s.strip()]
        else:
            specs = list(children)

        for spec in specs:
            tag, min_c, max_c = _parse_tag_spec(spec)
            parsed_children[tag] = (min_c, max_c)

    def decorator(func: Callable) -> Callable:
        # Determine validation model(s)
        # Priority: per-tag models > explicit model > signature-based model
        signature_model: type | None = None
        explicit_model: type | None = None

        if model is True and PYDANTIC_AVAILABLE:
            # Create model from function signature
            signature_model = _create_model_from_signature(func, f'{func.__name__}_Model')
        elif model is not False and PYDANTIC_AVAILABLE:
            # model is a BaseModel subclass
            if isinstance(model, type) and issubclass(model, BaseModel):
                explicit_model = model

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Perform validation if Pydantic is available and validation is enabled
            if PYDANTIC_AVAILABLE and (tag_models or explicit_model or signature_model):
                # Get the tag from kwargs (injected by TreeStore dispatch)
                current_tag = kwargs.get('tag')

                # Determine which model to use
                model_to_use: type | None = None
                if current_tag and current_tag in tag_models:
                    # Per-tag model has highest priority
                    model_to_use = tag_models[current_tag]
                elif explicit_model:
                    model_to_use = explicit_model
                elif signature_model:
                    model_to_use = signature_model

                if model_to_use:
                    # Extract only the kwargs that the model knows about
                    model_fields = set(model_to_use.model_fields.keys())
                    attrs_to_validate = {
                        k: v for k, v in kwargs.items()
                        if k in model_fields
                    }
                    # Validate - will raise ValidationError if invalid
                    model_to_use(**attrs_to_validate)

            return func(*args, **kwargs)

        # Store validation rules on the function
        # _valid_children: set of allowed tag names
        # _child_cardinality: dict mapping tag -> (min, max)
        if has_refs:
            # Contains =references - store raw spec for runtime resolution
            wrapper._raw_children_spec = children
            wrapper._valid_children = frozenset()  # Will be resolved at runtime
            wrapper._child_cardinality = {}
        else:
            wrapper._valid_children = frozenset(parsed_children.keys())
            wrapper._child_cardinality = parsed_children

        # Store tags this method handles
        # If no tags specified, will use method name (set in __init_subclass__)
        wrapper._element_tags = tuple(tag_list) if tag_list else None

        # Store validation info for introspection
        wrapper._validation_model = explicit_model or signature_model
        wrapper._tag_models = tag_models if tag_models else None

        return wrapper

    return decorator


# Alias for backwards compatibility
valid_children = element
