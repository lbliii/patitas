"""Fast path for simple block quote parsing.

Bypasses the complex recursive sub-parser overhead for simple block quotes.

Simple block quote criteria (all must be true):
1. No nested block quotes (`>>`)
2. No lazy continuation (every line starts with `>`)
3. Content is simple paragraphs (no lists, code blocks, headings, etc.)
4. No blank lines within the quote (single paragraph)

Performance: ~3-5% improvement for block quote-heavy documents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from patitas.nodes import BlockQuote, Paragraph
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Inline
    from patitas.tokens import Token


def is_simple_block_quote(tokens: list, start_pos: int) -> bool:
    """Check if the block quote starting at start_pos meets simple criteria.

    Args:
        tokens: Full token list
        start_pos: Position of first BLOCK_QUOTE_MARKER token

    Returns:
        True if block quote qualifies for fast path
    """
    if start_pos >= len(tokens):
        return False

    first_token = tokens[start_pos]
    if first_token.type != TokenType.BLOCK_QUOTE_MARKER:
        return False

    first_lineno = first_token.location.lineno
    pos = start_pos + 1  # Skip the first marker
    tokens_len = len(tokens)
    saw_content = False
    last_lineno = first_lineno

    while pos < tokens_len:
        token = tokens[pos]
        token_lineno = token.location.lineno

        # If we're on a new line
        if token_lineno != last_lineno:
            # New line must start with BLOCK_QUOTE_MARKER or we end
            if token.type == TokenType.BLOCK_QUOTE_MARKER:
                # Check for nested quote (>> pattern)
                # Look ahead to see if next token on same line is also a marker
                if pos + 1 < tokens_len:
                    next_tok = tokens[pos + 1]
                    if (
                        next_tok.type == TokenType.BLOCK_QUOTE_MARKER
                        and next_tok.location.lineno == token_lineno
                    ):
                        # Nested block quote - not simple
                        return False
                last_lineno = token_lineno
                pos += 1
                continue
            elif token.type in (TokenType.BLANK_LINE, TokenType.EOF):
                # Blank line or EOF ends the quote - that's OK for simple quote
                break
            else:
                # No > marker on new line = lazy continuation
                # (unless it's a blank line ending the quote)
                return False

        # Check token type for complexity
        if token.type == TokenType.PARAGRAPH_LINE:
            content = token.value
            # Check for 4+ leading spaces (potential indented code)
            stripped = content.lstrip()
            leading_spaces = len(content) - len(stripped)
            if leading_spaces >= 4:
                # Potential indented code - not simple
                return False
            # Check if content starts with < (potential HTML)
            if stripped.startswith("<"):
                # Potential HTML block - not simple
                return False
            saw_content = True
            last_lineno = token_lineno
            pos += 1
        elif token.type == TokenType.BLOCK_QUOTE_MARKER:
            # Another marker on same line = nested
            return False
        elif token.type == TokenType.BLANK_LINE:
            # Blank line within quote = loose quote (not simple)
            return False
        elif token.type in (
            TokenType.ATX_HEADING,
            TokenType.FENCED_CODE_START,
            TokenType.LIST_ITEM_MARKER,
            TokenType.THEMATIC_BREAK,
            TokenType.INDENTED_CODE,
            TokenType.HTML_BLOCK,
            TokenType.LINK_REFERENCE_DEF,
        ):
            # Complex block-level content
            return False
        else:
            # Unknown token - be conservative
            return False

    # Must have at least some content
    return saw_content


def parse_simple_block_quote(
    tokens: list,
    start_pos: int,
    parse_inline_fn,
) -> tuple[BlockQuote, int]:
    """Parse a simple block quote using the fast path.

    Args:
        tokens: Full token list
        start_pos: Position of first BLOCK_QUOTE_MARKER token
        parse_inline_fn: Function to parse inline content: (text, location) -> tuple[Inline, ...]

    Returns:
        (BlockQuote node, new_position after quote)
    """
    first_token = tokens[start_pos]
    # Track paragraphs separately (blank lines create new paragraphs)
    paragraphs: list[list[str]] = [[]]
    pos = start_pos + 1  # Skip first marker
    tokens_len = len(tokens)
    first_lineno = first_token.location.lineno
    last_lineno = first_lineno
    line_had_content = False  # Track if current line has content after marker

    while pos < tokens_len:
        token = tokens[pos]
        token_lineno = token.location.lineno

        # If we're on a new line
        if token_lineno != last_lineno:
            if token.type == TokenType.BLOCK_QUOTE_MARKER:
                # New line with > marker
                # If previous line had no content (just >), it's a blank line in quote
                if not line_had_content and paragraphs[-1]:
                    # Start new paragraph
                    paragraphs.append([])
                line_had_content = False
                last_lineno = token_lineno
                pos += 1
                continue
            else:
                # Quote ends
                break

        # Accumulate content
        if token.type == TokenType.PARAGRAPH_LINE:
            # Strip leading whitespace from content
            paragraphs[-1].append(token.value.lstrip())
            line_had_content = True
            last_lineno = token_lineno
            pos += 1
        elif token.type == TokenType.BLOCK_QUOTE_MARKER:
            # Additional marker on same line (shouldn't happen in simple path)
            last_lineno = token_lineno
            pos += 1
        else:
            # End of quote
            break

    # Build paragraph nodes
    children: list[Paragraph] = []
    for para_lines in paragraphs:
        if para_lines:
            content = "\n".join(para_lines)
            inlines = parse_inline_fn(content, first_token.location)
            children.append(Paragraph(location=first_token.location, children=inlines))

    return BlockQuote(location=first_token.location, children=tuple(children)), pos
