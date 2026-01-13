"""Pattern-specific optimized parsers.

Each parser is tailored for a specific token pattern, eliminating
unnecessary branching and checks.

Top 10 patterns cover 79.1% of CommonMark spec:
1. (PARAGRAPH_LINE,)                                    45.7%  ← ultra_fast.py
2. (BLANK_LINE, LINK_REFERENCE_DEF, PARAGRAPH_LINE)     10.7%  ← parse_linkref_paragraphs
3. (HTML_BLOCK,)                                         3.7%  ← parse_html_only
4. (LIST_ITEM_MARKER, PARAGRAPH_LINE)                    3.5%  ← parse_simple_flat_list
5. (BLANK_LINE, INDENTED_CODE, LIST_ITEM_MARKER, ...)    3.1%  ← (complex)
6. (BLANK_LINE, PARAGRAPH_LINE)                          3.1%  ← parse_paragraphs_with_blanks
7. (FENCED_CODE_CONTENT, FENCED_CODE_END, ...)           2.9%  ← parse_fenced_code_only
8. (BLANK_LINE, LIST_ITEM_MARKER, PARAGRAPH_LINE)        2.3%  ← parse_simple_list_with_blanks
9. (ATX_HEADING,)                                        2.1%  ← parse_atx_only
10. (INDENTED_CODE,)                                     2.0%  ← parse_indented_only
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from patitas.nodes import (
    Block,
    FencedCode,
    Heading,
    HtmlBlock,
    IndentedCode,
    List,
    ListItem,
    Paragraph,
)
from patitas.parsing.blocks.list.marker import extract_marker_info
from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Inline
    from patitas.tokens import Token


def parse_html_only(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 3: (HTML_BLOCK,) - 3.7% of examples.
    
    Just HTML blocks, no other content.
    """
    blocks: list[Block] = []
    for tok in tokens:
        if tok.type == TokenType.HTML_BLOCK:
            blocks.append(HtmlBlock(location=tok.location, html=tok.value))
    return tuple(blocks)


def parse_atx_only(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 9: (ATX_HEADING,) - 2.1% of examples.
    
    Just ATX headings, no other content.
    """
    blocks: list[Block] = []
    for tok in tokens:
        if tok.type == TokenType.ATX_HEADING:
            # ATX_HEADING value format: "### content" (raw markdown)
            value = tok.value
            # Count leading hashes for level
            level = 0
            for ch in value:
                if ch == "#":
                    level += 1
                else:
                    break
            # Extract content after hashes (strip whitespace only)
            content = value[level:].strip()
            inlines = parse_inline_fn(content, tok.location)
            blocks.append(Heading(
                location=tok.location,
                level=level,
                children=inlines,
                style="atx",
            ))
    return tuple(blocks)


def parse_indented_only(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 10: (INDENTED_CODE,) - 2.0% of examples.
    
    Just indented code blocks, no other content.
    """
    blocks: list[Block] = []
    code_lines: list[str] = []
    first_location = None
    
    for tok in tokens:
        if tok.type == TokenType.INDENTED_CODE:
            if first_location is None:
                first_location = tok.location
            # Token value already includes trailing newline
            code_lines.append(tok.value)
        elif tok.type == TokenType.EOF:
            if code_lines and first_location:
                # Concatenate directly - values already have newlines
                content = "".join(code_lines)
                blocks.append(IndentedCode(location=first_location, code=content))
    
    return tuple(blocks)


def parse_fenced_code_only(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 7: (FENCED_CODE_*) - 2.9% of examples.
    
    Just fenced code blocks, no other content.
    """
    blocks: list[Block] = []
    in_fence = False
    fence_location = None
    fence_info = ""
    fence_lang = ""
    code_lines: list[str] = []
    
    for tok in tokens:
        if tok.type == TokenType.FENCED_CODE_START:
            in_fence = True
            fence_location = tok.location
            # Parse info string (language)
            fence_info = tok.value.strip()
            fence_lang = fence_info.split()[0] if fence_info else ""
            code_lines = []
        elif tok.type == TokenType.FENCED_CODE_CONTENT:
            if in_fence:
                code_lines.append(tok.value)
        elif tok.type == TokenType.FENCED_CODE_END:
            if in_fence and fence_location:
                content = "\n".join(code_lines)
                if code_lines and not content.endswith("\n"):
                    content += "\n"
                blocks.append(FencedCode(
                    location=fence_location,
                    content=content,
                    info_string=fence_info,
                    language=fence_lang,
                ))
            in_fence = False
            fence_location = None
    
    return tuple(blocks)


def parse_paragraphs_with_blanks(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 6: (BLANK_LINE, PARAGRAPH_LINE) - 3.1% of examples.
    
    Paragraphs separated by blank lines.
    """
    blocks: list[Block] = []
    current_lines: list[str] = []
    current_location = None
    
    for tok in tokens:
        if tok.type == TokenType.PARAGRAPH_LINE:
            if current_location is None:
                current_location = tok.location
            current_lines.append(tok.value.lstrip())
        elif tok.type == TokenType.BLANK_LINE:
            if current_lines and current_location:
                content = "\n".join(current_lines).rstrip()
                inlines = parse_inline_fn(content, current_location)
                blocks.append(Paragraph(location=current_location, children=inlines))
                current_lines = []
                current_location = None
        elif tok.type == TokenType.EOF:
            if current_lines and current_location:
                content = "\n".join(current_lines).rstrip()
                inlines = parse_inline_fn(content, current_location)
                blocks.append(Paragraph(location=current_location, children=inlines))
    
    return tuple(blocks)


def parse_simple_flat_list(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 4: (LIST_ITEM_MARKER, PARAGRAPH_LINE) - 3.5% of examples.
    
    Simple flat list with no nesting, no blank lines.
    """
    items: list[ListItem] = []
    current_marker = None
    current_content: list[str] = []
    list_location = None
    ordered = False
    start = 1
    
    for tok in tokens:
        if tok.type == TokenType.LIST_ITEM_MARKER:
            # Flush previous item
            if current_marker is not None:
                if current_content:
                    content = "\n".join(current_content).rstrip()
                    inlines = parse_inline_fn(content, current_marker.location)
                    children: tuple[Block, ...] = (Paragraph(location=current_marker.location, children=inlines),)
                else:
                    children = ()
                items.append(ListItem(location=current_marker.location, children=children))
            
            current_marker = tok
            current_content = []
            
            if list_location is None:
                list_location = tok.location
                marker_info = extract_marker_info(tok.value)
                ordered = marker_info.ordered
                start = marker_info.start
                
        elif tok.type == TokenType.PARAGRAPH_LINE:
            if current_marker is not None:
                current_content.append(tok.value.lstrip())
        elif tok.type == TokenType.EOF:
            # Flush last item
            if current_marker is not None:
                if current_content:
                    content = "\n".join(current_content).rstrip()
                    inlines = parse_inline_fn(content, current_marker.location)
                    children = (Paragraph(location=current_marker.location, children=inlines),)
                else:
                    children = ()
                items.append(ListItem(location=current_marker.location, children=children))
    
    if not items or list_location is None:
        return ()
    
    return (List(
        location=list_location,
        items=tuple(items),
        ordered=ordered,
        start=start,
        tight=True,
    ),)


def parse_simple_list_with_blanks(
    tokens: list,
    parse_inline_fn: Callable,
) -> tuple[Block, ...]:
    """Pattern 8: (BLANK_LINE, LIST_ITEM_MARKER, PARAGRAPH_LINE) - 2.3%.
    
    List with blank lines (loose list).
    """
    items: list[ListItem] = []
    current_marker = None
    current_content: list[str] = []
    list_location = None
    ordered = False
    start = 1
    has_blanks = False
    
    for tok in tokens:
        if tok.type == TokenType.LIST_ITEM_MARKER:
            # Flush previous item
            if current_marker is not None:
                if current_content:
                    content = "\n".join(current_content).rstrip()
                    inlines = parse_inline_fn(content, current_marker.location)
                    children: tuple[Block, ...] = (Paragraph(location=current_marker.location, children=inlines),)
                else:
                    children = ()
                items.append(ListItem(location=current_marker.location, children=children))
            
            current_marker = tok
            current_content = []
            
            if list_location is None:
                list_location = tok.location
                marker_info = extract_marker_info(tok.value)
                ordered = marker_info.ordered
                start = marker_info.start
                
        elif tok.type == TokenType.PARAGRAPH_LINE:
            if current_marker is not None:
                current_content.append(tok.value.lstrip())
        elif tok.type == TokenType.BLANK_LINE:
            has_blanks = True
        elif tok.type == TokenType.EOF:
            if current_marker is not None:
                if current_content:
                    content = "\n".join(current_content).rstrip()
                    inlines = parse_inline_fn(content, current_marker.location)
                    children = (Paragraph(location=current_marker.location, children=inlines),)
                else:
                    children = ()
                items.append(ListItem(location=current_marker.location, children=children))
    
    if not items or list_location is None:
        return ()
    
    return (List(
        location=list_location,
        items=tuple(items),
        ordered=ordered,
        start=start,
        tight=not has_blanks,
    ),)


# Pattern signature → parser function mapping
PATTERN_PARSERS: dict[frozenset[TokenType], Callable] = {
    frozenset({TokenType.HTML_BLOCK}): parse_html_only,
    frozenset({TokenType.ATX_HEADING}): parse_atx_only,
    frozenset({TokenType.INDENTED_CODE}): parse_indented_only,
    frozenset({
        TokenType.FENCED_CODE_START,
        TokenType.FENCED_CODE_CONTENT,
        TokenType.FENCED_CODE_END,
    }): parse_fenced_code_only,
    frozenset({TokenType.BLANK_LINE, TokenType.PARAGRAPH_LINE}): parse_paragraphs_with_blanks,
    frozenset({TokenType.LIST_ITEM_MARKER, TokenType.PARAGRAPH_LINE}): parse_simple_flat_list,
    frozenset({
        TokenType.BLANK_LINE,
        TokenType.LIST_ITEM_MARKER,
        TokenType.PARAGRAPH_LINE,
    }): parse_simple_list_with_blanks,
}


def get_pattern_parser(tokens: list) -> Callable | None:
    """Get specialized parser for token pattern if available.
    
    Args:
        tokens: Token list from lexer
        
    Returns:
        Specialized parser function, or None if no pattern match
    """
    # Get unique token types (excluding EOF and BLANK_LINE for matching)
    types = frozenset(tok.type for tok in tokens if tok.type != TokenType.EOF)
    
    return PATTERN_PARSERS.get(types)
