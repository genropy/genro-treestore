# Builders Module

The `builders` package provides typed APIs for constructing TreeStore hierarchies.

## Module Structure

```{mermaid}
graph TB
    subgraph "genro_treestore.builders"
        BASE[base.py<br/>BuilderBase]
        DEC[decorators.py<br/>@element]
        HTML[html.py<br/>HtmlBuilder]

        subgraph "rnc/"
            RNC[RncBuilder]
            LAZY[LazyRncBuilder]
        end

        subgraph "xsd/"
            XSD[XsdBuilder]
        end

        BASE --> HTML
        BASE --> RNC
        BASE --> XSD
        DEC --> BASE
    end
```

## BuilderBase

```{eval-rst}
.. autoclass:: genro_treestore.BuilderBase
   :members:
   :undoc-members:
   :show-inheritance:
```

## Decorators

### @element

```{eval-rst}
.. autofunction:: genro_treestore.element
```

```{note}
`valid_children` is an alias for `element` - they are the same decorator.
The `element` decorator handles both tag registration and children validation.
```

## HtmlBuilder

```{eval-rst}
.. autoclass:: genro_treestore.HtmlBuilder
   :members:
   :undoc-members:
   :show-inheritance:
```

### HTML5 Content Model

```{mermaid}
graph TB
    subgraph "Content Categories"
        FLOW[Flow Content<br/>div, p, section...]
        PHRASING[Phrasing Content<br/>span, a, em...]
        EMBEDDED[Embedded Content<br/>img, video, iframe...]
        INTERACTIVE[Interactive Content<br/>a, button, input...]
        METADATA[Metadata Content<br/>head, title, meta...]
    end

    FLOW --> PHRASING
    FLOW --> EMBEDDED
    FLOW --> INTERACTIVE
```

## RncBuilder

Dynamic builder from RELAX NG Compact schemas.

```{eval-rst}
.. autoclass:: genro_treestore.builders.RncBuilder
   :members:
   :undoc-members:
   :show-inheritance:
```

### Example

```python
from genro_treestore import TreeStore
from genro_treestore.builders import RncBuilder

builder = RncBuilder.from_rnc('''
    start = document
    document = element doc { section+ }
    section = element section { title, para* }
    title = element title { text }
    para = element para { text }
''')

store = TreeStore(builder=builder)
doc = store.doc()
sec = doc.section()
sec.title(value='Introduction')
sec.para(value='Welcome.')
```

## XsdBuilder

Dynamic builder from XML Schema (XSD) files.

```{eval-rst}
.. autoclass:: genro_treestore.XsdBuilder
   :members:
   :undoc-members:
   :show-inheritance:
```

### Example

```python
from genro_treestore import TreeStore
from genro_treestore.builders import XsdBuilder

# Load XSD schema
xsd_content = open('invoice.xsd').read()
schema = TreeStore.from_xml(xsd_content)
builder = XsdBuilder(schema)

# Build validated structure
store = TreeStore(builder=builder)
invoice = store.Invoice()
invoice.Header().Date(value='2025-01-01')
```

## Builder Architecture

```{mermaid}
classDiagram
    class BuilderBase {
        <<abstract>>
        +_schema: dict
        +child(tag, **attr)
        +__getattr__(name)
    }

    class HtmlBuilder {
        +div(**attr)
        +span(**attr)
        +p(**attr)
        ...
    }

    class RncBuilder {
        +from_rnc(content)
        +from_rnc_file(path)
    }

    class XsdBuilder {
        +__init__(schema)
    }

    BuilderBase <|-- HtmlBuilder
    BuilderBase <|-- RncBuilder
    BuilderBase <|-- XsdBuilder
```

## Validation Flow

```{mermaid}
flowchart TD
    ADD[Add child node]
    CHK{Valid child?}
    CARD{Cardinality OK?}
    OK[Node added]
    ERR[InvalidChildError]
    CERR[TooManyChildrenError]

    ADD --> CHK
    CHK -->|Yes| CARD
    CHK -->|No| ERR
    CARD -->|Yes| OK
    CARD -->|No| CERR
```

## Cardinality Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `tag` | Zero or more | `'div'` |
| `tag[:]` | Zero or more | `'div[:]'` |
| `tag[1]` | Exactly one | `'title[1]'` |
| `tag[0:1]` | Zero or one | `'subtitle[0:1]'` |
| `tag[1:]` | One or more | `'section[1:]'` |
| `tag[2:5]` | Range | `'item[2:5]'` |

## See Also

- [Builders Guide](../guide/builders.md) - Creating custom builders
- [Validation Guide](../guide/validation.md) - Validation rules
