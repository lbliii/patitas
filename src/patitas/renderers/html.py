"""HTML renderer using StringBuilder pattern.

Renders typed AST to HTML with O(n) performance using StringBuilder.

Thread Safety:
All per-render state is encapsulated in RenderContext, created fresh for each
render() call. Multiple threads can safely share a single HtmlRenderer instance
and call render() concurrently without synchronization.

Single-Pass Heading Decoration:
Heading IDs are generated during the AST walk, eliminating the need for
regex-based post-processing. TOC data is collected during rendering.
"""

import html
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote as url_quote

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
    TableRow,
    Text,
    ThematicBreak,
)
from patitas.stringbuilder import StringBuilder
from patitas.utils.text import slugify as default_slugify

if TYPE_CHECKING:
    from patitas.directives.registry import DirectiveRegistry
    from patitas.roles.registry import RoleRegistry

logger = logging.getLogger(__name__)


def html_escape(s: str) -> str:
    """Escape HTML special characters.

    CommonMark-compliant: escapes <, >, &, " but NOT single quotes.
    Python's html.escape() escapes ' to &#x27; which CommonMark doesn't require.
    """
    return html.escape(s, quote=False).replace('"', "&quot;")


def _encode_url(url: str) -> str:
    """Encode URL for CommonMark compliance.

    CommonMark requires:
    1. Decode HTML entities (e.g., &auml; → ä)
    2. Percent-encode special characters (spaces, backslashes, non-ASCII)

    Returns URL safe for href attribute (still needs html_escape for quotes).
    """
    # First decode HTML entities
    decoded = html.unescape(url)
    # Then percent-encode, preserving already-encoded sequences and common URL chars
    # safe= characters that don't need encoding (per RFC 3986 + common URL chars)
    return url_quote(decoded, safe="/:?#[]@!$&'()*+,;=-_.~%")


@dataclass(frozen=True, slots=True)
class HeadingInfo:
    """Heading metadata collected during rendering.

    Used to build TOC without post-render regex scanning.
    Collected by HtmlRenderer during the AST walk.
    """

    level: int
    text: str
    slug: str


@dataclass(slots=True)
class RenderContext:
    """Per-render mutable state.

    Encapsulates all state that changes during a single render() call.
    Created fresh for each render, ensuring thread safety when sharing
    HtmlRenderer instances across threads.

    Thread Safety:
        Each render() call creates its own RenderContext instance.
        No shared mutable state between concurrent renders.
    """

    headings: list[HeadingInfo] = field(default_factory=list)
    seen_slugs: set[str] = field(default_factory=set)
    footnote_defs: dict[str, FootnoteDef] = field(default_factory=dict)
    footnote_refs: list[str] = field(default_factory=list)


class HtmlRenderer:
    """Render AST to HTML using StringBuilder pattern.

    O(n) rendering using StringBuilder for string accumulation.
    All per-render state is encapsulated in RenderContext.

    Usage:
        >>> from patitas.parser import Parser
        >>> parser = Parser()
        >>> doc = parser.parse("# Hello **World**")
        >>> renderer = HtmlRenderer()
        >>> html = renderer.render(doc)
        '<h1>Hello <strong>World</strong></h1>\\n'

    Thread Safety:
        Multiple threads can safely share a single HtmlRenderer instance.
        Each render() call creates an independent RenderContext, ensuring
        no shared mutable state between concurrent renders.
    """

    __slots__ = (
        "_source",
        "_highlight",
        "_directive_registry",
        "_role_registry",
        "_text_transformer",
        "_slugify",
        "_last_context",
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
        self._last_context: RenderContext | None = None

    def render(self, node: Document) -> str:
        """Render document AST to HTML string.

        Args:
            node: Document AST root

        Returns:
            HTML string

        Thread Safety:
            Creates independent RenderContext per call.
            Safe for concurrent execution from multiple threads.
        """
        # Create fresh context for this render (thread-safe)
        ctx = RenderContext()

        # First pass: collect footnote definitions
        self._collect_footnotes(node, ctx)

        # Render blocks
        sb = StringBuilder()
        for child in node.children:
            self._render_block(child, sb, ctx)

        # Render footnotes section if any refs were used
        if ctx.footnote_refs:
            self._render_footnotes_section(sb, ctx)

        # Store context for get_headings() (note: not thread-safe for get_headings)
        self._last_context = ctx

        return sb.build()

    def get_headings(self) -> list[HeadingInfo]:
        """Get heading info collected during last render.

        Returns:
            List of HeadingInfo from the last render() call.
            Empty if render() hasn't been called.

        Note:
            This method returns data from the most recent render() call.
            In multi-threaded scenarios, use the returned value immediately
            after render() in the same thread for accurate results.
        """
        if self._last_context is None:
            return []
        return self._last_context.headings.copy()

    # =========================================================================
    # Block rendering
    # =========================================================================

    def _render_block(self, block: Block, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render a block node."""
        match block:
            case Heading():
                self._render_heading(block, sb, ctx)
            case Paragraph():
                self._render_paragraph(block, sb, ctx)
            case FencedCode():
                self._render_fenced_code(block, sb)
            case IndentedCode():
                self._render_indented_code(block, sb)
            case BlockQuote():
                self._render_blockquote(block, sb, ctx)
            case List():
                self._render_list(block, sb, ctx)
            case ThematicBreak():
                sb.append("<hr />\n")
            case HtmlBlock():
                # CommonMark: HTML blocks end with exactly one newline
                html_content = block.html.rstrip("\n")
                sb.append(html_content).append("\n")
            case Table():
                self._render_table(block, sb, ctx)
            case MathBlock():
                self._render_math_block(block, sb)
            case Directive():
                self._render_directive(block, sb, ctx)
            case FootnoteDef():
                pass  # Rendered in footnotes section
            case Document():
                for child in block.children:
                    self._render_block(child, sb, ctx)
            case ListItem():
                # Should be rendered by list, but handle standalone
                self._render_list_item(block, sb, ctx, tight=True)

    def _render_heading(self, heading: Heading, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render heading with ID for anchoring."""
        # Extract plain text for slug
        text = self._extract_text(heading.children)

        # Use explicit ID if provided, otherwise generate slug
        slug = heading.explicit_id or self._slugify(text)

        # Ensure unique slug
        original_slug = slug
        counter = 1
        while slug in ctx.seen_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1
        ctx.seen_slugs.add(slug)

        # Collect heading info for TOC
        ctx.headings.append(HeadingInfo(level=heading.level, text=text, slug=slug))

        # Render
        sb.append(f'<h{heading.level} id="{html_escape(slug)}">')
        self._render_inlines(heading.children, sb, ctx)
        sb.append(f"</h{heading.level}>\n")

    def _render_paragraph(self, para: Paragraph, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render paragraph."""
        sb.append("<p>")
        self._render_inlines(para.children, sb, ctx)
        sb.append("</p>\n")

    def _render_fenced_code(self, code: FencedCode, sb: StringBuilder) -> None:
        """Render fenced code block."""
        content = code.get_code(self._source)
        # CommonMark: decode HTML entities in info string, then take first word as language
        info = html.unescape(code.info) if code.info else None
        lang = info.split()[0] if info else None
        lang_class = f' class="language-{html_escape(lang)}"' if lang else ""

        if self._highlight and lang:
            # Try syntax highlighting
            try:
                from patitas.highlighting import highlight

                highlighted = highlight(content, lang)
                sb.append(highlighted).append("\n")
                return
            except ImportError:
                # Highlighter not available - fall through to plain rendering
                pass
            except Exception:
                # Log unexpected errors but continue with fallback
                logger.debug("Syntax highlighting failed for language %r", lang, exc_info=True)

        sb.append(f"<pre><code{lang_class}>")
        sb.append(html_escape(content))
        sb.append("</code></pre>\n")

    def _render_indented_code(self, code: IndentedCode, sb: StringBuilder) -> None:
        """Render indented code block."""
        sb.append("<pre><code>")
        sb.append(html_escape(code.code))
        sb.append("</code></pre>\n")

    def _render_blockquote(self, quote: BlockQuote, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render block quote."""
        sb.append("<blockquote>\n")
        for child in quote.children:
            self._render_block(child, sb, ctx)
        sb.append("</blockquote>\n")

    def _render_list(self, lst: List, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render ordered or unordered list."""
        if lst.ordered:
            start_attr = f' start="{lst.start}"' if lst.start != 1 else ""
            sb.append(f"<ol{start_attr}>\n")
        else:
            sb.append("<ul>\n")

        for item in lst.items:
            self._render_list_item(item, sb, ctx, lst.tight)

        sb.append("</ol>\n" if lst.ordered else "</ul>\n")

    def _render_list_item(
        self, item: ListItem, sb: StringBuilder, ctx: RenderContext, tight: bool
    ) -> None:
        """Render list item.

        CommonMark:
        - Tight lists: Single paragraph items render as text (no <p> tags)
        - Loose lists: All paragraphs wrapped in <p> tags
        """
        # Task list checkbox
        checkbox = ""
        if item.checked is not None:
            checked = " checked" if item.checked else ""
            checkbox = f'<input type="checkbox" disabled{checked} /> '

        sb.append("<li>")
        if checkbox:
            sb.append(checkbox)

        # CommonMark tight/loose list rendering rules:
        # - Tight list, single paragraph: <li>text</li> (no <p>, no newlines)
        # - Tight list, first is paragraph: <li>text\n...rest</li>
        # - Tight list, first is non-paragraph: <li>\n<block>...</li>
        # - Tight list, heading + paragraph: paragraphs render as text (no <p>)
        # - Loose list: <li>\n<p>text</p>\n...rest</li>
        if not item.children:
            # Empty item
            pass
        elif tight and len(item.children) == 1 and isinstance(item.children[0], Paragraph):
            # Single paragraph in tight list: render inline without <p>
            self._render_inlines(item.children[0].children, sb, ctx)
        elif tight:
            # Tight list with multiple blocks or non-paragraph first child
            first = item.children[0]
            if isinstance(first, Paragraph):
                # First is paragraph: render as text
                self._render_inlines(first.children, sb, ctx)
                sb.append("\n")
                for child in item.children[1:]:
                    self._render_block(child, sb, ctx)
            else:
                # First is non-paragraph (heading, blockquote, code, etc.): add newline
                sb.append("\n")
                for i, child in enumerate(item.children):
                    if isinstance(child, Paragraph):
                        # In tight list after heading, paragraphs render as text
                        self._render_inlines(child.children, sb, ctx)
                        # Add newline after inline content if not last item
                        if i < len(item.children) - 1:
                            sb.append("\n")
                    else:
                        self._render_block(child, sb, ctx)
        else:
            # Loose list: all blocks render normally with <p> tags
            sb.append("\n")
            for child in item.children:
                self._render_block(child, sb, ctx)

        sb.append("</li>\n")

    def _render_table(self, table: Table, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render GFM-style table."""
        sb.append("<table>\n")

        if table.head:
            sb.append("<thead>\n")
            for row in table.head:
                self._render_table_row(row, sb, ctx, is_header=True, alignments=table.alignments)
            sb.append("</thead>\n")

        if table.body:
            sb.append("<tbody>\n")
            for row in table.body:
                self._render_table_row(row, sb, ctx, is_header=False, alignments=table.alignments)
            sb.append("</tbody>\n")

        sb.append("</table>\n")

    def _render_table_row(
        self,
        row: TableRow,
        sb: StringBuilder,
        ctx: RenderContext,
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
            self._render_inlines(cell.children, sb, ctx)
            sb.append(f"</{tag}>\n")

        sb.append("</tr>\n")

    def _render_math_block(self, math: MathBlock, sb: StringBuilder) -> None:
        """Render block math."""
        sb.append('<div class="math-block">\n')
        sb.append(html_escape(math.content))
        sb.append("\n</div>\n")

    def _render_directive(
        self, directive: Directive[Any], sb: StringBuilder, ctx: RenderContext
    ) -> None:
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
                # Log directive rendering errors for debugging
                logger.debug(
                    "Directive handler %r failed", directive.name, exc_info=True
                )

        # Default: render as container
        title_html = html_escape(directive.title) if directive.title else ""
        sb.append(f'<div class="directive directive-{html_escape(directive.name)}">\n')
        if title_html:
            sb.append(f'<p class="directive-title">{title_html}</p>\n')
        for child in directive.children:
            self._render_block(child, sb, ctx)
        sb.append("</div>\n")

    # =========================================================================
    # Inline rendering
    # =========================================================================

    def _render_inlines(
        self, inlines: tuple[Inline, ...], sb: StringBuilder, ctx: RenderContext
    ) -> None:
        """Render a sequence of inline nodes."""
        for inline in inlines:
            self._render_inline(inline, sb, ctx)

    def _render_inline(self, inline: Inline, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render an inline node."""
        match inline:
            case Text():
                text = inline.content
                if self._text_transformer:
                    text = self._text_transformer(text)
                sb.append(html_escape(text))
            case Emphasis():
                sb.append("<em>")
                self._render_inlines(inline.children, sb, ctx)
                sb.append("</em>")
            case Strong():
                sb.append("<strong>")
                self._render_inlines(inline.children, sb, ctx)
                sb.append("</strong>")
            case Strikethrough():
                sb.append("<del>")
                self._render_inlines(inline.children, sb, ctx)
                sb.append("</del>")
            case Link():
                href = html_escape(_encode_url(inline.url))
                # CommonMark: decode HTML entities in title, then re-escape
                title_text = html.unescape(inline.title) if inline.title else None
                title = f' title="{html_escape(title_text)}"' if title_text else ""
                sb.append(f'<a href="{href}"{title}>')
                self._render_inlines(inline.children, sb, ctx)
                sb.append("</a>")
            case Image():
                src = html_escape(_encode_url(inline.url))
                alt = html_escape(inline.alt)
                # CommonMark: decode HTML entities in title, then re-escape
                title_text = html.unescape(inline.title) if inline.title else None
                title = f' title="{html_escape(title_text)}"' if title_text else ""
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
                ctx.footnote_refs.append(inline.identifier)
                ref_num = len(ctx.footnote_refs)
                esc_id = html_escape(inline.identifier)
                sb.append(f'<sup><a href="#fn-{esc_id}" id="fnref-{esc_id}-{ref_num}">{ref_num}</a></sup>')
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
                # Log role rendering errors for debugging
                logger.debug("Role handler %r failed", role.name, exc_info=True)

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
                case Image():
                    # Include alt text in extracted text (for heading slugs)
                    parts.append(inline.alt)
                case CodeSpan():
                    parts.append(inline.code)
                case Math():
                    parts.append(inline.content)
                case _:
                    pass
        return "".join(parts)

    def _collect_footnotes(self, doc: Document, ctx: RenderContext) -> None:
        """Collect footnote definitions from document."""
        for block in doc.children:
            if isinstance(block, FootnoteDef):
                ctx.footnote_defs[block.identifier] = block

    def _render_footnotes_section(self, sb: StringBuilder, ctx: RenderContext) -> None:
        """Render footnotes section at end of document."""
        sb.append('<section class="footnotes">\n')
        sb.append("<ol>\n")

        # Track which footnotes have been rendered to avoid duplicate IDs
        rendered_footnotes: set[str] = set()

        for identifier in ctx.footnote_refs:
            if identifier in ctx.footnote_defs and identifier not in rendered_footnotes:
                rendered_footnotes.add(identifier)
                fn_def = ctx.footnote_defs[identifier]
                sb.append(f'<li id="fn-{html_escape(identifier)}">\n')
                for child in fn_def.children:
                    self._render_block(child, sb, ctx)
                sb.append(f'<a href="#fnref-{html_escape(identifier)}-1">↩</a>\n')
                sb.append("</li>\n")

        sb.append("</ol>\n")
        sb.append("</section>\n")
