# Genro-TreeStore

Hierarchical data structures with builder pattern support for the Genro ecosystem (Genro Kyō).

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

**genro-treestore** provides a lightweight, zero-dependency library for creating and managing hierarchical data structures in Python.

### Key Features

- **TreeStore**: A container of nodes with hierarchical navigation
- **TreeStoreNode**: Nodes with label, attributes, and value (scalar or nested TreeStore)
- **TreeStoreBuilder**: Base class for typed builders with validation
- **@valid_children**: Decorator for child validation with cardinality constraints
- **Path access**: Dotted paths, positional (`#N`), and attribute (`?attr`) syntax

### Quick Example

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
```

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
