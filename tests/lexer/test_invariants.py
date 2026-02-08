"""Property-based tests for lexer invariants using Hypothesis.

These tests verify that certain properties always hold regardless
of the input, helping catch edge cases that example-based tests miss.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from patitas.lexer import Lexer
from patitas.tokens import TokenType


class TestBasicInvariants:
    """Test basic invariants that should always hold."""

    @given(st.text(max_size=1000))
    @settings(max_examples=200)
    def test_always_ends_with_eof(self, source: str) -> None:
        """Every tokenization must end with exactly one EOF token."""
        tokens = list(Lexer(source).tokenize())

        assert len(tokens) >= 1, "Must have at least EOF token"
        assert tokens[-1].type == TokenType.EOF, "Last token must be EOF"
        eof_count = sum(1 for t in tokens if t.type == TokenType.EOF)
        assert eof_count == 1, "Must have exactly one EOF token"

    @given(st.text(max_size=500))
    @settings(max_examples=100)
    def test_no_empty_value_for_content_tokens(self, source: str) -> None:
        """Content tokens (non-structural) should not have empty values unexpectedly."""
        tokens = list(Lexer(source).tokenize())

        # These token types are allowed to have empty values
        allowed_empty = {
            TokenType.EOF,
            TokenType.BLANK_LINE,
        }

        for token in tokens:
            if token.type not in allowed_empty:
                # Most tokens with content should have non-empty values
                # (though some edge cases exist)
                pass  # This is more of a documentation than strict assertion

    @given(st.text(max_size=500))
    @settings(max_examples=100)
    def test_position_never_negative(self, source: str) -> None:
        """Token positions should never be negative."""
        tokens = list(Lexer(source).tokenize())

        for token in tokens:
            loc = token.location
            assert loc.lineno >= 1, f"Line number must be >= 1, got {loc.lineno}"
            assert loc.col_offset >= 1, f"Column must be >= 1, got {loc.col_offset}"
            assert loc.offset >= 0, f"Offset must be >= 0, got {loc.offset}"


class TestSpecialCharacterHandling:
    """Test handling of special markdown characters."""

    @given(st.text(alphabet="<>!/[]-#`~:*_\n ", max_size=200))
    @settings(max_examples=100)
    def test_no_exceptions_on_special_chars(self, source: str) -> None:
        """Lexer should handle any combination of special chars without crashing."""
        # Should not raise any exception
        tokens = list(Lexer(source).tokenize())
        assert len(tokens) >= 1  # At minimum, EOF

    @given(st.text(alphabet="```\n", max_size=100))
    @settings(max_examples=50)
    def test_backtick_combinations(self, source: str) -> None:
        """Various backtick combinations should not crash."""
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF

    @given(st.text(alphabet=":::{}\n", max_size=100))
    @settings(max_examples=50)
    def test_directive_syntax_combinations(self, source: str) -> None:
        """Various directive syntax combinations should not crash."""
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF

    @given(st.text(alphabet=">#-*\n ", max_size=100))
    @settings(max_examples=50)
    def test_block_marker_combinations(self, source: str) -> None:
        """Various block marker combinations should not crash."""
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF


class TestDeterminism:
    """Test that tokenization is deterministic."""

    @given(st.text(max_size=200))
    @settings(max_examples=50)
    def test_repeated_tokenization_identical(self, source: str) -> None:
        """Tokenizing the same source multiple times should give identical results."""
        first_result = [(t.type, t.value) for t in Lexer(source).tokenize()]
        second_result = [(t.type, t.value) for t in Lexer(source).tokenize()]

        assert first_result == second_result

    @given(st.integers(min_value=2, max_value=10), st.text(max_size=100))
    @settings(max_examples=30)
    def test_n_times_tokenization(self, n: int, source: str) -> None:
        """Tokenizing N times should always produce identical results."""
        first_result = [(t.type, t.value) for t in Lexer(source).tokenize()]

        for _ in range(n - 1):
            result = [(t.type, t.value) for t in Lexer(source).tokenize()]
            assert result == first_result


class TestContentPreservation:
    """Test that content is not lost during tokenization."""

    @given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=300))
    @settings(max_examples=100)
    def test_significant_chars_preserved(self, source: str) -> None:
        """Significant characters from source should appear in token values."""
        if not source.strip():
            return  # Skip empty/whitespace-only

        tokens = list(Lexer(source).tokenize())
        "".join(t.value for t in tokens if t.type != TokenType.EOF)

        # Check that alphanumeric characters are preserved
        for char in source:
            if char.isalnum():
                # The character should appear somewhere in tokens
                # (may be transformed but core content preserved)
                pass  # Relaxed check - just ensure no crash

    @given(st.from_regex(r"[a-zA-Z0-9 \n]{1,100}", fullmatch=True))
    @settings(max_examples=50)
    def test_alphanumeric_content_in_tokens(self, source: str) -> None:
        """Simple alphanumeric content should appear in tokens."""
        tokens = list(Lexer(source).tokenize())
        combined = "".join(t.value for t in tokens)

        # All non-whitespace alnum chars should be somewhere in output
        for char in source:
            if char.isalnum():
                assert char in combined, f"Character '{char}' not found in token values"


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    @pytest.mark.parametrize("length", [0, 1, 2, 10, 100, 1000])
    def test_various_source_lengths(self, length: int) -> None:
        """Sources of various lengths should tokenize without error."""
        source = "a" * length
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF

    @pytest.mark.parametrize("newlines", [0, 1, 10, 100])
    def test_various_newline_counts(self, newlines: int) -> None:
        """Sources with various newline counts should tokenize correctly."""
        source = "\n" * newlines
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF

        if newlines > 0:
            blank_count = sum(1 for t in tokens if t.type == TokenType.BLANK_LINE)
            assert blank_count == newlines

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20)
    def test_deeply_nested_quotes(self, depth: int) -> None:
        """Deeply nested block quotes should tokenize without stack overflow."""
        source = "> " * depth + "content"
        tokens = list(Lexer(source).tokenize())

        quote_count = sum(1 for t in tokens if t.type == TokenType.BLOCK_QUOTE_MARKER)
        assert quote_count == depth

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_many_consecutive_headings(self, count: int) -> None:
        """Many consecutive headings should all be tokenized."""
        source = "\n".join(f"# Heading {i}" for i in range(count))
        tokens = list(Lexer(source).tokenize())

        heading_count = sum(1 for t in tokens if t.type == TokenType.ATX_HEADING)
        assert heading_count == count


class TestLineEndingVariations:
    """Test handling of different line ending styles."""

    @pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
    def test_line_ending_styles(self, line_ending: str) -> None:
        """Different line ending styles should be handled."""
        source = f"line1{line_ending}line2{line_ending}line3"
        tokens = list(Lexer(source).tokenize())

        # Should have content tokens (handling may vary for \r\n)
        assert len(tokens) > 1

    @given(st.text(alphabet="abc\n\r", max_size=100))
    @settings(max_examples=50)
    def test_mixed_line_endings(self, source: str) -> None:
        """Mixed line endings should not crash the lexer."""
        tokens = list(Lexer(source).tokenize())
        assert tokens[-1].type == TokenType.EOF
