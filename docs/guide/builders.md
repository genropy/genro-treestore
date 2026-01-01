# Typed Builders

BuilderBase provides an abstract base class for creating domain-specific builders with a fluent API.

## Why Use Builders?

Instead of using generic `set_item()` calls, builders let you:

- Create **type-safe** methods for specific node types
- Add **validation** for child relationships
- Provide **IDE autocompletion** and type hints
- Build **domain-specific languages** (DSLs)

## Basic Builder

```python
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element

class HtmlBuilder(BuilderBase):
    @element()
    def div(self, target, tag, **attr):
        """Create a div element."""
        return self.child(target, tag, **attr)

    @element()
    def span(self, target, tag, value=None, **attr):
        """Create a span element with optional text."""
        return self.child(target, tag, value=value, **attr)

    @element()
    def ul(self, target, tag, **attr):
        """Create an unordered list."""
        return self.child(target, tag, **attr)

    @element()
    def li(self, target, tag, value=None, **attr):
        """Create a list item."""
        return self.child(target, tag, value=value, **attr)
```

### Using the Builder

```python
store = TreeStore(builder=HtmlBuilder())

# Build structure
main = store.div(id='main')
header = main.div(class_='header')
header.span(value='Welcome!')

nav = main.ul(class_='nav')
nav.li(value='Home')
nav.li(value='About')
nav.li(value='Contact')

# Access values
store['div_0.div_0.span_0']  # 'Welcome!'
store['div_0?id']  # 'main'
```

## Method Chaining

Builder methods return new TreeStore/TreeStoreNode instances, enabling fluent chaining:

```python
store = TreeStore(builder=HtmlBuilder())

(store
    .div(id='container')
    .div(class_='content')
    .span(value='Nested content'))
```

## Custom Constructors

Add specialized methods for common patterns:

```python
class HtmlBuilder(BuilderBase):
    @element()
    def div(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def a(self, target, tag, href='#', value=None, **attr):
        """Create an anchor element."""
        return self.child(target, tag, href=href, value=value, **attr)

    @element()
    def img(self, target, tag, src='', alt='', **attr):
        """Create an image element."""
        return self.child(target, tag, src=src, alt=alt, value='', **attr)
```

## Child Validation

Use the `children` parameter to specify which child tags are allowed:

```python
class HtmlBuilder(BuilderBase):
    @element(children='li')  # Only 'li' children allowed
    def ul(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()  # Leaf element (no children)
    def li(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

    @element()
    def span(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

# Usage
store = TreeStore(builder=HtmlBuilder())
ul = store.ul()
ul.li(value='Item 1')  # OK
ul.li(value='Item 2')  # OK
ul.span(value='Bad!')  # Raises InvalidChildError
```

## Inheritance

Extend builders for specialized domains:

```python
class BaseBuilder(BuilderBase):
    @element()
    def container(self, target, tag, **attr):
        return self.child(target, tag, **attr)

class FormBuilder(BaseBuilder):
    @element()
    def input(self, target, tag, name='', type_='text', **attr):
        return self.child(target, tag, name=name, type=type_, value='', **attr)

    @element()
    def button(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

    @element(children='input, button')
    def form(self, target, tag, action='', method='POST', **attr):
        return self.child(target, tag, action=action, method=method, **attr)
```

## Type Hints

Add type hints for better IDE support:

```python
from typing import Self

class HtmlBuilder(BuilderBase):
    @element()
    def div(self, target, tag, **attr) -> TreeStore:
        """Create a div element."""
        return self.child(target, tag, **attr)

    @element()
    def span(self, target, tag, value: str | None = None, **attr) -> TreeStoreNode:
        """Create a span element."""
        return self.child(target, tag, value=value, **attr)
```

## Complete Example

```python
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element

class MenuBuilder(BuilderBase):
    """Builder for navigation menus."""

    @element(children='item, submenu')
    def menu(self, target, tag, title: str = '', **attr):
        """Create a menu container."""
        return self.child(target, tag, title=title, **attr)

    @element(children='item, submenu')
    def submenu(self, target, tag, title: str = '', **attr):
        """Create a submenu."""
        return self.child(target, tag, title=title, **attr)

    @element()  # Leaf - no children
    def item(self, target, tag, label: str = '', href: str = '#', **attr):
        """Create a menu item."""
        return self.child(target, tag, label=label, href=href, value='', **attr)


# Usage
store = TreeStore(builder=MenuBuilder())
nav = store.menu(title='Main Navigation')
nav.item(label='Home', href='/')
nav.item(label='Products', href='/products')

more = nav.submenu(title='More')
more.item(label='About', href='/about')
more.item(label='Contact', href='/contact')
```

## Next Steps

- Learn about [Validation](validation.md) with cardinality constraints
