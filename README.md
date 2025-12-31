# Genro-TreeStore

[![PyPI version](https://img.shields.io/pypi/v/genro-treestore?cacheSeconds=300)](https://pypi.org/project/genro-treestore/)
[![Tests](https://github.com/genropy/genro-treestore/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-treestore/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-treestore/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-treestore)
[![Documentation](https://readthedocs.org/projects/genro-treestore/badge/?version=latest)](https://genro-treestore.readthedocs.io/en/latest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A lightweight, zero-dependency hierarchical data structure for the Genro ecosystem (Genro Kyo).

## Installation

```bash
pip install genro-treestore
```

## Features

- **TreeStore**: Hierarchical data with `set_item`/`get_item`, path autocreate, fluent chaining
- **TreeStoreNode**: Nodes with label, attributes, and value
- **TreeStoreBuilder**: Builder pattern with auto-labeling and `@valid_children` validation
- **Path syntax**: Dotted paths, positional (`#N`), and attribute (`?attr`) access
- **Digest**: Extract data with `#k`, `#v`, `#a` syntax
- **Zero dependencies**: Pure Python, no external packages required

## Quick Start

### TreeStore API

```python
from genro_treestore import TreeStore

store = TreeStore()

# Create nested structure with autocreate
store.set_item('config.database.host', 'localhost')
store.set_item('config.database.port', 5432)

# Access values
store['config.database.host']  # 'localhost'
store.get_item('config.database.port')  # 5432

# Fluent chaining
store.set_item('html').set_item('body').set_item('div', id='main')
store['html.body.div?id']  # 'main'

# Attributes
store.set_attr('html.body.div', color='red', size=10)
store.get_attr('html.body.div', 'color')  # 'red'

# Digest
store.set_item('users.alice', 'Alice', role='admin')
store.set_item('users.bob', 'Bob', role='user')
users = store.get_node('users').value
users.digest('#k')  # ['alice', 'bob']
users.digest('#v')  # ['Alice', 'Bob']
users.digest('#a.role')  # ['admin', 'user']
users.digest('#k,#v')  # [('alice', 'Alice'), ('bob', 'Bob')]
```

### Builder Pattern (TreeStoreBuilder)

```python
from genro_treestore import TreeStoreBuilder, valid_children

class HtmlBuilder(TreeStoreBuilder):
    def div(self, **attr):
        return self.child('div', **attr)

    @valid_children('li')  # Only 'li' children allowed
    def ul(self, **attr):
        return self.child('ul', **attr)

    def li(self, value=None, **attr):
        return self.child('li', value=value, **attr)

builder = HtmlBuilder()
div = builder.div(id='container')
ul = div.ul()
ul.li('Item 1')
ul.li('Item 2')
ul.li('Item 3')

# Auto-generated labels: div_0, ul_0, li_0, li_1, li_2
builder['div_0.ul_0.li_0']  # 'Item 1'
builder['div_0?id']  # 'container'
```

## Path Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `'label'` | Access by label | `store['div']` |
| `'#N'` | Access by position | `store['#0']` (first), `store['#-1']` (last) |
| `'a.b.c'` | Dotted path | `store['html.body.div']` |
| `'path?attr'` | Get attribute | `store['div?color']` |
| `'path?attr' = val` | Set attribute | `store['div?color'] = 'red'` |

## Cardinality Constraints (Builder)

```python
@valid_children(
    title='1',      # exactly one required
    item='1:',      # one or more
    footer='0:1',   # zero or one (optional)
    tag='0:3',      # zero to three
    meta='2:5',     # two to five
)
def section(self, **attr):
    return self.child('section', **attr)
```

## API Comparison: TreeStore vs TreeStoreBuilder

| TreeStore | TreeStoreBuilder |
| --------- | ---------------- |
| `set_item(path, value, **attr)` | `child(tag, value=..., **attr)` |
| Explicit labels in path | Auto-generated labels (`tag_N`) |
| Fluent chaining (returns TreeStore) | Returns TreeStore/Node |
| No validation | `@valid_children` validation |

## Development

```bash
# Install dev dependencies
pip install -e ".[test,dev]"

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/genro_treestore --cov-report=term-missing
```

## Documentation

Full documentation is available at [genro-treestore.readthedocs.io](https://genro-treestore.readthedocs.io/).

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
