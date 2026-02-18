"""Tests for sanitization policies."""

from patitas import parse, sanitize
from patitas.location import SourceLocation
from patitas.nodes import (
    Document,
    HtmlBlock,
    HtmlInline,
    Image,
    Link,
    Paragraph,
    Text,
)
from patitas.sanitize import (
    llm_safe,
    normalize_unicode,
    strip_dangerous_urls,
    strip_html,
    strip_html_comments,
    strip_images,
    strip_raw_code,
    strict,
    web_safe,
)

LOC = SourceLocation(lineno=1, col_offset=0)


def _para(text: str) -> Paragraph:
    return Paragraph(location=LOC, children=(Text(location=LOC, content=text),))


class TestStripHtml:
    def test_removes_html_block(self) -> None:
        doc = parse("# Hi\n\n<div>raw</div>\n\nMore")
        clean = strip_html(doc)
        # HtmlBlock removed: Heading + Paragraph("More") only
        assert len(clean.children) == 2
        assert not any(isinstance(c, HtmlBlock) for c in clean.children)

    def test_removes_html_inline(self) -> None:
        doc = parse("Hello <span>world</span> there")
        clean = strip_html(doc)
        # HtmlInline removed from paragraph
        para = clean.children[0]
        assert isinstance(para, Paragraph)
        assert len(para.children) == 3  # Text, (HtmlInline removed), Text


class TestStripDangerousUrls:
    def test_removes_javascript_link(self) -> None:
        doc = parse("[click](javascript:alert(1))")
        clean = strip_dangerous_urls(doc)
        para = clean.children[0]
        assert isinstance(para, Paragraph)
        assert len(para.children) == 0  # Link removed

    def test_removes_data_image(self) -> None:
        doc = parse("![x](data:text/html,<script>)")
        clean = strip_dangerous_urls(doc)
        para = clean.children[0]
        assert len(para.children) == 0

    def test_keeps_https_link(self) -> None:
        doc = parse("[click](https://example.com)")
        clean = strip_dangerous_urls(doc)
        assert len(clean.children[0].children) == 1


class TestNormalizeUnicode:
    def test_strips_zero_width(self) -> None:
        doc = parse("Hello\u200bWorld")  # ZWSP
        clean = normalize_unicode(doc)
        para = clean.children[0]
        text = para.children[0]
        assert isinstance(text, Text)
        assert text.content == "HelloWorld"

    def test_strips_bidi_override(self) -> None:
        doc = parse("A\u202eB")  # RLO
        clean = normalize_unicode(doc)
        para = clean.children[0]
        text = para.children[0]
        assert "\u202e" not in text.content


class TestStripImages:
    def test_replaces_with_alt_text(self) -> None:
        doc = parse("![alt text](img.png)")
        clean = strip_images(doc)
        para = clean.children[0]
        assert len(para.children) == 1
        from patitas.nodes import Text

        assert isinstance(para.children[0], Text)
        assert para.children[0].content == "alt text"


class TestStripRawCode:
    def test_removes_fenced_code(self) -> None:
        doc = parse("# Hi\n\n```py\ncode\n```\n\nMore")
        clean = strip_raw_code(doc)
        from patitas.nodes import FencedCode

        assert not any(isinstance(c, FencedCode) for c in clean.children)

    def test_removes_indented_code(self) -> None:
        doc = parse("# Hi\n\n    code\n\nMore")
        clean = strip_raw_code(doc)
        from patitas.nodes import IndentedCode

        assert not any(isinstance(c, IndentedCode) for c in clean.children)


class TestComposition:
    def test_llm_safe_composes(self) -> None:
        doc = parse("# Hi\n\n<script>x</script>\n\n[j](javascript:y)")
        clean = llm_safe(doc)
        assert not any(isinstance(c, HtmlBlock) for c in clean.children)
        para = clean.children[1]
        assert len(para.children) == 0  # Link removed

    def test_sanitize_convenience(self) -> None:
        doc = parse("# Hi\n\n<div>raw</div>")
        clean = sanitize(doc, policy=llm_safe)
        assert not any(isinstance(c, HtmlBlock) for c in clean.children)


class TestPolicyOr:
    def test_policy_or_chains(self) -> None:
        doc = parse("A <span>B</span> C")
        custom = strip_html
        clean = custom(doc)
        # HtmlInline removed; only Text nodes remain
        from patitas.nodes import HtmlInline

        para = clean.children[0]
        assert not any(isinstance(c, HtmlInline) for c in para.children)
