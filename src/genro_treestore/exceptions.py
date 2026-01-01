# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore exceptions for validation and structural errors.

This module defines the exception hierarchy for TreeStore operations.
All exceptions inherit from TreeStoreError, allowing callers to catch
all TreeStore-related errors with a single except clause.

Exception Hierarchy::

    TreeStoreError (base)
    ├── InvalidChildError    - Child tag not allowed under parent
    ├── MissingChildError    - Required child tag is missing
    ├── TooManyChildrenError - Child count exceeds maximum
    └── InvalidParentError   - Node placed under wrong parent type

These exceptions are raised during builder validation when structural
rules defined by the builder are violated. Set ``raise_on_error=False``
on the TreeStore to collect errors without raising exceptions.

Example:
    Catching validation errors::

        from genro_treestore import TreeStore, InvalidChildError
        from genro_treestore.builders import HtmlBuilder

        store = TreeStore(builder=HtmlBuilder(), raise_on_error=True)
        body = store.body()
        try:
            body.li()  # li can only be child of ul/ol/menu
        except InvalidChildError as e:
            print(f"Invalid structure: {e}")
"""

from __future__ import annotations


class TreeStoreError(Exception):
    """Base exception for all TreeStore errors.

    This is the root exception class for the TreeStore library.
    All specific exceptions inherit from this class, allowing
    callers to catch any TreeStore error with::

        try:
            # TreeStore operations
        except TreeStoreError as e:
            # Handle any TreeStore error

    Attributes:
        args: Standard exception arguments containing the error message.
    """

    pass


class InvalidChildError(TreeStoreError):
    """Raised when a child tag is not allowed under the current parent.

    This exception is raised when attempting to add a child node with
    a tag that violates the builder's structural rules. Common causes:

    - Adding a child to a void/leaf element (e.g., children under <br>)
    - Tag not in the parent's valid_children list
    - Tag explicitly excluded from the parent

    Example:
        >>> store = TreeStore(builder=HtmlBuilder(), raise_on_error=True)
        >>> ul = store.body().ul()
        >>> ul.div()  # div is not a valid child of ul
        InvalidChildError: 'div' is not a valid child of 'ul'

    See Also:
        - :func:`~genro_treestore.builders.decorators.valid_children`
        - :class:`~genro_treestore.builders.base.BuilderBase`
    """

    pass


class MissingChildError(TreeStoreError):
    """Raised when a required child tag is missing from a parent.

    This exception is raised during validation when a parent node
    is missing one or more mandatory children as defined by the
    builder's cardinality rules (minimum count > 0).

    The error is typically raised when:

    - Calling ``store.builder.check()`` explicitly
    - Using ValidationSubscriber with hard error mode
    - Finalizing a structure that requires certain children

    Example:
        >>> # Assuming a builder requires 'head' and 'body' in 'html'
        >>> store = TreeStore(builder=HtmlBuilder())
        >>> html = store.html()
        >>> # Missing head and body children
        >>> store.builder.check(html)
        MissingChildError: 'html' requires child 'head' (min: 1, found: 0)

    See Also:
        - :meth:`~genro_treestore.builders.base.BuilderBase.check`
        - :class:`~genro_treestore.validation.ValidationSubscriber`
    """

    pass


class TooManyChildrenError(TreeStoreError):
    """Raised when a child tag exceeds its maximum allowed count.

    This exception is raised when adding a child would exceed the
    maximum cardinality defined by the builder's rules. For example,
    an HTML document can only have one <head> element.

    Cardinality is specified using slice notation in builder definitions:

    - ``tag`` or ``tag[:]`` - unlimited (0 to infinity)
    - ``tag[1]`` - exactly one required
    - ``tag[0:1]`` - zero or one (optional, max 1)
    - ``tag[1:3]`` - between 1 and 3 inclusive

    Example:
        >>> # Assuming 'head' has max cardinality of 1
        >>> store = TreeStore(builder=HtmlBuilder(), raise_on_error=True)
        >>> html = store.html()
        >>> html.head()  # First head - OK
        >>> html.head()  # Second head - Error
        TooManyChildrenError: 'html' already has maximum 'head' children (1)

    See Also:
        - :func:`~genro_treestore.builders.decorators.element`
        - :meth:`~genro_treestore.builders.base.BuilderBase._parse_children_spec`
    """

    pass


class InvalidParentError(TreeStoreError):
    """Raised when a node is placed under an invalid parent type.

    This exception is raised when a tag requires a specific parent
    type but is being added to a different parent. This is the
    inverse of InvalidChildError - it validates from the child's
    perspective rather than the parent's.

    Common use cases:

    - <li> elements must be children of <ul>, <ol>, or <menu>
    - <td>/<th> elements must be children of <tr>
    - <option> elements must be children of <select> or <datalist>

    Example:
        >>> store = TreeStore(builder=HtmlBuilder(), raise_on_error=True)
        >>> div = store.body().div()
        >>> div.td()  # td must be child of tr
        InvalidParentError: 'td' cannot be child of 'div', requires 'tr'

    See Also:
        - :class:`InvalidChildError`
        - :func:`~genro_treestore.builders.decorators.element`
    """

    pass
