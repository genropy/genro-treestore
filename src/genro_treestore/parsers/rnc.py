# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Parser for RelaxNG Compact (.rnc) files into TreeStore.

Based on rnc2rng parser structure, adapted for direct TreeStore output.

Converts .rnc schema files directly into TreeStore structure.
The TreeStore can then be used directly by builders without JSON conversion.

RNC structure maps naturally to TreeStore:
- `name = value` → node with label=name
- `element name { ... }` → branch node with _type='element', _tag=name
- `attribute name { ... }` → leaf node with _type='attribute', _tag=name
- `?`, `*`, `+` → node attributes (optional, multiple, required)
- `&`, `|`, `,` → combinator attributes (_combinator)

Example:
    >>> from genro_treestore.parsers import parse_rnc_file
    >>> store = parse_rnc_file('tables.rnc')
    >>> store['table.elem']           # element definition
    >>> store['td.attrs.colspan']     # attribute definition

    # Or from URL:
    >>> import urllib.request
    >>> url = 'https://raw.githubusercontent.com/validator/validator/main/schema/html5/tables.rnc'
    >>> with urllib.request.urlopen(url) as response:
    ...     content = response.read().decode('utf-8')
    >>> store = parse_rnc(content)
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from ..store import TreeStore as TreeStoreType


class TokenType(Enum):
    """Token types for RNC lexer."""
    # Structural
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]

    # Operators
    EQUAL = auto()       # =
    COMBINE = auto()     # |= or &=
    PIPE = auto()        # |
    COMMA = auto()       # ,
    AMP = auto()         # &
    MINUS = auto()       # -
    STAR = auto()        # *
    PLUS = auto()        # +
    QMARK = auto()       # ?
    TILDE = auto()       # ~

    # Identifiers and literals
    CNAME = auto()       # prefix:name (qualified name)
    ID = auto()          # identifier
    LITERAL = auto()     # "string"

    # Keywords (subset of ID)
    KEYWORD = auto()

    # Comments
    DOCUMENTATION = auto()  # ## doc comment
    COMMENT = auto()        # # comment

    # End
    EOF = auto()


# RNC Keywords
KEYWORDS = {
    'attribute', 'default', 'datatypes', 'div', 'element', 'empty',
    'external', 'grammar', 'include', 'inherit', 'list', 'mixed',
    'namespace', 'notAllowed', 'parent', 'start', 'string', 'text', 'token'
}


@dataclass
class Token:
    """A lexical token."""
    type: TokenType
    value: str
    line: int
    col: int


class RncLexer:
    """Tokenizer for RNC files.

    Based on rnc2rng lexer patterns.

    Example:
        >>> lexer = RncLexer('element div { text }')
        >>> tokens = list(lexer.tokenize())
        >>> [t.type.name for t in tokens]
        ['KEYWORD', 'ID', 'LBRACE', 'KEYWORD', 'RBRACE', 'EOF']
    """

    # NCNAME pattern: valid XML name (no colon)
    NCNAME = r'[A-Za-z_][\w.-]*'

    # Token patterns (order matters!)
    PATTERNS = [
        (r'\s+', None),                          # Whitespace (skip)
        (r'##.*', TokenType.DOCUMENTATION),      # Doc comment
        (r'#.*', TokenType.COMMENT),             # Comment
        (r'\(', TokenType.LPAREN),
        (r'\)', TokenType.RPAREN),
        (r'\{', TokenType.LBRACE),
        (r'\}', TokenType.RBRACE),
        (r'\[', TokenType.LBRACKET),
        (r'\]', TokenType.RBRACKET),
        (r'\|=|&=', TokenType.COMBINE),
        (r'=', TokenType.EQUAL),
        (r'\|', TokenType.PIPE),
        (r',', TokenType.COMMA),
        (r'&', TokenType.AMP),
        (r'-', TokenType.MINUS),
        (r'\*', TokenType.STAR),
        (r'\+', TokenType.PLUS),
        (r'\?', TokenType.QMARK),
        (r'~', TokenType.TILDE),
        (r'"[^"]*"', TokenType.LITERAL),         # Double-quoted string
        (r"'[^']*'", TokenType.LITERAL),         # Single-quoted string
        # Qualified name (prefix:name or prefix:*)
        (rf'({NCNAME}):({NCNAME}|\*)', TokenType.CNAME),
        # Plain identifier
        (rf'{NCNAME}', TokenType.ID),
    ]

    def __init__(self, content: str):
        """Initialize lexer with RNC content.

        Args:
            content: RNC source code string.
        """
        self.content = content
        self.pos = 0
        self.line = 1
        self.col = 1

        # Compile patterns
        self._patterns = [
            (re.compile(pattern), token_type)
            for pattern, token_type in self.PATTERNS
        ]

    def _update_position(self, text: str):
        """Update line and column based on consumed text."""
        for ch in text:
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1

    def tokenize(self) -> Iterator[Token]:
        """Generate tokens from content.

        Yields:
            Token objects for each recognized token.
        """
        while self.pos < len(self.content):
            match = None
            for pattern, token_type in self._patterns:
                match = pattern.match(self.content, self.pos)
                if match:
                    text = match.group(0)

                    if token_type is not None:
                        # Check if ID is a keyword
                        if token_type == TokenType.ID and text in KEYWORDS:
                            token_type = TokenType.KEYWORD

                        # Clean up literal values
                        value = text
                        if token_type == TokenType.LITERAL:
                            value = text[1:-1]  # Remove quotes
                        elif token_type in (TokenType.COMMENT, TokenType.DOCUMENTATION):
                            value = text.lstrip('#').strip()

                        yield Token(token_type, value, self.line, self.col)

                    self._update_position(text)
                    self.pos = match.end()
                    break

            if not match:
                # Skip unknown character
                self._update_position(self.content[self.pos])
                self.pos += 1

        yield Token(TokenType.EOF, '', self.line, self.col)


class RncParser:
    """Parser that converts RNC tokens to TreeStore.

    Example:
        >>> lexer = RncLexer(content)
        >>> tokens = list(lexer.tokenize())
        >>> parser = RncParser(tokens)
        >>> store = parser.parse()
    """

    def __init__(self, tokens: list[Token]):
        """Initialize parser with token list.

        Args:
            tokens: List of tokens from RncLexer.
        """
        # Import here to avoid circular imports
        from ..store import TreeStore

        # Filter out comments (but keep doc comments for metadata)
        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]
        self.pos = 0
        self.store = TreeStore()
        self._current_doc: str | None = None
        self._TreeStore = TreeStore

    def peek(self, offset: int = 0) -> Token:
        """Peek at token at current position + offset."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return Token(TokenType.EOF, '', 0, 0)
        return self.tokens[pos]

    def advance(self) -> Token:
        """Advance position and return current token."""
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, *types: TokenType) -> Token:
        """Expect a token of given type(s).

        Raises:
            SyntaxError: If token doesn't match expected type.
        """
        token = self.advance()
        if token.type not in types:
            expected = ' or '.join(t.name for t in types)
            raise SyntaxError(
                f"Expected {expected}, got {token.type.name} '{token.value}' "
                f"at line {token.line}:{token.col}"
            )
        return token

    def accept(self, *types: TokenType) -> Token | None:
        """Accept a token if it matches, else return None."""
        if self.peek().type in types:
            return self.advance()
        return None

    def parse(self) -> TreeStoreType:
        """Parse all definitions into TreeStore.

        Returns:
            TreeStore populated with RNC definitions.
        """
        self._parse_preamble()
        self._parse_body()
        return self.store

    def _parse_preamble(self):
        """Parse namespace and datatype declarations."""
        while True:
            # Capture doc comments
            while self.peek().type == TokenType.DOCUMENTATION:
                self._current_doc = self.advance().value

            token = self.peek()

            if token.type == TokenType.KEYWORD:
                if token.value == 'default':
                    self._parse_default_namespace()
                elif token.value == 'namespace':
                    self._parse_namespace()
                elif token.value == 'datatypes':
                    self._parse_datatypes()
                else:
                    break
            else:
                break

    def _parse_default_namespace(self):
        """Parse: default namespace = uri"""
        self.expect(TokenType.KEYWORD)  # default
        self.expect(TokenType.KEYWORD)  # namespace
        prefix = ''
        if self.peek().type == TokenType.ID:
            prefix = self.advance().value
        self.expect(TokenType.EQUAL)
        uri = self._parse_literal_or_inherit()
        self.store.set_item('_ns_default', uri, prefix=prefix)

    def _parse_namespace(self):
        """Parse: namespace prefix = uri"""
        self.expect(TokenType.KEYWORD)  # namespace
        prefix = self.expect(TokenType.ID, TokenType.KEYWORD).value
        self.expect(TokenType.EQUAL)
        uri = self._parse_literal_or_inherit()
        self.store.set_item(f'_ns_{prefix}', uri)

    def _parse_datatypes(self):
        """Parse: datatypes prefix = uri"""
        self.expect(TokenType.KEYWORD)  # datatypes
        prefix = self.expect(TokenType.ID, TokenType.KEYWORD).value
        self.expect(TokenType.EQUAL)
        uri = self.expect(TokenType.LITERAL).value
        self.store.set_item(f'_dt_{prefix}', uri)

    def _parse_literal_or_inherit(self) -> str:
        """Parse a literal or 'inherit' keyword."""
        token = self.peek()
        if token.type == TokenType.LITERAL:
            return self.advance().value
        elif token.type == TokenType.KEYWORD and token.value == 'inherit':
            self.advance()
            return 'inherit'
        else:
            return self.expect(TokenType.LITERAL).value

    def _parse_body(self):
        """Parse definitions and grammar content."""
        while self.peek().type != TokenType.EOF:
            # Capture doc comments
            while self.peek().type == TokenType.DOCUMENTATION:
                self._current_doc = self.advance().value

            if self.peek().type == TokenType.EOF:
                break

            self._parse_definition()

    def _parse_definition(self):
        """Parse a definition: name = pattern or name |= pattern"""
        # Skip annotations [...]
        while self.accept(TokenType.LBRACKET):
            self._skip_annotation()

        token = self.peek()

        # Handle start = pattern
        if token.type == TokenType.KEYWORD and token.value == 'start':
            self.advance()
            self.expect(TokenType.EQUAL, TokenType.COMBINE)
            value, attrs = self._parse_pattern()
            self.store.set_item('start', value, **attrs)
            return

        # Handle div { ... }
        if token.type == TokenType.KEYWORD and token.value == 'div':
            self.advance()
            self.expect(TokenType.LBRACE)
            while not self.accept(TokenType.RBRACE):
                self._parse_definition()
            return

        # Handle include "file"
        if token.type == TokenType.KEYWORD and token.value == 'include':
            self.advance()
            uri = self.expect(TokenType.LITERAL).value
            # Skip optional inherit and override block
            if self.peek().type == TokenType.KEYWORD and self.peek().value == 'inherit':
                self.advance()
                self.expect(TokenType.EQUAL)
                self.expect(TokenType.ID, TokenType.KEYWORD)
            if self.accept(TokenType.LBRACE):
                while not self.accept(TokenType.RBRACE):
                    self._parse_definition()
            self.store.set_item(f'_include_{uri}', uri, _type='include')
            return

        # Regular definition: name = pattern
        # Note: keywords like 'list', 'text', 'string', 'start', 'default' can appear
        # as definition names when they're part of a dotted name like 'input.attrs.list'
        if token.type not in (TokenType.ID, TokenType.KEYWORD):
            # Skip unexpected token
            self.advance()
            return

        # Consume name
        name = self.advance().value

        # Check for = or |= or &=
        op_token = self.accept(TokenType.EQUAL, TokenType.COMBINE)
        if not op_token:
            return

        # Parse the pattern
        value, attrs = self._parse_pattern()

        # Add documentation if captured
        if self._current_doc:
            attrs['_doc'] = self._current_doc
            self._current_doc = None

        # Handle combine operators
        if op_token.type == TokenType.COMBINE:
            attrs['_combine'] = op_token.value

        # Store the definition
        self.store.set_item(name, value, **attrs)

    def _skip_annotation(self):
        """Skip annotation content until matching ]"""
        depth = 1
        while depth > 0:
            token = self.advance()
            if token.type == TokenType.LBRACKET:
                depth += 1
            elif token.type == TokenType.RBRACKET:
                depth -= 1
            elif token.type == TokenType.EOF:
                break

    def _parse_pattern(self) -> tuple[str | TreeStoreType, dict]:
        """Parse a pattern expression."""
        return self._parse_choice()

    def _parse_choice(self) -> tuple[str | TreeStoreType, dict]:
        """Parse choice pattern: a | b | c"""
        left, attrs = self._parse_interleave()

        if self.peek().type == TokenType.PIPE:
            choices = self._TreeStore()
            choices.set_item('choice_0', left, **attrs)
            idx = 1

            while self.accept(TokenType.PIPE):
                right, right_attrs = self._parse_interleave()
                choices.set_item(f'choice_{idx}', right, **right_attrs)
                idx += 1

            return choices, {'_combinator': 'choice'}

        return left, attrs

    def _parse_interleave(self) -> tuple[str | TreeStoreType, dict]:
        """Parse interleave pattern: a & b & c"""
        left, attrs = self._parse_sequence()

        if self.peek().type == TokenType.AMP:
            items = self._TreeStore()
            items.set_item('item_0', left, **attrs)
            idx = 1

            while self.accept(TokenType.AMP):
                right, right_attrs = self._parse_sequence()
                items.set_item(f'item_{idx}', right, **right_attrs)
                idx += 1

            return items, {'_combinator': 'interleave'}

        return left, attrs

    def _parse_sequence(self) -> tuple[str | TreeStoreType, dict]:
        """Parse sequence pattern: a, b, c"""
        left, attrs = self._parse_unary()

        if self.peek().type == TokenType.COMMA:
            items = self._TreeStore()
            items.set_item('item_0', left, **attrs)
            idx = 1

            while self.accept(TokenType.COMMA):
                right, right_attrs = self._parse_unary()
                items.set_item(f'item_{idx}', right, **right_attrs)
                idx += 1

            return items, {'_combinator': 'sequence'}

        return left, attrs

    def _parse_unary(self) -> tuple[str | TreeStoreType, dict]:
        """Parse unary pattern with modifiers: primary? | primary* | primary+"""
        value, attrs = self._parse_primary()

        # Check for cardinality modifier
        if self.accept(TokenType.QMARK):
            attrs['optional'] = True
        elif self.accept(TokenType.STAR):
            attrs['multiple'] = True
            attrs['min'] = 0
        elif self.accept(TokenType.PLUS):
            attrs['multiple'] = True
            attrs['min'] = 1

        return value, attrs

    def _parse_primary(self) -> tuple[str | TreeStoreType, dict]:
        """Parse primary expression."""
        attrs: dict = {}

        # Skip annotations
        while self.accept(TokenType.LBRACKET):
            self._skip_annotation()

        token = self.peek()

        # Grouped expression: ( pattern )
        if token.type == TokenType.LPAREN:
            self.advance()
            value, inner_attrs = self._parse_pattern()
            self.expect(TokenType.RPAREN)
            attrs.update(inner_attrs)
            return value, attrs

        # Keywords: element, attribute, etc.
        if token.type == TokenType.KEYWORD:
            keyword = self.advance().value

            if keyword == 'element':
                return self._parse_element()
            elif keyword == 'attribute':
                return self._parse_attribute()
            elif keyword == 'empty':
                return 'empty', {'_type': 'empty'}
            elif keyword == 'text':
                return 'text', {'_type': 'text'}
            elif keyword == 'notAllowed':
                return 'notAllowed', {'_type': 'notAllowed'}
            elif keyword == 'mixed':
                self.expect(TokenType.LBRACE)
                value, inner_attrs = self._parse_pattern()
                self.expect(TokenType.RBRACE)
                inner_attrs['_mixed'] = True
                return value, inner_attrs
            elif keyword == 'list':
                self.expect(TokenType.LBRACE)
                value, inner_attrs = self._parse_pattern()
                self.expect(TokenType.RBRACE)
                inner_attrs['_list'] = True
                return value, inner_attrs
            elif keyword == 'grammar':
                return self._parse_grammar()
            elif keyword == 'external':
                uri = self.expect(TokenType.LITERAL).value
                return uri, {'_type': 'external'}
            elif keyword == 'parent':
                ref = self.expect(TokenType.ID, TokenType.KEYWORD).value
                return ref, {'_type': 'parent_ref'}
            elif keyword in ('string', 'token'):
                # Datatype
                params = None
                if self.peek().type == TokenType.LITERAL:
                    params = self.advance().value
                return keyword, {'_type': 'datatype', '_params': params} if params else {'_type': 'datatype'}
            else:
                return keyword, {'_type': 'keyword'}

        # Qualified name (datatype): prefix:name
        if token.type == TokenType.CNAME:
            cname = self.advance().value
            # Check for literal parameter
            params = None
            if self.peek().type == TokenType.LITERAL:
                params = self.advance().value
            # Check for { param = value } block (datatype parameters)
            if self.accept(TokenType.LBRACE):
                dt_params = self._parse_datatype_params()
                self.expect(TokenType.RBRACE)
                result_attrs = {'_type': 'datatype', '_datatype': cname}
                if params:
                    result_attrs['_params'] = params
                if dt_params:
                    result_attrs['_dt_params'] = dt_params
                return cname, result_attrs
            return cname, {'_type': 'datatype', '_params': params} if params else {'_type': 'datatype'}

        # Literal string
        if token.type == TokenType.LITERAL:
            return self.advance().value, {'_type': 'literal'}

        # Reference (identifier)
        if token.type == TokenType.ID:
            ref = self.advance().value
            return ref, {'_type': 'ref'}

        # If we get here, skip unknown token
        if token.type != TokenType.EOF:
            self.advance()

        return '', attrs

    def _parse_element(self) -> tuple[TreeStoreType, dict]:
        """Parse: element name { pattern }"""
        name, name_attrs = self._parse_name_class()
        self.expect(TokenType.LBRACE)
        content, content_attrs = self._parse_pattern()
        self.expect(TokenType.RBRACE)

        result = self._TreeStore()
        if isinstance(content, self._TreeStore):
            result = content
        else:
            result.set_item('content', content, **content_attrs)

        attrs = {'_type': 'element', '_tag': name}
        attrs.update(name_attrs)
        return result, attrs

    def _parse_attribute(self) -> tuple[str | TreeStoreType, dict]:
        """Parse: attribute name { pattern }"""
        name, name_attrs = self._parse_name_class()
        self.expect(TokenType.LBRACE)
        content, content_attrs = self._parse_pattern()
        self.expect(TokenType.RBRACE)

        attrs = {'_type': 'attribute', '_tag': name}
        attrs.update(name_attrs)
        attrs.update(content_attrs)

        # For attributes, the content is usually a datatype
        return content, attrs

    def _parse_datatype_params(self) -> dict:
        """Parse datatype parameters: { param = value, ... }"""
        params = {}
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            # Expect: name = value
            if self.peek().type in (TokenType.ID, TokenType.KEYWORD):
                name = self.advance().value
                if self.accept(TokenType.EQUAL):
                    # Value can be literal or identifier
                    if self.peek().type == TokenType.LITERAL:
                        params[name] = self.advance().value
                    elif self.peek().type in (TokenType.ID, TokenType.KEYWORD):
                        params[name] = self.advance().value
                    else:
                        params[name] = True
                else:
                    params[name] = True
            else:
                # Skip unexpected token
                self.advance()

            # Optional separator (- is used in some RNC files)
            self.accept(TokenType.MINUS)

        return params

    def _parse_name_class(self) -> tuple[str, dict]:
        """Parse name or name class."""
        attrs: dict = {}
        token = self.peek()

        # Simple name (ID or KEYWORD - keywords can be used as element/attribute names)
        if token.type in (TokenType.ID, TokenType.KEYWORD):
            name = self.advance().value
            # Check for subtraction: name - (exceptions)
            if self.peek().type == TokenType.MINUS:
                self.advance()
                exceptions = self._parse_name_exceptions()
                return name, {'_except': exceptions}
            return name, attrs

        # Qualified name (with optional wildcard like local:*)
        if token.type == TokenType.CNAME:
            name = self.advance().value
            # Check for subtraction: name - (exceptions)
            if self.peek().type == TokenType.MINUS:
                self.advance()
                exceptions = self._parse_name_exceptions()
                return name, {'_except': exceptions}
            return name, attrs

        # Name class in parentheses: (name | name | ...)
        if token.type == TokenType.LPAREN:
            self.advance()
            names = []

            # First name (ID, KEYWORD, CNAME, or STAR all valid)
            if self.peek().type in (TokenType.ID, TokenType.KEYWORD, TokenType.CNAME, TokenType.STAR):
                names.append(self.advance().value)

            # Additional names with |
            while self.accept(TokenType.PIPE):
                if self.peek().type in (TokenType.ID, TokenType.KEYWORD, TokenType.CNAME, TokenType.STAR):
                    names.append(self.advance().value)

            self.expect(TokenType.RPAREN)

            result_name = '|'.join(names) if len(names) > 1 else (names[0] if names else '')
            result_attrs = {'_name_choice': True} if len(names) > 1 else {}

            # Check for subtraction after group
            if self.peek().type == TokenType.MINUS:
                self.advance()
                exceptions = self._parse_name_exceptions()
                result_attrs['_except'] = exceptions

            return result_name, result_attrs

        # Any name: *
        if token.type == TokenType.STAR:
            self.advance()
            # Check for subtraction: * - (exceptions)
            if self.peek().type == TokenType.MINUS:
                self.advance()
                exceptions = self._parse_name_exceptions()
                return '*', {'_any_name': True, '_except': exceptions}
            return '*', {'_any_name': True}

        return '', attrs

    def _parse_name_exceptions(self) -> list[str]:
        """Parse name exceptions: (name | name | ...)"""
        exceptions = []

        if self.accept(TokenType.LPAREN):
            # List of names to exclude (ID, KEYWORD, or CNAME)
            if self.peek().type in (TokenType.ID, TokenType.KEYWORD, TokenType.CNAME):
                exceptions.append(self.advance().value)

            while self.accept(TokenType.PIPE):
                if self.peek().type in (TokenType.ID, TokenType.KEYWORD, TokenType.CNAME):
                    exceptions.append(self.advance().value)

            self.expect(TokenType.RPAREN)
        elif self.peek().type in (TokenType.ID, TokenType.KEYWORD, TokenType.CNAME):
            # Single name exception
            exceptions.append(self.advance().value)

        return exceptions

    def _parse_grammar(self) -> tuple[TreeStoreType, dict]:
        """Parse: grammar { ... }"""
        self.expect(TokenType.LBRACE)

        grammar = self._TreeStore()
        # Save current store and parse into grammar
        outer_store = self.store
        self.store = grammar

        while not self.accept(TokenType.RBRACE):
            if self.peek().type == TokenType.EOF:
                break
            self._parse_definition()

        self.store = outer_store
        return grammar, {'_type': 'grammar'}


def parse_rnc(content: str) -> TreeStoreType:
    """Parse RNC content string into TreeStore.

    Args:
        content: RNC source code as string.

    Returns:
        TreeStore populated with schema definitions.

    Example:
        >>> store = parse_rnc('element div { text }')
        >>> node = store.get_node('start')
    """
    lexer = RncLexer(content)
    tokens = list(lexer.tokenize())
    parser = RncParser(tokens)
    return parser.parse()


def parse_rnc_file(filepath: str | Path) -> TreeStoreType:
    """Parse RNC file into TreeStore.

    Args:
        filepath: Path to .rnc file.

    Returns:
        TreeStore populated with schema definitions.

    Example:
        >>> store = parse_rnc_file('schema/html5/tables.rnc')
        >>> store['table.elem']
    """
    filepath = Path(filepath)
    content = filepath.read_text()
    return parse_rnc(content)
