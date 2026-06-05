"""Tests for sanitization policies."""

import pytest

from patitas import parse, sanitize
from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    HtmlBlock,
    HtmlInline,
    Link,
    Paragraph,
    Text,
)
from patitas.sanitize import (
    allow_url_schemes,
    limit_depth,
    llm_safe,
    normalize_unicode,
    strict,
    strip_dangerous_urls,
    strip_html,
    strip_images,
    strip_raw_code,
    web_safe,
)


def _links(doc) -> list:
    """All Link nodes in the first paragraph of a parsed doc."""
    if not doc.children:
        return []
    para = doc.children[0]
    return [c for c in getattr(para, "children", ()) if isinstance(c, Link)]


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
        # Chain strip_html | normalize_unicode; both transformations apply
        doc = parse("A\u200b <span>B</span> C")
        custom = strip_html | normalize_unicode
        clean = custom(doc)
        para = clean.children[0]
        assert not any(isinstance(c, HtmlInline) for c in para.children)
        for child in para.children:
            if isinstance(child, Text):
                assert "\u200b" not in child.content


class TestDangerousUrlObfuscationBypass:
    """The scheme check must see through entity/whitespace/case obfuscation."""

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "&#106;avascript:alert(1)",  # entity-encoded 'j'
            "&#x6a;avascript:alert(1)",  # hex entity
            "java\tscript:alert(1)",  # embedded tab
            "  javascript:alert(1)",  # leading whitespace
        ],
    )
    def test_obfuscated_javascript_is_stripped(self, url: str) -> None:
        doc = parse(f"[x]({url})")
        for policy in (strip_dangerous_urls, llm_safe, web_safe, strict):
            assert _links(policy(doc)) == [], f"{policy} kept dangerous url {url!r}"

    def test_data_uri_stripped(self) -> None:
        doc = parse("[x](&#100;ata:text/html,<script>)")
        assert _links(llm_safe(doc)) == []


class TestAllowListKeepsSafeUrls:
    """Allow-list filtering must keep relative/fragment/known-scheme links."""

    @pytest.mark.parametrize(
        "url", ["/relative/path", "#anchor", "page.html", "https://ok.com", "mailto:a@b.com"]
    )
    def test_safe_urls_kept(self, url: str) -> None:
        doc = parse(f"[x]({url})")
        assert len(_links(allow_url_schemes()(doc))) == 1, f"dropped safe url {url!r}"

    def test_unknown_scheme_dropped_by_default(self) -> None:
        doc = parse("[x](ftp://host/file)")
        assert _links(allow_url_schemes()(doc)) == []

    def test_custom_allowed_scheme(self) -> None:
        doc = parse("[x](ftp://host/file)")
        assert len(_links(allow_url_schemes("ftp")(doc))) == 1


class TestLimitDepth:
    """limit_depth must actually prune (it used to be a documented no-op)."""

    def test_prunes_deep_blockquotes(self) -> None:
        doc = parse(">" * 8 + " deep")
        pruned = limit_depth(3)(doc)

        def block_depth(node, d=0):
            if isinstance(node, BlockQuote):
                d += 1
            kids = getattr(node, "children", ())
            return max((block_depth(c, d) for c in kids), default=d)

        assert block_depth(doc) > 3
        assert block_depth(pruned) <= 3

    def test_shallow_content_unchanged(self) -> None:
        doc = parse("> a\n\npara")
        assert limit_depth(10)(doc) == doc
