"""Test unterminated blocks at EOF - ensures content isn't silently lost.

These tests specifically target the bug where HTML block content was
being accumulated but never emitted when the source ended without
the proper closing delimiter.

Regression tests for: HTML block types 1-5 content loss at EOF.
"""

import pytest

from patitas.lexer import Lexer
from patitas.tokens import TokenType


class TestUnterminatedHtmlBlocks:
    """Tests for HTML blocks that aren't properly closed before EOF."""

    @pytest.mark.parametrize("tag", ["pre", "script", "style", "textarea"])
    def test_html_type1_unterminated_at_eof(self, tag: str) -> None:
        """HTML block type 1 content must be emitted even without closing tag."""
        source = f"<{tag}>content without closing"
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1, f"Expected HTML_BLOCK token for <{tag}>"
        assert f"<{tag}>" in html_tokens[0].value
        assert "content without closing" in html_tokens[0].value

    @pytest.mark.parametrize("tag", ["pre", "script", "style", "textarea"])
    def test_html_type1_unterminated_with_newline(self, tag: str) -> None:
        """HTML block type 1 with trailing newline but no closing tag."""
        source = f"<{tag}>content\n"
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1, f"Expected HTML_BLOCK token for <{tag}>"

    @pytest.mark.parametrize(
        "source,name",
        [
            ("<!-- unclosed comment", "type 2 comment"),
            ("<?xml unclosed", "type 3 processing instruction"),
            ("<!DOCTYPE unclosed", "type 4 declaration"),
            ("<![CDATA[ unclosed", "type 5 CDATA"),
        ],
    )
    def test_html_type2_5_unterminated_at_eof(self, source: str, name: str) -> None:
        """HTML block types 2-5 must emit content even without closing delimiter."""
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1, f"Expected HTML_BLOCK for {name}"
        # Content should be preserved
        assert source.split()[0] in html_tokens[0].value

    def test_html_comment_unterminated_multiline(self) -> None:
        """Multi-line HTML comment without --> must preserve all content."""
        source = "<!-- comment\nline 2\nline 3"
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1
        assert "line 2" in html_tokens[0].value
        assert "line 3" in html_tokens[0].value

    def test_html_block_multiline_unterminated(self) -> None:
        """Multi-line HTML block without closing must preserve all lines."""
        source = "<pre>\nline1\nline2\nline3"
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1
        assert "line1" in html_tokens[0].value
        assert "line2" in html_tokens[0].value
        assert "line3" in html_tokens[0].value

    def test_cdata_unterminated_with_content(self) -> None:
        """CDATA section without ]]> should emit all content."""
        source = "<![CDATA[\nsome data\nmore data"
        tokens = list(Lexer(source).tokenize())

        html_tokens = [t for t in tokens if t.type == TokenType.HTML_BLOCK]
        assert len(html_tokens) == 1
        assert "some data" in html_tokens[0].value


class TestUnterminatedCodeFences:
    """Tests for code fences that aren't closed before EOF."""

    def test_code_fence_unterminated_at_eof(self) -> None:
        """Unterminated code fence should still emit content tokens."""
        source = "```python\ncode line 1\ncode line 2"
        tokens = list(Lexer(source).tokenize())

        assert any(t.type == TokenType.FENCED_CODE_START for t in tokens)
        content_tokens = [t for t in tokens if t.type == TokenType.FENCED_CODE_CONTENT]
        assert len(content_tokens) >= 1

    def test_code_fence_unterminated_single_line(self) -> None:
        """Code fence with content on same line, unterminated."""
        source = "```python"
        tokens = list(Lexer(source).tokenize())

        assert any(t.type == TokenType.FENCED_CODE_START for t in tokens)
        assert tokens[-1].type == TokenType.EOF

    def test_tilde_fence_unterminated(self) -> None:
        """Tilde code fence without closing should emit content."""
        source = "~~~\ncode here\nmore code"
        tokens = list(Lexer(source).tokenize())

        assert any(t.type == TokenType.FENCED_CODE_START for t in tokens)
        content_tokens = [t for t in tokens if t.type == TokenType.FENCED_CODE_CONTENT]
        assert len(content_tokens) >= 1


class TestUnterminatedDirectives:
    """Tests for directives that aren't closed before EOF."""

    def test_directive_unterminated_at_eof(self) -> None:
        """Unterminated directive should emit its content."""
        source = ":::{note}\ncontent line"
        tokens = list(Lexer(source).tokenize())

        assert any(t.type == TokenType.DIRECTIVE_OPEN for t in tokens)
        assert any(t.type == TokenType.DIRECTIVE_NAME for t in tokens)
        assert any(t.type == TokenType.PARAGRAPH_LINE for t in tokens)

    def test_nested_directives_unterminated(self) -> None:
        """Nested directives without closing should emit all content."""
        source = ":::{outer}\n::::{inner}\ncontent"
        tokens = list(Lexer(source).tokenize())

        directive_opens = [t for t in tokens if t.type == TokenType.DIRECTIVE_OPEN]
        assert len(directive_opens) == 2

    def test_directive_with_options_unterminated(self) -> None:
        """Directive with options but no closing should emit options."""
        source = ":::{note}\n:class: warning\ncontent"
        tokens = list(Lexer(source).tokenize())

        assert any(t.type == TokenType.DIRECTIVE_OPTION for t in tokens)


class TestEOFEdgeCases:
    """Edge cases around end-of-file handling."""

    def test_empty_source(self) -> None:
        """Empty source should only produce EOF."""
        tokens = list(Lexer("").tokenize())
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_single_newline(self) -> None:
        """Single newline produces BLANK_LINE + EOF."""
        tokens = list(Lexer("\n").tokenize())
        assert tokens[0].type == TokenType.BLANK_LINE
        assert tokens[-1].type == TokenType.EOF

    def test_multiple_newlines(self) -> None:
        """Multiple newlines produce multiple BLANK_LINE tokens."""
        tokens = list(Lexer("\n\n\n").tokenize())
        blank_tokens = [t for t in tokens if t.type == TokenType.BLANK_LINE]
        assert len(blank_tokens) == 3

    def test_no_trailing_newline(self) -> None:
        """Content without trailing newline should be fully captured."""
        source = "paragraph text"
        tokens = list(Lexer(source).tokenize())

        para_tokens = [t for t in tokens if t.type == TokenType.PARAGRAPH_LINE]
        assert len(para_tokens) == 1
        assert "paragraph text" in para_tokens[0].value

    def test_only_whitespace(self) -> None:
        """Whitespace-only content should produce BLANK_LINE."""
        for ws in ["   ", "\t", "  \t  "]:
            tokens = list(Lexer(ws).tokenize())
            assert tokens[0].type == TokenType.BLANK_LINE

    def test_whitespace_then_eof(self) -> None:
        """Trailing whitespace before EOF should be handled."""
        source = "content   "
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF
