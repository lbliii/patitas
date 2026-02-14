"""Ultra-fast parser for simple documents.

Handles documents with only PARAGRAPH_LINE and BLANK_LINE tokens.
Bypasses all block-level decision logic for maximum speed.

This covers 47.5% of CommonMark test cases and likely 60-80% of
real-world documents (prose, comments, simple READMEs).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from patitas.nodes import Paragraph
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block, Inline
    from patitas.tokens import Token


def parse_ultra_simple(
    tokens: list[Token],
    parse_inline_fn: Callable[[str, SourceLocation], tuple[Inline, ...]],
) -> tuple[Block, ...]:
    """Parse document with only paragraphs and blank lines.

    Ultra-fast path: No block-level decisions, no container tracking,
    no indentation analysis. Just split on blank lines and parse inline.

    Args:
        tokens: Token list (must contain only PARAGRAPH_LINE, BLANK_LINE, EOF)
        parse_inline_fn: Function to parse inline content

    Returns:
        Tuple of Paragraph blocks
    """
    blocks: list[Block] = []
    current_lines: list[str] = []
    current_location: SourceLocation | None = None

    for tok in tokens:
        if tok.type == TokenType.PARAGRAPH_LINE:
            if current_location is None:
                current_location = tok.location
            # Strip leading whitespace (CommonMark: leading spaces in paragraphs removed)
            current_lines.append(tok.value.lstrip())

        elif tok.type == TokenType.BLANK_LINE:
            # Flush current paragraph
            if current_lines and current_location is not None:
                content = "\n".join(current_lines).rstrip()
                inlines = parse_inline_fn(content, current_location)
                blocks.append(Paragraph(location=current_location, children=inlines))
                current_lines = []
                current_location = None

        elif tok.type == TokenType.EOF:
            # Final flush
            if current_lines and current_location is not None:
                content = "\n".join(current_lines).rstrip()
                inlines = parse_inline_fn(content, current_location)
                blocks.append(Paragraph(location=current_location, children=inlines))

    return tuple(blocks)


def can_use_ultra_fast(tokens: list[Token]) -> bool:
    """Check if document qualifies for ultra-fast path.

    O(n) check, but very cheap per-token (just type comparison).

    Args:
        tokens: Token list from lexer

    Returns:
        True if only simple PARAGRAPH_LINE, BLANK_LINE, EOF tokens present
    """
    for tok in tokens:
        if tok.type == TokenType.PARAGRAPH_LINE:
            content = tok.value.strip()
            if not content:
                continue

            # Check for setext heading underlines (=== or ---)
            if all(c == "=" for c in content) or all(c == "-" for c in content):
                # Potential setext underline - not ultra-simple
                return False

            # Check for table rows (start with |)
            if content.startswith("|"):
                # Potential table - not ultra-simple
                return False

        elif tok.type not in (TokenType.BLANK_LINE, TokenType.EOF):
            return False
    return True
