# Child Validation

The `@valid_children` decorator enforces rules about which children a node can contain.

## Basic Usage

```python
from genro_treestore import TreeStoreBuilder, valid_children

class HtmlBuilder(TreeStoreBuilder):
    @valid_children('li')  # Only 'li' children allowed
    def ul(self, **attr):
        return self.child('ul', **attr)

    def li(self, value=None, **attr):
        return self.child('li', value=value, **attr)

    def span(self, value=None, **attr):
        return self.child('span', value=value, **attr)
```

### Valid Children

```python
builder = HtmlBuilder()
ul = builder.ul()
ul.li('Item 1')  # OK
ul.li('Item 2')  # OK
```

### Invalid Children

```python
builder = HtmlBuilder()
ul = builder.ul()
ul.span('Invalid!')  # Raises InvalidChildError
```

## Cardinality Constraints

Control how many children of each type are allowed:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `'tag'` | Zero or more (default) | `'li'` - any number of li |
| `'tag=1'` | Exactly one | `'title=1'` - must have one title |
| `'tag=1:'` | One or more | `'item=1:'` - at least one item |
| `'tag=0:1'` | Zero or one | `'footer=0:1'` - optional, max one |
| `'tag=0:3'` | Zero to three | `'option=0:3'` - max three options |
| `'tag=2:5'` | Two to five | `'row=2:5'` - between 2 and 5 rows |

## Examples

### Required Child

```python
@valid_children('title=1', 'item')
def section(self, **attr):
    """Section must have exactly one title, any number of items."""
    return self.child('section', **attr)
```

### Optional Single Child

```python
@valid_children('header=0:1', 'content=1', 'footer=0:1')
def page(self, **attr):
    """Page has optional header/footer, required content."""
    return self.child('page', **attr)
```

### Minimum Required

```python
@valid_children('option=1:')
def select(self, **attr):
    """Select must have at least one option."""
    return self.child('select', **attr)
```

### Maximum Limit

```python
@valid_children('column=1:4')
def row(self, **attr):
    """Row must have 1-4 columns."""
    return self.child('row', **attr)
```

## Exceptions

### InvalidChildError

Raised when adding a child with a non-allowed tag:

```python
from genro_treestore import InvalidChildError

try:
    ul.span('text')  # ul only allows 'li'
except InvalidChildError as e:
    print(e)  # "Invalid child 'span' for parent 'ul'"
```

### MissingChildError

Raised when validation detects missing required children:

```python
from genro_treestore import MissingChildError

@valid_children('title=1', 'content=1')
def article(self, **attr):
    return self.child('article', **attr)

# If article node is finalized without required children
# MissingChildError: "Missing required child 'title' for 'article'"
```

### TooManyChildrenError

Raised when exceeding maximum allowed children:

```python
from genro_treestore import TooManyChildrenError

@valid_children('item=0:3')
def menu(self, **attr):
    return self.child('menu', **attr)

menu = builder.menu()
menu.item('A')
menu.item('B')
menu.item('C')
menu.item('D')  # Raises TooManyChildrenError
```

## Complete Example

```python
from genro_treestore import TreeStoreBuilder, valid_children

class DocumentBuilder(TreeStoreBuilder):
    @valid_children('head=1', 'body=1')
    def html(self, **attr):
        """HTML document requires exactly one head and one body."""
        return self.child('html', **attr)

    @valid_children('title=1', 'meta', 'link')
    def head(self, **attr):
        """Head requires one title, allows meta and link tags."""
        return self.child('head', **attr)

    @valid_children('header=0:1', 'main=1', 'footer=0:1')
    def body(self, **attr):
        """Body has optional header/footer, required main."""
        return self.child('body', **attr)

    def title(self, value, **attr):
        return self.child('title', value=value, **attr)

    def meta(self, **attr):
        return self.child('meta', **attr)

    def link(self, **attr):
        return self.child('link', **attr)

    @valid_children('article', 'section', 'div')
    def main(self, **attr):
        return self.child('main', **attr)

    def header(self, **attr):
        return self.child('header', **attr)

    def footer(self, **attr):
        return self.child('footer', **attr)

    def article(self, **attr):
        return self.child('article', **attr)

    def section(self, **attr):
        return self.child('section', **attr)

    def div(self, **attr):
        return self.child('div', **attr)


# Usage
builder = DocumentBuilder()
html = builder.html()

head = html.head()
head.title('My Page')
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
