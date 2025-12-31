# Quick Start

This guide will help you get started with genro-treestore in a few minutes.

## Installation

```bash
pip install genro-treestore
```

## TreeStore (Bag-like API)

TreeStore provides a familiar API inspired by Genro Bag.

### Creating a TreeStore

```python
from genro_treestore import TreeStore

store = TreeStore()

# Create nodes with setItem (autocreates path)
store.setItem('config.database.host', 'localhost')
store.setItem('config.database.port', 5432)
store.setItem('config.cache.enabled', True)
```

### Accessing Values

```python
# Using __getitem__
store['config.database.host']  # 'localhost'

# Using getItem (with default)
store.getItem('config.database.host')  # 'localhost'
store.getItem('missing', 'default')  # 'default'
```

### Setting Values

```python
# Using __setitem__ (autocreates path)
store['users.alice'] = 'Alice'
store['users.bob'] = 'Bob'

# Using setItem with attributes
store.setItem('items.product', 'Widget', price=9.99, stock=100)
```

### Fluent Chaining

`setItem` returns TreeStore for fluent chaining:

```python
# Chain branches (returns child store)
store.setItem('html').setItem('body').setItem('div', id='main')

# Chain leaves on same level (returns parent)
ul = store.setItem('html.body.ul')
ul.setItem('li1', 'Item 1').setItem('li2', 'Item 2').setItem('li3', 'Item 3')
```

### Attributes

```python
# Set attributes
store.setItem('div', color='red', size=10)
store.setAttr('div', border='1px')

# Get attributes
store['div?color']  # 'red'
store.getAttr('div', 'size')  # 10
store.getAttr('div')  # {'color': 'red', 'size': 10, 'border': '1px'}
```

### Path Syntax

```python
store['label']           # by label
store['#0']              # first node (positional)
store['#-1']             # last node
store['a.b.c']           # dotted path
store['#0.child.#2']     # mixed
store['path?attr']       # get attribute
store['path?attr'] = v   # set attribute
```

### Digest

Extract data from nodes:

```python
store.setItem('users.alice', 'Alice', role='admin')
store.setItem('users.bob', 'Bob', role='user')

users = store.getNode('users').value
users.digest('#k')  # ['alice', 'bob']
users.digest('#v')  # ['Alice', 'Bob']
users.digest('#a.role')  # ['admin', 'user']
users.digest('#k,#v')  # [('alice', 'Alice'), ('bob', 'Bob')]
```

### Iteration

```python
# Iterate over nodes
for node in store:
    print(node.label, node.value)

# Get lists
store.keys()    # ['label1', 'label2', ...]
store.values()  # [value1, value2, ...]
store.items()   # [('label1', value1), ...]
store.nodes()   # [TreeStoreNode, ...]

# Walk tree
for path, node in store.walk():
    print(path, node.value)
```

## TreeStoreBuilder (Builder Pattern)

For structured data with auto-labeling and validation.

### Basic Builder

```python
from genro_treestore import TreeStoreBuilder

builder = TreeStoreBuilder()

# child() creates nodes with auto-labels
div = builder.child('div', color='red')  # label: div_0
span = div.child('span', value='Hello')  # label: span_0

builder['div_0.span_0']  # 'Hello'
builder['div_0?color']   # 'red'
```

### Typed Builder

```python
from genro_treestore import TreeStoreBuilder, valid_children

class HtmlBuilder(TreeStoreBuilder):
    def div(self, **attr):
        return self.child('div', **attr)

    @valid_children('li')  # Only 'li' allowed
    def ul(self, **attr):
        return self.child('ul', **attr)

    def li(self, value=None, **attr):
        return self.child('li', value=value, **attr)

builder = HtmlBuilder()
div = builder.div(id='container')
ul = div.ul()
ul.li('Item 1')
ul.li('Item 2')

# Auto-labels: div_0, ul_0, li_0, li_1
builder['div_0.ul_0.li_0']  # 'Item 1'
```

## Next Steps

- Learn about [Path Syntax](path-syntax.md) for advanced navigation
- Create [Typed Builders](builders.md) for structured data
- Add [Validation](validation.md) with cardinality constraints
