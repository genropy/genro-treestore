# Quick Start

This guide will help you get started with genro-treestore in a few minutes.

## Installation

```bash
pip install genro-treestore
```

## TreeStore API

TreeStore provides a hierarchical data structure with path-based access.

### Creating a TreeStore

```python
from genro_treestore import TreeStore

store = TreeStore()

# Create nodes with set_item (autocreates path)
store.set_item('config.database.host', 'localhost')
store.set_item('config.database.port', 5432)
store.set_item('config.cache.enabled', True)
```

### Accessing Values

```python
# Using __getitem__
store['config.database.host']  # 'localhost'

# Using get_item (with default)
store.get_item('config.database.host')  # 'localhost'
store.get_item('missing', 'default')  # 'default'
```

### Setting Values

```python
# Using __setitem__ (autocreates path)
store['users.alice'] = 'Alice'
store['users.bob'] = 'Bob'

# Using set_item with attributes
store.set_item('items.product', 'Widget', price=9.99, stock=100)
```

### Fluent Chaining

`set_item` returns TreeStore for fluent chaining:

```python
# Chain branches (returns child store)
store.set_item('html').set_item('body').set_item('div', id='main')

# Chain leaves on same level (returns parent)
ul = store.set_item('html.body.ul')
ul.set_item('li1', 'Item 1').set_item('li2', 'Item 2').set_item('li3', 'Item 3')
```

### Attributes

```python
# Set attributes
store.set_item('div', color='red', size=10)
store.set_attr('div', border='1px')

# Get attributes
store['div?color']  # 'red'
store.get_attr('div', 'size')  # 10
store.get_attr('div')  # {'color': 'red', 'size': 10, 'border': '1px'}
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
store.set_item('users.alice', 'Alice', role='admin')
store.set_item('users.bob', 'Bob', role='user')

users = store.get_node('users').value
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

## Using Builders (Builder Pattern)

Builders provide typed APIs with auto-labeling and validation.

### Using HtmlBuilder

```python
from genro_treestore import TreeStore
from genro_treestore.builders import HtmlBuilder

store = TreeStore(builder=HtmlBuilder())

# Fluent API - methods create nodes with auto-labels
div = store.div(id='main')         # creates div_0
span = div.span(value='Hello')     # creates span_0 under div_0
div.p(value='World')               # creates p_0 under div_0

# Access by auto-generated labels
store['div_0.span_0']  # 'Hello'
store['div_0?id']      # 'main'
```

### Creating Custom Builders

```python
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element

class MyBuilder(BuilderBase):
    @element(children='li')  # ul can only contain li children
    def ul(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()  # li is a leaf (no children)
    def li(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

    @element()
    def div(self, target, tag, **attr):
        return self.child(target, tag, **attr)

# Usage
store = TreeStore(builder=MyBuilder())
div = store.div(id='container')
ul = div.ul()
ul.li(value='Item 1')
ul.li(value='Item 2')

# Auto-labels: div_0, ul_0, li_0, li_1
store['div_0.ul_0.li_0']  # 'Item 1'
```

## Next Steps

- Learn about [Path Syntax](path-syntax.md) for advanced navigation
- Create [Typed Builders](builders.md) for structured data
- Add [Validation](validation.md) with cardinality constraints
