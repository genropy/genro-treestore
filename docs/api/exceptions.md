# Exceptions Module

The `exceptions` module defines all custom exceptions raised by TreeStore.

## Exception Hierarchy

```{mermaid}
graph TB
    subgraph "Exception Hierarchy"
        BASE[TreeStoreError<br/>Base exception]
        IC[InvalidChildError<br/>Invalid child tag]
        IP[InvalidParentError<br/>Invalid parent context]
        MC[MissingChildError<br/>Missing mandatory child]
        TMC[TooManyChildrenError<br/>Cardinality exceeded]

        BASE --> IC
        BASE --> IP
        BASE --> MC
        BASE --> TMC
    end
```

## TreeStoreError

```{eval-rst}
.. autoexception:: genro_treestore.TreeStoreError
   :members:
   :show-inheritance:
```

Base exception for all TreeStore errors. Catch this to handle any TreeStore-specific exception.

```python
from genro_treestore import TreeStore, TreeStoreError

try:
    store = TreeStore(builder=my_builder)
    store.invalid_tag()
except TreeStoreError as e:
    print(f"TreeStore error: {e}")
```

## InvalidChildError

```{eval-rst}
.. autoexception:: genro_treestore.InvalidChildError
   :members:
   :show-inheritance:
```

Raised when attempting to add a child that is not allowed by the builder's validation rules.

```python
from genro_treestore import TreeStore, InvalidChildError
from genro_treestore.builders import HtmlBuilder

store = TreeStore(builder=HtmlBuilder())
ul = store.ul()

try:
    ul.div()  # div is not a valid child of ul
except InvalidChildError as e:
    print(f"Invalid child: {e}")
    # InvalidChildError: 'div' is not a valid child of 'ul'
```

## InvalidParentError

```{eval-rst}
.. autoexception:: genro_treestore.InvalidParentError
   :members:
   :show-inheritance:
```

Raised when a tag is added in an invalid parent context.

```python
from genro_treestore import TreeStore, InvalidParentError

store = TreeStore(builder=my_builder)

try:
    store.body()  # body may only be child of html
except InvalidParentError as e:
    print(f"Invalid parent: {e}")
```

## MissingChildError

```{eval-rst}
.. autoexception:: genro_treestore.MissingChildError
   :members:
   :show-inheritance:
```

Raised when a mandatory child element is missing during validation.

```python
from genro_treestore import TreeStore, MissingChildError
from genro_treestore.builders import BuilderBase, element, valid_children

class DocBuilder(BuilderBase):
    @element
    @valid_children('title[1]')  # title is required
    def section(self, store, parent, **attrs):
        pass

store = TreeStore(builder=DocBuilder())
sec = store.section()

# During validation, if title is missing:
# MissingChildError: 'section' requires at least 1 'title' child
```

## TooManyChildrenError

```{eval-rst}
.. autoexception:: genro_treestore.TooManyChildrenError
   :members:
   :show-inheritance:
```

Raised when adding a child would exceed the maximum cardinality.

```python
from genro_treestore import TreeStore, TooManyChildrenError
from genro_treestore.builders import BuilderBase, element, valid_children

class DocBuilder(BuilderBase):
    @element
    @valid_children('title[1]')  # exactly one title
    def section(self, store, parent, **attrs):
        pass

    @element
    def title(self, store, parent, value=None, **attrs):
        pass

store = TreeStore(builder=DocBuilder())
sec = store.section()
sec.title(value='First Title')

try:
    sec.title(value='Second Title')  # exceeds limit
except TooManyChildrenError as e:
    print(f"Too many: {e}")
    # TooManyChildrenError: 'section' allows at most 1 'title' child
```

## Exception Handling Patterns

### Catching All TreeStore Errors

```python
from genro_treestore import TreeStoreError

try:
    # Any TreeStore operation
    store.some_operation()
except TreeStoreError as e:
    logger.error(f"TreeStore operation failed: {e}")
```

### Specific Exception Handling

```python
from genro_treestore import (
    InvalidChildError,
    MissingChildError,
    TooManyChildrenError,
)

try:
    store.build_structure()
except InvalidChildError as e:
    print(f"Invalid structure: {e}")
except MissingChildError as e:
    print(f"Missing required element: {e}")
except TooManyChildrenError as e:
    print(f"Too many elements: {e}")
```

## Exception Flow

```{mermaid}
flowchart TD
    OP[Operation]
    CHK{Validation<br/>Check}
    OK[Success]
    IC[InvalidChildError]
    MC[MissingChildError]
    TMC[TooManyChildrenError]

    OP --> CHK
    CHK -->|Valid child| OK
    CHK -->|Unknown tag| IC
    CHK -->|Missing required| MC
    CHK -->|Exceeds max| TMC
```

## See Also

- [Validation Guide](../guide/validation.md) - Validation rules and cardinality
- [Builders Guide](../guide/builders.md) - Creating builders with validation
