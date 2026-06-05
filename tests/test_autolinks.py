"""Behavioral tests for autolinking.

Previously the only autolink tests asserted ``config.autolinks_enabled`` is True
and never checked that any URL was actually linked — so the fact that the
``autolinks`` plugin was a no-op (the flag was plumbed but read by zero parsing
code) went unnoticed. These tests assert real HTML output.

- CommonMark angle-bracket autolinks (<https://...>) work WITHOUT any plugin.
- GFM extended autolinks (bare https://, www., bare email) are recognized only
  when the ``autolinks`` plugin is enabled, following the GFM extension rules:
  https://github.github.com/gfm/#autolinks-extension-
"""

from patitas import Markdown


class TestCommonMarkAngleAutolinks:
    """Angle-bracket autolinks are CommonMark core — no plugin required."""

    def test_uri_autolink(self) -> None:
        out = Markdown()("Visit <https://example.com> today")
        assert '<a href="https://example.com">https://example.com</a>' in out

    def test_email_autolink(self) -> None:
        out = Markdown()("Mail <me@example.com>")
        assert '<a href="mailto:me@example.com">me@example.com</a>' in out


class TestGfmExtendedAutolinks:
    """GFM extended autolinks: bare URL / www / email, gated on the plugin."""

    def test_bare_url_now_linked(self) -> None:
        # Previously asserted the no-op behavior ('<a ' not in out); the feature
        # is now implemented, so the bare URL must be linked.
        out = Markdown(plugins=["autolinks"])("Visit https://example.com now")
        assert '<a href="https://example.com">https://example.com</a>' in out

    def test_bare_url_should_be_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("Visit https://example.com now")
        assert '<a href="https://example.com">https://example.com</a>' in out

    def test_http_scheme_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("Go to http://example.com here")
        assert '<a href="http://example.com">http://example.com</a>' in out

    def test_www_should_be_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("See www.example.com")
        assert 'href="http://www.example.com"' in out
        # The link TEXT shows the original 'www...' text, not the http:// href.
        assert ">www.example.com</a>" in out

    def test_bare_email_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("Mail foo@example.com today")
        assert '<a href="mailto:foo@example.com">foo@example.com</a>' in out

    def test_trailing_period_excluded(self) -> None:
        out = Markdown(plugins=["autolinks"])("see https://example.com.")
        assert '<a href="https://example.com">https://example.com</a>' in out
        # The trailing period is left as plain text, outside the link.
        assert out.rstrip().endswith(".</p>")

    def test_trailing_punctuation_excluded(self) -> None:
        for trailer in "?!,:":
            out = Markdown(plugins=["autolinks"])(f"x https://example.com{trailer} y")
            assert '<a href="https://example.com">https://example.com</a>' in out
            assert f"{trailer} y</p>" in out

    def test_parentheses_balanced_kept(self) -> None:
        # Balanced parens inside the path are part of the link.
        out = Markdown(plugins=["autolinks"])("https://example.com/foo(bar)")
        assert '<a href="https://example.com/foo(bar)">https://example.com/foo(bar)</a>' in out

    def test_parentheses_unbalanced_trailing_excluded(self) -> None:
        # A trailing ')' is excluded when there are more ')' than '(' in match.
        out = Markdown(plugins=["autolinks"])("(see https://example.com/path)")
        assert '<a href="https://example.com/path">https://example.com/path</a>' in out
        # The closing ')' is left outside the link.
        assert ")</p>" in out

    def test_trailing_entity_reference_stripped(self) -> None:
        out = Markdown(plugins=["autolinks"])("https://example.com/?a=1&amp; rest")
        # The trailing '&amp;' entity is stripped from the link target.
        assert '<a href="https://example.com/?a=1">https://example.com/?a=1</a>' in out

    def test_boundary_glued_to_word_not_linked(self) -> None:
        # Glued to a preceding word char -> not a valid left boundary.
        out = Markdown(plugins=["autolinks"])("xhttps://example.com")
        assert "<a " not in out

    def test_boundary_after_space_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("x https://example.com")
        assert '<a href="https://example.com">https://example.com</a>' in out

    def test_off_without_plugin(self) -> None:
        # Default config: GFM extended autolinks are OFF -> not linked.
        out = Markdown()("https://example.com")
        assert "<a " not in out

    def test_email_off_without_plugin(self) -> None:
        out = Markdown()("foo@example.com")
        assert "<a " not in out

    def test_no_dot_domain_not_linked(self) -> None:
        # GFM requires at least one '.' in the authority.
        out = Markdown(plugins=["autolinks"])("https://localhost here")
        assert "<a " not in out
