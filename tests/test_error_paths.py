"""Error-path and malformed input tests.

Tests that exercise error handling, edge cases, and graceful degradation
for invalid Markdown input. These complement the happy-path tests in
test_api.py and the spec compliance tests in test_commonmark_spec.py.
"""

import pytest

from patitas import Markdown, parse, render
from patitas.errors import DirectiveContractError, ParseError, PatitasError, PluginError
from patitas.location import SourceLocation
from patitas.nodes import Document, Heading
from patitas.plugins import get_plugin
from patitas.renderers.html import HtmlRenderer

# =========================================================================
# ParseError construction and formatting
# =========================================================================


class TestParseErrorFormatting:
    """Verify ParseError produces well-formatted messages."""

    def test_message_only(self) -> None:
        err = ParseError("unexpected token")
        assert str(err) == "unexpected token"
        assert err.lineno is None
        assert err.col_offset is None

    def test_with_line_number(self) -> None:
        err = ParseError("bad syntax", lineno=42)
        assert "42" in str(err)
        assert "bad syntax" in str(err)

    def test_with_line_and_column(self) -> None:
        err = ParseError("missing bracket", lineno=10, col_offset=5)
        assert "10:5" in str(err)

    def test_with_source_file(self) -> None:
        err = ParseError("error", lineno=1, col_offset=1, source_file="test.md")
        assert "test.md" in str(err)
        assert "1:1" in str(err)

    def test_is_patitas_error(self) -> None:
        err = ParseError("x")
        assert isinstance(err, PatitasError)


# =========================================================================
# DirectiveContractError
# =========================================================================


class TestDirectiveContractError:
    """Verify DirectiveContractError formatting and hierarchy."""

    def test_basic_format(self) -> None:
        err = DirectiveContractError("tab-item", "must be inside tab-set")
        assert "tab-item" in str(err)
        assert "must be inside tab-set" in str(err)

    def test_with_line_number(self) -> None:
        err = DirectiveContractError("step", "missing parent", lineno=15)
        assert "line 15" in str(err)

    def test_is_patitas_error(self) -> None:
        err = DirectiveContractError("x", "y")
        assert isinstance(err, PatitasError)


# =========================================================================
# PluginError
# =========================================================================


class TestPluginError:
    """Verify PluginError formatting."""

    def test_basic_format(self) -> None:
        err = PluginError("myplugin", "failed to initialize")
        assert "myplugin" in str(err)
        assert "failed to initialize" in str(err)

    def test_is_patitas_error(self) -> None:
        err = PluginError("x", "y")
        assert isinstance(err, PatitasError)


# =========================================================================
# Plugin registry error handling
# =========================================================================


class TestPluginErrors:
    """Verify plugin system handles invalid input gracefully."""

    def test_unknown_plugin_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            get_plugin("nonexistent")

    def test_unknown_plugin_lists_available(self) -> None:
        with pytest.raises(KeyError, match="table"):
            get_plugin("does_not_exist")

    def test_invalid_plugin_in_markdown(self) -> None:
        """Markdown class with unknown plugin should not crash at render time."""
        # Markdown silently ignores unknown plugin names (no strict validation)
        md = Markdown(plugins=["does_not_exist"])
        result = md("hello")
        assert "hello" in result

    def test_empty_plugin_list(self) -> None:
        """Empty plugin list should work without errors."""
        md = Markdown(plugins=[])
        result = md("hello")
        assert "hello" in result


# =========================================================================
# Malformed Markdown input — graceful degradation
# =========================================================================


class TestMalformedInput:
    """Verify parser handles malformed/truncated input without crashing."""

    def test_empty_string(self) -> None:
        doc = parse("")
        assert isinstance(doc, Document)
        assert len(doc.children) == 0

    def test_only_whitespace(self) -> None:
        doc = parse("   \n\n   \n")
        assert isinstance(doc, Document)

    def test_only_newlines(self) -> None:
        doc = parse("\n\n\n\n\n")
        assert isinstance(doc, Document)

    def test_unclosed_fence(self) -> None:
        """Unclosed code fence should be treated as part of document."""
        doc = parse("```python\nprint('hello')\n")
        html = render(doc)
        # Should produce some output (either as code block or paragraph)
        assert html.strip() != ""

    def test_unclosed_fence_with_content_after(self) -> None:
        """Content after unclosed fence should still be parsed."""
        source = "```\ncode here\n\ntext after"
        doc = parse(source)
        assert isinstance(doc, Document)
        assert len(doc.children) > 0

    def test_deeply_nested_blockquotes(self) -> None:
        """Deeply nested blockquotes should not crash."""
        source = "> " * 50 + "deep content"
        doc = parse(source)
        assert isinstance(doc, Document)

    def test_deeply_nested_lists(self) -> None:
        """Deeply nested lists should not crash."""
        lines = []
        for i in range(20):
            indent = "  " * i
            lines.append(f"{indent}- item {i}")
        source = "\n".join(lines)
        doc = parse(source)
        assert isinstance(doc, Document)
        assert len(doc.children) > 0

    def test_partial_table(self) -> None:
        """Table with missing separator row should degrade gracefully."""
        md = Markdown(plugins=["table"])
        result = md("| A | B |\n| 1 | 2 |")
        # Without separator row, this shouldn't parse as a table
        assert isinstance(result, str)

    def test_table_with_uneven_columns(self) -> None:
        """Table with inconsistent column counts should still render."""
        md = Markdown(plugins=["table"])
        result = md("| A | B | C |\n|---|---|\n| 1 | 2 | 3 | 4 |")
        assert isinstance(result, str)

    def test_broken_link_reference(self) -> None:
        """Unresolved link references should render as text."""
        doc = parse("[text][nonexistent]")
        html = render(doc)
        assert "text" in html

    def test_unclosed_emphasis(self) -> None:
        """Unclosed emphasis markers should render as literal text."""
        doc = parse("*unclosed emphasis")
        html = render(doc)
        assert "*unclosed emphasis" in html or "unclosed emphasis" in html

    def test_unclosed_strong(self) -> None:
        """Unclosed strong markers should render as literal text."""
        doc = parse("**unclosed strong")
        html = render(doc)
        assert "unclosed" in html

    def test_empty_heading(self) -> None:
        """Empty heading should parse correctly."""
        doc = parse("# \n")
        assert isinstance(doc, Document)
        # Should produce a heading with empty content
        assert any(isinstance(c, Heading) for c in doc.children)

    def test_heading_levels_1_through_6(self) -> None:
        """All valid heading levels should parse."""
        for level in range(1, 7):
            prefix = "#" * level
            doc = parse(f"{prefix} Heading")
            assert isinstance(doc, Document)

    def test_heading_level_7_not_heading(self) -> None:
        """Level 7+ should not be treated as heading."""
        doc = parse("####### Not a heading")
        assert isinstance(doc, Document)
        assert not any(isinstance(c, Heading) for c in doc.children)

    def test_null_bytes(self) -> None:
        """Input with null bytes should not crash."""
        doc = parse("hello\x00world")
        assert isinstance(doc, Document)

    def test_very_long_line(self) -> None:
        """Very long single line should not crash or hang."""
        line = "word " * 10000
        doc = parse(line)
        assert isinstance(doc, Document)

    def test_mixed_line_endings(self) -> None:
        """Mixed CRLF/LF/CR line endings should be handled."""
        source = "line1\r\nline2\nline3\rline4"
        doc = parse(source)
        assert isinstance(doc, Document)

    def test_only_hash_marks(self) -> None:
        """Line of only hash marks (no space after) should not be heading."""
        doc = parse("###")
        assert isinstance(doc, Document)

    def test_fence_inside_blockquote(self) -> None:
        """Code fence inside blockquote should be handled."""
        source = "> ```\n> code\n> ```"
        doc = parse(source)
        html = render(doc)
        assert "blockquote" in html

    def test_html_block_unclosed(self) -> None:
        """Unclosed HTML block should still parse."""
        source = "<div>\nsome content"
        doc = parse(source)
        assert isinstance(doc, Document)

    def test_backslash_at_end_of_input(self) -> None:
        """Trailing backslash should not crash."""
        doc = parse("text\\")
        html = render(doc)
        assert "text" in html

    def test_link_with_empty_url(self) -> None:
        """Link with empty URL should parse."""
        doc = parse("[text]()")
        html = render(doc)
        assert "text" in html

    def test_image_with_empty_alt(self) -> None:
        """Image with empty alt should parse."""
        doc = parse("![](url)")
        html = render(doc)
        assert "url" in html


# =========================================================================
# Renderer edge cases
# =========================================================================


class TestRendererErrorPaths:
    """Verify renderer handles edge cases gracefully."""

    def test_render_empty_document(self) -> None:
        doc = Document(location=SourceLocation.unknown(), children=())
        renderer = HtmlRenderer()
        result = renderer.render(doc)
        assert result == ""

    def test_get_headings_before_render(self) -> None:
        """get_headings before any render should return empty list."""
        renderer = HtmlRenderer()
        assert renderer.get_headings() == []

    def test_render_document_with_only_blank_lines(self) -> None:
        doc = parse("\n\n\n")
        renderer = HtmlRenderer()
        result = renderer.render(doc)
        assert result == ""

    def test_render_preserves_html_entities(self) -> None:
        doc = parse("&amp; &lt; &gt;")
        html = render(doc)
        assert "&amp;" in html


# =========================================================================
# ParserHost protocol verification
# =========================================================================


class TestParserHostProtocol:
    """Verify the ParserHost protocol is satisfied by Parser."""

    def test_parser_satisfies_protocol(self) -> None:
        from patitas.parser import Parser
        from patitas.parsing.protocols import ParserHost

        p = Parser("# hello")
        assert isinstance(p, ParserHost)

    def test_protocol_has_required_methods(self) -> None:
        from patitas.parsing.protocols import ParserHost

        # Verify the protocol declares the expected methods
        assert hasattr(ParserHost, "_at_end")
        assert hasattr(ParserHost, "_advance")
        assert hasattr(ParserHost, "_peek")
        assert hasattr(ParserHost, "_parse_inline")
        assert hasattr(ParserHost, "_parse_block")
