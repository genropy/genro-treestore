# API Reference

Complete API documentation for genro-treestore.

```{toctree}
:maxdepth: 2

store
builders
resolvers
exceptions
```

## Package Overview

```{mermaid}
graph TB
    subgraph "genro_treestore"
        INIT[Public API<br/>__init__.py]

        subgraph "Core"
            STORE[store/<br/>TreeStore, TreeStoreNode]
            SER[serialization<br/>TYTX format]
            SUB[subscription<br/>Event system]
        end

        subgraph "Extensions"
            BUILD[builders/<br/>BuilderBase, HtmlBuilder]
            RES[resolvers/<br/>CallbackResolver]
            VAL[validation<br/>ValidationSubscriber]
        end

        subgraph "Schema"
            XSD[xsd/<br/>XsdBuilder]
        end

        INIT --> STORE
        INIT --> BUILD
        INIT --> RES
        BUILD --> XSD
    end
```

## Module Summary

| Module | Description |
|--------|-------------|
| `store` | Core TreeStore and TreeStoreNode classes |
| `builders` | BuilderBase and typed builders (HTML, XSD) |
| `resolvers` | Lazy value resolution (Callback, Directory, TxtDoc) |
| `exceptions` | Custom exception hierarchy |

## Quick Import

```python
from genro_treestore import (
    # Core classes
    TreeStore,
    TreeStoreNode,

    # Builders
    BuilderBase,
    HtmlBuilder,
    XsdBuilder,

    # Builder decorators
    element,
    valid_children,

    # Resolvers
    TreeStoreResolver,
    CallbackResolver,
    DirectoryResolver,
    TxtDocResolver,

    # Validation
    ValidationSubscriber,

    # Exceptions
    TreeStoreError,
    InvalidChildError,
    InvalidParentError,
    MissingChildError,
    TooManyChildrenError,
)
```

## Class Hierarchy

```{mermaid}
classDiagram
    class TreeStore {
        +parent: TreeStoreNode
        +builder: BuilderBase
        +set_item()
        +get_item()
        +subscribe()
    }

    class TreeStoreNode {
        +label: str
        +value: Any
        +attr: dict
        +resolver: TreeStoreResolver
    }

    class BuilderBase {
        <<abstract>>
        +child()
    }

    class TreeStoreResolver {
        <<abstract>>
        +load()
    }

    class TreeStoreError {
        <<exception>>
    }

    TreeStore *-- TreeStoreNode
    TreeStore --> BuilderBase
    TreeStoreNode --> TreeStoreResolver
    InvalidChildError --|> TreeStoreError
    MissingChildError --|> TreeStoreError
    TooManyChildrenError --|> TreeStoreError
```

## See Also

- [Quick Start](../guide/quickstart.md) - Getting started
- [Path Syntax](../guide/path-syntax.md) - Navigation
- [Builders](../guide/builders.md) - Typed APIs
