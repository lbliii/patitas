"""Fast path for simple list parsing.

Bypasses the complex general-purpose list parsing logic for simple cases.

Simple List Criteria (v2 - Extended):
1. All items use the same marker type (all `-`, all `*`, or all `1.`)
2. All items start at column 0 (no nesting from parent)
3. No blank lines between items (tight list) OR single blank between items (uniform)
4. Each item contains only PARAGRAPH_LINE tokens (no sub-blocks)
5. No nested list markers in content
6. No HTML-like content (no `<` at start of paragraph)
7. No code fence markers in content
8. No block quote markers in content

Performance: ~30-50% improvement for list-heavy documents.
"""

from typing import TYPE_CHECKING, Callable

from patitas.nodes import List, ListItem, Paragraph
from patitas.parsing.blocks.list.marker import extract_marker_info
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Inline
    from patitas.tokens import Token


def is_simple_list(tokens: list, start_pos: int) -> bool:
    """Check if the list starting at start_pos qualifies for fast path.

    Pre-scans tokens to determine if all criteria are met.
    This is O(n) but much cheaper than the full parse decision tree.

    Args:
        tokens: Full token list
        start_pos: Position of first LIST_ITEM_MARKER token

    Returns:
        True if list qualifies for fast path
    """
    tokens_len = len(tokens)
    if start_pos >= tokens_len:
        return False

    start_token = tokens[start_pos]
    if start_token.type != TokenType.LIST_ITEM_MARKER:
        return False

    # Must start at column 0
    if start_token.line_indent != 0:
        return False

    # Extract marker info for the first item
    marker_info = extract_marker_info(start_token.value)
    if marker_info.indent != 0:
        return False

    pos = start_pos
    in_item = False

    while pos < tokens_len:
        tok = tokens[pos]

        if tok.type == TokenType.LIST_ITEM_MARKER:
            tok_marker = extract_marker_info(tok.value)

            # Rule 1: Same marker type
            if (
                tok_marker.ordered != marker_info.ordered
                or tok_marker.bullet_char != marker_info.bullet_char
                or tok_marker.ordered_marker_char != marker_info.ordered_marker_char
            ):
                # Different marker - end of this list, OK
                break

            # Rule 2: Column 0 only
            if tok_marker.indent != 0:
                # Nested list marker - not simple
                return False

            in_item = True
            pos += 1
            continue

        if tok.type == TokenType.PARAGRAPH_LINE:
            if not in_item:
                break

            # Rules 5-8: Check for complex content
            content = tok.value.lstrip()
            if _is_complex_content(content):
                return False

            pos += 1
            continue

        if tok.type == TokenType.BLANK_LINE:
            # Blank lines are OK (tight/loose handled in parse)
            pos += 1
            continue

        if tok.type == TokenType.EOF:
            break

        # Any other token type means complex content
        return False

    return in_item  # Must have found at least one item


def parse_simple_list(
    tokens: list,
    start_pos: int,
    parse_inline_fn: Callable[[str, SourceLocation], tuple[Inline, ...]],
) -> tuple[List, int]:
    """Parse a simple list using the fast path.

    PRECONDITION: is_simple_list(tokens, start_pos) returned True.

    Args:
        tokens: Full token list
        start_pos: Position of first LIST_ITEM_MARKER token
        parse_inline_fn: Function to parse inline content

    Returns:
        (List node, new_position after list)
    """
    tokens_len = len(tokens)
    start_token = tokens[start_pos]
    marker_info = extract_marker_info(start_token.value)

    # Collect items with their content spans
    items: list[ListItem] = []
    pos = start_pos
    current_marker_pos: int | None = None
    content_parts: list[str] = []
    has_blank_between = False
    blank_since_last_item = False

    def flush_item() -> None:
        """Finalize the current item."""
        nonlocal content_parts, blank_since_last_item, has_blank_between
        if current_marker_pos is None:
            return

        marker_tok = tokens[current_marker_pos]
        if content_parts:
            content = "\n".join(content_parts)
            inlines = parse_inline_fn(content, marker_tok.location)
            children: tuple = (Paragraph(location=marker_tok.location, children=inlines),)
        else:
            children = ()

        items.append(ListItem(location=marker_tok.location, children=children))

        if blank_since_last_item and len(items) > 1:
            has_blank_between = True

        content_parts = []
        blank_since_last_item = False

    while pos < tokens_len:
        tok = tokens[pos]

        if tok.type == TokenType.LIST_ITEM_MARKER:
            tok_marker = extract_marker_info(tok.value)

            # Check if same list type
            if (
                tok_marker.ordered != marker_info.ordered
                or tok_marker.bullet_char != marker_info.bullet_char
                or tok_marker.ordered_marker_char != marker_info.ordered_marker_char
            ):
                # Different marker - end of list
                flush_item()
                break

            # Flush previous item, start new one
            flush_item()
            current_marker_pos = pos
            pos += 1
            continue

        if tok.type == TokenType.PARAGRAPH_LINE:
            content_parts.append(tok.value.lstrip())
            pos += 1
            continue

        if tok.type == TokenType.BLANK_LINE:
            blank_since_last_item = True
            pos += 1
            continue

        if tok.type == TokenType.EOF:
            flush_item()
            break

        # Unexpected token - end list
        flush_item()
        break

    tight = not has_blank_between

    return (
        List(
            location=start_token.location,
            items=tuple(items),
            ordered=marker_info.ordered,
            start=marker_info.start,
            tight=tight,
        ),
        pos,
    )


def _is_complex_content(content: str) -> bool:
    """Check if paragraph content requires complex parsing.

    Returns True if content contains patterns that need special handling.
    """
    if not content:
        return False

    first_char = content[0]

    # Rule 6: HTML-like content
    if first_char == "<":
        return True

    # Rule 8: Block quote marker
    if first_char == ">":
        return True

    # Rule 5: Nested list marker (unordered)
    if first_char in "-*+":
        if len(content) > 1 and content[1] in " \t":
            return True

    # Rule 5: Ordered list marker (digit followed by . or ))
    if first_char.isdigit():
        pos = 0
        while pos < len(content) and content[pos].isdigit():
            pos += 1
        if pos < len(content) and content[pos] in ".)":
            if pos + 1 < len(content) and content[pos + 1] in " \t":
                return True
            if pos + 1 == len(content):
                return True

    # Rule 7: Code fence markers
    if content.startswith("```") or content.startswith("~~~"):
        return True

    # Rule 7: Potential setext underline (at least 3 chars)
    if len(content) >= 3:
        stripped = content.rstrip()
        if stripped and all(c == "=" for c in stripped):
            return True
        if stripped and all(c == "-" for c in stripped):
            return True

    return False
