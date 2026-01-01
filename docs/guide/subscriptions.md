# Subscriptions

TreeStore provides a reactive subscription system for monitoring changes to the tree structure. Subscribers receive notifications when nodes are inserted, updated, or deleted.

## Event Propagation

```{mermaid}
graph BT
    subgraph "Event Propagation"
        LEAF[Leaf Node<br/>value changed]
        PARENT[Parent Store]
        ROOT[Root Store<br/>subscriber]

        LEAF -->|"upd_value"| PARENT
        PARENT -->|propagate| ROOT
    end

    ROOT -->|callback| CB[Handler Function]
```

Events bubble up from the changed node to the root, allowing subscribers at any level to receive notifications.

## Event Types

| Event | Description | Triggered By |
|-------|-------------|--------------|
| `ins` | Node inserted | `set_item()` on new path |
| `del` | Node deleted | `del_item()`, `pop()` |
| `upd_value` | Node value changed | `set_item()` on existing path |
| `upd_attr` | Node attribute changed | `set_attr()` |

## Basic Subscription

```python
from genro_treestore import TreeStore

store = TreeStore()

def on_change(node, path, evt, **kw):
    """Handle any tree change."""
    print(f"{evt}: {path} = {node.value}")

# Subscribe to all events
store.subscribe('logger', any=on_change)

store.set_item('users.alice', 'Alice')
# Output: ins: users.alice = Alice

store.set_item('users.alice', 'Alicia')
# Output: upd_value: users.alice = Alicia

store.del_item('users.alice')
# Output: del: users.alice = Alicia
```

## Subscription Flow

```{mermaid}
sequenceDiagram
    participant C as Client
    participant S as TreeStore
    participant N as Node
    participant SUB as Subscriber

    C->>S: set_item('path', value)
    S->>N: create/update node
    N->>S: trigger event
    S->>SUB: notify(node, path, evt)
    SUB-->>SUB: execute callback
    SUB-->>S: done
    S-->>C: return
```

## Selective Subscriptions

Subscribe to specific event types:

```python
def on_insert(node, path, evt, **kw):
    print(f"New node: {path}")

def on_delete(node, path, evt, **kw):
    print(f"Deleted: {path}")

def on_update(node, path, evt, **kw):
    print(f"Updated: {path} = {node.value}")

# Subscribe to specific events
store.subscribe('insert_logger', ins=on_insert)
store.subscribe('delete_logger', delete=on_delete)
store.subscribe('update_logger', upd_value=on_update)
```

## Callback Signature

```python
def callback(
    node: TreeStoreNode,  # The affected node
    path: str,            # Full path to the node
    evt: str,             # Event type: 'ins', 'del', 'upd_value', 'upd_attr'
    **kw                  # Additional keyword arguments
) -> None:
    pass
```

## Unsubscribing

```python
# Unsubscribe from all events
store.unsubscribe('logger', any=True)

# Unsubscribe from specific events
store.unsubscribe('insert_logger', ins=True)
store.unsubscribe('delete_logger', delete=True)
```

## Multiple Subscribers

```python
store = TreeStore()

# Audit logging
def audit_log(node, path, evt, **kw):
    with open('audit.log', 'a') as f:
        f.write(f"{evt}: {path}\n")

# Real-time sync
def sync_to_db(node, path, evt, **kw):
    if evt == 'ins':
        db.insert(path, node.value)
    elif evt == 'upd_value':
        db.update(path, node.value)
    elif evt == 'del':
        db.delete(path)

# UI updates
def update_ui(node, path, evt, **kw):
    ui.refresh(path)

store.subscribe('audit', any=audit_log)
store.subscribe('db_sync', any=sync_to_db)
store.subscribe('ui', any=update_ui)
```

## Subscription Architecture

```{mermaid}
graph TB
    subgraph "TreeStore"
        STORE[TreeStore]
        SUBS[Subscribers Dict]

        STORE -->|manages| SUBS
    end

    subgraph "Subscribers"
        S1[audit<br/>any=audit_log]
        S2[db_sync<br/>any=sync_to_db]
        S3[insert_only<br/>ins=on_insert]

        SUBS --> S1
        SUBS --> S2
        SUBS --> S3
    end

    subgraph "Events"
        INS[ins]
        DEL[del]
        UPD[upd_value]

        INS --> S1
        INS --> S2
        INS --> S3
        DEL --> S1
        DEL --> S2
        UPD --> S1
        UPD --> S2
    end
```

## Use Cases

### Change Tracking

```python
changes = []

def track_changes(node, path, evt, **kw):
    changes.append({
        'event': evt,
        'path': path,
        'value': node.value,
        'timestamp': datetime.now()
    })

store.subscribe('tracker', any=track_changes)
```

### Validation on Change

```python
def validate_on_change(node, path, evt, **kw):
    if evt in ('ins', 'upd_value'):
        if path.startswith('config.'):
            validate_config_value(path, node.value)

store.subscribe('validator', any=validate_on_change)
```

### Computed Properties

```python
def update_computed(node, path, evt, **kw):
    if path in ('data.price', 'data.quantity'):
        price = store.get_item('data.price', 0)
        quantity = store.get_item('data.quantity', 0)
        store.set_item('data.total', price * quantity)

store.subscribe('computed', any=update_computed)
```

## Best Practices

1. **Use descriptive subscriber names**: Makes debugging easier
2. **Keep callbacks fast**: Long-running operations should be queued
3. **Handle exceptions**: Callbacks should not raise exceptions
4. **Avoid infinite loops**: Be careful with callbacks that modify the store
5. **Unsubscribe when done**: Clean up subscribers to prevent memory leaks

## See Also

- {class}`~genro_treestore.SubscriberCallback` - Callback type definition
- [Validation](validation.md) - Using ValidationSubscriber for reactive validation
