# Path Syntax

genro-treestore provides a flexible path syntax for navigating hierarchical structures.

## Basic Paths

### Label Access

Access nodes by their label:

```python
from genro_treestore import TreeStore

store = TreeStore()
div = store.set_item('div', id='main')
span = div.set_item('span')

# Access by label
node = store['div']
nested = store['div.span']
```

### Positional Access

Use `#N` to access nodes by position (0-indexed):

```python
store = TreeStore()
store.set_item('div')   # #0
store.set_item('span')  # #1
store.set_item('p')     # #2

first = store['#0']   # First child (div)
second = store['#1']  # Second child (span)
last = store['#-1']   # Last child (p)
```

## Dotted Paths

Chain multiple segments with dots for nested access:

```python
# Label path
store['div.ul.li']

# Positional path
store['#0.#0.#0']

# Mixed path
store['div.#0.li']
```

## Attribute Access

Use `?attr` to read or write node attributes:

### Reading Attributes

```python
store = TreeStore()
store.set_item('div', color='red', size=10)

color = store['div?color']  # 'red'
size = store['div?size']    # 10
```

### Setting Attributes

```python
store['div?color'] = 'blue'
store['div?new_attr'] = 'value'
```

### Path + Attribute

```python
# Access attribute on nested node
value = store['div.span?class']
store['div.span?class'] = 'highlight'
```

## Special Cases

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
html = store.set_item('html')
body = html.set_item('body')
div = body.set_item('div', id='container')
ul = div.set_item('ul', class_='list')
ul.set_item('li_0', value='Item 1')
ul.set_item('li_1', value='Item 2')
ul.set_item('li_2', value='Item 3')

# Various access patterns
store['html']                      # html node
store['html.body']                 # body node
store['html.body.div']             # div node
store['#0.#0.#0']                  # same as above
store['html.body.div?id']          # 'container'
store['#0.#0.#0.ul.#1']            # second li
store['#0.#0.#0.ul.li_1']          # 'Item 2'
```

## Use Cases

### Configuration Trees

```python
config = TreeStore()
db = config.set_item('database')
db.set_item('host', value='localhost')
db.set_item('port', value=5432)

# Access
host = config['database.host']  # 'localhost'
port = config['database.port']  # 5432
```

### DOM-like Structures

```python
page = TreeStore()
page.set_item('header', value='Welcome')
main = page.set_item('main')
main.set_item('article', id='post-1', value='Content...')
page.set_item('footer', value='Copyright 2025')

# Navigation
article_id = page['main.article?id']
```

## With Builders

When using builders, labels follow the `tag_N` pattern:

```python
from genro_treestore import TreeStore
from genro_treestore.builders import HtmlBuilder

store = TreeStore(builder=HtmlBuilder())
div = store.div(id='main')
div.span(value='Hello')
div.span(value='World')

# Access with auto-generated labels
store['div_0']           # First div
store['div_0.span_0']    # First span inside div
store['div_0.span_1']    # Second span inside div
store['div_0?id']        # 'main'
```
