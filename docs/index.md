# Genro-TreeStore Documentation

**A lightweight hierarchical data structure with builder pattern support for the Genro ecosystem (Genro Kyo).**

TreeStore provides a powerful tree-based container with O(1) path lookup, reactive subscriptions, lazy value resolution, and schema-driven builders.

```{toctree}
:maxdepth: 2
:caption: User Guide

guide/quickstart
guide/path-syntax
guide/builders
guide/resolvers
guide/subscriptions
guide/serialization
guide/validation
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/index
api/store
api/builders
api/resolvers
api/exceptions
```

## Architecture Overview

```{mermaid}
graph TB
    subgraph "TreeStore Core"
        TS[TreeStore<br/>Container]
        TSN[TreeStoreNode<br/>Node wrapper]
        TS -->|contains| TSN
        TSN -->|value is| TS2[TreeStore<br/>Branch]
        TSN -->|or| VAL[Leaf Value]
        TSN -->|parent ref| TS
        TS2 -->|parent ref| TSN
    end

    subgraph "Features"
        RES[Resolvers<br/>Lazy values]
        SUB[Subscriptions<br/>Reactive events]
        BLD[Builders<br/>Typed APIs]
        VAL2[Validation<br/>Structure rules]
    end

    TS --> RES
    TS --> SUB
    TS --> BLD
    BLD --> VAL2
```

## Key Features

| Feature | Description |
|---------|-------------|
| **O(1) Lookup** | Direct path-based access via internal index |
| **Builder Pattern** | Fluent APIs with auto-labeling and validation |
| **Reactive Subscriptions** | Event propagation for insert/update/delete |
| **Lazy Resolvers** | Dynamic value computation with TTL caching |
| **Schema Builders** | HtmlBuilder with W3C validation, XsdBuilder for XML Schema |
| **Type-Safe Serialization** | TYTX format preserves Decimal, date, datetime |

## Quick Example

```python
from genro_treestore import TreeStore
from genro_treestore.builders import HtmlBuilder

# Basic TreeStore usage
store = TreeStore()
store.set_item('config.database.host', 'localhost')
store.set_item('config.database.port', 5432)

print(store['config.database.host'])  # 'localhost'

# With HtmlBuilder
store = TreeStore(builder=HtmlBuilder())
body = store.body()
div = body.div(id='main')
div.h1(value='Welcome')
div.p(value='Hello, World!')

print(store['body_0.div_0.h1_0'])  # 'Welcome'
```

## Installation

```bash
pip install genro-treestore
```

## Module Structure

```{mermaid}
graph TB
    subgraph "genro_treestore"
        INIT[__init__.py<br/>Public API]

        subgraph "store/"
            CORE[core.py<br/>TreeStore]
            NODE[node.py<br/>TreeStoreNode]
            SUB[subscription.py<br/>Events]
            SER[serialization.py<br/>TYTX]
        end

        subgraph "builders/"
            BASE[base.py<br/>BuilderBase]
            HTML[html.py<br/>HtmlBuilder]
            XSD[xsd/<br/>XsdBuilder]
        end

        subgraph "resolvers/"
            RBASE[base.py<br/>TreeStoreResolver]
            DIR[directory.py<br/>DirectoryResolver]
        end

        EXC[exceptions.py]
        VAL[validation.py]
    end

    INIT --> CORE
    INIT --> BASE
    INIT --> RBASE
```

## License

Apache License 2.0 - See [LICENSE](https://github.com/genropy/genro-treestore/blob/main/LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
