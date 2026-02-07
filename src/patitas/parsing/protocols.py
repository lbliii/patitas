"""Protocols defining the parser mixin contracts.

These protocols formalize the implicit contracts between parser mixins.
Each mixin documents "Required Host Attributes/Methods" in its docstring;
this module turns those requirements into type-checkable Protocol classes.

Usage:
    Mixin methods that call across mixin boundaries can annotate `self`
    as the protocol they require::

        def _parse_block(self: ParserHost) -> Block | None:
            token = self._current  # type-checked via ParserHost
            ...

    Type checkers (ty, mypy) will verify that the concrete Parser class
    satisfies all protocol requirements at composition time.

Thread Safety:
    Protocols are purely structural — no runtime overhead.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from patitas.location import SourceLocation
from patitas.nodes import (
    Block,
    Directive,
    FootnoteDef,
    Inline,
    List,
    Table,
)
from patitas.parsing.containers import ContainerStack
from patitas.tokens import Token


@runtime_checkable
class TokenNavHost(Protocol):
    """Contract for token stream navigation.

    Provided by: TokenNavigationMixin
    Required by: BlockParsingCoreMixin, ListParsingMixin, InlineParsingCoreMixin
    """

    _tokens: Sequence[Token]
    _pos: int
    _current: Token | None
    _source: str

    def _at_end(self) -> bool: ...
    def _advance(self) -> Token | None: ...
    def _peek(self, offset: int = 1) -> Token | None: ...
    def _get_line_at(self, offset: int) -> str: ...
    def _strip_columns(self, text: str, count: int) -> str: ...


@runtime_checkable
class InlineParsingHost(Protocol):
    """Contract for inline content parsing.

    Provided by: InlineParsingMixin (composed from core + emphasis + links + special)
    Required by: BlockParsingCoreMixin, ListParsingMixin
    """

    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]: ...


@runtime_checkable
class BlockParsingHost(Protocol):
    """Contract for block-level parsing.

    Provided by: BlockParsingMixin (composed from core + list + table + directive + footnote)
    Required by: ListParsingMixin (calls _parse_block for nested content)
    """

    def _parse_block(self) -> Block | None: ...
    def _parse_list(self, parent_indent: int = -1) -> List: ...
    def _parse_directive(self) -> Directive: ...
    def _parse_footnote_def(self) -> FootnoteDef: ...
    def _try_parse_table(
        self, lines: list[str], location: SourceLocation
    ) -> Table | None: ...


@runtime_checkable
class ParserHost(TokenNavHost, InlineParsingHost, BlockParsingHost, Protocol):
    """Full parser contract combining all mixin requirements.

    The concrete Parser class must satisfy this protocol. Any class that
    composes TokenNavigationMixin + InlineParsingMixin + BlockParsingMixin
    and provides the required instance attributes will satisfy this protocol.

    Required instance attributes (set in __init__):
        _source: str — original source text
        _tokens: Sequence[Token] — token stream from Lexer
        _pos: int — current position in token stream
        _current: Token | None — current token (or None at end)
        _containers: ContainerStack — nesting context tracker
        _link_refs: dict[str, tuple[str, str]] — link reference definitions
        _allow_setext_headings: bool — setext heading control
    """

    _containers: ContainerStack
    _link_refs: dict[str, tuple[str, str]]
    _allow_setext_headings: bool
