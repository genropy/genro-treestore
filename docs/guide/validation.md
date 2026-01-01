# Child Validation

The `@element` decorator with the `children` parameter enforces rules about which children a node can contain.

## Basic Usage

```python
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element

class HtmlBuilder(BuilderBase):
    @element(children='li')  # Only 'li' children allowed
    def ul(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def li(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

    @element()
    def span(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)
```

### Valid Children

```python
store = TreeStore(builder=HtmlBuilder())
ul = store.ul()
ul.li(value='Item 1')  # OK
ul.li(value='Item 2')  # OK
```

### Invalid Children

```python
store = TreeStore(builder=HtmlBuilder())
ul = store.ul()
ul.span(value='Invalid!')  # Raises InvalidChildError
```

## Cardinality Constraints

Control how many children of each type are allowed:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `'tag'` | Zero or more (default) | `'li'` - any number of li |
| `'tag[1]'` | Exactly one | `'title[1]'` - must have one title |
| `'tag[1:]'` | One or more | `'item[1:]'` - at least one item |
| `'tag[0:1]'` | Zero or one | `'footer[0:1]'` - optional, max one |
| `'tag[0:3]'` | Zero to three | `'option[0:3]'` - max three options |
| `'tag[2:5]'` | Two to five | `'row[2:5]'` - between 2 and 5 rows |

## Examples

### Required Child

```python
@element(children='title[1], item')
def section(self, target, tag, **attr):
    """Section must have exactly one title, any number of items."""
    return self.child(target, tag, **attr)
```

### Optional Single Child

```python
@element(children='header[0:1], content[1], footer[0:1]')
def page(self, target, tag, **attr):
    """Page has optional header/footer, required content."""
    return self.child(target, tag, **attr)
```

### Minimum Required

```python
@element(children='option[1:]')
def select(self, target, tag, **attr):
    """Select must have at least one option."""
    return self.child(target, tag, **attr)
```

### Maximum Limit

```python
@element(children='column[1:4]')
def row(self, target, tag, **attr):
    """Row must have 1-4 columns."""
    return self.child(target, tag, **attr)
```

## Exceptions

### InvalidChildError

Raised when adding a child with a non-allowed tag:

```python
from genro_treestore import InvalidChildError

try:
    ul.span(value='text')  # ul only allows 'li'
except InvalidChildError as e:
    print(e)  # "Invalid child 'span' for parent 'ul'"
```

### MissingChildError

Raised when validation detects missing required children:

```python
from genro_treestore import MissingChildError

@element(children='title[1], content[1]')
def article(self, target, tag, **attr):
    return self.child(target, tag, **attr)

# If article node is finalized without required children
# MissingChildError: "Missing required child 'title' for 'article'"
```

### TooManyChildrenError

Raised when exceeding maximum allowed children:

```python
from genro_treestore import TooManyChildrenError

@element(children='item[0:3]')
def menu(self, target, tag, **attr):
    return self.child(target, tag, **attr)

store = TreeStore(builder=MyBuilder())
menu = store.menu()
menu.item(value='A')
menu.item(value='B')
menu.item(value='C')
menu.item(value='D')  # Raises TooManyChildrenError
```

## Complete Example

```python
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element

class DocumentBuilder(BuilderBase):
    @element(children='head[1], body[1]')
    def html(self, target, tag, **attr):
        """HTML document requires exactly one head and one body."""
        return self.child(target, tag, **attr)

    @element(children='title[1], meta, link')
    def head(self, target, tag, **attr):
        """Head requires one title, allows meta and link tags."""
        return self.child(target, tag, **attr)

    @element(children='header[0:1], main[1], footer[0:1]')
    def body(self, target, tag, **attr):
        """Body has optional header/footer, required main."""
        return self.child(target, tag, **attr)

    @element()
    def title(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

    @element()
    def meta(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def link(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(children='article, section, div')
    def main(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def header(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def footer(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def article(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def section(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def div(self, target, tag, **attr):
        return self.child(target, tag, **attr)


# Usage
store = TreeStore(builder=DocumentBuilder())
html = store.html()

head = html.head()
head.title(value='My Page')
head.meta(charset='utf-8')

body = html.body()
body.header()
main = body.main()
main.article()
body.footer()
```

## Validation Timing

Validation happens at different times:

1. **Invalid child** - Immediately when `child()` is called
2. **Too many children** - Immediately when exceeding max count
3. **Missing children** - When explicitly validated (implementation-dependent)

## Tips

- Use validation for document structures, configuration schemas, UI hierarchies
- Start without validation, add it incrementally
- Use clear error messages to guide users
- Consider making some constraints warnings instead of errors during development
