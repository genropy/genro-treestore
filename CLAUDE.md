# Claude Code Instructions - Genro-TreeStore

## Project Context

**genro-treestore** is a lightweight, zero-dependency Python library providing hierarchical data structures with builder pattern support for the Genro ecosystem (Genro Kyō).

Part of **genro-modules** (Apache 2.0 license).

## Repository Structure

```
genro-treestore/
├── src/genro_treestore/
│   ├── __init__.py      # Public API exports
│   ├── store/           # TreeStore, TreeStoreNode
│   ├── builders/        # BuilderBase, HtmlBuilder
│   ├── resolvers/       # TreeStoreResolver, CallbackResolver
│   └── py.typed         # PEP 561 marker
├── tests/
├── pyproject.toml
├── LICENSE              # Apache 2.0
├── NOTICE
└── README.md
```

## Public API

```python
from genro_treestore import (
    TreeStore,           # Container of nodes with builder methods
    TreeStoreNode,       # Node with label, attr, value
    BuilderBase,         # Base for typed builders
    element,             # Decorator for builder methods
    InvalidChildError,   # Invalid child tag
    MissingChildError,   # Missing mandatory child
    TooManyChildrenError,# Too many children of type
)
```

## Key Concepts

- **Dual relationship**: TreeStoreNode.parent → TreeStore, TreeStore.parent → TreeStoreNode
- **Auto-labeling**: `tag_N` pattern (div_0, div_1, etc.)
- **Tag in attributes**: `node.attr['_tag']` stores the node type
- **Path syntax**: dotted (`a.b.c`), positional (`#0`), attribute (`?attr`)

## Development

### Running Tests

```bash
pytest tests/
pytest tests/ --cov=src/genro_treestore --cov-report=term-missing
```

### Code Style

- Python 3.10+
- Type hints required
- English for all code, comments, and commit messages

## Git Commit Authorship

- **NEVER** include Claude as a co-author in commits
- **ALWAYS** remove the "Co-Authored-By: Claude" line

## Language Policy

- All code, comments, and commit messages in **English**
