"""Tests for accurate source location tracking in the lexer.

Token locations are critical for error messages, IDE integration,
and source mapping. These tests verify that line numbers, column
offsets, and byte offsets are correctly tracked.
"""

from patitas.lexer import Lexer
from patitas.tokens import TokenType


class TestSingleLineLocations:
    """Test location tracking for single-line tokens."""

    def test_heading_location(self) -> None:
        """ATX heading should have correct location."""
        source = "# Heading"
        tokens = list(Lexer(source).tokenize())

        heading = tokens[0]
        assert heading.type == TokenType.ATX_HEADING
        assert heading.location.lineno == 1
        assert heading.location.col_offset == 1

    def test_paragraph_location(self) -> None:
        """Paragraph line should have correct location."""
        source = "paragraph text"
        tokens = list(Lexer(source).tokenize())

        para = tokens[0]
        assert para.type == TokenType.PARAGRAPH_LINE
        assert para.location.lineno == 1
        assert para.location.col_offset == 1

    def test_thematic_break_location(self) -> None:
        """Thematic break should have correct location."""
        source = "---"
        tokens = list(Lexer(source).tokenize())

        hr = tokens[0]
        assert hr.type == TokenType.THEMATIC_BREAK
        assert hr.location.lineno == 1
        assert hr.location.col_offset == 1

    def test_indented_content_location(self) -> None:
        """Indented code should have correct location."""
        source = "    code"
        tokens = list(Lexer(source).tokenize())

        code = tokens[0]
        assert code.type == TokenType.INDENTED_CODE
        assert code.location.lineno == 1


class TestMultilineLocations:
    """Test location tracking for tokens across multiple lines."""

    def test_consecutive_paragraphs(self) -> None:
        """Consecutive paragraph lines should have incrementing line numbers."""
        source = "line1\nline2\nline3"
        tokens = list(Lexer(source).tokenize())

        para_tokens = [t for t in tokens if t.type == TokenType.PARAGRAPH_LINE]
        assert len(para_tokens) == 3
        assert para_tokens[0].location.lineno == 1
        assert para_tokens[1].location.lineno == 2
        assert para_tokens[2].location.lineno == 3

    def test_blank_lines_between_content(self) -> None:
        """Blank lines should have correct line numbers."""
        source = "para1\n\npara2"
        tokens = list(Lexer(source).tokenize())

        blank = next(t for t in tokens if t.type == TokenType.BLANK_LINE)
        assert blank.location.lineno == 2

    def test_code_fence_locations(self) -> None:
        """Code fence tokens should have correct locations."""
        source = "```python\ncode\n```"
        tokens = list(Lexer(source).tokenize())

        fence_start = next(t for t in tokens if t.type == TokenType.FENCED_CODE_START)
        fence_content = next(t for t in tokens if t.type == TokenType.FENCED_CODE_CONTENT)
        fence_end = next(t for t in tokens if t.type == TokenType.FENCED_CODE_END)

        assert fence_start.location.lineno == 1
        assert fence_content.location.lineno == 2
        assert fence_end.location.lineno == 3


class TestOffsetTracking:
    """Test byte offset tracking."""

    def test_start_offset_zero_for_first_token(self) -> None:
        """First token should start at offset 0."""
        source = "content"
        tokens = list(Lexer(source).tokenize())

        assert tokens[0].location.offset == 0

    def test_eof_offset_at_source_end(self) -> None:
        """EOF token should have offset at source end."""
        source = "abc"
        tokens = list(Lexer(source).tokenize())

        eof = tokens[-1]
        assert eof.type == TokenType.EOF
        assert eof.location.offset == len(source)

    def test_offsets_increase_monotonically(self) -> None:
        """Token start offsets should generally increase."""
        source = "# Heading\n\nParagraph"
        tokens = list(Lexer(source).tokenize())

        offsets = [t.location.offset for t in tokens]
        # Note: Some tokens may have same start if they come from same line
        # but they shouldn't decrease
        for i in range(1, len(offsets)):
            assert offsets[i] >= offsets[i - 1]


class TestEOFLocation:
    """Test EOF token location in various scenarios."""

    def test_eof_after_content(self) -> None:
        """EOF after content should be at end of source."""
        source = "content"
        tokens = list(Lexer(source).tokenize())

        eof = tokens[-1]
        assert eof.location.lineno == 1
        assert eof.location.offset == 7

    def test_eof_after_newline(self) -> None:
        """EOF after newline should be on next line."""
        source = "content\n"
        tokens = list(Lexer(source).tokenize())

        eof = tokens[-1]
        assert eof.location.lineno == 2
        assert eof.location.col_offset == 1

    def test_eof_empty_source(self) -> None:
        """EOF on empty source should be at line 1, col 1."""
        source = ""
        tokens = list(Lexer(source).tokenize())

        eof = tokens[0]
        assert eof.location.lineno == 1
        assert eof.location.col_offset == 1
        assert eof.location.offset == 0


class TestSourceFileTracking:
    """Test source file path is correctly propagated to tokens."""

    def test_source_file_in_token(self) -> None:
        """Tokens should include source file if provided."""
        source = "content"
        lexer = Lexer(source, source_file="test.md")
        tokens = list(lexer.tokenize())

        for token in tokens:
            assert token.location.source_file == "test.md"

    def test_no_source_file(self) -> None:
        """Tokens should have None source file if not provided."""
        source = "content"
        tokens = list(Lexer(source).tokenize())

        for token in tokens:
            assert token.location.source_file is None


class TestSpecialCharacterLocations:
    """Test location tracking with special characters."""

    def test_tab_in_content(self) -> None:
        """Tabs should be handled in location tracking."""
        source = "\tcontent"
        tokens = list(Lexer(source).tokenize())

        # Content is indented, should still start at line 1
        assert tokens[0].location.lineno == 1

    def test_unicode_content(self) -> None:
        """Unicode content should have correct locations."""
        source = "héllo wörld"
        tokens = list(Lexer(source).tokenize())

        assert tokens[0].location.lineno == 1
        assert tokens[0].location.col_offset == 1

    def test_emoji_content(self) -> None:
        """Emoji content should not break location tracking."""
        source = "Hello 👋 World"
        tokens = list(Lexer(source).tokenize())

        assert tokens[0].location.lineno == 1


class TestEndLocationTracking:
    """Test end line/column tracking for tokens."""

    def test_single_line_token_end(self) -> None:
        """Single-line token should have matching end line."""
        source = "# Heading"
        tokens = list(Lexer(source).tokenize())

        heading = tokens[0]
        # End should be on same line or next if newline consumed
        assert heading.location.end_lineno is not None
        assert heading.location.end_lineno >= heading.location.lineno

    def test_multiline_code_block_end(self) -> None:
        """Multi-line code block content should span lines."""
        source = "```\nline1\nline2\n```"
        tokens = list(Lexer(source).tokenize())

        # The fence end token should be on line 4
        fence_end = next(t for t in tokens if t.type == TokenType.FENCED_CODE_END)
        assert fence_end.location.lineno == 4
