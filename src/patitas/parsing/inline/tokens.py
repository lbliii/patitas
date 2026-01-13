"""Typed inline tokens for Patitas parser.

Uses NamedTuples for inline token representation, providing:
- Immutability by default (required for external match tracking)
- Tuple unpacking support
- Lower memory footprint (~80 bytes vs ~200 for dict)
- Faster attribute access (tuple index vs hash lookup)
- Full type safety with IDE autocomplete

Thread Safety:
All tokens are immutable and safe to share across threads.

Usage:
from patitas.parsing.inline.tokens import (
    DelimiterToken,
    TextToken,
    InlineToken,
)

    token = DelimiterToken(char="*", count=2, can_open=True, can_close=False)
match token:
    case DelimiterToken(char="*", count=count):
        print(f"Asterisk delimiter with count {count}")

"""

from __future__ import annotations

from typing import Literal, NamedTuple

# Inline token type tags for O(1) dispatch
TOKEN_TEXT = 0
TOKEN_DELIMITER = 1
TOKEN_CODE_SPAN = 2
TOKEN_NODE = 3
TOKEN_HARD_BREAK = 4
TOKEN_SOFT_BREAK = 5

# PEP 695 type alias for delimiter characters
type DelimiterChar = Literal["*", "_", "~"]


class DelimiterToken(NamedTuple):
    """Delimiter token for emphasis/strikethrough processing.

    Attributes:
        char: DelimiterChar
        run_length: int
        can_open: bool
        can_close: bool
        tag: int = TOKEN_DELIMITER
    """

    char: DelimiterChar
    run_length: int
    can_open: bool
    can_close: bool
    tag: int = TOKEN_DELIMITER

    @property
    def type(self) -> Literal["delimiter"]:
        """Token type identifier for dispatch."""
        return "delimiter"

    @property
    def original_count(self) -> int:
        """Original count (same as run_length for immutable tokens)."""
        return self.run_length


class TextToken(NamedTuple):
    """Plain text token."""

    content: str
    tag: int = TOKEN_TEXT

    @property
    def type(self) -> Literal["text"]:
        """Token type identifier for dispatch."""
        return "text"


class CodeSpanToken(NamedTuple):
    """Inline code span token."""

    code: str
    tag: int = TOKEN_CODE_SPAN

    @property
    def type(self) -> Literal["code_span"]:
        """Token type identifier for dispatch."""
        return "code_span"


class NodeToken(NamedTuple):
    """Pre-parsed AST node token (links, images, etc.)."""

    node: object  # Inline node type
    tag: int = TOKEN_NODE

    @property
    def type(self) -> Literal["node"]:
        """Token type identifier for dispatch."""
        return "node"


class HardBreakToken(NamedTuple):
    """Hard line break token."""

    tag: int = TOKEN_HARD_BREAK

    @property
    def type(self) -> Literal["hard_break"]:
        """Token type identifier for dispatch."""
        return "hard_break"


class SoftBreakToken(NamedTuple):
    """Soft line break token."""

    tag: int = TOKEN_SOFT_BREAK

    @property
    def type(self) -> Literal["soft_break"]:
        """Token type identifier for dispatch."""
        return "soft_break"


# PEP 695 type alias for all inline tokens
type InlineToken = (
    DelimiterToken | TextToken | CodeSpanToken | NodeToken | HardBreakToken | SoftBreakToken
)


__all__ = [
    "DelimiterChar",
    "DelimiterToken",
    "TextToken",
    "CodeSpanToken",
    "NodeToken",
    "HardBreakToken",
    "SoftBreakToken",
    "InlineToken",
]
