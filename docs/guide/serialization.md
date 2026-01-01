# Serialization

TreeStore supports multiple serialization formats for persisting and transferring tree data.

## Serialization Formats

```{mermaid}
graph LR
    subgraph "TreeStore"
        TS[TreeStore<br/>In-Memory]
    end

    subgraph "Formats"
        TYTX[TYTX<br/>Type-preserving]
        XML[XML<br/>Standard markup]
        DICT[Dict<br/>Python native]
    end

    TS -->|to_tytx()| TYTX
    TS -->|to_xml()| XML
    TS -->|as_dict()| DICT

    TYTX -->|from_tytx()| TS
    XML -->|from_xml()| TS
    DICT -->|TreeStore(source=dict)| TS
```

## TYTX Format

TYTX (TYped Tree eXchange) is TreeStore's native serialization format that preserves Python types.

### Supported Types

| Type | Preserved | Example |
|------|-----------|---------|
| `str` | ✓ | `"hello"` |
| `int` | ✓ | `42` |
| `float` | ✓ | `3.14` |
| `bool` | ✓ | `True` |
| `None` | ✓ | `None` |
| `Decimal` | ✓ | `Decimal('1234.56')` |
| `date` | ✓ | `date(2025, 1, 15)` |
| `datetime` | ✓ | `datetime.now()` |
| `list` | ✓ | `[1, 2, 3]` |
| `dict` | ✓ | `{'key': 'value'}` |

### Basic Usage

```python
from decimal import Decimal
from datetime import date, datetime
from genro_treestore import TreeStore

store = TreeStore()
store.set_item('invoice.amount', Decimal('1234.56'))
store.set_item('invoice.date', date(2025, 1, 15))
store.set_item('invoice.timestamp', datetime.now())
store.set_item('invoice.paid', False)

# Serialize to JSON (types preserved as metadata)
json_data = store.to_tytx()

# Deserialize - types restored exactly
restored = TreeStore.from_tytx(json_data)
assert isinstance(restored['invoice.amount'], Decimal)
assert isinstance(restored['invoice.date'], date)
assert isinstance(restored['invoice.timestamp'], datetime)
assert restored['invoice.paid'] is False
```

### Transport Formats

```{mermaid}
graph TB
    subgraph "TYTX Transports"
        JSON[JSON<br/>Human-readable]
        MSGPACK[MessagePack<br/>Binary, compact]
    end

    JSON -->|"transport='json'"| DEFAULT[Default]
    MSGPACK -->|"transport='msgpack'"| COMPACT[Compact]
```

```python
# JSON transport (default) - human-readable
json_data = store.to_tytx()  # or to_tytx(transport='json')

# MessagePack transport - more compact, binary
binary_data = store.to_tytx(transport='msgpack')

# Restore from either format
from_json = TreeStore.from_tytx(json_data)
from_msgpack = TreeStore.from_tytx(binary_data, transport='msgpack')
```

### TYTX Structure

The TYTX format uses a flat row-based structure for efficient serialization:

```json
{
  "rows": [
    ["", "invoice", null, null, {}],
    ["invoice", "amount", null, {"_t": "D", "v": "1234.56"}, {}],
    ["invoice", "date", null, {"_t": "d", "v": "2025-01-15"}, {}]
  ]
}
```

Each row is a tuple: `[parent_path, label, tag, value, attributes]`

- `parent_path`: Path to parent node (empty string for root children)
- `label`: Node's unique key within its parent
- `tag`: Node type from builder (null if no builder)
- `value`: Node value with type metadata, or null for branches
- `attributes`: Dict of node attributes

## XML Serialization

TreeStore can import and export XML documents.

### Parsing XML

```python
from genro_treestore import TreeStore

xml = '''<html>
    <head><title>Hello</title></head>
    <body><div id="main">Content</div></body>
</html>'''

store = TreeStore.from_xml(xml)

# Access by auto-generated labels
print(store['html_0.body_0.div_0'])      # 'Content'
print(store['html_0.body_0.div_0?id'])   # 'main'
```

### Generating XML

```python
from genro_treestore import TreeStore
from genro_treestore.builders import HtmlBuilder

store = TreeStore(builder=HtmlBuilder())
body = store.body()
div = body.div(id='container')
div.h1(value='Welcome')
div.p(value='Hello, World!')

# Generate XML
xml_output = store.to_xml()
```

### Namespace Handling

```python
# XML with namespaces
xml_with_ns = '''<root xmlns:custom="http://example.com">
    <custom:item>Value</custom:item>
</root>'''

store = TreeStore.from_xml(xml_with_ns)
# Namespace prefixes are preserved in tag names
```

## Dictionary Serialization

Convert to/from Python dictionaries:

```python
store = TreeStore()
store.set_item('config.host', 'localhost')
store.set_item('config.port', 5432)

# To dictionary
data = store.as_dict()
# {'config': {'host': 'localhost', 'port': 5432}}

# From dictionary (pass to constructor)
restored = TreeStore(source=data)
```

## Serialization Comparison

| Format | Type Safety | Size | Human Readable | Use Case |
|--------|-------------|------|----------------|----------|
| TYTX (JSON) | ✓ Full | Medium | ✓ Yes | Config files, APIs |
| TYTX (MsgPack) | ✓ Full | Small | ✗ No | Network, storage |
| XML | Partial | Large | ✓ Yes | Interop, documents |
| Dict | ✗ Basic | N/A | N/A | Python-to-Python |

## Best Practices

1. **Use TYTX for persistence**: Preserves all Python types exactly
2. **Use MessagePack for network**: More efficient than JSON
3. **Use XML for interoperability**: Standard format, widely supported
4. **Use Dict for Python interop**: Quick conversion within Python code

## See Also

- {meth}`~genro_treestore.TreeStore.to_tytx` - TYTX serialization
- {meth}`~genro_treestore.TreeStore.from_tytx` - TYTX deserialization
- {meth}`~genro_treestore.TreeStore.to_xml` - XML export
- {meth}`~genro_treestore.TreeStore.from_xml` - XML import
