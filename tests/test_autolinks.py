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

    def test_email_domain_underscore_in_last_two_segments_not_linked(self) -> None:
        # GFM: no underscores may be present in the last two segments of the
        # domain. 'b_c.com' has an underscore in the second-to-last segment.
        out = Markdown(plugins=["autolinks"])("mail a@b_c.com here")
        assert "<a " not in out

    def test_email_domain_underscore_in_earlier_segment_linked(self) -> None:
        # Underscores are allowed in segments before the last two. Here the last
        # two segments ('example', 'com') have no underscore, so it links.
        out = Markdown(plugins=["autolinks"])("mail a@foo_bar.example.com here")
        assert '<a href="mailto:a@foo_bar.example.com">a@foo_bar.example.com</a>' in out

    def test_email_trailing_dash_invalidates_address(self) -> None:
        # GFM: "The last character must not be one of '-' or '_'." A trailing
        # '-' invalidates the whole email (it is NOT trimmed-then-linked).
        out = Markdown(plugins=["autolinks"])("a.b-c_d@a.b-")
        assert "<a " not in out
        assert "a.b-c_d@a.b-" in out

    def test_email_trailing_underscore_invalidates_address(self) -> None:
        # GFM: a trailing '_' likewise invalidates the whole email.
        out = Markdown(plugins=["autolinks"])("a.b-c_d@a.b_")
        assert "<a " not in out
        assert "a.b-c_d@a.b_" in out

    def test_email_trailing_period_excluded_but_linked(self) -> None:
        # GFM: a trailing '.' is excluded from the link but the address is still
        # valid (the period is left as plain text).
        out = Markdown(plugins=["autolinks"])("a.b-c_d@a.b.")
        assert '<a href="mailto:a.b-c_d@a.b">a.b-c_d@a.b</a>' in out
        assert out.rstrip().endswith(".</p>")

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


class TestUrlBodyKeepsInlineSpecialChars:
    """A URL body runs until whitespace/'<', so '& ~ $ _' inside it are kept.

    These are the common real-world cases (query separators, '~user' paths,
    'Foo_(bar)' slugs) that a naive run-truncated scan would split mid-URL.
    """

    def test_ampersand_query_separator_kept(self) -> None:
        out = Markdown(plugins=["autolinks"])("https://example.com/?a=1&b=2 end")
        # '&' is HTML-escaped to '&amp;' in the rendered href/text but the whole
        # query string is inside one link.
        assert (
            '<a href="https://example.com/?a=1&amp;b=2">https://example.com/?a=1&amp;b=2</a>' in out
        )
        assert "end</p>" in out

    def test_tilde_in_path_kept(self) -> None:
        out = Markdown(plugins=["autolinks"])("https://example.com/~user")
        assert '<a href="https://example.com/~user">https://example.com/~user</a>' in out

    def test_underscore_and_balanced_parens_in_path_kept(self) -> None:
        # The Wikipedia 'Foo_(bar)' case: the underscore is part of the path and
        # the balanced trailing parens are kept; the outer ')' is excluded.
        out = Markdown(plugins=["autolinks"])("(https://en.wikipedia.org/wiki/Foo_(bar))")
        assert (
            '<a href="https://en.wikipedia.org/wiki/Foo_(bar)">'
            "https://en.wikipedia.org/wiki/Foo_(bar)</a>" in out
        )

    def test_dollar_in_path_kept(self) -> None:
        out = Markdown(plugins=["autolinks"])("https://example.com/a$b here")
        assert '<a href="https://example.com/a$b">https://example.com/a$b</a>' in out

    def test_backtick_ends_url_so_code_span_wins(self) -> None:
        # Code spans keep higher CommonMark/GFM precedence: a backtick ends the
        # URL body rather than being swallowed into the link.
        out = Markdown(plugins=["autolinks"])("see `http://no.link` end")
        assert "<code>http://no.link</code>" in out
        assert "<a " not in out

    def test_url_before_code_span_still_links_fully(self) -> None:
        out = Markdown(plugins=["autolinks"])("use https://a.com/p?x=1&y=2 then `code` end")
        assert '<a href="https://a.com/p?x=1&amp;y=2">https://a.com/p?x=1&amp;y=2</a>' in out
        assert "<code>code</code>" in out

    def test_email_local_part_underscore_linked(self) -> None:
        # GFM precedence: autolinks > emphasis. An '_' in an email *local part*
        # is recognized as part of the address before emphasis tokenization, so
        # the FULL local part is linked. (Previously this was a documented
        # limitation that linked only the post-delimiter portion; the inline
        # tokenizer now resolves the autolink first. Closes GFM example 631.)
        out = Markdown(plugins=["autolinks"])("a_b@example.com")
        assert '<a href="mailto:a_b@example.com">a_b@example.com</a>' in out

    def test_email_local_part_underscore_mid_paragraph_linked(self) -> None:
        # Same precedence rule when the address is surrounded by other text: the
        # preceding local-part chars are pulled into the link, not left as text.
        out = Markdown(plugins=["autolinks"])("ping a.b-c_d@a.b please")
        assert '<a href="mailto:a.b-c_d@a.b">a.b-c_d@a.b</a>' in out
        assert "ping <a " in out

    def test_email_emphasis_still_works_near_address(self) -> None:
        # The autolink check only fires when '_' is inside a valid email local
        # part; ordinary emphasis is untouched.
        out = Markdown(plugins=["autolinks"])("_emph_ and a_b@x.com")
        assert "<em>emph</em>" in out
        assert '<a href="mailto:a_b@x.com">a_b@x.com</a>' in out
