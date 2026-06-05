"""Unit coverage for the simple-list fast path (``patitas.parsing.blocks.list.fast_path``).

WHY THESE ARE UNIT TESTS, NOT PUBLIC-API TESTS
----------------------------------------------
This module is currently **unreachable through the public API**. The fast path
is only invoked from ``ListParsingMixin._parse_list`` behind the guard::

    parent_indent == -1 and not self._containers._stack and is_simple_list(...)

but ``ContainerStack`` *always* holds a root ``DOCUMENT`` frame during real
parsing (see ``ContainerStack.__post_init__`` -- "stack[0] is always
DOCUMENT"), so ``not self._containers._stack`` is never true. Independently, a
document that contains *only* a simple flat list is intercepted even earlier by
``parse_simple_flat_list`` in ``pattern_parsers.py`` (whole-document pattern
dispatch). The net effect is that ``fast_path.parse_simple_list`` is never
executed via ``Markdown()`` / ``parse()``. This was verified empirically while
writing issue #28 and is documented in that PR.

The functions are nonetheless real, correct, and worth pinning: these tests
exercise them directly and assert their AST output. They build tokens with the
real ``Lexer`` (no fabricated token internals) so the contract under test
matches what production tokenization produces.
"""

import pytest

from patitas.config import ParseConfig, reset_parse_config, set_parse_config
from patitas.directives.registry import create_default_registry
from patitas.lexer import Lexer
from patitas.nodes import Paragraph, Text
from patitas.parsing.blocks.list.fast_path import (
    _is_complex_content,
    is_simple_list,
    parse_simple_list,
)
from patitas.tokens import TokenType


@pytest.fixture(autouse=True)
def _parse_config():
    set_parse_config(ParseConfig(directive_registry=create_default_registry()))
    yield
    reset_parse_config()


def _tokens(src: str) -> list:
    return list(Lexer(src).tokenize())


def _first_marker(tokens: list) -> int:
    for i, tok in enumerate(tokens):
        if tok.type == TokenType.LIST_ITEM_MARKER:
            return i
    return 0


def _fake_inline(text: str, loc) -> tuple:
    return (Text(location=loc, content=text),)


def _item_texts(node) -> list[str]:
    texts: list[str] = []
    for item in node.items:
        if item.children and isinstance(item.children[0], Paragraph):
            inner = item.children[0].children
            texts.append(inner[0].content if inner else "")
        else:
            texts.append("")
    return texts


class TestIsSimpleList:
    def test_recognises_simple_bullet_list(self) -> None:
        toks = _tokens("- a\n- b\n- c\n")
        assert is_simple_list(toks, _first_marker(toks)) is True

    def test_recognises_simple_ordered_list(self) -> None:
        toks = _tokens("1. x\n2. y\n")
        assert is_simple_list(toks, _first_marker(toks)) is True

    def test_rejects_indented_first_marker(self) -> None:
        toks = _tokens("  - indented\n")
        assert is_simple_list(toks, _first_marker(toks)) is False

    def test_rejects_html_content(self) -> None:
        toks = _tokens("- <div>raw</div>\n")
        assert is_simple_list(toks, _first_marker(toks)) is False

    def test_rejects_when_start_is_not_a_marker(self) -> None:
        toks = _tokens("plain paragraph\n")
        assert is_simple_list(toks, 0) is False

    def test_rejects_out_of_range_start(self) -> None:
        toks = _tokens("- a\n")
        assert is_simple_list(toks, len(toks) + 5) is False


class TestParseSimpleList:
    def test_unordered_items_and_tightness(self) -> None:
        toks = _tokens("- a\n- b\n- c\n")
        node, pos = parse_simple_list(toks, _first_marker(toks), _fake_inline)
        assert node.ordered is False
        assert node.start == 1
        assert node.tight is True
        assert _item_texts(node) == ["a", "b", "c"]
        assert pos == len(toks) or toks[pos].type == TokenType.EOF

    def test_ordered_list_preserves_marker(self) -> None:
        toks = _tokens("1. first\n2. second\n")
        node, _ = parse_simple_list(toks, _first_marker(toks), _fake_inline)
        assert node.ordered is True
        assert _item_texts(node) == ["first", "second"]

    def test_ordered_start_number_is_honoured(self) -> None:
        toks = _tokens("3. third\n4. fourth\n")
        node, _ = parse_simple_list(toks, _first_marker(toks), _fake_inline)
        assert node.ordered is True
        assert node.start == 3
        assert _item_texts(node) == ["third", "fourth"]


class TestIsComplexContent:
    @pytest.mark.parametrize(
        "content",
        ["<div>", "> quote", "- nested", "1. ordered", "```py", "~~~", "===", "---"],
    )
    def test_flags_complex_content(self, content: str) -> None:
        assert _is_complex_content(content) is True

    @pytest.mark.parametrize("content", ["", "plain text", "a normal sentence."])
    def test_allows_simple_content(self, content: str) -> None:
        assert _is_complex_content(content) is False


class TestParseSimpleListBoundaries:
    def test_loose_list_with_blank_lines_is_not_tight(self) -> None:
        # Blank lines between items emit BLANK_LINE tokens -> loose list.
        toks = _tokens("- a\n\n- b\n\n- c\n")
        node, _ = parse_simple_list(toks, _first_marker(toks), _fake_inline)
        assert node.tight is False
        assert _item_texts(node) == ["a", "b", "c"]

    def test_different_marker_type_ends_the_list(self) -> None:
        # "- a" then "* b": different bullet char ends the first list.
        toks = _tokens("- a\n* b\n")
        start = _first_marker(toks)
        node, pos = parse_simple_list(toks, start, _fake_inline)
        assert len(node.items) == 1
        assert _item_texts(node) == ["a"]
        # Parsing stops at the second (different) marker, not the EOF.
        assert toks[pos].type == TokenType.LIST_ITEM_MARKER
