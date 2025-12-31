# Genro-TreeStore

A lightweight, zero-dependency hierarchical data structure inspired by Genro Bag.

```{toctree}
:maxdepth: 2
:caption: Contents

guide/quickstart
guide/path-syntax
guide/builders
guide/validation
api/index
```

## Overview

**genro-treestore** provides two complementary APIs:

1. **TreeStore**: Bag-like API with `setItem`/`getItem`, path autocreate, fluent chaining
2. **TreeStoreBuilder**: Builder pattern with auto-labeling and validation

### TreeStore (Bag-like API)

```python
from genro_treestore import TreeStore

store = TreeStore()

# Create nested structure with autocreate
store.setItem('config.database.host', 'localhost')
store.setItem('config.database.port', 5432)

# Access values
store['config.database.host']  # 'localhost'

# Fluent chaining
store.setItem('html').setItem('body').setItem('div', id='main')

# Attributes
store.setAttr('html.body.div', color='red')
store['html.body.div?color']  # 'red'

# Digest
store.digest('#k')  # labels
store.digest('#v')  # values
store.digest('#k,#v,#a.color')  # tuples
```

### TreeStoreBuilder (Builder Pattern)

```python
from genro_treestore import TreeStoreBuilder, valid_children

class HtmlBuilder(TreeStoreBuilder):
    @valid_children('li')
    def ul(self, **attr):
        return self.child('ul', **attr)

    def li(self, value=None, **attr):
        return self.child('li', value=value, **attr)

builder = HtmlBuilder()
ul = builder.ul()
ul.li('Item 1')
ul.li('Item 2')

# Auto-labels: ul_0, li_0, li_1
builder['ul_0.li_0']  # 'Item 1'
```

## Key Features

- **Zero dependencies**: Pure Python, no external packages
- **O(1) lookup**: Dict-based internal storage
- **Path autocreate**: `store.setItem('a.b.c', value)` creates all intermediate nodes
- **Fluent chaining**: Chain `setItem` calls for readable code
- **Digest**: Extract data with `#k`, `#v`, `#a` syntax (like Bag)
- **Builder validation**: `@valid_children` with cardinality constraints

## Installation

```bash
pip install genro-treestore
```

## License

Apache License 2.0 - See [LICENSE](https://github.com/genropy/genro-treestore/blob/main/LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
