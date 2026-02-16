"""Extract plain-text excerpts from Patitas AST.

Provides structurally correct excerpt extraction that stops at block boundaries,
avoiding mid-markdown truncation and properly handling headings, paragraphs,
and lists.

Example:
    >>> from patitas import parse, extract_excerpt, extract_meta_description
    >>> doc = parse("# Title\\n\\nFirst paragraph. Second sentence.")
    >>> extract_excerpt(doc)
    'First paragraph. Second sentence.'
    >>> extract_meta_description(doc)
    'First paragraph.'
"""

from __future__ import annotations

from collections.abc import Sequence

from patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Directive,
    Document,
    Emphasis,
    FencedCode,
    Heading,
    Image,
    IndentedCode,
    Inline,
    Link,
    List,
    ListItem,
    Paragraph,
    Role,
    Strong,
    Text,
)


def _inline_text(node: Inline) -> str:
    """Recursively extract plain text from inline nodes."""
    if isinstance(node, Text):
        return node.content
    if isinstance(node, CodeSpan):
        return node.code
    if isinstance(node, Role):
        return node.content
    if isinstance(node, Image):
        return node.alt
    if hasattr(node, "children"):
        return "".join(_inline_text(c) for c in node.children)
    return ""


def _inline_text_html(node: Inline) -> str:
    """Recursively extract HTML from inline nodes (preserves strong, emphasis, links)."""
    if isinstance(node, Text):
        return node.content
    if isinstance(node, CodeSpan):
        return f"<code>{node.code}</code>"
    if isinstance(node, Role):
        return node.content
    if isinstance(node, Image):
        return node.alt
    if isinstance(node, Strong):
        inner = "".join(_inline_text_html(c) for c in node.children)
        return f"<strong>{inner}</strong>" if inner else ""
    if isinstance(node, Emphasis):
        inner = "".join(_inline_text_html(c) for c in node.children)
        return f"<em>{inner}</em>" if inner else ""
    if isinstance(node, Link):
        inner = "".join(_inline_text_html(c) for c in node.children)
        return inner  # Plain text for excerpt; omit href for brevity
    if hasattr(node, "children"):
        return "".join(_inline_text_html(c) for c in node.children)
    return ""


def _block_text(node: Block, source: str) -> str:
    """Extract plain text from a block node."""
    if isinstance(node, Paragraph):
        return "".join(_inline_text(c) for c in node.children)
    if isinstance(node, Heading):
        return "".join(_inline_text(c) for c in node.children)
    if isinstance(node, ListItem):
        parts: list[str] = []
        for child in node.children:
            if isinstance(child, Paragraph):
                parts.append("".join(_inline_text(c) for c in child.children))
            elif isinstance(child, List):
                parts.extend([_block_text(item, source) for item in child.items])
        return " ".join(parts)
    if isinstance(node, BlockQuote):
        return " ".join(_block_text(c, source) for c in node.children)
    if isinstance(node, List):
        return "\n".join(_block_text(item, source) for item in node.items)
    if isinstance(node, FencedCode):
        try:
            code = node.get_code(source)
            first_line = code.split("\n")[0] if code else ""
            return f" {first_line}" if first_line else ""
        except IndexError, TypeError:
            return ""
    if isinstance(node, IndentedCode):
        first_line = node.code.split("\n")[0] if node.code else ""
        return f" {first_line}" if first_line else ""
    return ""


def _block_text_html(node: Block, source: str) -> str:
    """Extract HTML from a block node (preserves inline formatting, uses block elements)."""
    if isinstance(node, Paragraph):
        inner = "".join(_inline_text_html(c) for c in node.children)
        return f"<p>{inner}</p>" if inner else ""
    if isinstance(node, Heading):
        inner = "".join(_inline_text_html(c) for c in node.children)
        return f'<div class="excerpt-heading">{inner}</div>' if inner else ""
    if isinstance(node, ListItem):
        parts: list[str] = []
        for child in node.children:
            if isinstance(child, Paragraph):
                parts.append("".join(_inline_text_html(c) for c in child.children))
            elif isinstance(child, List):
                parts.append(_block_text_html(child, source))
        return "".join(parts)  # Li content; List wraps in ul/ol + li
    if isinstance(node, BlockQuote):
        inner = " ".join(_block_text_html(c, source) for c in node.children)
        return f"<p>{inner}</p>" if inner else ""
    if isinstance(node, List):
        tag = "ol" if node.ordered else "ul"
        items_html = [f"<li>{_block_text_html(item, source)}</li>" for item in node.items]
        inner = "\n".join(items_html)
        return f'<{tag} class="excerpt-list">\n{inner}\n</{tag}>' if inner else ""
    if isinstance(node, FencedCode):
        try:
            code = node.get_code(source)
            first_line = code.split("\n")[0] if code else ""
            return f"<p><code>{first_line}</code></p>" if first_line else ""
        except IndexError, TypeError:
            return ""
    if isinstance(node, IndentedCode):
        first_line = node.code.split("\n")[0] if node.code else ""
        return f"<p><code>{first_line}</code></p>" if first_line else ""
    return ""


def extract_excerpt(
    ast: Document | Sequence[Block],
    source: str = "",
    *,
    max_chars: int = 750,
    skip_leading_h1: bool = True,
    include_headings: bool = True,
    excerpt_as_html: bool = False,
) -> str:
    """Extract excerpt from AST. Stops at block boundaries.

    Walks blocks in order, extracting text. Skips leading h1 by default.
    Stops when accumulated text reaches max_chars, always at a block boundary.

    Args:
        ast: Document or sequence of Block nodes
        source: Original source (for FencedCode zero-copy extraction)
        max_chars: Maximum characters (default 250)
        skip_leading_h1: Skip first Heading(level=1) (default True)
        include_headings: Include heading text in excerpt (default True)
        excerpt_as_html: If True, output block elements (<p>, <div class="excerpt-heading">)
            for structure, preserving <strong>, <em>, <code> (default False)

    Returns:
        Excerpt text (plain or HTML depending on excerpt_as_html)
    """
    blocks: Sequence[Block] = ast.children if isinstance(ast, Document) else ast

    if not blocks:
        return ""

    block_extractor = _block_text_html if excerpt_as_html else _block_text
    block_sep = "" if excerpt_as_html else " "  # Block elements need no separator

    accumulated: list[str] = []
    total = 0

    for block in blocks:
        if skip_leading_h1 and isinstance(block, Heading) and block.level == 1:
            continue

        if isinstance(block, Directive):
            continue

        text = block_extractor(block, source)
        if not text.strip():
            continue

        if isinstance(block, Heading) and not include_headings:
            continue

        # Ensure separator between blocks (plain text only)
        if accumulated and block_sep:
            text = block_sep + text.lstrip()

        block_len = len(text)
        if total + block_len >= max_chars:
            # Truncate this block to fit
            remaining = max_chars - total
            if remaining > 0:
                truncated = text[:remaining].rstrip()
                if truncated:
                    accumulated.append(truncated)
            break

        accumulated.append(text)
        total += block_len

    result = "".join(accumulated).strip()
    return _truncate_at_word(result, max_chars)


def _truncate_at_word(text: str, length: int, suffix: str = "...") -> str:
    """Truncate at word boundary within length."""
    if not text or len(text) <= length:
        return text
    max_content = length - len(suffix)
    if max_content <= 0:
        return suffix[:length]
    truncated = text[:max_content]
    last_space = truncated.rfind(" ")
    result = truncated[:last_space].strip() if last_space > 0 else truncated.strip()
    return result + suffix if result else suffix


def _truncate_at_sentence(text: str, length: int = 160, min_ratio: float = 0.6) -> str:
    """Truncate at sentence boundary. Falls back to word boundary if needed."""
    if not text or len(text) <= length:
        return text
    truncated = text[:length]
    sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )
    min_length = int(length * min_ratio)
    if sentence_end > min_length:
        return truncated[: sentence_end + 1].strip()
    return _truncate_at_word(text, length)


def extract_meta_description(
    ast: Document | Sequence[Block],
    source: str = "",
    *,
    max_chars: int = 160,
) -> str:
    """Extract SEO-friendly meta description from AST.

    Same logic as extract_excerpt but prefers sentence boundary at 160 chars.
    Uses extract_excerpt with larger buffer then truncates at sentence.

    Args:
        ast: Document or sequence of Block nodes
        source: Original source (for FencedCode)
        max_chars: Maximum length (default 160, SEO standard)

    Returns:
        Plain text meta description
    """
    raw = extract_excerpt(ast, source, max_chars=200)
    return _truncate_at_sentence(raw, length=max_chars)
