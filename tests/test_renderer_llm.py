"""Tests for LLM renderer."""

from patitas import parse, render_llm, sanitize
from patitas.sanitize import llm_safe


class TestRenderLlm:
    def test_heading(self) -> None:
        doc = parse("# Hello World")
        out = render_llm(doc)
        assert "# Hello World" in out
        assert out.endswith("\n\n")

    def test_paragraph(self) -> None:
        doc = parse("Plain paragraph text.")
        out = render_llm(doc)
        assert "Plain paragraph text." in out

    def test_list(self) -> None:
        doc = parse("- one\n- two")
        out = render_llm(doc)
        assert "- one" in out
        assert "- two" in out

    def test_blockquote(self) -> None:
        doc = parse("> Quoted text")
        out = render_llm(doc)
        assert "> " in out
        assert "Quoted" in out

    def test_code_block(self) -> None:
        doc = parse("```py\nx = 1\n```")
        out = render_llm(doc, source="```py\nx = 1\n```")
        assert "[code" in out
        assert "x = 1" in out
        assert "[/code]" in out

    def test_link_shows_url(self) -> None:
        doc = parse("[click](https://x.com)")
        out = render_llm(doc)
        assert "click" in out
        assert "https://x.com" in out

    def test_image_labeled(self) -> None:
        doc = parse("![alt](img.png)")
        out = render_llm(doc)
        assert "[image:" in out
        assert "alt" in out


class TestRoundTrip:
    def test_parse_sanitize_render(self) -> None:
        doc = parse("# Title\n\nBody with **bold** and [link](https://x.com).")
        clean = sanitize(doc, policy=llm_safe)
        out = render_llm(clean)
        assert "Title" in out
        assert "Body" in out
        assert "bold" in out
        assert "link" in out
        assert "https://x.com" in out
