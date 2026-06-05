"""Protocols defining the parser mixin contracts.

These protocols formalize the implicit contracts between parser mixins.
Each mixin documents "Required Host Attributes/Methods" in its docstring;
this module turns those requirements into type-checkable Protocol classes.

Usage:
    Mixin methods that call across mixin boundaries annotate ``self`` as the
    narrowest protocol they require::

        def _parse_block(self: ParserHost) -> Block | None:
            token = self._current  # type-checked via ParserHost
            ...

    Use ``TokenNavHost`` for pure token navigation, ``InlineParsingHost`` for
    inline content parsing, ``BlockParsingHost`` for block-level parsing, and
    ``ParserHost`` when a method needs the full parser surface (config,
    container stack, cross-domain dispatch, nesting guards, etc.).

    Type checkers (ty) verify that the concrete Parser class satisfies all
    protocol requirements at composition time, and that ``self``-typed methods
    only touch members the chosen protocol guarantees.

Thread Safety:
    Protocols are purely structural -- no runtime overhead. The annotations are
    runtime-inert and never change behaviour.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from patitas.location import SourceLocation
from patitas.nodes import (
    Block,
    BlockQuote,
    Directive,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    Link,
    List,
    ListItem,
    Math,
    Paragraph,
    Role,
    Table,
    ThematicBreak,
)
from patitas.parsing.containers import ContainerStack
from patitas.tokens import Token

if TYPE_CHECKING:
    from patitas.config import ParseConfig
    from patitas.directives.registry import DirectiveRegistry
    from patitas.parsing.inline.match_registry import MatchRegistry
    from patitas.parsing.inline.tokens import InlineToken


@runtime_checkable
class TokenNavHost(Protocol):
    """Contract for token stream navigation.

    Provided by: TokenNavigationMixin
    Required by: BlockParsingCoreMixin, ListParsingMixin, InlineParsingCoreMixin
    """

    _tokens: list[Token]
    _tokens_len: int
    _pos: int
    _current: Token | None
    _source: str
    _line_starts: list[int] | None

    def _at_end(self) -> bool: ...
    def _advance(self) -> Token | None: ...
    def _peek(self, offset: int = 1) -> Token | None: ...
    def _line_start_for_offset(self, offset: int) -> int: ...
    def _get_line_at(self, offset: int) -> str: ...
    def _strip_columns(self, text: str, count: int) -> str: ...


@runtime_checkable
class ConfigHost(Protocol):
    """Contract for parse configuration access.

    Provided by: Parser (config properties read from a ContextVar).
    Required by: mixins that branch on enabled features or recurse with a
    nesting guard.
    """

    _link_refs: dict[str, tuple[str, str]]

    @property
    def _config(self) -> ParseConfig: ...
    @property
    def _tables_enabled(self) -> bool: ...
    @property
    def _strikethrough_enabled(self) -> bool: ...
    @property
    def _task_lists_enabled(self) -> bool: ...
    @property
    def _footnotes_enabled(self) -> bool: ...
    @property
    def _math_enabled(self) -> bool: ...
    @property
    def _autolinks_enabled(self) -> bool: ...
    @property
    def _directive_registry(self) -> DirectiveRegistry | None: ...
    @property
    def _strict_contracts(self) -> bool: ...
    @property
    def _text_transformer(self) -> Callable[[str], str] | None: ...


@runtime_checkable
class InlineParsingHost(TokenNavHost, ConfigHost, Protocol):
    """Contract for inline content parsing.

    Provided by: InlineParsingMixin (composed from core + emphasis + links + special)
    Required by: BlockParsingCoreMixin, ListParsingMixin, and the inline mixins
    themselves (cross-mixin dispatch within inline parsing).
    """

    # Public entry point.
    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]: ...

    # Inline core internals (InlineParsingCoreMixin).
    def _tokenize_inline(self, text: str, location: SourceLocation) -> list[InlineToken]: ...
    def _find_code_span_close(self, text: str, start: int, backtick_count: int) -> int: ...
    def _try_parse_entity(self, text: str, pos: int) -> tuple[str, int] | None: ...
    def _build_inline_ast(
        self,
        tokens: list[InlineToken],
        registry: MatchRegistry,
        location: SourceLocation,
        start: int = 0,
        end: int | None = None,
    ) -> tuple[Inline, ...]: ...

    # Emphasis (EmphasisParsingMixin).
    def _is_left_flanking(self, before: str, after: str, delim: str) -> bool: ...
    def _is_right_flanking(self, before: str, after: str, delim: str) -> bool: ...
    def _is_punctuation(self, char: str) -> bool: ...
    def _process_emphasis(
        self, tokens: list[InlineToken], registry: MatchRegistry | None = None
    ) -> MatchRegistry: ...

    # Links / images / footnote refs (LinkParsingMixin).
    def _try_parse_link(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Link, int] | None: ...
    def _try_parse_image(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Image, int] | None: ...
    def _try_parse_footnote_ref(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[FootnoteRef, int] | None: ...

    # Autolinks / inline HTML / roles / math (SpecialParsingMixin).
    def _try_parse_autolink(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Link, int] | None: ...
    def _try_parse_html_inline(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[HtmlInline, int] | None: ...
    def _try_parse_role(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Role, int] | None: ...
    def _try_parse_math(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Math, int] | None: ...


@runtime_checkable
class BlockParsingHost(TokenNavHost, Protocol):
    """Contract for block-level parsing.

    Provided by: BlockParsingMixin (composed from core + list + table + directive + footnote)
    Required by: ListParsingMixin (calls _parse_block for nested content) and the
    block mixins themselves (cross-mixin dispatch within block parsing).
    """

    # Public dispatch entry points.
    def _parse_block(self) -> Block | None: ...
    def _parse_list(self, parent_indent: int = -1) -> List: ...
    def _parse_directive(self) -> Directive: ...
    def _parse_footnote_def(self) -> FootnoteDef: ...
    def _try_parse_table(self, lines: list[str], location: SourceLocation) -> Table | None: ...

    # Block core internals (BlockParsingCoreMixin).
    def _parse_atx_heading(self) -> Heading: ...
    def _parse_fenced_code(self, override_fence_indent: int | None = None) -> FencedCode: ...
    def _parse_orphaned_fence_content(self) -> Paragraph: ...
    def _parse_orphaned_fence_end(self) -> FencedCode: ...
    def _parse_thematic_break(self) -> ThematicBreak: ...
    def _parse_html_block(self) -> HtmlBlock: ...
    def _parse_block_quote(self) -> BlockQuote: ...
    def _parse_indented_code(self) -> IndentedCode: ...
    def _parse_paragraph(self) -> Paragraph | Table | Heading: ...
    def _is_setext_underline(self, line: str) -> bool: ...


@runtime_checkable
class ParserHost(InlineParsingHost, BlockParsingHost, Protocol):
    """Full parser contract combining all mixin requirements.

    The concrete Parser class must satisfy this protocol. Any class that
    composes TokenNavigationMixin + InlineParsingMixin + BlockParsingMixin
    and provides the required instance attributes will satisfy this protocol.

    Required instance attributes (set in __init__):
        _source: str -- original source text
        _tokens: Sequence[Token] -- token stream from Lexer
        _pos: int -- current position in token stream
        _current: Token | None -- current token (or None at end)
        _containers: ContainerStack -- nesting context tracker
        _link_refs: dict[str, tuple[str, str]] -- link reference definitions
        _allow_setext_headings: bool -- setext heading control
        _directive_stack: list[str] -- directive nesting context
        _nesting_depth: int -- block-container recursion guard
    """

    _containers: ContainerStack
    _allow_setext_headings: bool
    _directive_stack: list[str]
    _nesting_depth: int

    # Nested block parsing (defined on the concrete Parser, not a mixin).
    def _parse_nested_content(
        self,
        content: str,
        location: SourceLocation,
        *,
        allow_setext_headings: bool = True,
    ) -> tuple[Block, ...]: ...

    # List-internal helpers (ListParsingMixin) called via self across methods.
    def _parse_list_item(
        self,
        marker_token: Token,
        start_indent: int,
        content_indent: int,
        ordered: bool,
        bullet_char: str,
        ordered_marker_char: str,
        marker_stripped: str,
    ) -> ListItem: ...
    def _parse_list_item_impl(
        self,
        marker_token: Token,
        start_indent: int,
        content_indent: int,
        ordered: bool,
        bullet_char: str,
        ordered_marker_char: str,
        marker_stripped: str,
    ) -> ListItem: ...
    def _calculate_actual_content_indent(self, tok: Token, marker_stripped: str) -> int: ...
    def _handle_indented_code_in_item(
        self,
        tok: Token,
        marker_token: Token,
        content_lines: list[str],
        item_children: list[Block],
    ) -> str | tuple[list[str], list[Block]]: ...
