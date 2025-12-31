# Path Syntax

genro-treestore provides a flexible path syntax for navigating hierarchical structures.

## Basic Paths

### Label Access

Access nodes by their auto-generated label:

```python
store = TreeStore()
div = store.child('div', id='main')
span = div.child('span')

# Access by label
node = store['div_0']
nested = store['div_0.span_0']
```

### Positional Access

Use `#N` to access nodes by position (0-indexed):

```python
store = TreeStore()
store.child('div')  # #0
store.child('span') # #1
store.child('div')  # #2

first = store['#0']   # First child (div_0)
second = store['#1']  # Second child (span_0)
last = store['#-1']   # Last child (div_1)
```

## Dotted Paths

Chain multiple segments with dots for nested access:

```python
# Label path
store['div_0.ul_0.li_0']

# Positional path
store['#0.#0.#0']

# Mixed path
store['div_0.#0.li_2']
```

## Attribute Access

Use `?attr` to read or write node attributes:

### Reading Attributes

```python
store = TreeStore()
store.child('div', color='red', size=10)

color = store['div_0?color']  # 'red'
size = store['div_0?size']    # 10
```

### Setting Attributes

```python
store['div_0?color'] = 'blue'
store['div_0?new_attr'] = 'value'
```

### Path + Attribute

```python
# Access attribute on nested node
value = store['div_0.span_0?class']
store['div_0.span_0?class'] = 'highlight'
```

## Special Cases

### Root Access

Empty path returns the store itself:

```python
root = store['']  # Returns store
```

### Non-existent Paths

Accessing non-existent paths raises `KeyError`:

```python
try:
    node = store['nonexistent']
except KeyError:
    print("Node not found")
```

### Attribute on Non-existent Node

```python
try:
    value = store['nonexistent?attr']
except KeyError:
    print("Node not found")
```

## Path Examples

```python
store = TreeStore()

# Build structure
html = store.child('html')
body = html.child('body')
div = body.child('div', id='container')
ul = div.child('ul', class_='list')
ul.child('li', value='Item 1')
ul.child('li', value='Item 2')
ul.child('li', value='Item 3')

# Various access patterns
store['html_0']                    # html node
store['html_0.body_0']             # body node
store['html_0.body_0.div_0']       # div node
store['#0.#0.#0']                  # same as above
store['html_0.body_0.div_0?id']    # 'container'
store['#0.#0.#0.ul_0.#1']          # second li
store['#0.#0.#0.ul_0.li_1'].value  # 'Item 2'
```

## Use Cases

### Configuration Trees

```python
config = TreeStore()
db = config.child('database')
db.child('host', value='localhost')
db.child('port', value=5432)

# Access
host = config['database_0.host_0'].value
port = config['database_0.port_0'].value
```

### DOM-like Structures

```python
page = TreeStore()
page.child('header', value='Welcome')
main = page.child('main')
main.child('article', id='post-1', value='Content...')
page.child('footer', value='Copyright 2025')

# Navigation
article_id = page['main_0.article_0?id']
```
