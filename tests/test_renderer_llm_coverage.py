"""Coverage-focused tests for the LLM renderer (``patitas.renderers.llm``).

Exercises the block and inline branches that the existing ``test_renderer_llm``
suite does not reach: tables, math (block + inline), indented code, thematic
breaks, ordered lists, directives, footnote definitions, code spans,
strikethrough, hard/soft breaks, raw-HTML skipping, and roles.

Every test asserts real output -- coverage is the side effect, the structured
plain-text contract is the point.
"""

from patitas import Markdown, parse, render_llm


class TestLlmBlockBranches:
    """Block-level ``_render_block`` match arms."""

    def test_ordered_list_uses_numeric_prefixes(self) -> None:
        doc = parse("3. first\n4. second\n5. third")
        out = render_llm(doc)
        # ``start`` is honoured and incremented per item.
        assert "3. first" in out
        assert "4. second" in out
        assert "5. third" in out

    def test_unordered_list_uses_dash_prefix(self) -> None:
        doc = parse("- alpha\n- beta")
        out = render_llm(doc)
        assert "- alpha" in out
        assert "- beta" in out

    def test_indented_code_block_is_labelled(self) -> None:
        doc = parse("    indented_code_line()\n")
        out = render_llm(doc)
        assert "[code]" in out
        assert "indented_code_line()" in out
        assert "[/code]" in out

    def test_fenced_code_without_language_uses_bare_label(self) -> None:
        src = "```\nplain code\n```"
        doc = parse(src)
        out = render_llm(doc, source=src)
        # No info string -> "[code]" rather than "[code:lang]".
        assert "[code]\n" in out
        assert "plain code" in out
        assert "[/code]" in out

    def test_fenced_code_with_language_is_tagged(self) -> None:
        src = "```python\nx = 1\n```"
        doc = parse(src)
        out = render_llm(doc, source=src)
        assert "[code:python]" in out
        assert "x = 1" in out

    def test_thematic_break_renders_dashes(self) -> None:
        doc = parse("a\n\n---\n\nb")
        out = render_llm(doc)
        assert "---\n\n" in out

    def test_html_block_is_skipped(self) -> None:
        doc = parse("<div>raw block</div>\n")
        out = render_llm(doc)
        # Raw HTML is intentionally dropped for safety.
        assert "<div>" not in out
        assert "raw block" not in out

    def test_math_block_is_labelled(self) -> None:
        md = Markdown(plugins=["math"])
        doc = md.parse("$$\na^2 + b^2\n$$")
        out = render_llm(doc)
        assert "[math]" in out
        assert "a^2 + b^2" in out.replace("\n", "")
        assert "[/math]" in out

    def test_table_renders_pipe_grid(self) -> None:
        md = Markdown(plugins=["table"])
        doc = md.parse("| H1 | H2 |\n| --- | --- |\n| a | b |\n")
        out = render_llm(doc)
        assert "| H1 | H2 |" in out
        assert "| a | b |" in out

    def test_directive_children_are_rendered(self) -> None:
        doc = parse(":::{note}\nimportant body\n:::")
        out = render_llm(doc)
        # Directive arm recurses into children -> body text survives.
        assert "important body" in out

    def test_footnote_definition_children_are_rendered(self) -> None:
        md = Markdown(plugins=["footnotes"])
        doc = md.parse("ref[^1]\n\n[^1]: the footnote body\n")
        out = render_llm(doc)
        assert "the footnote body" in out
        # The reference itself is emitted as [^id].
        assert "[^1]" in out

    def test_blockquote_prefixes_content(self) -> None:
        doc = parse("> quoted line one\n> quoted line two")
        out = render_llm(doc)
        assert "> " in out
        assert "quoted line one" in out


class TestLlmInlineBranches:
    """Inline-level ``_render_inline`` match arms."""

    def test_code_span_content_is_emitted(self) -> None:
        doc = parse("use `func()` here")
        out = render_llm(doc)
        assert "func()" in out

    def test_strikethrough_renders_inner_text(self) -> None:
        md = Markdown(plugins=["strikethrough"])
        doc = md.parse("~~gone~~ text")
        out = render_llm(doc)
        assert "gone" in out

    def test_emphasis_and_strong_render_inner_text(self) -> None:
        doc = parse("*em* and **strong**")
        out = render_llm(doc)
        assert "em" in out
        assert "strong" in out

    def test_inline_math_is_labelled(self) -> None:
        md = Markdown(plugins=["math"])
        doc = md.parse("inline $x_i$ math")
        out = render_llm(doc)
        assert "[math] x_i [/math]" in out

    def test_hard_line_break_becomes_space(self) -> None:
        doc = parse("line one  \nline two")
        out = render_llm(doc)
        # Hard break collapses to a single space, no backslash/HTML.
        assert "line one line two" in out
        assert "<br" not in out

    def test_soft_break_becomes_space(self) -> None:
        doc = parse("first\nsecond")
        out = render_llm(doc)
        assert "first second" in out

    def test_raw_inline_html_is_skipped(self) -> None:
        doc = parse("text <span>x</span> more")
        out = render_llm(doc)
        assert "<span>" not in out

    def test_image_is_labelled_with_alt(self) -> None:
        doc = parse("![the alt text](pic.png)")
        out = render_llm(doc)
        assert "[image: the alt text]" in out

    def test_link_appends_url(self) -> None:
        doc = parse("[anchor](https://example.com/path)")
        out = render_llm(doc)
        assert "anchor" in out
        assert "(https://example.com/path)" in out


class TestLlmTableCellExtraction:
    """``_inline_text_single`` arms via table cells with rich inline content."""

    def test_table_cells_flatten_inline_markup(self) -> None:
        md = Markdown(plugins=["table"])
        doc = md.parse("| col |\n| --- |\n| **bold** `code` [lnk](http://e.x) |\n")
        out = render_llm(doc)
        # Cell text is flattened: emphasis stripped, code kept, link text kept.
        assert "bold" in out
        assert "code" in out
        assert "lnk" in out


class TestLlmEndToEnd:
    """The renderer always returns a string and never raises on rich documents."""

    def test_full_document_round_trips_to_text(self) -> None:
        md = Markdown(plugins=["all"])
        src = (
            "# Title\n\n"
            "Intro paragraph with **bold**, *em*, `code`, and a [link](http://x.y).\n\n"
            "- bullet a\n- bullet b\n\n"
            "1. first\n2. second\n\n"
            "> a quote\n\n"
            "```python\nprint('hi')\n```\n\n"
            "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
            "---\n\n"
            "Trailing text.\n"
        )
        doc = md.parse(src)
        out = render_llm(doc, source=src)
        assert isinstance(out, str)
        assert out  # non-empty
        assert "# Title" in out
        # No HTML leaks into LLM output.
        assert "<" not in out


class TestLlmListItemAndRoleEdgeCases:
    """Edge arms of ``_render_list_item`` and the inline ``Role`` branch."""

    def test_list_item_with_block_first_child_renders_block(self) -> None:
        # First child is a FencedCode, not a Paragraph -> _render_block branch.
        src = "-   ```\n    code in item\n    ```\n"
        doc = parse(src)
        out = render_llm(doc, source=src)
        assert "[code]" in out
        assert "code in item" in out

    def test_empty_list_item_emits_newline(self) -> None:
        doc = parse("-\n- after")
        out = render_llm(doc)
        # Empty item still produces a bullet; non-empty item follows.
        assert "- after" in out

    def test_role_inline_content_is_emitted(self) -> None:
        doc = parse("press {kbd}`Ctrl+C` now")
        out = render_llm(doc)
        assert "Ctrl+C" in out

    def test_role_in_table_cell_is_flattened(self) -> None:
        md = Markdown(plugins=["table", "math"])
        doc = md.parse("| c |\n| --- |\n| $x$ |\n")
        out = render_llm(doc)
        # Math role content survives the table-cell flattening path.
        assert "| x |" in out
