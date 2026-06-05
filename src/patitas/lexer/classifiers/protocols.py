"""Protocol defining the lexer classifier mixin contract.

The :class:`~patitas.lexer.core.Lexer` is composed from many classifier
mixins. Several classifiers dispatch to *sibling* classifiers (for example, a
list marker may be followed by an ATX heading, a fenced code block, or a nested
block quote). ty cannot resolve those cross-mixin calls through a bare ``self``,
so the cross-calling methods annotate ``self`` as ``LexerClassifierHost``.

The annotation is runtime-inert; it never changes behaviour.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from patitas.tokens import Token, TokenType


@runtime_checkable
class LexerClassifierHost(Protocol):
    """Structural contract for the composed Lexer used by classifier mixins."""

    # Token construction / indentation helpers (provided by Lexer core).
    def _make_token(
        self,
        token_type: TokenType,
        value: str,
        start_pos: int,
        *,
        start_col: int | None = None,
        end_pos: int | None = None,
        line_indent: int = -1,
    ) -> Token: ...
    def _expand_tabs(self, text: str, start_col: int = 1) -> str: ...
    def _calc_indent(self, line: str) -> tuple[int, int]: ...

    # Sibling classifiers invoked across mixin boundaries.
    def _try_classify_atx_heading(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None: ...
    def _try_classify_thematic_break(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None: ...
    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0, *, change_mode: bool = True
    ) -> Token | None: ...
    def _try_classify_link_reference_def(
        self, first_line_content: str, line_start: int, indent: int = 0
    ) -> Token | None: ...
    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None: ...
    def _classify_block_quote(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]: ...
    def _yield_list_marker_and_content(
        self, marker: str, remaining: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]: ...
