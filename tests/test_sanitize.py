"""Tests for sanitization policies."""

import pytest

from patitas import parse, sanitize
from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    Directive,
    Document,
    FencedCode,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Link,
    Paragraph,
    Text,
)
from patitas.sanitize import (
    Policy,
    allow_url_schemes,
    limit_depth,
    llm_safe,
    normalize_unicode,
    strict,
    strip_dangerous_urls,
    strip_html,
    strip_html_comments,
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

    def test_empty_container_at_limit_unchanged(self) -> None:
        # A depth container with no children (e.g. an empty block quote) is
        # returned as-is: there is nothing to prune even though it is a
        # container. This guards the no-children early return in prune().
        from patitas.location import SourceLocation
        from patitas.nodes import Document

        loc = SourceLocation(lineno=1, col_offset=0)
        doc = Document(location=loc, children=(BlockQuote(location=loc, children=()),))
        assert limit_depth(1)(doc) == doc

    def test_does_not_recurse_into_deep_inline(self) -> None:
        # limit_depth bounds *block* nesting; it must not traverse (and crash on)
        # deeply nested inline content such as emphasis runs.
        import sys

        from patitas import Markdown

        # Deep inline emphasis is now bounded by max_nesting_depth (issue #25), so
        # raise the limit to actually build a deep inline AST for this test.
        doc = Markdown(max_nesting_depth=2000).parse("*" * 400 + "x" + "*" * 400)
        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(300)
        try:
            limit_depth(3)(doc)  # must not raise RecursionError
        finally:
            sys.setrecursionlimit(original_limit)


def _imgs(doc) -> list:
    """All Image nodes in the first paragraph of a parsed doc."""
    if not doc.children:
        return []
    para = doc.children[0]
    return [c for c in getattr(para, "children", ()) if isinstance(c, Image)]


def _fenced(location: SourceLocation, content: str) -> FencedCode:
    """A minimal FencedCode node for directly-constructed AST tests."""
    return FencedCode(
        location=location,
        source_start=0,
        source_end=0,
        info="py",
        marker="```",
        fence_indent=0,
        content_override=content,
    )


class TestPolicyCompositionAdversarial:
    """Composition semantics of sanitization policies.

    ``Policy.__or__`` is *ordered* function composition, not a commutative set
    union: ``(a | b)(doc)`` applies ``a`` then ``b``. Some policies rewrite
    nodes into other node types (``strip_images`` turns ``Image`` into ``Text``),
    so a later policy never sees what an earlier one consumed. These tests pin
    that ordering contract and the idempotence (or non-idempotence) of each
    primitive, and directly exercise ``Policy.__init__``/``__call__``/``__or__``.
    """

    # -- Direct exercises of the Policy wrapper ---------------------------

    def test_policy_init_and_call_identity(self) -> None:
        # A Policy is a thin wrapper over a Document -> Document callable;
        # __call__ just delegates to the wrapped function.
        ident = Policy(lambda d: d)
        doc = parse("# Hi")
        assert ident(doc) is doc

    def test_policy_call_applies_wrapped_fn(self) -> None:
        doc = parse("a <span>b</span> c")
        wrapped = Policy(strip_html._fn)  # reuse the underlying transform fn
        clean = wrapped(doc)
        para = clean.children[0]
        assert not any(isinstance(c, HtmlInline) for c in para.children)

    def test_policy_or_returns_new_policy_left_to_right(self) -> None:
        # (a | b) is a new Policy that runs a then b; it must not mutate either
        # operand. We prove order by composing two transforms that record the
        # sequence in which they run.
        order: list[str] = []
        a = Policy(lambda d: (order.append("a"), d)[1])
        b = Policy(lambda d: (order.append("b"), d)[1])
        composed = a | b
        assert isinstance(composed, Policy)
        assert composed is not a and composed is not b
        composed(parse("x"))
        assert order == ["a", "b"]

    # -- Order-dependence -------------------------------------------------

    def test_strip_images_before_url_filter_keeps_alt_text(self) -> None:
        # strip_images rewrites an Image into a Text(alt) node *before* the URL
        # filter runs, so a disallowed-scheme image survives as its alt text.
        doc = parse("![alt](ftp://host/i.png)")
        result = (strip_images | allow_url_schemes())(doc)
        children = result.children[0].children
        assert _imgs(result) == []
        assert [c.content for c in children if isinstance(c, Text)] == ["alt"]

    def test_url_filter_before_strip_images_drops_image_entirely(self) -> None:
        # Reverse order: the URL filter drops the disallowed-scheme image first,
        # so strip_images has nothing to turn into alt text -> empty paragraph.
        doc = parse("![alt](ftp://host/i.png)")
        result = (allow_url_schemes() | strip_images)(doc)
        assert result.children[0].children == ()

    def test_order_matters_results_differ(self) -> None:
        # The two orderings above are not equal: composition is non-commutative.
        doc = parse("![alt](ftp://host/i.png)")
        forward = (strip_images | allow_url_schemes())(doc)
        reverse = (allow_url_schemes() | strip_images)(doc)
        assert forward != reverse

    # -- Idempotence ------------------------------------------------------

    @pytest.mark.parametrize(
        "policy, markdown",
        [
            (strip_html, "a <span>b</span> c"),
            (strip_html_comments, "a <!-- c --> b"),
            (strip_dangerous_urls, "[x](javascript:alert(1))"),
            (normalize_unicode, "a​‮b"),
            (strip_images, "![alt](i.png)"),
            (strip_raw_code, "# Hi\n\n```py\ncode\n```\n"),
            (allow_url_schemes(), "[a](ftp://h/f) [b](https://ok.com)"),
        ],
    )
    def test_primitives_are_idempotent(self, policy: Policy, markdown: str) -> None:
        # p | p must equal p for these node-removing/rewriting policies: applying
        # twice removes nothing new and reaches a fixed point.
        doc = parse(markdown)
        once = policy(doc)
        twice = (policy | policy)(doc)
        assert once == twice

    def test_strict_is_idempotent(self) -> None:
        doc = parse(
            "# Hi\n\n<script>x</script>\n\n[j](javascript:y)\n\n![pic](i.png)\n\n```py\ncode\n```\n"
        )
        once = strict(doc)
        twice = (strict | strict)(doc)
        assert once == twice

    # -- Edge cases -------------------------------------------------------

    def test_strip_images_empty_alt_yields_empty_text(self) -> None:
        # An image with empty alt text becomes an empty Text node (not dropped).
        doc = parse("![](i.png)")
        clean = strip_images(doc)
        children = clean.children[0].children
        assert len(children) == 1
        assert isinstance(children[0], Text)
        assert children[0].content == ""

    def test_strip_html_comments_removes_only_comments(self) -> None:
        # Exercises _strip_html_comments: comment HtmlInline dropped, other
        # inline HTML kept.
        doc = parse("a <!-- secret --> b <span>c</span> d")
        clean = strip_html_comments(doc)
        para = clean.children[0]
        inlines = [c for c in para.children if isinstance(c, HtmlInline)]
        assert all(not c.html.strip().startswith("<!--") for c in inlines)
        assert any(c.html.strip().startswith("<span") for c in inlines)

    def test_strip_raw_code_strips_code_inside_directive(self) -> None:
        # strip_raw_code must reach FencedCode/IndentedCode nested inside a
        # Directive container, not just top-level blocks.
        code = _fenced(LOC, "secret()")
        indented = IndentedCode(location=LOC, code="also_secret()")
        directive = Directive(
            location=LOC,
            name="note",
            title="",
            options={},
            children=(_para("intro"), code, indented),
            raw_content="",
        )
        doc = Document(location=LOC, children=(directive,))
        clean = strip_raw_code(doc)
        kept = clean.children[0].children
        assert not any(isinstance(c, (FencedCode, IndentedCode)) for c in kept)
        assert [c for c in kept if isinstance(c, Paragraph)]

    def test_allow_url_schemes_drops_disallowed_image(self) -> None:
        # Exercises the Image branch of allow_url_schemes (an image, not a link,
        # with a disallowed scheme is removed).
        doc = parse("![pic](ftp://host/i.png)")
        assert len(_imgs(doc)) == 1
        assert _imgs(allow_url_schemes()(doc)) == []
        assert len(_imgs(allow_url_schemes("ftp")(doc))) == 1

    def test_composed_allow_schemes_intersect(self) -> None:
        # Composing two allow_url_schemes with differing schemes is an
        # intersection (a link must satisfy *both* filters), unlike a single
        # call with multiple schemes which is a union.
        intersection = allow_url_schemes("https") | allow_url_schemes("ftp")
        assert _links(intersection(parse("[x](https://ok.com)"))) == []
        assert _links(intersection(parse("[x](ftp://host/f)"))) == []

        union = allow_url_schemes("https", "ftp")
        assert len(_links(union(parse("[x](https://ok.com)")))) == 1
        assert len(_links(union(parse("[x](ftp://host/f)")))) == 1

    def test_sanitize_accepts_plain_callable(self) -> None:
        # sanitize() accepts a bare Document -> Document callable, not just a
        # Policy (exercises the non-Policy branch).
        doc = parse("# Hi")
        calls: list[Document] = []

        def passthrough(d: Document) -> Document:
            calls.append(d)
            return d

        out = sanitize(doc, policy=passthrough)
        assert out is doc
        assert calls == [doc]
