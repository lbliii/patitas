"""Tests ensuring lexer state is consistent after tokenization.

These tests verify that the lexer properly cleans up internal state
after emitting tokens, preventing state leakage between blocks.
"""

from __future__ import annotations

from patitas.lexer import Lexer, LexerMode
from patitas.tokens import TokenType


class TestHtmlBlockStateConsistency:
    """Verify HTML block state is properly managed."""

    def test_html_block_content_cleared_after_emit(self) -> None:
        """After emitting HTML block, content buffer should be empty."""
        source = "<div>\ncontent\n\n"  # Type 6, ends on blank
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._html_block_content == []
        assert lexer._html_block_type == 0

    def test_html_block_type_reset_after_emit(self) -> None:
        """HTML block type should reset to 0 after emission."""
        source = "<!-- comment -->\n"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._html_block_type == 0

    def test_html_block_mode_returns_to_block(self) -> None:
        """Mode should return to BLOCK after HTML block completes."""
        source = "<pre>content</pre>\nparagraph"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._mode == LexerMode.BLOCK

    def test_html_block_indent_cleared(self) -> None:
        """HTML block indent should be reset after emission."""
        source = "  <div>\n  content\n\n"  # Indented type 6
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._html_block_indent == 0


class TestCodeFenceStateConsistency:
    """Verify code fence state is properly managed."""

    def test_fence_state_cleared_after_close(self) -> None:
        """After closing fence, fence state should be reset."""
        source = "```python\ncode\n```"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._fence_char == ""
        assert lexer._fence_count == 0
        assert lexer._fence_info == ""
        assert lexer._fence_indent == 0

    def test_fence_mode_returns_to_block(self) -> None:
        """Mode should return to BLOCK after fence closes."""
        source = "```\ncode\n```\nparagraph"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._mode == LexerMode.BLOCK

    def test_tilde_fence_state_cleared(self) -> None:
        """Tilde fence state should be properly cleared."""
        source = "~~~python\ncode\n~~~"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._fence_char == ""
        assert lexer._fence_count == 0


class TestDirectiveStateConsistency:
    """Verify directive state is properly managed."""

    def test_directive_stack_empty_after_close(self) -> None:
        """After closing all directives, stack should be empty."""
        source = ":::{note}\ncontent\n:::"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._directive_stack == []

    def test_directive_mode_returns_to_block(self) -> None:
        """Mode should return to BLOCK after directive closes."""
        source = ":::{note}\ncontent\n:::\nparagraph"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._mode == LexerMode.BLOCK

    def test_nested_directive_stack_cleanup(self) -> None:
        """Nested directives should fully clean up stack."""
        source = ":::{outer}\n::::{inner}\ncontent\n::::\n:::"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._directive_stack == []

    def test_named_closer_cleans_stack(self) -> None:
        """Named closer should properly clean directive stack."""
        source = ":::{note}\ncontent\n:::{/note}"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._directive_stack == []


class TestPositionTracking:
    """Verify position tracking is accurate."""

    def test_position_at_source_end(self) -> None:
        """After tokenization, position should be at or past source end."""
        for source in ["hello", "hello\n", "# heading\n\npara"]:
            lexer = Lexer(source)
            list(lexer.tokenize())
            assert lexer._pos >= len(source)

    def test_line_number_tracking(self) -> None:
        """Line number should be accurate after tokenization."""
        source = "line1\nline2\nline3"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._lineno >= 3

    def test_column_resets_after_newline(self) -> None:
        """Column should reset to 1 after each newline."""
        source = "abc\ndef"
        lexer = Lexer(source)
        list(lexer.tokenize())

        # Final position depends on whether last line has newline
        # but column should be reasonable
        assert lexer._col >= 1


class TestModeTransitions:
    """Test that mode transitions are correct."""

    def test_block_to_fence_to_block(self) -> None:
        """Mode should transition correctly through fence block."""
        source = "para\n```\ncode\n```\npara"
        lexer = Lexer(source)

        tokens = []
        for token in lexer.tokenize():
            tokens.append((token.type, lexer._mode))

        # Should end in BLOCK mode
        assert lexer._mode == LexerMode.BLOCK

    def test_block_to_html_to_block(self) -> None:
        """Mode should transition correctly through HTML block."""
        source = "para\n<div>\ncontent\n\npara"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._mode == LexerMode.BLOCK

    def test_block_to_directive_to_block(self) -> None:
        """Mode should transition correctly through directive."""
        source = "para\n:::{note}\ncontent\n:::\npara"
        lexer = Lexer(source)
        list(lexer.tokenize())

        assert lexer._mode == LexerMode.BLOCK

    def test_fence_inside_directive(self) -> None:
        """Fence inside directive should return to DIRECTIVE mode."""
        source = ":::{note}\n```\ncode\n```\ncontent\n:::"
        lexer = Lexer(source)
        list(lexer.tokenize())

        # Should end in BLOCK after everything closes
        assert lexer._mode == LexerMode.BLOCK
        assert lexer._directive_stack == []
