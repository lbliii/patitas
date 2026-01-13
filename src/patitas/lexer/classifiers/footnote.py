"""Footnote definition classifier mixin."""

from __future__ import annotations

from patitas.tokens import Token, TokenType


class FootnoteClassifierMixin:
    """Mixin providing footnote definition classification."""

    def _make_token(
        self,
        token_type: TokenType,
        value: str,
        start_pos: int,
        *,
        start_col: int | None = None,
        end_pos: int | None = None,
        line_indent: int = -1,
    ) -> Token:
        """Create token with raw coordinates. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_footnote_def(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as footnote definition.

        Format: [^identifier]: content

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Returns:
            FOOTNOTE_DEF token if valid, None otherwise.
            Token value format: identifier:content
        """
        if not content.startswith("[^"):
            return None

        # Find ]: after identifier
        bracket_end = content.find("]:")
        if bracket_end == -1 or bracket_end < 3:
            return None

        identifier = content[2:bracket_end]
        if not identifier:
            return None

        # Identifier must be alphanumeric with dashes/underscores
        if not all(c.isalnum() or c in "-_" for c in identifier):
            return None

        # Content after ]: (may be empty, with content on following lines)
        fn_content = content[bracket_end + 2 :].strip().rstrip("\n")

        # Value format: identifier:content
        value = f"{identifier}:{fn_content}"
        return self._make_token(TokenType.FOOTNOTE_DEF, value, line_start, line_indent=indent)
