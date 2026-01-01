# XSD Builder

Dynamic TreeStore builder from XML Schema Definition (XSD) schemas.

## Overview

XSD is the W3C standard for defining XML document structure. This module
parses XSD schemas (via TreeStore.from_xml) and creates builders from them.

## Usage

```python
from genro_treestore import TreeStore
from genro_treestore.builders.xsd import XsdBuilder

# Load XSD schema
xsd_content = open('fatturapa_v1.2.2.xsd').read()
schema = TreeStore.from_xml(xsd_content)

# Create builder
builder = XsdBuilder(schema)

# Use with TreeStore
fattura = TreeStore(builder=builder)
fe = fattura.FatturaElettronica(versione='FPR12')
header = fe.FatturaElettronicaHeader()
# ...
```

## How It Works

1. Parse XSD with `TreeStore.from_xml(xsd_content)`
2. `XsdBuilder` extracts element and type definitions
3. Builder methods are created dynamically for each element
4. Child element constraints are derived from complexType definitions
