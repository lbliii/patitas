"""Comprehensive tests for patitas roles package.

Tests cover:
- DocRole suffix handling (rstrip vs removesuffix)
- KbdRole plus key edge cases
- IconRole registry isolation
- RoleRegistry immutability
- Property-based edge case discovery
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from patitas.location import SourceLocation
from patitas.roles import RoleRegistryBuilder, create_default_registry
from patitas.roles.builtins import (
    AbbrRole,
    DocRole,
    IconRole,
    KbdRole,
    MathRole,
    RefRole,
    SubRole,
    SupRole,
)
from patitas.stringbuilder import StringBuilder

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def loc() -> SourceLocation:
    """Standard source location for tests."""
    return SourceLocation(1, 1)


@pytest.fixture
def sb() -> StringBuilder:
    """Fresh StringBuilder for each test."""
    return StringBuilder()


# =============================================================================
# DocRole Tests - Suffix Handling
# =============================================================================


class TestDocRoleSuffixHandling:
    """Tests for .md suffix removal - catches rstrip vs removesuffix bugs."""

    @pytest.fixture
    def role(self) -> DocRole:
        return DocRole()

    @pytest.mark.parametrize(
        ("target", "expected_href"),
        [
            # Normal cases
            ("getting-started.md", "getting-started.html"),
            ("docs/install.md", "docs/install.html"),
            ("/absolute/path.md", "/absolute/path.html"),
            # Edge cases that expose rstrip bug (names with m, d, . chars)
            ("readme.md", "readme.html"),  # NOT "rea.html"
            ("document.md", "document.html"),  # NOT "docu.html"
            ("cmd.md", "cmd.html"),  # NOT "c.html"
            ("ammad.md", "ammad.html"),  # NOT "a.html" (rstrip would eat all chars)
            ("mode.md", "mode.html"),  # NOT "mo.html"
            ("dim.md", "dim.html"),  # NOT "di.html" or ""
            # Already correct extension
            ("page.html", "page.html"),
            ("styles.css.html", "styles.css.html"),
            # Directory paths (no extension change)
            ("dir/", "dir/"),
            ("docs/api/", "docs/api/"),
            # No extension (should add .html)
            ("page", "page.html"),
            ("docs/quickstart", "docs/quickstart.html"),
        ],
    )
    def test_md_suffix_removal(
        self, role: DocRole, loc: SourceLocation, target: str, expected_href: str
    ) -> None:
        """Verify .md suffix is removed correctly, not character-by-character."""
        node = role.parse("doc", target, loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert f'href="{expected_href}"' in result, f"Expected href={expected_href} in {result}"

    def test_display_text_with_target(self, role: DocRole, loc: SourceLocation) -> None:
        """Test explicit display text syntax."""
        node = role.parse("doc", "Installation Guide </docs/install.md>", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "Installation Guide" in result
        assert "/docs/install.html" in result

    def test_escapes_html_in_display(self, role: DocRole, loc: SourceLocation) -> None:
        """Display text should be HTML escaped."""
        node = role.parse("doc", "<script>alert(1)</script> </docs/page.md>", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# =============================================================================
# RefRole Tests
# =============================================================================


class TestRefRole:
    """Tests for reference role parsing and rendering."""

    @pytest.fixture
    def role(self) -> RefRole:
        return RefRole()

    def test_simple_target(self, role: RefRole, loc: SourceLocation) -> None:
        """Simple target uses target as display text."""
        node = role.parse("ref", "installation", loc)
        assert node.target == "installation"
        assert node.content == "installation"

    def test_explicit_display_text(self, role: RefRole, loc: SourceLocation) -> None:
        """Explicit display text syntax: 'text <target>'."""
        node = role.parse("ref", "Getting Started <quickstart>", loc)
        assert node.target == "quickstart"
        assert node.content == "Getting Started"

    def test_render_produces_anchor(self, role: RefRole, loc: SourceLocation) -> None:
        """Render should produce anchor with href."""
        node = role.parse("ref", "my-section", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert '<a class="reference internal"' in result
        assert 'href="#my-section"' in result

    def test_escapes_html(self, role: RefRole, loc: SourceLocation) -> None:
        """Target and display should be HTML escaped."""
        node = role.parse("ref", '<script> <"target">', loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<script>" not in result


# =============================================================================
# KbdRole Tests - Plus Key Handling
# =============================================================================


class TestKbdRoleBasic:
    """Basic tests for keyboard shortcut rendering."""

    @pytest.fixture
    def role(self) -> KbdRole:
        return KbdRole()

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            # Normal shortcuts
            ("Ctrl+C", "<kbd>Ctrl</kbd>+<kbd>C</kbd>"),
            ("Ctrl+Shift+P", "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>"),
            ("Alt+F4", "<kbd>Alt</kbd>+<kbd>F4</kbd>"),
            ("Cmd+Shift+S", "<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd>"),
            # Single keys (no +)
            ("Enter", "<kbd>Enter</kbd>"),
            ("Space", "<kbd>Space</kbd>"),
            ("Escape", "<kbd>Escape</kbd>"),
            ("Tab", "<kbd>Tab</kbd>"),
            ("F1", "<kbd>F1</kbd>"),
            # Special characters as single keys
            ("-", "<kbd>-</kbd>"),
            ("=", "<kbd>=</kbd>"),
            ("[", "<kbd>[</kbd>"),
        ],
    )
    def test_kbd_rendering(
        self, role: KbdRole, loc: SourceLocation, content: str, expected: str
    ) -> None:
        """Verify keyboard shortcuts render correctly."""
        node = role.parse("kbd", content, loc)
        sb = StringBuilder()
        role.render(node, sb)
        assert sb.build() == expected


class TestKbdRolePlusKey:
    """Tests for + key handling edge cases."""

    @pytest.fixture
    def role(self) -> KbdRole:
        return KbdRole()

    def test_single_plus_key(self, role: KbdRole, loc: SourceLocation) -> None:
        """Single + key must render as <kbd>+</kbd>, not empty."""
        node = role.parse("kbd", "+", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert result == "<kbd>+</kbd>"

    def test_plus_key_not_empty(self, role: KbdRole, loc: SourceLocation) -> None:
        """Single + key must not render as empty string."""
        node = role.parse("kbd", "+", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert result != ""
        assert "<kbd>" in result

    def test_ctrl_plus_plus(self, role: KbdRole, loc: SourceLocation) -> None:
        """Ctrl++ should render as Ctrl + plus key."""
        node = role.parse("kbd", "Ctrl++", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        # Should have Ctrl and the + key
        assert "<kbd>Ctrl</kbd>" in result
        assert "<kbd>+</kbd>" in result

    def test_shift_plus_plus(self, role: KbdRole, loc: SourceLocation) -> None:
        """Shift++ should render as Shift + plus key."""
        node = role.parse("kbd", "Shift++", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<kbd>Shift</kbd>" in result
        assert "<kbd>+</kbd>" in result

    def test_whitespace_stripped(self, role: KbdRole, loc: SourceLocation) -> None:
        """Whitespace around keys should be stripped."""
        node = role.parse("kbd", " Ctrl + C ", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<kbd>Ctrl</kbd>" in result
        assert "<kbd>C</kbd>" in result

    def test_html_escaping(self, role: KbdRole, loc: SourceLocation) -> None:
        """Key names should be HTML escaped."""
        node = role.parse("kbd", "<script>", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# =============================================================================
# AbbrRole Tests
# =============================================================================


class TestAbbrRole:
    """Tests for abbreviation role."""

    @pytest.fixture
    def role(self) -> AbbrRole:
        return AbbrRole()

    def test_abbr_with_expansion(self, role: AbbrRole, loc: SourceLocation) -> None:
        """Abbreviation with expansion in parentheses."""
        node = role.parse("abbr", "HTML (HyperText Markup Language)", loc)
        assert node.content == "HTML"
        assert node.target == "HyperText Markup Language"

    def test_abbr_without_expansion(self, role: AbbrRole, loc: SourceLocation) -> None:
        """Abbreviation without expansion."""
        node = role.parse("abbr", "NASA", loc)
        assert node.content == "NASA"
        assert node.target is None

    def test_render_with_title(self, role: AbbrRole, loc: SourceLocation) -> None:
        """Render should include title attribute for expansion."""
        node = role.parse("abbr", "CSS (Cascading Style Sheets)", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert '<abbr title="Cascading Style Sheets">' in result
        assert "CSS</abbr>" in result

    def test_render_without_title(self, role: AbbrRole, loc: SourceLocation) -> None:
        """Render without expansion omits title."""
        node = role.parse("abbr", "API", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert result == "<abbr>API</abbr>"

    def test_escapes_html_in_expansion(self, role: AbbrRole, loc: SourceLocation) -> None:
        """Expansion text should be HTML escaped."""
        node = role.parse("abbr", 'XSS (<script>alert("hi")</script>)', loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "<script>" not in result


# =============================================================================
# MathRole Tests
# =============================================================================


class TestMathRole:
    """Tests for inline math role."""

    @pytest.fixture
    def role(self) -> MathRole:
        return MathRole()

    def test_preserves_whitespace(self, role: MathRole, loc: SourceLocation) -> None:
        """Math content should preserve whitespace."""
        node = role.parse("math", " x + y ", loc)
        assert node.content == " x + y "  # Not stripped

    def test_render_with_delimiters(self, role: MathRole, loc: SourceLocation) -> None:
        """Render should include \\( \\) delimiters."""
        node = role.parse("math", "E = mc^2", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "\\(" in result
        assert "\\)" in result
        assert "E = mc^2" in result

    def test_escapes_html(self, role: MathRole, loc: SourceLocation) -> None:
        """Math content should be HTML escaped."""
        node = role.parse("math", "x < y", loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert "x &lt; y" in result


# =============================================================================
# SubRole and SupRole Tests
# =============================================================================


class TestSubSupRoles:
    """Tests for subscript and superscript roles."""

    def test_sub_render(self, loc: SourceLocation) -> None:
        """Subscript should render with <sub> tag."""
        role = SubRole()
        node = role.parse("sub", "2", loc)
        sb = StringBuilder()
        role.render(node, sb)
        assert sb.build() == "<sub>2</sub>"

    def test_sup_render(self, loc: SourceLocation) -> None:
        """Superscript should render with <sup> tag."""
        role = SupRole()
        node = role.parse("sup", "2", loc)
        sb = StringBuilder()
        role.render(node, sb)
        assert sb.build() == "<sup>2</sup>"

    def test_sub_escapes_html(self, loc: SourceLocation) -> None:
        """Subscript should escape HTML."""
        role = SubRole()
        node = role.parse("sub", "<i>", loc)
        sb = StringBuilder()
        role.render(node, sb)
        assert "<i>" not in sb.build()

    def test_sup_escapes_html(self, loc: SourceLocation) -> None:
        """Superscript should escape HTML."""
        role = SupRole()
        node = role.parse("sup", "<b>", loc)
        sb = StringBuilder()
        role.render(node, sb)
        assert "<b>" not in sb.build()


# =============================================================================
# IconRole Tests - Registry Isolation
# =============================================================================


class TestIconRoleBasic:
    """Basic tests for icon role."""

    def test_no_resolver_renders_placeholder(self, loc: SourceLocation) -> None:
        """IconRole without resolver should render placeholder."""
        icon = IconRole()
        node = icon.parse("icon", "github", loc)
        sb = StringBuilder()
        icon.render(node, sb)
        assert "[icon:github]" in sb.build()
        assert "icon-placeholder" in sb.build()

    def test_resolver_returns_svg(self, loc: SourceLocation) -> None:
        """IconRole with resolver should return SVG."""

        def resolver(name: str) -> str | None:
            return f"<svg data-icon='{name}'></svg>"

        icon = IconRole(resolver=resolver)
        node = icon.parse("icon", "check", loc)
        sb = StringBuilder()
        icon.render(node, sb)
        assert sb.build() == "<svg data-icon='check'></svg>"

    def test_resolver_returning_none_falls_back(self, loc: SourceLocation) -> None:
        """Resolver returning None should fall back to placeholder."""

        def selective_resolver(name: str) -> str | None:
            if name == "check":
                return "<svg>✓</svg>"
            return None

        icon = IconRole(resolver=selective_resolver)

        # Known icon
        node = icon.parse("icon", "check", loc)
        sb = StringBuilder()
        icon.render(node, sb)
        assert "<svg>" in sb.build()

        # Unknown icon
        node = icon.parse("icon", "unknown", loc)
        sb = StringBuilder()
        icon.render(node, sb)
        assert "[icon:unknown]" in sb.build()


class TestIconRoleIsolation:
    """Tests for registry isolation - ensures no shared state between instances."""

    def test_separate_instances_have_separate_resolvers(self, loc: SourceLocation) -> None:
        """Different IconRole instances should have independent resolvers."""

        def resolver_a(name: str) -> str | None:
            return f"<svg id='a-{name}'></svg>"

        def resolver_b(name: str) -> str | None:
            return f"<svg id='b-{name}'></svg>"

        icon_a = IconRole(resolver=resolver_a)
        icon_b = IconRole(resolver=resolver_b)

        # Render with icon_a
        node = icon_a.parse("icon", "check", loc)
        sb_a = StringBuilder()
        icon_a.render(node, sb_a)

        # Render with icon_b
        sb_b = StringBuilder()
        icon_b.render(node, sb_b)

        assert "a-check" in sb_a.build()
        assert "b-check" in sb_b.build()
        assert sb_a.build() != sb_b.build()

    def test_one_instance_with_resolver_other_without(self, loc: SourceLocation) -> None:
        """One instance with resolver shouldn't affect instance without."""

        def resolver(name: str) -> str | None:
            return "<svg>RESOLVED</svg>"

        icon_with = IconRole(resolver=resolver)
        icon_without = IconRole()

        node = icon_with.parse("icon", "test", loc)

        # With resolver
        sb1 = StringBuilder()
        icon_with.render(node, sb1)
        assert "RESOLVED" in sb1.build()

        # Without resolver (should NOT be affected)
        sb2 = StringBuilder()
        icon_without.render(node, sb2)
        assert "RESOLVED" not in sb2.build()
        assert "[icon:test]" in sb2.build()

    def test_registries_with_different_icon_resolvers(self) -> None:
        """Multiple registries can have different icon configurations."""

        def resolver_emoji(name: str) -> str | None:
            return {"check": "✓", "x": "✗"}.get(name)

        def resolver_svg(name: str) -> str | None:
            return f"<svg>{name}</svg>"

        # Build two registries with different icon resolvers
        builder1 = RoleRegistryBuilder()
        builder1.register(IconRole(resolver=resolver_emoji))
        registry1 = builder1.build()

        builder2 = RoleRegistryBuilder()
        builder2.register(IconRole(resolver=resolver_svg))
        registry2 = builder2.build()

        # Get handlers
        handler1 = registry1.get("icon")
        handler2 = registry2.get("icon")

        assert handler1 is not handler2

        # Render same icon with each
        loc = SourceLocation(1, 1)
        node = handler1.parse("icon", "check", loc)  # type: ignore

        sb1 = StringBuilder()
        handler1.render(node, sb1)  # type: ignore

        sb2 = StringBuilder()
        handler2.render(node, sb2)  # type: ignore

        assert sb1.build() == "✓"
        assert sb2.build() == "<svg>check</svg>"


# =============================================================================
# RoleRegistry Tests - Immutability
# =============================================================================


class TestRoleRegistryBasic:
    """Basic registry functionality tests."""

    def test_get_existing_role(self) -> None:
        """Can retrieve registered role by name."""
        registry = create_default_registry()
        handler = registry.get("ref")
        assert handler is not None
        assert "ref" in handler.names

    def test_get_nonexistent_role(self) -> None:
        """Getting nonexistent role returns None."""
        registry = create_default_registry()
        assert registry.get("nonexistent") is None

    def test_has_role(self) -> None:
        """has() returns True for registered roles."""
        registry = create_default_registry()
        assert registry.has("ref")
        assert registry.has("kbd")
        assert not registry.has("nonexistent")

    def test_contains_syntax(self) -> None:
        """'name in registry' syntax works."""
        registry = create_default_registry()
        assert "ref" in registry
        assert "kbd" in registry
        assert "nonexistent" not in registry

    def test_names_property(self) -> None:
        """names property returns all registered names."""
        registry = create_default_registry()
        names = registry.names
        assert isinstance(names, frozenset)
        assert "ref" in names
        assert "kbd" in names
        assert "math" in names

    def test_handlers_property(self) -> None:
        """handlers property returns tuple of handlers."""
        registry = create_default_registry()
        handlers = registry.handlers
        assert isinstance(handlers, tuple)
        assert len(handlers) > 0

    def test_len(self) -> None:
        """len() returns number of registered role names."""
        registry = create_default_registry()
        assert len(registry) >= 8  # At least the built-in roles


class TestRoleRegistryImmutability:
    """Tests for true immutability of RoleRegistry."""

    def test_cannot_modify_by_name_after_creation(self) -> None:
        """Registry's by_name mapping must be immutable."""
        registry = create_default_registry()

        with pytest.raises(TypeError):
            registry._by_name["hacked"] = "bad"  # type: ignore

    def test_cannot_modify_by_token_type_after_creation(self) -> None:
        """Registry's by_token_type mapping must be immutable."""
        registry = create_default_registry()

        with pytest.raises(TypeError):
            registry._by_token_type["hacked"] = "bad"  # type: ignore

    def test_cannot_delete_from_by_name(self) -> None:
        """Cannot delete entries from by_name mapping."""
        registry = create_default_registry()

        with pytest.raises(TypeError):
            del registry._by_name["ref"]  # type: ignore

    def test_cannot_delete_from_by_token_type(self) -> None:
        """Cannot delete entries from by_token_type mapping."""
        registry = create_default_registry()

        with pytest.raises(TypeError):
            del registry._by_token_type["reference"]  # type: ignore

    def test_handlers_tuple_is_immutable(self) -> None:
        """Registry's handlers must be a tuple (immutable sequence)."""
        registry = create_default_registry()
        assert isinstance(registry.handlers, tuple)

    def test_names_returns_frozenset(self) -> None:
        """names property returns frozenset (immutable)."""
        registry = create_default_registry()
        names = registry.names
        assert isinstance(names, frozenset)


# =============================================================================
# RoleRegistryBuilder Tests
# =============================================================================


class TestRoleRegistryBuilder:
    """Tests for RoleRegistryBuilder."""

    def test_register_returns_self(self) -> None:
        """register() returns self for chaining."""
        builder = RoleRegistryBuilder()
        result = builder.register(KbdRole())
        assert result is builder

    def test_chained_registration(self) -> None:
        """Can chain multiple register calls."""
        registry = (
            RoleRegistryBuilder()
            .register(KbdRole())
            .register(AbbrRole())
            .register(MathRole())
            .build()
        )
        assert "kbd" in registry
        assert "abbr" in registry
        assert "math" in registry

    def test_register_all(self) -> None:
        """register_all() registers multiple handlers."""
        builder = RoleRegistryBuilder()
        builder.register_all([KbdRole(), AbbrRole(), MathRole()])
        registry = builder.build()
        assert len(registry) == 3

    def test_duplicate_name_raises(self) -> None:
        """Registering duplicate role name raises ValueError."""
        builder = RoleRegistryBuilder()
        builder.register(KbdRole())

        with pytest.raises(ValueError, match="already registered"):
            builder.register(KbdRole())

    def test_missing_names_raises(self) -> None:
        """Handler missing 'names' attribute raises TypeError."""
        builder = RoleRegistryBuilder()

        class BadRole:
            token_type = "bad"

        with pytest.raises(TypeError, match="missing 'names'"):
            builder.register(BadRole())  # type: ignore

    def test_missing_token_type_raises(self) -> None:
        """Handler missing 'token_type' attribute raises TypeError."""
        builder = RoleRegistryBuilder()

        class BadRole:
            names = ("bad",)

        with pytest.raises(TypeError, match="missing 'token_type'"):
            builder.register(BadRole())  # type: ignore

    def test_len_counts_handlers(self) -> None:
        """len() on builder returns handler count."""
        builder = RoleRegistryBuilder()
        assert len(builder) == 0
        builder.register(KbdRole())
        assert len(builder) == 1
        builder.register(AbbrRole())
        assert len(builder) == 2


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


class TestRolePropertyBased:
    """Property-based tests for edge case discovery."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_kbd_never_returns_empty_for_nonempty_input(self, content: str) -> None:
        """KbdRole should never return empty string for non-empty input."""
        content = content.strip()
        if not content:
            return  # Skip empty after strip

        role = KbdRole()
        loc = SourceLocation(1, 1)
        node = role.parse("kbd", content, loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()

        assert result != "", f"Empty output for input: {content!r}"
        assert "<kbd>" in result, f"No <kbd> tag for input: {content!r}"

    @given(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/",
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=100)
    def test_doc_role_preserves_path_structure(self, path: str) -> None:
        """DocRole should preserve path structure, only change extension."""
        role = DocRole()
        loc = SourceLocation(1, 1)
        input_path = f"{path}.md"
        node = role.parse("doc", input_path, loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()

        # The path should appear in the href (with .html extension)
        expected = f"{path}.html"
        assert expected in result, f"Expected {expected} in {result}"

    @given(st.text(min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_abbr_never_crashes(self, content: str) -> None:
        """AbbrRole should handle any input without crashing."""
        role = AbbrRole()
        loc = SourceLocation(1, 1)
        node = role.parse("abbr", content, loc)
        sb = StringBuilder()
        # Should not raise
        role.render(node, sb)
        # Should produce some output
        assert isinstance(sb.build(), str)

    @given(st.text(min_size=0, max_size=50))
    @settings(max_examples=100)
    def test_math_preserves_content(self, content: str) -> None:
        """MathRole should preserve content (possibly escaped)."""
        role = MathRole()
        loc = SourceLocation(1, 1)
        node = role.parse("math", content, loc)
        # Content should be preserved in node
        assert node.content == content

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_", min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_ref_role_target_in_href(self, target: str) -> None:
        """RefRole should include target in href."""
        role = RefRole()
        loc = SourceLocation(1, 1)
        node = role.parse("ref", target, loc)
        sb = StringBuilder()
        role.render(node, sb)
        result = sb.build()
        assert f"#{target}" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestDefaultRegistry:
    """Tests for the default registry with all built-in roles."""

    def test_all_builtin_roles_registered(self) -> None:
        """Default registry should have all built-in roles."""
        registry = create_default_registry()

        expected_roles = ["ref", "doc", "kbd", "abbr", "math", "sub", "sup", "icon"]
        for role_name in expected_roles:
            assert role_name in registry, f"Missing role: {role_name}"

    def test_get_by_token_type(self) -> None:
        """Can retrieve handlers by token type."""
        registry = create_default_registry()

        ref_handler = registry.get_by_token_type("reference")
        assert ref_handler is not None
        assert "ref" in ref_handler.names

        kbd_handler = registry.get_by_token_type("kbd")
        assert kbd_handler is not None
        assert "kbd" in kbd_handler.names

    def test_each_role_can_parse_and_render(self) -> None:
        """Each registered role can parse and render without error."""
        registry = create_default_registry()
        loc = SourceLocation(1, 1)

        test_content = {
            "ref": "target",
            "doc": "/path/to/doc.md",
            "kbd": "Ctrl+C",
            "abbr": "HTML (HyperText Markup Language)",
            "math": "x^2",
            "sub": "2",
            "sup": "2",
            "icon": "check",
        }

        for role_name, content in test_content.items():
            handler = registry.get(role_name)
            assert handler is not None, f"Handler not found for {role_name}"

            node = handler.parse(role_name, content, loc)
            assert node is not None, f"Parse returned None for {role_name}"

            sb = StringBuilder()
            handler.render(node, sb)
            result = sb.build()
            assert result, f"Empty render result for {role_name}"
