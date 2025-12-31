# Genro-TreeStore

[![PyPI version](https://img.shields.io/pypi/v/genro-treestore?cacheSeconds=300)](https://pypi.org/project/genro-treestore/)
[![Tests](https://github.com/genropy/genro-treestore/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-treestore/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-treestore/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-treestore)
[![Documentation](https://readthedocs.org/projects/genro-treestore/badge/?version=latest)](https://genro-treestore.readthedocs.io/en/latest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Hierarchical data structures with builder pattern support for the Genro ecosystem (Genro Kyō).

## Installation

```bash
pip install genro-treestore
```

## Features

- **TreeStore**: A container of nodes with hierarchical navigation
- **TreeStoreNode**: Nodes with label, attributes, and value (scalar or nested TreeStore)
- **TreeStoreBuilder**: Base class for typed builders with validation
- **@valid_children**: Decorator for child validation with cardinality constraints
- **Path access**: Dotted paths, positional (#N), and attribute (?attr) syntax

## Quick Start

```python
from genro_treestore import TreeStore, TreeStoreBuilder, valid_children

# Basic usage
store = TreeStore()
div = store.child('div', color='red')
ul = div.child('ul')
ul.child('li', value='First item')
ul.child('li', value='Second item')

# Access by path
store['div_0.ul_0.li_0'].value  # 'First item'
store['div_0?color']  # 'red'

# Typed builder with validation
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
```

## Path Syntax

- `store['div_0']` - Access by label
- `store['#0']` - Access by position (first node)
- `store['div_0.ul_0.li_0']` - Dotted path
- `store['#0.ul_0.#3']` - Mixed positional and label
- `store['div_0?color']` - Get attribute
- `store['div_0?color'] = 'blue'` - Set attribute

## Cardinality Constraints

```python
@valid_children(
    title='1',      # exactly one
    item='1:',      # one or more
    footer='0:1',   # zero or one
    tag='0:3',      # zero to three
)
def container(self, **attr):
    return self.child('container', **attr)
```

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
