"""Behavioral tests for autolinking.

Previously the only autolink tests asserted ``config.autolinks_enabled`` is True
and never checked that any URL was actually linked — so the fact that the
``autolinks`` plugin is a no-op (the flag is plumbed but read by zero parsing
code) went unnoticed. These tests assert real HTML output.

- CommonMark angle-bracket autolinks (<https://...>) work WITHOUT any plugin.
- GFM extended autolinks (bare https://, www., bare email) are NOT yet
  implemented; the xfail tests below flip to passing once they are (tracked in
  the "implement GFM extended autolinks" issue).
"""

import pytest

from patitas import Markdown


class TestCommonMarkAngleAutolinks:
    """Angle-bracket autolinks are CommonMark core — no plugin required."""

    def test_uri_autolink(self) -> None:
        out = Markdown()("Visit <https://example.com> today")
        assert '<a href="https://example.com">https://example.com</a>' in out

    def test_email_autolink(self) -> None:
        out = Markdown()("Mail <me@example.com>")
        assert '<a href="mailto:me@example.com">me@example.com</a>' in out


class TestGfmExtendedAutolinksNotYetImplemented:
    """Document current reality: bare URLs are NOT linked, even with the plugin."""

    def test_bare_url_currently_not_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("Visit https://example.com now")
        assert "<a " not in out  # honest: feature is a no-op today

    @pytest.mark.xfail(
        reason="GFM extended autolinks (bare URL) not yet implemented; "
        "tracked in the GFM extended autolinks issue",
        strict=True,
    )
    def test_bare_url_should_be_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("Visit https://example.com now")
        assert '<a href="https://example.com">https://example.com</a>' in out

    @pytest.mark.xfail(reason="GFM www. autolinks not yet implemented", strict=True)
    def test_www_should_be_linked(self) -> None:
        out = Markdown(plugins=["autolinks"])("See www.example.com")
        assert 'href="http://www.example.com"' in out
