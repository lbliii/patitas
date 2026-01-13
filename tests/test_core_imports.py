"""Verify core module imports work correctly."""

from __future__ import annotations


def test_import_location() -> None:
    """Test SourceLocation import and instantiation."""
    from patitas.location import SourceLocation

    loc = SourceLocation(lineno=1, col_offset=1)
    assert loc.lineno == 1
    assert loc.col_offset == 1
    assert str(loc) == "1:1"


def test_import_tokens() -> None:
    """Test Token and TokenType imports with lazy SourceLocation."""
    from patitas.tokens import Token, TokenType

    # Token now stores raw coordinates and lazily creates SourceLocation
    tok = Token(
        type=TokenType.ATX_HEADING,
        value="# Hello",
        _lineno=1,
        _col=1,
        _start_offset=0,
        _end_offset=7,
    )
    assert tok.type == TokenType.ATX_HEADING
    assert tok.value == "# Hello"
    assert tok.lineno == 1
    assert tok.col == 1
    # Test lazy location creation
    assert tok.location.lineno == 1
    assert tok.location.col_offset == 1
    # Test caching - same object returned
    assert tok.location is tok.location


def test_import_nodes() -> None:
    """Test AST node imports."""
    from patitas.location import SourceLocation
    from patitas.nodes import (
        Heading,
        Text,
    )

    loc = SourceLocation(1, 1)

    # Create simple nodes
    text = Text(location=loc, content="Hello")
    assert text.content == "Hello"

    heading = Heading(location=loc, level=1, children=(text,))
    assert heading.level == 1


def test_import_lexer() -> None:
    """Test Lexer import and basic tokenization."""
    from patitas.lexer import Lexer
    from patitas.tokens import TokenType

    lexer = Lexer("# Hello\n\nWorld")
    tokens = list(lexer.tokenize())

    assert len(tokens) >= 3
    assert tokens[0].type == TokenType.ATX_HEADING
    assert tokens[-1].type == TokenType.EOF


def test_import_stringbuilder() -> None:
    """Test StringBuilder import."""
    from patitas.stringbuilder import StringBuilder

    sb = StringBuilder()
    sb.append("<h1>").append("Hello").append("</h1>")
    assert sb.build() == "<h1>Hello</h1>"


def test_import_directive_options() -> None:
    """Test DirectiveOptions import."""
    from patitas.directives.options import AdmonitionOptions

    opts = AdmonitionOptions.from_raw({"collapsible": "true"})
    assert opts.collapsible is True


def test_import_plugins() -> None:
    """Test plugin system imports."""
    from patitas.plugins import (
        BUILTIN_PLUGINS,
    )

    assert "table" in BUILTIN_PLUGINS
    assert "strikethrough" in BUILTIN_PLUGINS
    assert "math" in BUILTIN_PLUGINS


def test_import_roles() -> None:
    """Test role system imports."""
    from patitas.roles.builtins import (
        DocRole,
        KbdRole,
        RefRole,
    )

    # Verify role classes exist
    assert "ref" in RefRole.names
    assert "doc" in DocRole.names
    assert "kbd" in KbdRole.names


def test_import_parser() -> None:
    """Test Parser import (may be incomplete until Phase 3+)."""
    from patitas.parser import Parser

    # Parser class exists and can be referenced
    assert Parser is not None
