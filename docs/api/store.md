# Store Module

The `store` package contains the core TreeStore implementation.

## Module Structure

```{mermaid}
graph TB
    subgraph "genro_treestore.store"
        CORE[core.py<br/>TreeStore class]
        NODE[node.py<br/>TreeStoreNode class]
        SUB[subscription.py<br/>Event system]
        SER[serialization.py<br/>TYTX format]

        CORE --> NODE
        CORE --> SUB
        CORE --> SER
    end
```

## TreeStore

```{eval-rst}
.. autoclass:: genro_treestore.TreeStore
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __getitem__, __setitem__, __delitem__, __iter__, __len__, __contains__
```

## TreeStoreNode

```{eval-rst}
.. autoclass:: genro_treestore.TreeStoreNode
   :members:
   :undoc-members:
   :show-inheritance:
```

## Class Relationships

```{mermaid}
classDiagram
    class TreeStore {
        +parent: TreeStoreNode | None
        +builder: BuilderBase | None
        +set_item(path, value, **attr)
        +get_item(path, default)
        +del_item(path)
        +get_node(path)
        +subscribe(name, **callbacks)
        +unsubscribe(name, **events)
    }

    class TreeStoreNode {
        +label: str
        +value: Any
        +attr: dict
        +parent: TreeStore
        +resolver: TreeStoreResolver | None
    }

    TreeStore "1" *-- "*" TreeStoreNode : contains
    TreeStoreNode "1" --> "0..1" TreeStore : value can be
    TreeStoreNode --> TreeStore : parent
    TreeStore --> TreeStoreNode : parent
```

## Path Resolution

```{mermaid}
flowchart LR
    subgraph "Path Types"
        DOT[a.b.c<br/>Dotted path]
        POS[#0, #-1<br/>Positional]
        ATTR[path?attr<br/>Attribute]
    end

    subgraph "Resolution"
        DOT --> SPLIT[Split by dot]
        POS --> INDEX[Array index]
        ATTR --> GETATTR[Get attribute]
    end
```

## Subscription System

```{eval-rst}
.. automodule:: genro_treestore.store.subscription
   :members:
   :undoc-members:
```

### Event Types

| Event | Constant | Description |
|-------|----------|-------------|
| Insert | `'ins'` | Node created |
| Delete | `'del'` | Node removed |
| Update Value | `'upd_value'` | Value changed |
| Update Attribute | `'upd_attr'` | Attribute changed |

## Serialization

```{eval-rst}
.. automodule:: genro_treestore.store.serialization
   :members:
   :undoc-members:
```

## See Also

- [Quick Start](../guide/quickstart.md) - Getting started guide
- [Path Syntax](../guide/path-syntax.md) - Path navigation details
- [Subscriptions](../guide/subscriptions.md) - Event subscription guide
