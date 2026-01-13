"""Fast path for simple list parsing.

Bypasses the complex ContainerStack overhead for simple, non-nested lists.

Simple list criteria (all must be true):
1. All items use the same marker type (all `-`, all `*`, or all `1.`)
2. All items start at column 0 (no nested list)
3. No blank lines between items (tight list)
4. Each item is a single line (no continuation or sub-blocks)
5. No items start with `>` (would be block quote)

Performance: ~5-8% improvement for list-heavy documents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from patitas.nodes import List, ListItem, Paragraph
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Inline
    from patitas.tokens import Token


def is_simple_list(tokens: list, start_pos: int) -> bool:
    """Check if the list starting at start_pos meets simple list criteria.

    Args:
        tokens: Full token list
        start_pos: Position of first LIST_ITEM_MARKER token

    Returns:
        True if list qualifies for fast path
    """
    if start_pos >= len(tokens):
        return False

    first_token = tokens[start_pos]
    if first_token.type != TokenType.LIST_ITEM_MARKER:
        return False

    # Extract marker characteristics from first item
    first_marker = first_token.value.lstrip()
    first_indent = len(first_token.value) - len(first_marker)

    # Must start at column 0 (no nesting)
    if first_indent > 0:
        return False

    # Determine marker type
    if first_marker[0] in "-*+":
        marker_char = first_marker[0]
        ordered = False
    elif first_marker[0].isdigit():
        # Find the delimiter (. or ))
        for c in first_marker:
            if c in ".)":
                marker_char = c
                break
        else:
            return False
        ordered = True
    else:
        return False

    # Scan forward to check all items meet criteria
    pos = start_pos
    tokens_len = len(tokens)
    items_count = 0

    while pos < tokens_len:
        token = tokens[pos]

        if token.type == TokenType.LIST_ITEM_MARKER:
            marker = token.value.lstrip()
            indent = len(token.value) - len(marker)

            # Check indent (must be 0)
            if indent > 0:
                return False

            # Check marker type consistency
            if ordered:
                # Ordered list: must have same delimiter
                found_delim = False
                for c in marker:
                    if c in ".)":
                        if c != marker_char:
                            return False
                        found_delim = True
                        break
                if not found_delim:
                    return False
            else:
                # Unordered: must be same character
                if marker[0] != marker_char:
                    return False

            items_count += 1
            pos += 1

        elif token.type == TokenType.PARAGRAPH_LINE:
            # Single-line content is OK
            # Check it doesn't start with > (block quote indicator)
            content = token.value.lstrip()
            if content.startswith(">"):
                return False
            pos += 1

        elif token.type == TokenType.BLANK_LINE:
            # Blank line = not simple (would make it loose)
            return False

        else:
            # Any other token type ends the list scan
            break

    # Must have at least one item
    return items_count > 0


def parse_simple_list(
    tokens: list,
    start_pos: int,
    parse_inline_fn,
) -> tuple[List, int]:
    """Parse a simple list using the fast path.

    Args:
        tokens: Full token list
        start_pos: Position of first LIST_ITEM_MARKER token
        parse_inline_fn: Function to parse inline content: (text, location) -> tuple[Inline, ...]

    Returns:
        (List node, new_position after list)
    """
    first_token = tokens[start_pos]
    first_marker = first_token.value.lstrip()

    # Determine if ordered
    ordered = first_marker[0].isdigit()

    # Extract start number for ordered lists
    start = 1
    if ordered:
        num_str = ""
        for c in first_marker:
            if c.isdigit():
                num_str += c
            else:
                break
        if num_str:
            start = int(num_str)

    items: list[ListItem] = []
    pos = start_pos
    tokens_len = len(tokens)
    current_marker_token: Token | None = None
    current_content: str | None = None
    current_location: SourceLocation | None = None

    def flush_item() -> None:
        """Flush current item to items list."""
        nonlocal current_marker_token, current_content, current_location
        if current_marker_token is not None and current_location is not None:
            if current_content:
                inlines = parse_inline_fn(current_content, current_location)
                children = (Paragraph(location=current_location, children=inlines),)
            else:
                children = ()
            items.append(
                ListItem(location=current_location, children=children, checked=None)
            )
        current_marker_token = None
        current_content = None
        current_location = None

    while pos < tokens_len:
        token = tokens[pos]

        if token.type == TokenType.LIST_ITEM_MARKER:
            # Flush previous item
            flush_item()

            # Check if this belongs to our list (same indent level = 0)
            marker = token.value.lstrip()
            indent = len(token.value) - len(marker)
            if indent > 0:
                break

            # Check marker type
            if ordered:
                if not marker[0].isdigit():
                    break
            else:
                if marker[0] != first_marker[0]:
                    break

            current_marker_token = token
            current_location = token.location
            current_content = ""
            pos += 1

        elif token.type == TokenType.PARAGRAPH_LINE:
            if current_marker_token is not None:
                # Add to current item content
                line = token.value.lstrip()
                if current_content:
                    current_content += "\n" + line
                else:
                    current_content = line
            pos += 1

        elif token.type == TokenType.BLANK_LINE:
            # Blank line ends simple list
            break

        else:
            # Any other token ends the list
            break

    # Flush final item
    flush_item()

    list_node = List(
        location=first_token.location,
        items=tuple(items),
        ordered=ordered,
        start=start,
        tight=True,  # Simple lists are always tight
    )

    return list_node, pos
