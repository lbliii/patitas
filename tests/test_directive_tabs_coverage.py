"""Coverage-focused tests for the tab directives (``patitas.directives.builtins.tabs``).

Drives both rendering modes ("enhanced" JS tabs and "css_state_machine"
URL-driven tabs) plus per-item options (icon, badge, selected, disabled),
the explicit ``id`` option, the no-matches fallback, and slug generation --
all through the PUBLIC ``Markdown()`` render path.
"""

from patitas import Markdown


def _md() -> Markdown:
    return Markdown()


class TestEnhancedTabMode:
    """Default JavaScript-enhanced tabs (``mode`` unset / "enhanced")."""

    def test_basic_tab_set_builds_nav_and_panes(self) -> None:
        out = _md()("::::{tab-set}\n:::{tab-item} One\nA\n:::\n:::{tab-item} Two\nB\n:::\n::::")
        assert 'class="tabs"' in out
        assert 'data-patitas="tabs"' in out
        assert "tab-nav" in out
        assert "tab-pane" in out
        assert "data-tab-target" in out
        assert ">One<" in out and ">Two<" in out
        # First tab active by default when none marked selected.
        assert "active" in out

    def test_explicit_id_is_used_verbatim(self) -> None:
        out = _md()("::::{tab-set}\n:id: mytabs\n\n:::{tab-item} Alpha\nA\n:::\n::::")
        assert 'id="mytabs"' in out
        assert 'data-tab-target="mytabs-0"' in out
        assert 'id="mytabs-0"' in out

    def test_icon_badge_disabled_selected_options(self) -> None:
        out = _md()(
            "::::{tab-set}\n:id: t\n\n"
            ":::{tab-item} First\n:icon: star\n:selected:\nA\n:::\n"
            ":::{tab-item} Second\n:badge: Pro\n:disabled:\nB\n:::\n"
            "::::"
        )
        # Icon span on the first tab.
        assert 'class="tab-icon" data-icon="star"' in out
        # Selected tab is active.
        assert "active" in out
        # Badge text on the second tab.
        assert '<span class="tab-badge">Pro</span>' in out
        # Disabled tab gets aria + tabindex and disabled class.
        assert 'aria-disabled="true"' in out
        assert 'tabindex="-1"' in out
        assert "disabled" in out

    def test_sync_key_emitted_as_data_attr(self) -> None:
        out = _md()("::::{tab-set}\n:sync: lang\n\n:::{tab-item} Py\nA\n:::\n::::")
        assert 'data-sync="lang"' in out

    def test_auto_id_is_stable_for_same_content(self) -> None:
        src = "::::{tab-set}\n:::{tab-item} X\nbody\n:::\n::::"
        out1 = _md()(src)
        out2 = _md()(src)
        # No explicit id -> deterministic hash-based id (stable builds).
        assert out1 == out2
        assert 'id="tabs-' in out1


class TestCssStateMachineMode:
    """URL-driven tabs (``:mode: css_state_machine``)."""

    def test_native_tabs_use_aria_roles_and_slugs(self) -> None:
        out = _md()(
            "::::{tab-set}\n:mode: css_state_machine\n:id: t\n\n"
            ":::{tab-item} Java Script\n:icon: js\n:badge: New\nB\n:::\n"
            "::::"
        )
        assert 'class="tabs tabs--native"' in out
        assert 'role="tablist"' in out
        assert 'role="tab"' in out
        assert 'role="tabpanel"' in out
        # Slug derived from the title ("Java Script" -> "java-script").
        assert 'id="t-java-script"' in out
        assert 'aria-controls="t-java-script"' in out
        # Icon + badge spans present.
        assert 'class="tab-icon" data-icon="js"' in out
        assert '<span class="tab-badge">New</span>' in out

    def test_native_disabled_tab_gets_aria_disabled(self) -> None:
        out = _md()(
            "::::{tab-set}\n:mode: css_state_machine\n\n:::{tab-item} Off\n:disabled:\nx\n:::\n::::"
        )
        assert 'aria-disabled="true"' in out
        assert 'tabindex="-1"' in out

    def test_native_sync_key_emitted(self) -> None:
        out = _md()(
            "::::{tab-set}\n:mode: css_state_machine\n:sync: grp\n\n:::{tab-item} A\nx\n:::\n::::"
        )
        assert 'data-sync="grp"' in out


class TestTabSetFallback:
    """A tab-set with no extractable tab-item children falls back to a plain div."""

    def test_tab_set_without_items_falls_back_to_div(self) -> None:
        out = _md()("::::{tab-set}\njust prose, no tab items\n::::")
        assert 'class="tabs"' in out
        assert 'data-patitas="tabs"' in out
        # No navigation is produced when there are no tab items.
        assert "tab-nav" not in out
        assert "just prose" in out


class TestNestedDivExtraction:
    """``_extract_tab_items`` must balance nested <div>s when slicing item content."""

    def test_nested_directive_div_does_not_break_item_boundaries(self) -> None:
        out = _md()(
            "::::{tab-set}\n:id: t\n\n"
            ":::{tab-item} One\n"
            "::::{note}\nnested admonition body\n::::\n"
            ":::\n"
            ":::{tab-item} Two\nplain\n:::\n"
            "::::"
        )
        # The nested admonition <div> stays inside the first pane...
        assert 'class="admonition note"' in out
        assert "nested admonition body" in out
        # ...and the second tab is still correctly recognised (depth balanced).
        assert ">Two<" in out
        assert 'id="t-1"' in out
        assert "plain" in out
