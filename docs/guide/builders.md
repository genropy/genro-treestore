# Typed Builders

TreeStoreBuilder provides a base class for creating domain-specific builders with a fluent API.

## Why Use Builders?

Instead of using generic `child()` calls, builders let you:

- Create **type-safe** methods for specific node types
- Add **validation** for child relationships
- Provide **IDE autocompletion** and type hints
- Build **domain-specific languages** (DSLs)

## Basic Builder

```python
from genro_treestore import TreeStoreBuilder

class HtmlBuilder(TreeStoreBuilder):
    def div(self, **attr):
        """Create a div element."""
        return self.child('div', **attr)

    def span(self, value=None, **attr):
        """Create a span element with optional text."""
        return self.child('span', value=value, **attr)

    def ul(self, **attr):
        """Create an unordered list."""
        return self.child('ul', **attr)

    def li(self, value=None, **attr):
        """Create a list item."""
        return self.child('li', value=value, **attr)
```

### Using the Builder

```python
builder = HtmlBuilder()

# Build structure
main = builder.div(id='main')
header = main.div(class_='header')
header.span('Welcome!')

nav = main.ul(class_='nav')
nav.li('Home')
nav.li('About')
nav.li('Contact')

# Access the underlying store
store = builder.store
```

## Method Chaining

Builder methods return new builder instances, enabling fluent chaining:

```python
builder = HtmlBuilder()

(builder
    .div(id='container')
    .div(class_='content')
    .span('Nested content'))
```

## Custom Constructors

Add specialized methods for common patterns:

```python
class HtmlBuilder(TreeStoreBuilder):
    def div(self, **attr):
        return self.child('div', **attr)

    def link(self, href, text):
        """Create an anchor element."""
        return self.child('a', href=href, value=text)

    def image(self, src, alt=''):
        """Create an image element."""
        return self.child('img', src=src, alt=alt)

    def list_from_items(self, items):
        """Create a ul with multiple li children."""
        ul = self.ul()
        for item in items:
            ul.li(item)
        return ul
```

## Inheritance

Extend builders for specialized domains:

```python
class BaseBuilder(TreeStoreBuilder):
    def container(self, **attr):
        return self.child('container', **attr)

class FormBuilder(BaseBuilder):
    def input(self, name, type_='text', **attr):
        return self.child('input', name=name, type=type_, **attr)

    def button(self, label, **attr):
        return self.child('button', value=label, **attr)

    def form(self, action='', method='POST', **attr):
        return self.child('form', action=action, method=method, **attr)
```

## Type Hints

Add type hints for better IDE support:

```python
from typing import Self

class HtmlBuilder(TreeStoreBuilder):
    def div(self, **attr) -> Self:
        """Create a div element."""
        return self.child('div', **attr)

    def span(self, value: str | None = None, **attr) -> Self:
        """Create a span element."""
        return self.child('span', value=value, **attr)
```

## Complete Example

```python
from genro_treestore import TreeStoreBuilder, valid_children

class MenuBuilder(TreeStoreBuilder):
    """Builder for navigation menus."""

    @valid_children('item', 'submenu')
    def menu(self, title: str, **attr):
        """Create a menu container."""
        return self.child('menu', title=title, **attr)

    @valid_children('item', 'submenu')
    def submenu(self, title: str, **attr):
        """Create a submenu."""
        return self.child('submenu', title=title, **attr)

    def item(self, label: str, href: str = '#', **attr):
        """Create a menu item."""
        return self.child('item', label=label, href=href, **attr)


# Usage
builder = MenuBuilder()
nav = builder.menu('Main Navigation')
nav.item('Home', '/')
nav.item('Products', '/products')

more = nav.submenu('More')
more.item('About', '/about')
more.item('Contact', '/contact')
```

## Next Steps

- Learn about [Validation](validation.md) with `@valid_children`
