"""Tests for transform() with node removal (None return)."""

from patitas.location import SourceLocation
from patitas.nodes import (
    Document,
    HtmlBlock,
    HtmlInline,
    Paragraph,
    Text,
)
from patitas.visitor import transform

LOC = SourceLocation(lineno=1, col_offset=0)


def _doc(*children) -> Document:
    return Document(location=LOC, children=tuple(children))


def _para(*inlines) -> Paragraph:
    return Paragraph(location=LOC, children=tuple(inlines))


def _text(s: str) -> Text:
    return Text(location=LOC, content=s)


class TestTransformRemoval:
    def test_remove_html_block(self) -> None:
        doc = _doc(
            _para(_text("a")),
            HtmlBlock(location=LOC, html="<div>x</div>"),
            _para(_text("b")),
        )

        def remove_html(node):
            if isinstance(node, HtmlBlock):
                return None
            return node

        result = transform(doc, remove_html)
        assert len(result.children) == 2
        assert result.children[0].children[0].content == "a"
        assert result.children[1].children[0].content == "b"

    def test_remove_html_inline(self) -> None:
        doc = _doc(_para(_text("a"), HtmlInline(location=LOC, html="<br>"), _text("b")))

        def remove_html(node):
            if isinstance(node, HtmlInline):
                return None
            return node

        result = transform(doc, remove_html)
        para = result.children[0]
        assert len(para.children) == 2  # Two Text nodes
        assert para.children[0].content == "a"
        assert para.children[1].content == "b"

    def test_root_cannot_be_removed(self) -> None:
        doc = _doc(_para(_text("x")))

        def remove_all(node):
            return None

        try:
            transform(doc, remove_all)
            assert False, "Expected TypeError"
        except TypeError as e:
            assert "root" in str(e).lower() or "Document" in str(e)
