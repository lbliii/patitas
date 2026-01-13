"""
Patitas — Modern Markdown Parser for Python 3.14t

A CommonMark-compliant Markdown parser designed for free-threaded Python.
Features O(n) guaranteed parsing, typed AST, and zero runtime dependencies.

Quick Start:
    >>> from patitas import parse, render
    >>> doc = parse("# Hello, World!")
    >>> html = render(doc)
    >>> print(html)
    <h1 id="hello-world">Hello, World!</h1>

    >>> # Or use the high-level Markdown class
    >>> from patitas import Markdown
    >>> md = Markdown()
    >>> html = md("# Hello **World**")

Custom Directives:
    >>> from patitas import Markdown, create_registry_with_defaults
    >>>
    >>> # Extend defaults with your own directives
    >>> builder = create_registry_with_defaults()
    >>> builder.register(MyCustomDirective())
    >>> md = Markdown(directive_registry=builder.build())
    >>> html = md(":::{my-directive}\\nContent\\n:::")

Installation:
    pip install patitas              # Core parser with directives (zero deps)
    pip install patitas[syntax]      # + Syntax highlighting via Rosettes
"""

from __future__ import annotations

from patitas.directives.registry import (
    DirectiveRegistry,
    DirectiveRegistryBuilder,
    create_default_registry,
    create_registry_with_defaults,
)
from patitas.lexer import Lexer
from patitas.location import SourceLocation
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
from patitas.parser import Parser
from patitas.renderers.html import HtmlRenderer
from patitas.tokens import Token, TokenType

__version__ = "0.1.0"


def parse(
    source: str,
    *,
    source_file: str | None = None,
    directive_registry: DirectiveRegistry | None = None,
) -> Document:
    """Parse Markdown source into a typed AST.

    Args:
        source: Markdown source text
        source_file: Optional source file path for error messages
        directive_registry: Custom directive registry (uses defaults if None)

    Returns:
        Document AST root node

    Example:
        >>> doc = parse("# Hello **World**")
        >>> doc.children[0]
        Heading(level=1, ...)

        >>> # With custom directives
        >>> from patitas import DirectiveRegistryBuilder
        >>> builder = DirectiveRegistryBuilder()
        >>> builder.register(MyDirective())
        >>> doc = parse(source, directive_registry=builder.build())
    """
    registry = directive_registry or create_default_registry()
    parser = Parser(source, source_file=source_file, directive_registry=registry)
    blocks = parser.parse()
    # Wrap blocks in a Document
    loc = SourceLocation(
        lineno=1,
        col_offset=1,
        offset=0,
        end_offset=len(source),
        source_file=source_file,
    )
    return Document(location=loc, children=tuple(blocks))


def render(
    doc: Document,
    *,
    source: str = "",
    highlight: bool = False,
    directive_registry: DirectiveRegistry | None = None,
) -> str:
    """Render an AST Document to HTML.

    Args:
        doc: Document AST to render
        source: Original source (needed for zero-copy code block extraction)
        highlight: Enable syntax highlighting for code blocks
        directive_registry: Custom directive registry for rendering

    Returns:
        HTML string

    Example:
        >>> doc = parse("# Hello")
        >>> html = render(doc)
        >>> print(html)
        <h1 id="hello">Hello</h1>
    """
    registry = directive_registry or create_default_registry()
    renderer = HtmlRenderer(source=source, highlight=highlight, directive_registry=registry)
    return renderer.render(doc)


class Markdown:
    """High-level Markdown processor combining parser and renderer.

    Usage:
        >>> md = Markdown()
        >>> html = md("# Hello **World**")
        '<h1 id="hello-world">Hello <strong>World</strong></h1>\\n'

        >>> # Access the AST
        >>> doc = md.parse("# Heading")
        >>> print(doc.children[0].level)
        1

        >>> # Custom directives
        >>> from patitas import DirectiveRegistryBuilder
        >>> builder = DirectiveRegistryBuilder()
        >>> builder.register(MyDirective())
        >>> md = Markdown(directive_registry=builder.build())
    """

    def __init__(
        self,
        *,
        highlight: bool = False,
        plugins: list[str] | None = None,
        directive_registry: DirectiveRegistry | None = None,
    ) -> None:
        """Initialize Markdown processor.

        Args:
            highlight: Enable syntax highlighting for code blocks
            plugins: List of plugin names to enable (e.g., ["table", "math"])
            directive_registry: Custom directive registry (uses defaults if None)
        """
        self._highlight = highlight
        self._plugins = plugins or []
        self._directive_registry = directive_registry or create_default_registry()

    def __call__(self, source: str) -> str:
        """Parse and render Markdown in one call.

        Args:
            source: Markdown source text

        Returns:
            HTML string
        """
        doc = self.parse(source)
        renderer = HtmlRenderer(
            source=source,
            highlight=self._highlight,
            directive_registry=self._directive_registry,
        )
        return renderer.render(doc)

    def parse(self, source: str, *, source_file: str | None = None) -> Document:
        """Parse Markdown source into AST.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages

        Returns:
            Document AST root node
        """
        parser = Parser(
            source,
            source_file=source_file,
            directive_registry=self._directive_registry,
        )
        blocks = parser.parse()
        # Wrap blocks in a Document
        loc = SourceLocation(
            lineno=1,
            col_offset=1,
            offset=0,
            end_offset=len(source),
            source_file=source_file,
        )
        return Document(location=loc, children=tuple(blocks))

    def render(self, doc: Document, *, source: str = "") -> str:
        """Render AST to HTML.

        Args:
            doc: Document AST to render
            source: Original source (for zero-copy code extraction)

        Returns:
            HTML string
        """
        renderer = HtmlRenderer(
            source=source,
            highlight=self._highlight,
            directive_registry=self._directive_registry,
        )
        return renderer.render(doc)


__all__ = [
    # Version
    "__version__",
    # Core API
    "parse",
    "render",
    "Markdown",
    # Parser components
    "Parser",
    "Lexer",
    "HtmlRenderer",
    # Directive extensibility
    "DirectiveRegistry",
    "DirectiveRegistryBuilder",
    "create_default_registry",
    "create_registry_with_defaults",
    # Location
    "SourceLocation",
    # Tokens
    "Token",
    "TokenType",
    # Block nodes
    "Block",
    "Document",
    "Heading",
    "Paragraph",
    "FencedCode",
    "IndentedCode",
    "BlockQuote",
    "List",
    "ListItem",
    "ThematicBreak",
    "HtmlBlock",
    "Directive",
    "Table",
    "TableRow",
    "TableCell",
    "MathBlock",
    "FootnoteDef",
    # Inline nodes
    "Inline",
    "Text",
    "Emphasis",
    "Strong",
    "Strikethrough",
    "Link",
    "Image",
    "CodeSpan",
    "LineBreak",
    "SoftBreak",
    "HtmlInline",
    "Role",
    "Math",
    "FootnoteRef",
]
