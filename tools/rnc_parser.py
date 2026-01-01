# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Parser for RelaxNG Compact (.rnc) files from W3C HTML Validator.

Parses .rnc files and generates JSON schema for use with TreeStore builders.

Output format:
{
    "elements": {
        "tag": {
            "children": "child1, child2[:1], =ref",  # or null for leaf
            "leaf": true/false,
            "attrs": {
                "attrname": {
                    "type": "int|string|uri|bool|enum|idrefs",
                    "required": true/false,
                    "min": number,
                    "max": number,
                    "default": value,
                    "values": ["a", "b"]  # for enum
                }
            }
        }
    },
    "refs": {
        "flow": "div, p, span, ...",
        "phrasing": "a, abbr, ..."
    }
}

Usage:
    python rnc_parser.py tables.rnc -o html_tables.json
    python rnc_parser.py *.rnc -o html_schema.json --merge
"""

from __future__ import annotations

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field


# Patterns for parsing RNC
ELEMENT_DEF = re.compile(r'^(\w+)\.elem\s*=\s*element\s+(\w+)\s*\{([^}]*)\}', re.MULTILINE)
ATTRS_DEF = re.compile(r'^(\w+)\.attrs\s*=\s*\(?\s*([^)]+)\)?', re.MULTILINE | re.DOTALL)
ATTR_DEF = re.compile(r'^(\w+)\.attrs\.(\w+)\s*=\s*attribute\s+(\w+)\s*\{([^}]*)\}', re.MULTILINE)
CONTENT_DEF = re.compile(r'^(\w+)\.content\s*=\s*(.+?)(?=\n\w+\.|$)', re.MULTILINE | re.DOTALL)

# Data type patterns
DATATYPE_MAP = {
    'common.data.integer.positive': {'type': 'int', 'min': 1},
    'common.data.integer.non-negative': {'type': 'int', 'min': 0},
    'common.data.integer': {'type': 'int'},
    'common.data.uri': {'type': 'uri'},
    'common.data.uri.non-empty': {'type': 'uri', 'required': True},
    'w:string': {'type': 'string'},
    'w:browsing-context-name-or-keyword': {'type': 'string'},
    'string': {'type': 'string'},
    'text': {'type': 'string'},
    'common.data.idrefs': {'type': 'idrefs'},
    'common.data.idref': {'type': 'idref'},
    'w:color': {'type': 'color'},
}


@dataclass
class ElementSpec:
    """Specification for an HTML element."""
    tag: str
    children: str | None = None  # None = leaf, str = children spec
    attrs: dict[str, dict] = field(default_factory=dict)
    leaf: bool = False


@dataclass
class RncSchema:
    """Parsed RNC schema."""
    elements: dict[str, ElementSpec] = field(default_factory=dict)
    refs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        result = {
            'elements': {},
            'refs': self.refs
        }
        for tag, spec in self.elements.items():
            elem_dict = {}
            if spec.leaf:
                elem_dict['leaf'] = True
            if spec.children:
                elem_dict['children'] = spec.children
            if spec.attrs:
                elem_dict['attrs'] = spec.attrs
            result['elements'][tag] = elem_dict
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class RncParser:
    """Parser for RelaxNG Compact syntax files."""

    def __init__(self):
        self.schema = RncSchema()
        self._raw_content = ''
        self._attrs_defs: dict[str, dict[str, dict]] = {}  # element -> attr -> spec
        self._content_defs: dict[str, str] = {}  # element -> content model

    def parse_file(self, filepath: str | Path) -> RncSchema:
        """Parse a single .rnc file."""
        filepath = Path(filepath)
        self._raw_content = filepath.read_text()
        return self.parse(self._raw_content)

    def parse(self, content: str) -> RncSchema:
        """Parse RNC content string."""
        self._raw_content = content

        # First pass: collect all definitions
        self._parse_attr_definitions()
        self._parse_content_definitions()

        # Second pass: parse elements
        self._parse_elements()

        return self.schema

    def _parse_attr_definitions(self):
        """Parse individual attribute definitions like: td.attrs.colspan = ..."""
        for match in ATTR_DEF.finditer(self._raw_content):
            element = match.group(1)
            attr_name = match.group(2)
            # actual_name = match.group(3)  # name in HTML
            datatype = match.group(4).strip()

            if element not in self._attrs_defs:
                self._attrs_defs[element] = {}

            self._attrs_defs[element][attr_name] = self._parse_datatype(datatype)

    def _parse_datatype(self, datatype: str) -> dict:
        """Convert RNC datatype to our attr spec."""
        datatype = datatype.strip()

        # Check for enum: "value1" | "value2" | "value3"
        if '"' in datatype:
            values = re.findall(r'"([^"]+)"', datatype)
            if values:
                return {'type': 'enum', 'values': values}

        # Check known datatypes
        for pattern, spec in DATATYPE_MAP.items():
            if pattern in datatype:
                return spec.copy()

        # Default to string
        return {'type': 'string'}

    def _parse_content_definitions(self):
        """Parse content model definitions like: td.content = ..."""
        for match in CONTENT_DEF.finditer(self._raw_content):
            element = match.group(1)
            content = match.group(2).strip()
            self._content_defs[element] = content

    def _parse_elements(self):
        """Parse element definitions like: td.elem = element td { ... }"""
        for match in ELEMENT_DEF.finditer(self._raw_content):
            elem_name = match.group(1)
            tag = match.group(2)
            inner = match.group(3).strip()

            spec = ElementSpec(tag=tag)

            # Get attributes
            if elem_name in self._attrs_defs:
                spec.attrs = self._attrs_defs[elem_name]

            # Get content model
            if elem_name in self._content_defs:
                spec.children = self._normalize_content(self._content_defs[elem_name])
            else:
                # Check if content mentioned in element definition
                if 'empty' in inner.lower() or not self._has_content(elem_name):
                    spec.leaf = True

            self.schema.elements[tag] = spec

    def _has_content(self, elem_name: str) -> bool:
        """Check if element has content model defined."""
        pattern = rf'{elem_name}\.content\s*='
        return bool(re.search(pattern, self._raw_content))

    def _normalize_content(self, content: str) -> str:
        """Normalize content model to our children spec format."""
        # Remove comments
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)

        # Handle common patterns
        # (a | b | c)* -> a, b, c
        # (a | b | c)+ -> a[1:], b, c (at least one of the group)
        # a? -> a[:1]
        # a* -> a
        # a+ -> a[1:]

        # For now, simplified extraction of element references
        elements = re.findall(r'(\w+)\.elem', content)
        if elements:
            return ', '.join(elements)

        # Try to extract direct element names
        elements = re.findall(r'\b([a-z][a-z0-9]*)\b', content)
        # Filter out keywords
        keywords = {'empty', 'text', 'notallowed', 'element', 'attribute'}
        elements = [e for e in elements if e not in keywords]

        if elements:
            return ', '.join(sorted(set(elements)))

        return ''


def parse_tables_rnc(content: str) -> dict:
    """Parse tables.rnc specifically with hardcoded knowledge.

    This is a specialized parser that knows the structure of tables.rnc
    and generates accurate schema.
    """
    schema = {
        'elements': {
            'table': {
                'children': 'caption[:1], colgroup, thead[:1], tbody, tfoot[:1], tr',
            },
            'caption': {
                'children': '=flow',
            },
            'colgroup': {
                'children': 'col',
            },
            'col': {
                'leaf': True,
                'attrs': {
                    'span': {'type': 'int', 'min': 1, 'default': 1}
                }
            },
            'thead': {
                'children': 'tr',
            },
            'tbody': {
                'children': 'tr',
            },
            'tfoot': {
                'children': 'tr',
            },
            'tr': {
                'children': 'th, td',
            },
            'th': {
                'children': '=flow',
                'attrs': {
                    'colspan': {'type': 'int', 'min': 1, 'default': 1},
                    'rowspan': {'type': 'int', 'min': 0, 'default': 1},
                    'headers': {'type': 'idrefs'},
                    'scope': {'type': 'enum', 'values': ['row', 'col', 'rowgroup', 'colgroup']},
                    'abbr': {'type': 'string'},
                }
            },
            'td': {
                'children': '=flow',
                'attrs': {
                    'colspan': {'type': 'int', 'min': 1, 'default': 1},
                    'rowspan': {'type': 'int', 'min': 0, 'default': 1},
                    'headers': {'type': 'idrefs'},
                }
            },
        },
        'refs': {
            'flow': 'div, p, span, a, em, strong, ul, ol, table',  # simplified
        }
    }
    return schema


def main():
    parser = argparse.ArgumentParser(
        description='Parse RelaxNG Compact files and generate JSON schema'
    )
    parser.add_argument('files', nargs='+', help='RNC files to parse')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('--merge', action='store_true', help='Merge multiple files')
    parser.add_argument('--tables', action='store_true',
                       help='Use specialized tables.rnc parser')

    args = parser.parse_args()

    if args.tables:
        # Use hardcoded tables parser
        schema = parse_tables_rnc('')
    else:
        # Use generic parser
        rnc_parser = RncParser()
        for filepath in args.files:
            rnc_parser.parse_file(filepath)
        schema = rnc_parser.schema.to_dict()

    output = json.dumps(schema, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Schema written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
