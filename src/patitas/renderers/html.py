"""HTML renderer using StringBuilder pattern.

Renders typed AST to HTML with O(n) performance using StringBuilder.

Thread Safety:
All state is local to each render() call.
Multiple threads can render concurrently without synchronization.

Single-Pass Heading Decoration:
Heading IDs are generated during the AST walk, eliminating the need for
regex-based post-processing. TOC data is collected during rendering.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, Any

from patitas.nodes import (
    Block,
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
from patitas.utils.text import slugify as default_slugify

if TYPE_CHECKING:
    from patitas.directives.registry import DirectiveRegistry
    from patitas.roles.registry import RoleRegistry


@dataclass(frozen=True, slots=True)
class HeadingInfo:
    """Heading metadata collected during rendering.
    
    Used to build TOC without post-render regex scanning.
    Collected by HtmlRenderer during the AST walk.
    """

    level: int
    text: str
    slug: str


class HtmlRenderer:
    """Render AST to HTML using StringBuilder pattern.
    
    O(n) rendering using StringBuilder for string accumulation.
    All state is local to each render() call.
    
    Usage:
        >>> from patitas.parser import Parser
        >>> parser = Parser()
        >>> doc = parser.parse("# Hello **World**")
        >>> renderer = HtmlRenderer()
        >>> html = renderer.render(doc)
        '<h1>Hello <strong>World</strong></h1>\\n'
    
    Thread Safety:
        Multiple threads can render concurrently without synchronization.
        Each call creates independent StringBuilder.
    """

    __slots__ = (
        "_source",
        "_highlight",
        "_directive_registry",
        "_role_registry",
        "_text_transformer",
        "_headings",
        "_slugify",
        "_seen_slugs",
        "_footnote_defs",
        "_footnote_refs",
    )

    def __init__(
        self,
        source: str = "",
        *,
        highlight: bool = False,
        directive_registry: DirectiveRegistry | None = None,
        role_registry: RoleRegistry | None = None,
        text_transformer: Callable[[str], str] | None = None,
        slugify: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize renderer.

        Args:
            source: Original source buffer for zero-copy extraction
            highlight: Enable syntax highlighting for code blocks
            directive_registry: Optional registry for custom directive rendering
            role_registry: Optional registry for custom role rendering
            text_transformer: Optional callback to transform plain text nodes
            slugify: Optional custom slugify function for heading IDs
        """
        self._source = source
        self._highlight = highlight
        self._directive_registry = directive_registry
        self._role_registry = role_registry
        self._text_transformer = text_transformer
        self._slugify = slugify or default_slugify
        self._headings: list[HeadingInfo] = []
        self._seen_slugs: set[str] = set()
        self._footnote_defs: dict[str, FootnoteDef] = {}
        self._footnote_refs: list[str] = []

    def render(self, node: Document) -> str:
        """Render document AST to HTML string.

        Args:
            node: Document AST root

        Returns:
            HTML string

        Thread Safety:
            Creates independent StringBuilder per call.
            Safe for concurrent execution.
        """
        # Reset per-render state
        self._headings = []
        self._seen_slugs = set()
        self._footnote_defs = {}
        self._footnote_refs = []

        # First pass: collect footnote definitions
        self._collect_footnotes(node)

        # Render blocks
        sb = StringBuilder()
        for child in node.children:
            self._render_block(child, sb)

        # Render footnotes section if any refs were used
        if self._footnote_refs:
            self._render_footnotes_section(sb)

        return sb.build()

    def get_headings(self) -> list[HeadingInfo]:
        """Get heading info collected during last render.

        Returns:
            List of HeadingInfo from the last render() call.
            Empty if render() hasn't been called.
        """
        return self._headings.copy()

    # =========================================================================
    # Block rendering
    # =========================================================================

    def _render_block(self, block: Block, sb: StringBuilder) -> None:
        """Render a block node."""
        match block:
            case Heading():
                self._render_heading(block, sb)
            case Paragraph():
                self._render_paragraph(block, sb)
            case FencedCode():
                self._render_fenced_code(block, sb)
            case IndentedCode():
                self._render_indented_code(block, sb)
            case BlockQuote():
                self._render_blockquote(block, sb)
            case List():
                self._render_list(block, sb)
            case ThematicBreak():
                sb.append("<hr />\n")
            case HtmlBlock():
                sb.append(block.html).append("\n")
            case Table():
                self._render_table(block, sb)
            case MathBlock():
                self._render_math_block(block, sb)
            case Directive():
                self._render_directive(block, sb)
            case FootnoteDef():
                pass  # Rendered in footnotes section
            case Document():
                for child in block.children:
                    self._render_block(child, sb)
            case ListItem():
                # Should be rendered by list, but handle standalone
                self._render_list_item(block, sb, ordered=False, start=1)

    def _render_heading(self, heading: Heading, sb: StringBuilder) -> None:
        """Render heading with ID for anchoring."""
        # Extract plain text for slug
        text = self._extract_text(heading.children)
        
        # Use explicit ID if provided, otherwise generate slug
        if heading.explicit_id:
            slug = heading.explicit_id
        else:
            slug = self._slugify(text)

        # Ensure unique slug
        original_slug = slug
        counter = 1
        while slug in self._seen_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1
        self._seen_slugs.add(slug)

        # Collect heading info for TOC
        self._headings.append(HeadingInfo(level=heading.level, text=text, slug=slug))

        # Render
        sb.append(f'<h{heading.level} id="{html_escape(slug)}">')
        self._render_inlines(heading.children, sb)
        sb.append(f"</h{heading.level}>\n")

    def _render_paragraph(self, para: Paragraph, sb: StringBuilder) -> None:
        """Render paragraph."""
        sb.append("<p>")
        self._render_inlines(para.children, sb)
        sb.append("</p>\n")

    def _render_fenced_code(self, code: FencedCode, sb: StringBuilder) -> None:
        """Render fenced code block."""
        content = code.get_code(self._source)
        lang_class = f' class="language-{html_escape(code.info)}"' if code.info else ""

        if self._highlight and code.info:
            # Try syntax highlighting
            try:
                from patitas.highlighting import highlight
                highlighted = highlight(content, code.info)
                sb.append(highlighted).append("\n")
                return
            except Exception:
                pass  # Fall through to plain rendering

        sb.append(f"<pre><code{lang_class}>")
        sb.append(html_escape(content))
        sb.append("</code></pre>\n")

    def _render_indented_code(self, code: IndentedCode, sb: StringBuilder) -> None:
        """Render indented code block."""
        sb.append("<pre><code>")
        sb.append(html_escape(code.code))
        sb.append("</code></pre>\n")

    def _render_blockquote(self, quote: BlockQuote, sb: StringBuilder) -> None:
        """Render block quote."""
        sb.append("<blockquote>\n")
        for child in quote.children:
            self._render_block(child, sb)
        sb.append("</blockquote>\n")

    def _render_list(self, lst: List, sb: StringBuilder) -> None:
        """Render ordered or unordered list."""
        if lst.ordered:
            start_attr = f' start="{lst.start}"' if lst.start != 1 else ""
            sb.append(f"<ol{start_attr}>\n")
        else:
            sb.append("<ul>\n")

        for item in lst.items:
            self._render_list_item(item, sb, lst.ordered, lst.start)

        sb.append("</ol>\n" if lst.ordered else "</ul>\n")

    def _render_list_item(
        self, item: ListItem, sb: StringBuilder, ordered: bool, start: int
    ) -> None:
        """Render list item."""
        # Task list checkbox
        checkbox = ""
        if item.checked is not None:
            checked = " checked" if item.checked else ""
            checkbox = f'<input type="checkbox" disabled{checked} /> '

        sb.append("<li>")
        if checkbox:
            sb.append(checkbox)

        # For tight lists, render inline content directly
        # For loose lists, render block content
        for i, child in enumerate(item.children):
            if isinstance(child, Paragraph) and len(item.children) == 1:
                # Single paragraph in tight list: render inline without <p>
                self._render_inlines(child.children, sb)
            else:
                if i == 0 and isinstance(child, Paragraph):
                    # First paragraph: render inline
                    self._render_inlines(child.children, sb)
                    sb.append("\n")
                else:
                    self._render_block(child, sb)

        sb.append("</li>\n")

    def _render_table(self, table: Table, sb: StringBuilder) -> None:
        """Render GFM-style table."""
        sb.append("<table>\n")

        if table.head:
            sb.append("<thead>\n")
            for row in table.head:
                self._render_table_row(row, sb, is_header=True, alignments=table.alignments)
            sb.append("</thead>\n")

        if table.body:
            sb.append("<tbody>\n")
            for row in table.body:
                self._render_table_row(row, sb, is_header=False, alignments=table.alignments)
            sb.append("</tbody>\n")

        sb.append("</table>\n")

    def _render_table_row(
        self,
        row: TableRow,
        sb: StringBuilder,
        is_header: bool,
        alignments: tuple[str | None, ...],
    ) -> None:
        """Render table row."""
        sb.append("<tr>\n")
        tag = "th" if is_header else "td"

        for i, cell in enumerate(row.cells):
            align = alignments[i] if i < len(alignments) else None
            style = f' style="text-align: {align}"' if align else ""
            sb.append(f"<{tag}{style}>")
            self._render_inlines(cell.children, sb)
            sb.append(f"</{tag}>\n")

        sb.append("</tr>\n")

    def _render_math_block(self, math: MathBlock, sb: StringBuilder) -> None:
        """Render block math."""
        sb.append('<div class="math-block">\n')
        sb.append(html_escape(math.content))
        sb.append("\n</div>\n")

    def _render_directive(self, directive: Directive[Any], sb: StringBuilder) -> None:
        """Render directive block.
        
        If a directive registry is configured and has a handler for this
        directive, use it. Otherwise, render as a generic container.
        """
        if self._directive_registry:
            try:
                handler = self._directive_registry.get(directive.name)
                if handler:
                    result = handler.render(directive, self)
                    sb.append(result)
                    return
            except Exception:
                pass  # Fall through to default rendering

        # Default: render as container
        title_html = html_escape(directive.title) if directive.title else ""
        sb.append(f'<div class="directive directive-{html_escape(directive.name)}">\n')
        if title_html:
            sb.append(f'<p class="directive-title">{title_html}</p>\n')
        for child in directive.children:
            self._render_block(child, sb)
        sb.append("</div>\n")

    # =========================================================================
    # Inline rendering
    # =========================================================================

    def _render_inlines(self, inlines: tuple[Inline, ...], sb: StringBuilder) -> None:
        """Render a sequence of inline nodes."""
        for inline in inlines:
            self._render_inline(inline, sb)

    def _render_inline(self, inline: Inline, sb: StringBuilder) -> None:
        """Render an inline node."""
        match inline:
            case Text():
                text = inline.content
                if self._text_transformer:
                    text = self._text_transformer(text)
                sb.append(html_escape(text))
            case Emphasis():
                sb.append("<em>")
                self._render_inlines(inline.children, sb)
                sb.append("</em>")
            case Strong():
                sb.append("<strong>")
                self._render_inlines(inline.children, sb)
                sb.append("</strong>")
            case Strikethrough():
                sb.append("<del>")
                self._render_inlines(inline.children, sb)
                sb.append("</del>")
            case Link():
                href = html_escape(inline.url)
                title = f' title="{html_escape(inline.title)}"' if inline.title else ""
                sb.append(f'<a href="{href}"{title}>')
                self._render_inlines(inline.children, sb)
                sb.append("</a>")
            case Image():
                src = html_escape(inline.url)
                alt = html_escape(inline.alt)
                title = f' title="{html_escape(inline.title)}"' if inline.title else ""
                sb.append(f'<img src="{src}" alt="{alt}"{title} />')
            case CodeSpan():
                sb.append("<code>")
                sb.append(html_escape(inline.code))
                sb.append("</code>")
            case LineBreak():
                sb.append("<br />\n")
            case SoftBreak():
                sb.append("\n")
            case HtmlInline():
                sb.append(inline.html)
            case Math():
                sb.append('<span class="math">')
                sb.append(html_escape(inline.content))
                sb.append("</span>")
            case FootnoteRef():
                self._footnote_refs.append(inline.identifier)
                ref_num = len(self._footnote_refs)
                sb.append(f'<sup><a href="#fn-{html_escape(inline.identifier)}" id="fnref-{html_escape(inline.identifier)}">{ref_num}</a></sup>')
            case Role():
                self._render_role(inline, sb)

    def _render_role(self, role: Role, sb: StringBuilder) -> None:
        """Render inline role."""
        if self._role_registry:
            try:
                handler = self._role_registry.get(role.name)
                if handler:
                    result = handler.render(role.content, role.location)
                    sb.append(result)
                    return
            except Exception:
                pass  # Fall through to default

        # Default: render as span
        sb.append(f'<span class="role role-{html_escape(role.name)}">')
        sb.append(html_escape(role.content))
        sb.append("</span>")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _extract_text(self, inlines: tuple[Inline, ...]) -> str:
        """Extract plain text from inline nodes."""
        parts: list[str] = []
        for inline in inlines:
            match inline:
                case Text():
                    parts.append(inline.content)
                case Emphasis() | Strong() | Strikethrough():
                    parts.append(self._extract_text(inline.children))
                case Link():
                    parts.append(self._extract_text(inline.children))
                case CodeSpan():
                    parts.append(inline.code)
                case Math():
                    parts.append(inline.content)
                case _:
                    pass
        return "".join(parts)

    def _collect_footnotes(self, doc: Document) -> None:
        """Collect footnote definitions from document."""
        for block in doc.children:
            if isinstance(block, FootnoteDef):
                self._footnote_defs[block.identifier] = block

    def _render_footnotes_section(self, sb: StringBuilder) -> None:
        """Render footnotes section at end of document."""
        sb.append('<section class="footnotes">\n')
        sb.append("<ol>\n")

        for identifier in self._footnote_refs:
            if identifier in self._footnote_defs:
                fn_def = self._footnote_defs[identifier]
                sb.append(f'<li id="fn-{html_escape(identifier)}">\n')
                for child in fn_def.children:
                    self._render_block(child, sb)
                sb.append(f'<a href="#fnref-{html_escape(identifier)}">↩</a>\n')
                sb.append("</li>\n")

        sb.append("</ol>\n")
        sb.append("</section>\n")
