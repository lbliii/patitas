"""LLM-optimized renderer — structured plain text for model consumption.

Outputs markdown-like plain text with explicit labels for code, math, and images.
No HTML. Normalized whitespace. Predictable, parseable format.

Example:
    >>> from patitas import parse, render_llm
    >>> doc = parse("# Hello **World**\\n\\n- item")
    >>> render_llm(doc)
    '## Hello World\\n\\n- item\\n'
"""

from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Directive,
    Document,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)
from patitas.stringbuilder import StringBuilder


class LlmRenderer:
    """Render AST to structured plain text for LLM consumption.

    No HTML. Preserves hierarchy via markdown-like markers.
    Labels non-text content explicitly.
    """

    __slots__ = ("_source",)

    def __init__(self, source: str = "") -> None:
        self._source = source

    def render(self, node: Document) -> str:
        """Render document to LLM-friendly plain text."""
        sb = StringBuilder()
        for child in node.children:
            self._render_block(child, sb)
        return sb.build()

    def _render_block(self, block, sb: StringBuilder) -> None:
        """Render a block node."""
        match block:
            case Document():
                for child in block.children:
                    self._render_block(child, sb)
            case Heading():
                prefix = "#" * block.level + " "
                sb.append(prefix)
                self._render_inlines(block.children, sb)
                sb.append("\n\n")
            case Paragraph():
                self._render_inlines(block.children, sb)
                sb.append("\n\n")
            case FencedCode():
                lang = (block.info or "").split()[0] if block.info else ""
                tag = f"[code:{lang}]" if lang else "[code]"
                sb.append(tag).append("\n")
                try:
                    sb.append(block.get_code(self._source))
                except (IndexError, TypeError):
                    pass
                sb.append("\n[/code]\n\n")
            case IndentedCode():
                sb.append("[code]\n").append(block.code).append("\n[/code]\n\n")
            case BlockQuote():
                sb.append("> ")
                for child in block.children:
                    self._render_block(child, sb)
                sb.append("\n")
            case List():
                for i, item in enumerate(block.items):
                    prefix = f"{block.start + i}. " if block.ordered else "- "
                    sb.append(prefix)
                    self._render_list_item(item, sb)
                sb.append("\n")
            case ListItem():
                self._render_list_item(block, sb)
            case ThematicBreak():
                sb.append("---\n\n")
            case HtmlBlock():
                sb.append(block.html).append("\n\n")
            case Table():
                self._render_table(block, sb)
            case MathBlock():
                sb.append("[math] ").append(block.content).append(" [/math]\n\n")
            case Directive():
                for child in block.children:
                    self._render_block(child, sb)
            case FootnoteDef():
                for child in block.children:
                    self._render_block(child, sb)
            case _:
                pass

    def _render_list_item(self, item: ListItem, sb: StringBuilder) -> None:
        """Render list item content."""
        if not item.children:
            sb.append("\n")
            return
        first = item.children[0]
        if isinstance(first, Paragraph):
            self._render_inlines(first.children, sb)
        else:
            self._render_block(first, sb)
        for child in item.children[1:]:
            self._render_block(child, sb)
        sb.append("\n")

    def _render_table(self, table: Table, sb: StringBuilder) -> None:
        """Render table as markdown-style grid."""
        rows = list(table.head) + list(table.body)
        for row in rows:
            cells = [self._inline_text(cell) for cell in row.cells]
            sb.append("| ").append(" | ".join(cells)).append(" |\n")
        sb.append("\n")

    def _inline_text(self, node) -> str:
        """Extract plain text from a node with inline children."""
        parts: list[str] = []
        for child in getattr(node, "children", ()):
            parts.append(self._inline_text_single(child))
        return "".join(parts)

    def _render_inlines(self, inlines: tuple[Inline, ...], sb: StringBuilder) -> None:
        """Render inline nodes."""
        for inline in inlines:
            self._render_inline(inline, sb)

    def _render_inline(self, inline: Inline, sb: StringBuilder) -> None:
        """Render a single inline node."""
        match inline:
            case Text():
                sb.append(inline.content)
            case Emphasis() | Strong() | Strikethrough():
                self._render_inlines(inline.children, sb)
            case Link():
                self._render_inlines(inline.children, sb)
                sb.append(f" ({inline.url})")
            case Image():
                sb.append(f"[image: {inline.alt}]")
            case CodeSpan():
                sb.append(inline.code)
            case LineBreak() | SoftBreak():
                sb.append(" ")
            case HtmlInline():
                pass  # Skip raw HTML in LLM output
            case Math():
                sb.append(f"[math] {inline.content} [/math]")
            case FootnoteRef():
                sb.append(f"[^{inline.identifier}]")
            case Role():
                sb.append(inline.content)
            case _:
                pass

    def _inline_text_single(self, inline: Inline) -> str:
        """Extract plain text from one inline (for table cells)."""
        match inline:
            case Text():
                return inline.content
            case CodeSpan():
                return inline.code
            case Image():
                return inline.alt
            case Math():
                return inline.content
            case Role():
                return inline.content
            case Link():
                return "".join(self._inline_text_single(c) for c in inline.children)
            case Emphasis() | Strong() | Strikethrough():
                return "".join(self._inline_text_single(c) for c in inline.children)
            case LineBreak() | SoftBreak():
                return " "
            case _:
                return ""


def render_llm(doc: Document, *, source: str = "") -> str:
    """Render document to LLM-friendly plain text.

    Args:
        doc: Document AST to render.
        source: Original source (for FencedCode zero-copy extraction).

    Returns:
        Structured plain text for LLM consumption.
    """
    renderer = LlmRenderer(source=source)
    return renderer.render(doc)
