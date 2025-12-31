# Quick Start

This guide will help you get started with genro-treestore in a few minutes.

## Installation

```bash
pip install genro-treestore
```

## Basic Usage

### Creating a TreeStore

```python
from genro_treestore import TreeStore

# Create an empty store
store = TreeStore()

# Add children
div = store.child('div', id='main', color='red')
span = div.child('span', value='Hello World')
```

### Understanding the Structure

A TreeStore is a container of nodes. Each node has:

- **label**: Auto-generated identifier (e.g., `div_0`, `div_1`)
- **tag**: The type of node (stored in `attr['_tag']`)
- **attr**: Dictionary of attributes
- **value**: Either a scalar value or a nested TreeStore

```python
# Node attributes
print(div.label)      # 'div_0'
print(div.attr)       # {'_tag': 'div', 'id': 'main', 'color': 'red'}
print(span.value)     # 'Hello World'

# Parent-child relationship
print(span.parent)    # The TreeStore containing span
print(span.parent.parent)  # The div node
```

### Auto-labeling

Labels are automatically generated using the pattern `tag_N`:

```python
store = TreeStore()
store.child('div')    # label: div_0
store.child('div')    # label: div_1
store.child('span')   # label: span_0
store.child('div')    # label: div_2
```

## Accessing Nodes

### By Label

```python
node = store['div_0']
```

### By Position

```python
first = store['#0']   # First child
last = store['#-1']   # Last child
```

### By Path

```python
# Nested access
nested = store['div_0.ul_0.li_0']

# Mixed positional and label
node = store['#0.ul_0.#2']
```

### Attributes

```python
# Get attribute
color = store['div_0?color']

# Set attribute
store['div_0?color'] = 'blue'
```

## Working with Values

```python
# Set value directly
node = store.child('item', value=42)
print(node.value)  # 42

# Nested TreeStore as value
parent = store.child('container')
child = parent.child('nested', value='inside')
print(parent.value['nested_0'].value)  # 'inside'
```

## Iteration

```python
# Iterate over children
for node in store:
    print(node.label, node.attr['_tag'])

# Get all nodes
all_nodes = list(store)

# Length
print(len(store))  # Number of children
```

## Next Steps

- Learn about [Path Syntax](path-syntax.md) for advanced navigation
- Create [Typed Builders](builders.md) for structured data
- Add [Validation](validation.md) with cardinality constraints
