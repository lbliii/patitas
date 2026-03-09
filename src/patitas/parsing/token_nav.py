"""Token navigation utilities for Patitas parser.

Provides mixin for token stream navigation and basic parsing operations.
"""

import bisect
from typing import TYPE_CHECKING

from patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Sequence


class TokenNavigationMixin:
    """Mixin providing token stream navigation methods.

    Required Host Attributes:
        - _tokens: Sequence[Token]
        - _tokens_len: int (cached len(_tokens) for hot loops)
        - _pos: int
        - _current: Token | None
        - _source: str
        - _line_starts: list[int] | None (lazy line index for O(log n) boundary lookup)

    """

    _tokens: Sequence[Token]
    _pos: int
    _current: Token | None
    _source: str

    def _at_end(self) -> bool:
        """Check if at end of token stream."""
        return self._current is None or self._current.type == TokenType.EOF

    def _advance(self) -> Token | None:
        """Advance to next token and return it."""
        self._pos += 1
        if self._pos < self._tokens_len:
            self._current = self._tokens[self._pos]
        else:
            self._current = None
        return self._current

    def _peek(self, offset: int = 1) -> Token | None:
        """Peek at token at offset from current position."""
        pos = self._pos + offset
        if pos < self._tokens_len:
            return self._tokens[pos]
        return None

    def _line_start_for_offset(self, offset: int) -> int:
        """Get start offset of line containing offset. O(log n) with lazy line index."""
        if self._line_starts is None:
            line_starts = [0]
            for i, c in enumerate(self._source):
                if c == "\n":
                    line_starts.append(i + 1)
            self._line_starts = line_starts
        idx = bisect.bisect_right(self._line_starts, offset) - 1
        return self._line_starts[idx] if idx >= 0 else 0

    def _get_line_at(self, offset: int) -> str:
        """Get the full line content containing the given source offset."""
        start = self._line_start_for_offset(offset)
        end = self._source.find("\n", offset)
        if end == -1:
            end = len(self._source)
        return self._source[start:end]

    def _strip_columns(self, text: str, count: int) -> str:
        """Strip up to 'count' columns of whitespace/tabs from start of text."""
        col = 0
        pos = 0
        while pos < len(text) and col < count:
            char = text[pos]
            if char == " ":
                col += 1
                pos += 1
            elif char == "\t":
                expansion = 4 - (col % 4)
                if col + expansion <= count:
                    col += expansion
                    pos += 1
                else:
                    # Partial tab consumption
                    needed = count - col
                    return " " * (expansion - needed) + text[pos + 1 :]
            else:
                break
        return text[pos:]
