"""End-to-end directive rendering tests through the PUBLIC render path.

Regression coverage for the bug where ``HtmlRenderer._render_directive`` called
handlers with the wrong arity (``handler.render(directive, self)`` instead of the
``render(node, rendered_children, sb)`` contract). The resulting ``TypeError`` was
swallowed by a bare ``except``, so every directive silently degraded to a generic
``<div>`` — yet the test suite stayed green because existing tests asserted config
flags or called handlers directly instead of rendering through ``Markdown()``.

These tests deliberately exercise ``Markdown()(...)`` / ``render()`` so a broken
render path fails loudly.
"""

import pytest

from patitas import Markdown, create_registry_with_defaults
from patitas.directives.decorator import directive


@pytest.fixture
def md() -> Markdown:
    return Markdown()


class TestBuiltinDirectivesRenderThroughHandlers:
    """Each builtin must produce its handler's HTML, not the generic fallback."""

    def test_admonition_note_uses_handler_markup(self, md: Markdown) -> None:
        out = md(":::{note}\nHello **world**\n:::")
        # Handler markup (NOT the generic 'directive directive-note' fallback).
        assert 'class="admonition note"' in out
        assert 'class="admonition-title"' in out
        assert "<strong>world</strong>" in out
        assert "directive-note" not in out  # generic fallback must not appear

    @pytest.mark.parametrize("name", ["warning", "tip", "danger", "info", "success"])
    def test_admonition_variants(self, md: Markdown, name: str) -> None:
        out = md(f":::{{{name}}}\nbody\n:::")
        assert "admonition" in out
        assert "directive-" not in out

    def test_tab_set_renders_tab_navigation(self, md: Markdown) -> None:
        out = md(
            "::::{tab-set}\n"
            ":::{tab-item} One\nA\n:::\n"
            ":::{tab-item} Two\nB\n:::\n"
            "::::"
        )
        assert 'class="tabs"' in out
        assert "tab-nav" in out
        assert "tab-pane" in out
        assert ">One<" in out and ">Two<" in out
        assert "directive-tab" not in out

    def test_dropdown_renders_details_summary(self, md: Markdown) -> None:
        out = md(":::{dropdown} Click me\nhidden\n:::")
        assert "<details" in out
        assert "<summary>" in out
        assert "Click me" in out
        assert "directive-dropdown" not in out


class TestCustomDirective:
    """The documented @directive flow must work end-to-end through render()."""

    def test_custom_directive_renders(self) -> None:
        @directive("greet")
        def render_greet(node, children, sb):
            sb.append(f'<aside class="greet">{children}</aside>')

        builder = create_registry_with_defaults()
        builder.register(render_greet())
        md = Markdown(directive_registry=builder.build())

        out = md(":::{greet}\nHello **you**\n:::")
        assert '<aside class="greet">' in out
        assert "<strong>you</strong>" in out

    def test_unknown_directive_falls_back_to_generic_container(self, md: Markdown) -> None:
        # Unregistered names still render as a generic container (intended).
        out = md(":::{totally-unknown}\nbody\n:::")
        assert 'class="directive directive-totally-unknown"' in out


class TestHandlerErrorsAreNotSwallowed:
    """A broken handler must surface, not silently emit wrong HTML."""

    def test_handler_exception_propagates(self) -> None:
        @directive("boom")
        def render_boom(node, children, sb):
            raise ValueError("handler is broken")

        builder = create_registry_with_defaults()
        builder.register(render_boom())
        md = Markdown(directive_registry=builder.build())

        with pytest.raises(ValueError, match="handler is broken"):
            md(":::{boom}\nbody\n:::")
