# API Reference

Complete API documentation for genro-treestore.

```{toctree}
:maxdepth: 2

treestore
```

## Module Overview

The `genro_treestore` module provides:

- {class}`~genro_treestore.TreeStore` - The main container class
- {class}`~genro_treestore.TreeStoreNode` - Individual node class
- {class}`~genro_treestore.TreeStoreBuilder` - Base class for typed builders
- {func}`~genro_treestore.valid_children` - Decorator for child validation
- {class}`~genro_treestore.InvalidChildError` - Exception for invalid child tags
- {class}`~genro_treestore.MissingChildError` - Exception for missing mandatory children
- {class}`~genro_treestore.TooManyChildrenError` - Exception for cardinality violations

## Quick Import

```python
from genro_treestore import (
    TreeStore,
    TreeStoreNode,
    TreeStoreBuilder,
    valid_children,
    InvalidChildError,
    MissingChildError,
    TooManyChildrenError,
)
```
