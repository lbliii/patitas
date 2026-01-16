"""Recursive descent parser producing typed AST.

Consumes token stream from Lexer and builds typed AST nodes.
Produces immutable (frozen) dataclass nodes for thread-safety.

Architecture:
The parser uses a mixin-based design for separation of concerns:
- `TokenNavigationMixin`: Token stream traversal
- `InlineParsingMixin`: Inline content (emphasis, links, code spans)
- `BlockParsingMixin`: Block-level content (paragraphs, lists, tables)

Thread Safety:
- Parser produces immutable AST (frozen dataclasses)
- Configuration is read from ContextVar (thread-local)
- Safe to share AST across threads

"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from patitas.config import ParseConfig, get_parse_config
from patitas.lexer import Lexer
from patitas.location import SourceLocation
from patitas.nodes import Block, FencedCode
from patitas.parsing import (
    BlockParsingMixin,
    InlineParsingMixin,
    TokenNavigationMixin,
)
from patitas.parsing.containers import ContainerStack
from patitas.parsing.inline.links import _normalize_label, _process_escapes
from patitas.parsing.compiled_dispatch import get_dispatcher
from patitas.parsing.ultra_fast import can_use_ultra_fast, parse_ultra_simple
from patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from patitas.directives.registry import DirectiveRegistry


class Parser(
    TokenNavigationMixin,
    InlineParsingMixin,
    BlockParsingMixin,
):
    """Recursive descent parser for Markdown.

    Consumes tokens from Lexer and builds typed AST.

    Architecture:
        Uses mixin inheritance to separate concerns while maintaining
        a single entry point. Each mixin handles one aspect of the grammar:

        - `TokenNavigationMixin`: Token stream access, advance, peek
        - `InlineParsingMixin`: Emphasis, links, code spans, etc.
        - `BlockParsingMixin`: Lists, tables, code blocks, directives, etc.

    Usage:
            >>> parser = Parser("# Hello\n\nWorld")
            >>> ast = parser.parse()
            >>> ast[0]
        Heading(level=1, children=(Text(content='Hello'),), ...)

    Thread Safety:
        Parser instances are single-use and not thread-safe. Create one per
        parse operation. Configuration is read from ContextVar (thread-local).
        The resulting AST is immutable and thread-safe.

    Configuration:
        Parser reads configuration from ContextVar instead of instance attributes.
        This provides:
        - 50% smaller memory footprint (9 vs 18 slots)
        - Faster instantiation (no config copying)
        - Automatic config inheritance for sub-parsers
        - Thread-safe by design

    """

    __slots__ = (
        # Per-parse state only (9 slots, was 18)
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        # Directive stack (per-parse state)
        "_directive_stack",
        # Link reference definitions (per-document state)
        "_link_refs",
        # Container stack for tracking nesting context
        "_containers",
        # Setext heading control - disabled for blockquote lazy continuation content
        "_allow_setext_headings",
    )

    def __init__(
        self,
        source: str,
        source_file: str | None = None,
    ) -> None:
        """Initialize parser with source text.

        Configuration is read from ContextVar, not passed as parameters.
        Use set_parse_config() or parse_config_context() before creating
        a Parser if you need non-default configuration.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages

        """
        self._source = source
        self._source_file = source_file
        self._tokens: list[Token] = []
        self._pos = 0
        self._current: Token | None = None

        # Link reference definitions: label (lowercase) -> (url, title)
        self._link_refs: dict[str, tuple[str, str]] = {}

        # Directive stack (per-parse state)
        self._directive_stack: list[str] = []

        # Container stack for tracking nesting context
        # Initialized to document-level frame by default
        self._containers = ContainerStack()

        # Setext heading control - can be disabled for blockquote lazy continuation
        self._allow_setext_headings = True

    def _reinit(self, source: str, source_file: str | None = None) -> None:
        """Reinitialize parser for reuse (enables pooling).

        Resets all per-parse state while keeping the instance allocated.
        This enables frameworks like Bengal to pool Parser instances and
        avoid allocation overhead for high-volume parsing.

        Args:
            source: New Markdown source text
            source_file: Optional source file path for error messages

        Usage (in Bengal's ParserPool):
            if pool:
                parser = pool.pop()
                parser._reinit(source, source_file)
            else:
                parser = Parser(source, source_file)

        Thread Safety:
            Parser instances are single-use per thread. Pooling is thread-local.

        """
        self._source = source
        self._source_file = source_file
        self._tokens = []
        self._pos = 0
        self._current = None
        self._link_refs = {}
        self._directive_stack = []
        self._containers = ContainerStack()
        self._allow_setext_headings = True

    # =========================================================================
    # Configuration Properties (read from ContextVar)
    # =========================================================================
    # These properties provide backward-compatible access to config fields.
    # Config is read from thread-local ContextVar, not instance attributes.
    # =========================================================================

    @property
    def _config(self) -> ParseConfig:
        """Get current parse configuration (thread-local)."""
        return get_parse_config()

    @property
    def _tables_enabled(self) -> bool:
        """Whether GFM table parsing is enabled."""
        return self._config.tables_enabled

    @property
    def _strikethrough_enabled(self) -> bool:
        """Whether ~~strikethrough~~ syntax is enabled."""
        return self._config.strikethrough_enabled

    @property
    def _task_lists_enabled(self) -> bool:
        """Whether - [ ] task list items are enabled."""
        return self._config.task_lists_enabled

    @property
    def _footnotes_enabled(self) -> bool:
        """Whether [^ref] footnote references are enabled."""
        return self._config.footnotes_enabled

    @property
    def _math_enabled(self) -> bool:
        """Whether $inline$ and $$block$$ math is enabled."""
        return self._config.math_enabled

    @property
    def _autolinks_enabled(self) -> bool:
        """Whether automatic URL linking is enabled."""
        return self._config.autolinks_enabled

    @property
    def _directive_registry(self) -> "DirectiveRegistry | None":
        """Registry for directive handlers."""
        return self._config.directive_registry

    @property
    def _strict_contracts(self) -> bool:
        """Whether to raise errors on directive contract violations."""
        return self._config.strict_contracts

    @property
    def _text_transformer(self) -> Callable[[str], str] | None:
        """Optional callback to transform plain text lines."""
        return self._config.text_transformer

    def parse(self) -> Sequence[Block]:
        """Parse source into AST blocks.

        Returns:
            Sequence of Block nodes

        Thread Safety:
            Returns immutable AST (frozen dataclasses).
        """
        # Tokenize source
        lexer = Lexer(self._source, self._source_file, text_transformer=self._text_transformer)
        self._tokens = list(lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None

        # ULTRA-FAST PATH: Documents with only paragraphs and blank lines
        # Covers ~47.5% of CommonMark spec, ~60-80% of real-world docs
        # Bypasses all block-level decision logic for maximum speed
        if can_use_ultra_fast(self._tokens):
            return parse_ultra_simple(self._tokens, self._parse_inline)

        # COMPILED DISPATCH: Pattern-specific parsers for common patterns
        # Covers ~58% of CommonMark spec with 16.5x average speedup
        # Only used for patterns that don't need link reference collection
        dispatcher = get_dispatcher()
        pattern_parser = dispatcher.get_parser(self._tokens)
        if pattern_parser is not None:
            # Check if pattern needs link refs (has LINK_REFERENCE_DEF tokens)
            has_link_refs = any(
                tok.type == TokenType.LINK_REFERENCE_DEF for tok in self._tokens
            )
            if not has_link_refs:
                # Fast path: use pattern-specific parser
                return pattern_parser(self._tokens, self._parse_inline)

        # First pass: collect link reference definitions
        # These are needed before inline parsing to resolve [text][ref] patterns
        # Note: CommonMark 6.1 says link reference definitions cannot interrupt paragraphs.
        in_paragraph = False

        for token in self._tokens:
            if token.type == TokenType.LINK_REFERENCE_DEF:
                if not in_paragraph:
                    # Value format: label|url|title
                    parts = token.value.split("|", 2)
                    if len(parts) >= 2:
                        raw_label = parts[0]
                        # Skip labels containing unescaped '[' (e.g., ref[])
                        if "[" in raw_label.replace("\\[", ""):
                            continue
                        label = _normalize_label(raw_label)
                        # CommonMark 6.1: "If there are several link reference definitions
                        # with the same case-insensitive label, the first one is used."
                        if label not in self._link_refs:
                            # Process backslash escapes in URL and title (CommonMark 6.1)
                            url = _process_escapes(parts[1])
                            title = _process_escapes(parts[2]) if len(parts) > 2 else ""
                            self._link_refs[label] = (url, title)
                # Link ref defs themselves terminate any preceding paragraph
                in_paragraph = False
            elif token.type in (TokenType.PARAGRAPH_LINE, TokenType.INDENTED_CODE):
                # Both PARAGRAPH_LINE and INDENTED_CODE can be part of a paragraph
                in_paragraph = True
            elif token.type == TokenType.BLANK_LINE:
                in_paragraph = False
            elif token.type in (
                TokenType.ATX_HEADING,
                TokenType.THEMATIC_BREAK,
                TokenType.FENCED_CODE_START,
                TokenType.BLOCK_QUOTE_MARKER,
                TokenType.LIST_ITEM_MARKER,
                TokenType.HTML_BLOCK,
                TokenType.DIRECTIVE_OPEN,
                TokenType.FOOTNOTE_DEF,
            ):
                # Most block-level elements terminate a paragraph
                in_paragraph = False

        # Parse blocks
        blocks: list[Block] = []
        while not self._at_end():
            block = self._parse_block()
            if block is not None:
                blocks.append(block)

        return tuple(blocks)

    def _parse_nested_content(
        self,
        content: str,
        location: SourceLocation,
        *,
        allow_setext_headings: bool = True,
    ) -> tuple[Block, ...]:
        """Parse nested content as blocks (for block quotes, list items).

        Creates a sub-parser to handle nested block-level content.
        Configuration is automatically inherited via ContextVar—no copying needed!

        Args:
            content: The markdown content to parse as blocks
            location: Source location for error reporting
            allow_setext_headings: If False, disable setext heading detection
                (used for blockquote content with lazy continuation lines)

        Returns:
            Tuple of Block nodes

        Thread Safety:
            Sub-parser reads config from the same ContextVar as parent,
            ensuring consistent configuration without manual copying.

        """
        if not content.strip():
            return ()

        # Create sub-parser (config inherited automatically via ContextVar!)
        sub_parser = Parser(content, self._source_file)

        # Setext heading control (per-parse state, not config)
        sub_parser._allow_setext_headings = allow_setext_headings

        # Share link reference definitions (document-wide state)
        sub_parser._link_refs = self._link_refs

        blocks = sub_parser.parse()

        # Fix up FencedCode nodes: their source_start/source_end are relative
        # to `content`, not the original source. Add content_override so
        # get_code() returns the correct content.
        fixed_blocks = []
        for block in blocks:
            if isinstance(block, FencedCode) and block.content_override is None:
                # Extract code from sub-parser's source (content)
                code = block.get_code(content)
                fixed_block = FencedCode(
                    location=block.location,
                    source_start=block.source_start,
                    source_end=block.source_end,
                    info=block.info,
                    marker=block.marker,
                    fence_indent=block.fence_indent,
                    content_override=code,
                )
                fixed_blocks.append(fixed_block)
            else:
                fixed_blocks.append(block)

        return tuple(fixed_blocks)
