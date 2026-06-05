"""Unit coverage for the block-quote token-reuse path
(``patitas.parsing.blocks.quote_token_reuse``).

WHY THESE ARE UNIT TESTS, NOT PUBLIC-API TESTS
----------------------------------------------
This module is **unreachable through the public API**, and its guard function is
additionally **buggy**. ``can_use_token_reuse`` initialises
``saw_marker_on_line = True`` and then begins its scan *at* the first
``BLOCK_QUOTE_MARKER`` (``pos = start_pos``) instead of *after* it. On the very
first iteration the first marker is therefore treated as "a second marker on the
same line" and the function returns ``False``. As a result it returns ``False``
for *every* block-quote input (verified empirically for issue #28), so
``_parse_block_quote`` in ``blocks/core.py`` never dispatches to
``parse_blockquote_with_token_reuse``. (Even if the guard were fixed, the
``is_simple_block_quote`` fast path -- checked first -- already absorbs the
multi-line/multi-paragraph quotes this module targets.)

These tests pin the real behaviour of the *parsing* function (which is itself
correct) using tokens produced by the real ``Lexer``, and exhaustively cover the
``_is_complex_blockquote_content`` classifier. The guard bug is documented in the
issue #28 PR rather than silently "fixed" here, to keep this change scoped to
coverage + harness work.
"""

import pytest

from patitas.config import ParseConfig, reset_parse_config, set_parse_config
from patitas.directives.registry import create_default_registry
from patitas.lexer import Lexer
from patitas.nodes import Paragraph, Text
from patitas.parsing.blocks.quote_token_reuse import (
    _is_complex_blockquote_content,
    can_use_token_reuse,
    parse_blockquote_with_token_reuse,
)
from patitas.tokens import TokenType


@pytest.fixture(autouse=True)
def _parse_config():
    set_parse_config(ParseConfig(directive_registry=create_default_registry()))
    yield
    reset_parse_config()


def _tokens(src: str) -> list:
    return list(Lexer(src).tokenize())


def _first_quote_marker(tokens: list) -> int:
    for i, tok in enumerate(tokens):
        if tok.type == TokenType.BLOCK_QUOTE_MARKER:
            return i
    return 0


def _fake_inline(text: str, loc) -> tuple:
    return (Text(location=loc, content=text),)


def _paragraph_texts(node) -> list[str]:
    return [
        child.children[0].content
        for child in node.children
        if isinstance(child, Paragraph) and child.children
    ]


class TestCanUseTokenReuseGuard:
    """The guard currently rejects everything; pin that documented behaviour."""

    def test_returns_false_when_start_is_not_a_marker(self) -> None:
        toks = _tokens("plain text\n")
        assert can_use_token_reuse(toks, 0) is False

    def test_returns_false_for_out_of_range_start(self) -> None:
        toks = _tokens("> q\n")
        assert can_use_token_reuse(toks, len(toks) + 3) is False

    def test_guard_rejects_simple_multiline_quote_due_to_off_by_one(self) -> None:
        # Documents the known guard bug (see module docstring): a perfectly
        # simple multi-line quote is still rejected.
        toks = _tokens("> a\n> b\n")
        assert can_use_token_reuse(toks, _first_quote_marker(toks)) is False


class TestParseBlockquoteWithTokenReuse:
    """The parsing function itself is correct; exercise it directly."""

    def test_single_line_quote(self) -> None:
        toks = _tokens("> hello\n")
        node, pos = parse_blockquote_with_token_reuse(toks, _first_quote_marker(toks), _fake_inline)
        assert _paragraph_texts(node) == ["hello"]
        assert pos == len(toks) or toks[pos].type == TokenType.EOF

    def test_multiline_quote_joins_lines(self) -> None:
        toks = _tokens("> a\n> b\n")
        node, _ = parse_blockquote_with_token_reuse(toks, _first_quote_marker(toks), _fake_inline)
        # Continuation lines under markers join into one paragraph.
        assert _paragraph_texts(node) == ["a\nb"]


class TestIsComplexBlockquoteContent:
    @pytest.mark.parametrize(
        "content",
        [
            "<div>",
            "> nested",
            "- list",
            "1. ordered",
            "```",
            "# heading",
            "--- ",
            "    indented code",
        ],
    )
    def test_flags_complex_content(self, content: str) -> None:
        assert _is_complex_blockquote_content(content) is True

    @pytest.mark.parametrize("content", ["", "plain prose", "a normal sentence."])
    def test_allows_simple_content(self, content: str) -> None:
        assert _is_complex_blockquote_content(content) is False


class TestParseBlockquoteMultiParagraph:
    """Multi-paragraph splitting path.

    The real ``Lexer`` does not emit ``BLANK_LINE`` tokens *inside* a quote (an
    empty ``>`` line becomes a lone ``BLOCK_QUOTE_MARKER``), so this branch is
    not reachable from production tokenization. We exercise it against the
    function's documented contract using a constructed, well-formed token list
    that contains a separating ``BLANK_LINE``.
    """

    def test_blank_line_token_splits_into_two_paragraphs(self) -> None:
        from patitas.tokens import Token
        from patitas.tokens import TokenType as TT

        def _tok(tt: TT, value: str, line: int) -> Token:
            return Token(tt, value, line, 1, 0, len(value))

        toks = [
            _tok(TT.BLOCK_QUOTE_MARKER, ">", 1),
            _tok(TT.PARAGRAPH_LINE, "para one", 1),
            _tok(TT.BLANK_LINE, "", 2),
            _tok(TT.BLOCK_QUOTE_MARKER, ">", 3),
            _tok(TT.PARAGRAPH_LINE, "para two", 3),
            _tok(TT.EOF, "", 4),
        ]
        node, pos = parse_blockquote_with_token_reuse(toks, 0, _fake_inline)
        assert _paragraph_texts(node) == ["para one", "para two"]
        assert toks[pos].type == TT.EOF
