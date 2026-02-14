"""Tests for patitas.serialization — AST JSON round-trip."""

import json

from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    CodeSpan,
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
from patitas.serialization import from_dict, from_json, to_dict, to_json

_LOC = SourceLocation(lineno=1, col_offset=0)


def _doc(*blocks) -> Document:  # type: ignore[no-untyped-def]
    return Document(location=_LOC, children=tuple(blocks))


def _para(*inlines) -> Paragraph:  # type: ignore[no-untyped-def]
    return Paragraph(location=_LOC, children=tuple(inlines))


def _text(content: str) -> Text:
    return Text(location=_LOC, content=content)


def _heading(level: int, text: str) -> Heading:
    return Heading(
        location=_LOC,
        level=level,  # type: ignore[arg-type]
        children=(Text(location=_LOC, content=text),),
    )


class TestRoundTrip:
    """Verify round-trip serialization for all node types."""

    def test_text(self) -> None:
        doc = _doc(_para(_text("hello")))
        assert from_dict(to_dict(doc)) == doc

    def test_heading(self) -> None:
        doc = _doc(_heading(2, "Title"))
        assert from_dict(to_dict(doc)) == doc

    def test_emphasis(self) -> None:
        doc = _doc(_para(Emphasis(location=_LOC, children=(_text("em"),))))
        assert from_dict(to_dict(doc)) == doc

    def test_strong(self) -> None:
        doc = _doc(_para(Strong(location=_LOC, children=(_text("bold"),))))
        assert from_dict(to_dict(doc)) == doc

    def test_strikethrough(self) -> None:
        doc = _doc(_para(Strikethrough(location=_LOC, children=(_text("del"),))))
        assert from_dict(to_dict(doc)) == doc

    def test_link(self) -> None:
        link = Link(
            location=_LOC,
            url="https://example.com",
            title="Ex",
            children=(_text("click"),),
        )
        doc = _doc(_para(link))
        assert from_dict(to_dict(doc)) == doc

    def test_image(self) -> None:
        doc = _doc(_para(Image(location=_LOC, url="img.png", alt="photo", title="My photo")))
        assert from_dict(to_dict(doc)) == doc

    def test_code_span(self) -> None:
        doc = _doc(_para(CodeSpan(location=_LOC, code="x = 1")))
        assert from_dict(to_dict(doc)) == doc

    def test_line_break(self) -> None:
        doc = _doc(_para(LineBreak(location=_LOC)))
        assert from_dict(to_dict(doc)) == doc

    def test_soft_break(self) -> None:
        doc = _doc(_para(SoftBreak(location=_LOC)))
        assert from_dict(to_dict(doc)) == doc

    def test_html_inline(self) -> None:
        doc = _doc(_para(HtmlInline(location=_LOC, html="<br>")))
        assert from_dict(to_dict(doc)) == doc

    def test_role(self) -> None:
        doc = _doc(_para(Role(location=_LOC, name="ref", content="target")))
        assert from_dict(to_dict(doc)) == doc

    def test_math_inline(self) -> None:
        doc = _doc(_para(Math(location=_LOC, content="x^2")))
        assert from_dict(to_dict(doc)) == doc

    def test_footnote_ref(self) -> None:
        doc = _doc(_para(FootnoteRef(location=_LOC, identifier="1")))
        assert from_dict(to_dict(doc)) == doc

    def test_fenced_code(self) -> None:
        code = FencedCode(location=_LOC, source_start=0, source_end=10, info="python")
        doc = _doc(code)
        assert from_dict(to_dict(doc)) == doc

    def test_fenced_code_with_override(self) -> None:
        code = FencedCode(
            location=_LOC,
            source_start=0,
            source_end=10,
            info="python",
            content_override="print('hi')",
        )
        doc = _doc(code)
        assert from_dict(to_dict(doc)) == doc

    def test_indented_code(self) -> None:
        doc = _doc(IndentedCode(location=_LOC, code="x = 1"))
        assert from_dict(to_dict(doc)) == doc

    def test_block_quote(self) -> None:
        doc = _doc(BlockQuote(location=_LOC, children=(_para(_text("quoted")),)))
        assert from_dict(to_dict(doc)) == doc

    def test_list(self) -> None:
        item = ListItem(location=_LOC, children=(_para(_text("item")),))
        lst = List(location=_LOC, items=(item,), ordered=True, start=1, tight=True)
        doc = _doc(lst)
        assert from_dict(to_dict(doc)) == doc

    def test_thematic_break(self) -> None:
        doc = _doc(ThematicBreak(location=_LOC))
        assert from_dict(to_dict(doc)) == doc

    def test_html_block(self) -> None:
        doc = _doc(HtmlBlock(location=_LOC, html="<div>hi</div>"))
        assert from_dict(to_dict(doc)) == doc

    def test_math_block(self) -> None:
        doc = _doc(MathBlock(location=_LOC, content="E = mc^2"))
        assert from_dict(to_dict(doc)) == doc

    def test_footnote_def(self) -> None:
        fndef = FootnoteDef(location=_LOC, identifier="1", children=(_para(_text("note")),))
        doc = _doc(fndef)
        assert from_dict(to_dict(doc)) == doc

    def test_table(self) -> None:
        cell = TableCell(location=_LOC, children=(_text("A"),), is_header=True, align="left")
        row = TableRow(location=_LOC, cells=(cell,), is_header=True)
        table = Table(location=_LOC, head=(row,), body=(), alignments=("left",))
        doc = _doc(table)
        assert from_dict(to_dict(doc)) == doc

    def test_empty_document(self) -> None:
        doc = _doc()
        assert from_dict(to_dict(doc)) == doc

    def test_complex_document(self) -> None:
        doc = _doc(
            _heading(1, "Title"),
            _para(_text("Hello "), Strong(location=_LOC, children=(_text("World"),))),
            BlockQuote(location=_LOC, children=(_para(_text("quoted")),)),
            FencedCode(location=_LOC, source_start=0, source_end=5, info="python"),
        )
        assert from_dict(to_dict(doc)) == doc


class TestJsonRoundTrip:
    def test_json_round_trip(self) -> None:
        doc = _doc(_heading(1, "Hello"), _para(_text("World")))
        json_str = to_json(doc)
        restored = from_json(json_str)
        assert restored == doc

    def test_json_deterministic(self) -> None:
        doc = _doc(_heading(1, "Hello"))
        assert to_json(doc) == to_json(doc)

    def test_json_valid(self) -> None:
        doc = _doc(_para(_text("test")))
        data = json.loads(to_json(doc))
        assert data["_type"] == "Document"

    def test_json_with_indent(self) -> None:
        doc = _doc(_para(_text("test")))
        indented = to_json(doc, indent=2)
        assert "\n" in indented
        assert from_json(indented) == doc


class TestErrorHandling:
    def test_missing_type_field(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Missing '_type'"):
            from_dict({"children": []})

    def test_unknown_type(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Unknown node type"):
            from_dict({"_type": "UnknownNode"})

    def test_from_json_non_document(self) -> None:
        import pytest

        text_json = json.dumps(to_dict(_text("hello")))
        with pytest.raises(ValueError, match="Expected Document"):
            from_json(text_json)
