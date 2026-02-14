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

from collections.abc import Iterable

from patitas.cache import DictParseCache, ParseCache, hash_config, hash_content
from patitas.config import (
    ParseConfig,
    get_parse_config,
    parse_config_context,
    reset_parse_config,
    set_parse_config,
)
from patitas.context import CONTENT_CONTEXT_MAP, context_paths_for
from patitas.differ import ASTChange, diff_documents
from patitas.directives.registry import (
    DirectiveRegistry,
    DirectiveRegistryBuilder,
    create_default_registry,
    create_registry_with_defaults,
)
from patitas.incremental import parse_incremental
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
from patitas.notebook import parse_notebook
from patitas.parser import Parser
from patitas.profiling import ParseAccumulator, get_parse_accumulator, profiled_parse
from patitas.renderers.html import HtmlRenderer
from patitas.renderers.protocol import ASTRenderer
from patitas.serialization import from_dict, from_json, to_dict, to_json
from patitas.tokens import Token, TokenType
from patitas.visitor import BaseVisitor, transform

__version__ = "0.4.0"


def parse(
    source: str,
    *,
    source_file: str | None = None,
    directive_registry: DirectiveRegistry | None = None,
    cache: ParseCache | None = None,
) -> Document:
    """Parse Markdown source into a typed AST.

    Args:
        source: Markdown source text
        source_file: Optional source file path for error messages
        directive_registry: Custom directive registry (uses defaults if None)
        cache: Optional content-addressed parse cache. When provided, checks cache
            before parsing; on miss, parses and stores result. Cache is bypassed
            when config has text_transformer set. For parallel parsing, use a
            thread-safe cache implementation.

    Returns:
        Document AST root node

    Example:
        >>> doc = parse("# Hello **World**")
        >>> doc.children[0]
        Heading(level=1, ...)

        >>> # With parse cache
        >>> from patitas import DictParseCache
        >>> cache = DictParseCache()
        >>> doc = parse("# Hello", cache=cache)
    """
    from patitas.profiling import get_parse_accumulator

    registry = directive_registry or create_default_registry()

    # Build config and set via ContextVar for thread-safety
    config = ParseConfig(directive_registry=registry)
    set_parse_config(config)

    try:
        if cache is not None:
            config_hash = hash_config(config)
            if config_hash:
                content_hash = hash_content(source)
                cached = cache.get(content_hash, config_hash)
                if cached is not None:
                    return cached

        parser = Parser(source, source_file=source_file)
        blocks = parser.parse()
        # Wrap blocks in a Document
        loc = SourceLocation(
            lineno=1,
            col_offset=1,
            offset=0,
            end_offset=len(source),
            source_file=source_file,
        )
        doc = Document(location=loc, children=tuple(blocks))

        if cache is not None:
            config_hash = hash_config(config)
            if config_hash:
                content_hash = hash_content(source)
                cache.put(content_hash, config_hash, doc)

        # Record profiling metrics if accumulator is active
        acc = get_parse_accumulator()
        if acc is not None:
            acc.record_parse(source_length=len(source), node_count=len(blocks))

        return doc
    finally:
        reset_parse_config()


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

    Thread Safety:
        Uses ContextVar for thread-local configuration. Safe to use multiple
        Markdown instances concurrently from different threads.

    """

    __slots__ = ("_config", "_directive_registry", "_highlight", "_plugins")

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
            plugins: List of plugin names to enable (e.g., ["table", "math"]).
                Use ["all"] to enable all built-in plugins.
            directive_registry: Custom directive registry (uses defaults if None)
        """
        self._highlight = highlight
        self._directive_registry = directive_registry or create_default_registry()

        # Expand "all" to all built-in plugin names
        raw_plugins = plugins or []
        if "all" in raw_plugins:
            from patitas.plugins import BUILTIN_PLUGINS

            self._plugins = list(BUILTIN_PLUGINS.keys())
        else:
            self._plugins = raw_plugins

        # Build immutable config once (thread-safe, reused across calls)
        self._config = ParseConfig(
            tables_enabled="table" in self._plugins,
            strikethrough_enabled="strikethrough" in self._plugins,
            task_lists_enabled="task_lists" in self._plugins,
            footnotes_enabled="footnotes" in self._plugins,
            math_enabled="math" in self._plugins,
            autolinks_enabled="autolinks" in self._plugins,
            directive_registry=self._directive_registry,
        )

    def __call__(self, source: str) -> str:
        """Parse and render Markdown in one call.

        Args:
            source: Markdown source text

        Returns:
            HTML string

        Thread Safety:
            Sets config via ContextVar (thread-local). Safe for concurrent use.

        """
        doc = self.parse(source)  # parse() handles ContextVar set/reset
        renderer = HtmlRenderer(
            source=source,
            highlight=self._highlight,
            directive_registry=self._directive_registry,
        )
        return renderer.render(doc)

    def parse(
        self,
        source: str,
        *,
        source_file: str | None = None,
        cache: ParseCache | None = None,
    ) -> Document:
        """Parse Markdown source into AST.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
            cache: Optional content-addressed parse cache. For parallel parsing,
                use a thread-safe cache implementation.

        Returns:
            Document AST root node

        Thread Safety:
            Sets config via ContextVar (thread-local). Safe for concurrent use.

        """
        # Set config for this parse (thread-local via ContextVar)
        set_parse_config(self._config)

        try:
            if cache is not None:
                config_hash = hash_config(self._config)
                if config_hash:
                    content_hash = hash_content(source)
                    cached = cache.get(content_hash, config_hash)
                    if cached is not None:
                        return cached

            parser = Parser(source, source_file=source_file)
            blocks = parser.parse()
            # Wrap blocks in a Document
            loc = SourceLocation(
                lineno=1,
                col_offset=1,
                offset=0,
                end_offset=len(source),
                source_file=source_file,
            )
            doc = Document(location=loc, children=tuple(blocks))

            if cache is not None:
                config_hash = hash_config(self._config)
                if config_hash:
                    content_hash = hash_content(source)
                    cache.put(content_hash, config_hash, doc)

            return doc
        finally:
            # Reset to default (reuses module-level singleton, no allocation)
            reset_parse_config()

    def parse_many(
        self,
        sources: Iterable[str],
        *,
        source_file: str | None = None,
        cache: ParseCache | None = None,
    ) -> list[Document]:
        """Parse multiple Markdown sources into AST documents.

        Use for batch parsing; avoids per-doc config set/reset.
        Sets config once, parses all, resets once. When cache is provided,
        duplicate sources within the batch hit cache.

        Args:
            sources: Iterable of Markdown source strings
            source_file: Optional source file path for error messages (applies to all)
            cache: Optional content-addressed parse cache. For parallel parsing,
                use a thread-safe cache implementation.

        Returns:
            List of Document AST nodes

        Example:
            >>> md = Markdown()
            >>> docs = md.parse_many(["# Doc 1", "# Doc 2", "# Doc 3"])
        """
        set_parse_config(self._config)
        try:
            config_hash = hash_config(self._config) if cache is not None else ""
            use_cache = cache is not None and config_hash

            result: list[Document] = []
            for source in sources:
                if use_cache:
                    content_hash = hash_content(source)
                    cached = cache.get(content_hash, config_hash)
                    if cached is not None:
                        result.append(cached)
                        continue

                parser = Parser(source, source_file=source_file)
                blocks = parser.parse()
                loc = SourceLocation(
                    lineno=1,
                    col_offset=1,
                    offset=0,
                    end_offset=len(source),
                    source_file=source_file,
                )
                doc = Document(location=loc, children=tuple(blocks))

                if use_cache:
                    content_hash = hash_content(source)
                    cache.put(content_hash, config_hash, doc)

                result.append(doc)
            return result
        finally:
            reset_parse_config()

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


__all__ = [  # noqa: RUF022 — grouped by category for maintainability
    # Version
    "__version__",
    # Core API
    "parse",
    "parse_notebook",
    "render",
    # Parse cache
    "DictParseCache",
    "ParseCache",
    "hash_config",
    "hash_content",
    # Block nodes
    "Block",
    "BlockQuote",
    "Document",
    "FencedCode",
    "FootnoteDef",
    "Heading",
    "HtmlBlock",
    "IndentedCode",
    "List",
    "ListItem",
    "MathBlock",
    "Paragraph",
    "Table",
    "TableCell",
    "TableRow",
    "ThematicBreak",
    # Inline nodes
    "Inline",
    "CodeSpan",
    "Emphasis",
    "FootnoteRef",
    "HtmlInline",
    "Image",
    "LineBreak",
    "Link",
    "Math",
    "Role",
    "SoftBreak",
    "Strikethrough",
    "Strong",
    "Text",
    # Directive extensibility
    "Directive",
    "DirectiveRegistry",
    "DirectiveRegistryBuilder",
    "create_default_registry",
    "create_registry_with_defaults",
    # Parser components
    "Lexer",
    "Parser",
    # Renderer
    "HtmlRenderer",
    "ASTRenderer",
    # Visitor + Transform
    "BaseVisitor",
    "transform",
    # Differ
    "ASTChange",
    "diff_documents",
    # Incremental
    "parse_incremental",
    # Context mapping
    "CONTENT_CONTEXT_MAP",
    "context_paths_for",
    # Profiling
    "ParseAccumulator",
    "profiled_parse",
    "get_parse_accumulator",
    # Serialization
    "to_dict",
    "from_dict",
    "to_json",
    "from_json",
    # Configuration (ContextVar-based)
    "ParseConfig",
    "get_parse_config",
    "set_parse_config",
    "reset_parse_config",
    "parse_config_context",
    # Location
    "SourceLocation",
    # Tokens
    "Token",
    "TokenType",
    # High-level
    "Markdown",
]
