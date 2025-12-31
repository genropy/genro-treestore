# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore exceptions."""

from __future__ import annotations


class TreeStoreError(Exception):
    """Base exception for TreeStore errors."""

    pass


class InvalidChildError(TreeStoreError):
    """Raised when an invalid child tag is added to a node."""

    pass


class MissingChildError(TreeStoreError):
    """Raised when a required child tag is missing."""

    pass


class TooManyChildrenError(TreeStoreError):
    """Raised when a child tag exceeds its maximum allowed count."""

    pass


class InvalidParentError(TreeStoreError):
    """Raised when a node is placed under an invalid parent."""

    pass
