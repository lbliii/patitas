"""Token-reuse block quote parsing.

Instead of collecting strings and re-tokenizing, this approach
directly interprets existing tokens for block quote content.

This eliminates the re-tokenization overhead for block quotes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from patitas.nodes import BlockQuote, Paragraph
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block, Inline
    from patitas.tokens import Token


def can_use_token_reuse(tokens: list, start_pos: int) -> bool:
    """Check if block quote can use token reuse optimization.

    Criteria:
    1. Content is simple paragraphs only (no code blocks, lists, etc.)
    2. No lazy continuation (every content line follows a BLOCK_QUOTE_MARKER)
    3. No nested block quotes (>> pattern)

    Args:
        tokens: Full token list
        start_pos: Position of first BLOCK_QUOTE_MARKER

    Returns:
        True if token reuse is applicable
    """
    if start_pos >= len(tokens):
        return False

    first_token = tokens[start_pos]
    if first_token.type != TokenType.BLOCK_QUOTE_MARKER:
        return False

    pos = start_pos
    tokens_len = len(tokens)
    first_lineno = first_token.location.lineno
    last_lineno = first_lineno
    saw_marker_on_line = True  # First token is a marker
    saw_content = False

    while pos < tokens_len:
        tok = tokens[pos]
        token_lineno = tok.location.lineno

        # New line
        if token_lineno != last_lineno:
            if tok.type == TokenType.BLOCK_QUOTE_MARKER:
                # Check for nested quote (second marker on same line as first)
                if pos + 1 < tokens_len:
                    next_tok = tokens[pos + 1]
                    if (
                        next_tok.type == TokenType.BLOCK_QUOTE_MARKER
                        and next_tok.location.lineno == token_lineno
                    ):
                        # Nested >> pattern
                        return False
                saw_marker_on_line = True
                last_lineno = token_lineno
                pos += 1
                continue
            elif tok.type == TokenType.BLANK_LINE:
                # Blank line ends quote (OK)
                break
            else:
                # No marker on new line = lazy continuation (not supported)
                return False

        # Same line as marker
        if tok.type == TokenType.BLOCK_QUOTE_MARKER:
            if saw_marker_on_line:
                # Second marker on same line = nested
                return False
            saw_marker_on_line = True
            pos += 1
            continue

        if tok.type == TokenType.PARAGRAPH_LINE:
            saw_content = True
            # Check for complex content
            content = tok.value.lstrip()
            if _is_complex_blockquote_content(content):
                return False
            last_lineno = token_lineno
            pos += 1
            continue

        if tok.type == TokenType.BLANK_LINE:
            # Blank line ends quote
            break

        if tok.type == TokenType.EOF:
            break

        # Any other token = complex content
        return False

    return saw_content


def parse_blockquote_with_token_reuse(
    tokens: list,
    start_pos: int,
    parse_inline_fn: Callable[[str, SourceLocation], tuple[Inline, ...]],
) -> tuple[BlockQuote, int]:
    """Parse block quote by reusing existing tokens.

    PRECONDITION: can_use_token_reuse(tokens, start_pos) returned True.

    Args:
        tokens: Full token list
        start_pos: Position of first BLOCK_QUOTE_MARKER
        parse_inline_fn: Function to parse inline content

    Returns:
        (BlockQuote node, new position after quote)
    """
    tokens_len = len(tokens)
    first_token = tokens[start_pos]
    first_lineno = first_token.location.lineno

    # Collect content directly from PARAGRAPH_LINE tokens
    content_parts: list[str] = []
    pos = start_pos
    last_lineno = first_lineno
    blank_lines_between = 0

    while pos < tokens_len:
        tok = tokens[pos]
        token_lineno = tok.location.lineno

        if token_lineno != last_lineno:
            if tok.type == TokenType.BLOCK_QUOTE_MARKER:
                last_lineno = token_lineno
                pos += 1
                continue
            elif tok.type == TokenType.BLANK_LINE:
                # Count blank lines for paragraph separation
                blank_lines_between += 1
                pos += 1
                continue
            else:
                # End of quote
                break

        if tok.type == TokenType.BLOCK_QUOTE_MARKER:
            pos += 1
            continue

        if tok.type == TokenType.PARAGRAPH_LINE:
            # Add separator for new paragraph after blank lines
            if blank_lines_between > 0 and content_parts:
                content_parts.append("")  # Empty line = paragraph break
                blank_lines_between = 0
            content_parts.append(tok.value.lstrip())
            last_lineno = token_lineno
            pos += 1
            continue

        if tok.type == TokenType.BLANK_LINE:
            blank_lines_between += 1
            pos += 1
            continue

        if tok.type == TokenType.EOF:
            break

        # End of quote
        break

    # Build paragraph(s) from content
    children: list[Block] = []
    if content_parts:
        # Split on empty lines for multiple paragraphs
        paragraphs: list[list[str]] = [[]]
        for part in content_parts:
            if part == "":
                if paragraphs[-1]:  # Don't add empty paragraphs
                    paragraphs.append([])
            else:
                paragraphs[-1].append(part)

        for para_lines in paragraphs:
            if para_lines:
                content = "\n".join(para_lines)
                inlines = parse_inline_fn(content, first_token.location)
                children.append(Paragraph(location=first_token.location, children=inlines))

    return (
        BlockQuote(location=first_token.location, children=tuple(children)),
        pos,
    )


def _is_complex_blockquote_content(content: str) -> bool:
    """Check if content requires full sub-parser."""
    if not content:
        return False

    first_char = content[0]

    # HTML
    if first_char == "<":
        return True

    # Nested blockquote
    if first_char == ">":
        return True

    # List marker
    if first_char in "-*+":
        if len(content) > 1 and content[1] in " \t":
            return True

    # Ordered list
    if first_char.isdigit():
        pos = 0
        while pos < len(content) and content[pos].isdigit():
            pos += 1
        if pos < len(content) and content[pos] in ".)":
            return True

    # Code fence
    if content.startswith("```") or content.startswith("~~~"):
        return True

    # ATX heading
    if first_char == "#":
        return True

    # Thematic break
    if first_char in "-_*":
        stripped = content.replace(" ", "").replace("\t", "")
        if len(stripped) >= 3 and all(c == stripped[0] for c in stripped):
            return True

    # Indented code (4+ spaces)
    leading = len(content) - len(content.lstrip())
    if leading >= 4:
        return True

    return False
