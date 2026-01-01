# RNC Builder

Dynamic TreeStore builder from RELAX NG Compact (RNC) schemas.

## Overview

RNC is a compact, human-readable syntax for RELAX NG schemas. This module
provides tools to parse RNC schemas and create TreeStore builders from them.

## Components

- **rnc_schema.py**: `RncBuilder` and `LazyRncBuilder` classes
- **rnc_parser.py**: RNC parser that produces TreeStore

## Usage

```python
from genro_treestore import TreeStore
from genro_treestore.builders.rnc import RncBuilder

# From file
builder = RncBuilder.from_rnc_file('schema.rnc')

# From string
builder = RncBuilder.from_rnc('''
    start = html
    html = element html { head, body }
    head = element head { title }
    title = element title { text }
    body = element body { div* }
    div = element div { text }
''')

# Use with TreeStore
store = TreeStore(builder=builder)
store.html().head().title(value='My Page')
```

## LazyRncBuilder

For large schemas split across multiple files (like HTML5), use `LazyRncBuilder`:

```python
builder = RncBuilder.from_resolver(html5_schema_resolver())
```

This loads schema files on demand as elements are accessed.
