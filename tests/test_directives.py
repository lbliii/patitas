"""Tests for the directive system."""

from __future__ import annotations


class TestDirectiveRegistry:
    """Tests for directive registry."""

    def test_create_default_registry(self) -> None:
        """Test creating default registry."""
        from patitas.directives import create_default_registry

        registry = create_default_registry()

        # Should have admonition types
        assert registry.has("note")
        assert registry.has("warning")
        assert registry.has("tip")

        # Should have tabs
        assert registry.has("tab-set")
        assert registry.has("tab-item")

        # Should have dropdown
        assert registry.has("dropdown")

        # Should have container
        assert registry.has("container")

    def test_registry_builder(self) -> None:
        """Test building a custom registry."""
        from patitas.directives import DirectiveRegistryBuilder
        from patitas.directives.builtins import AdmonitionDirective

        builder = DirectiveRegistryBuilder()
        builder.register(AdmonitionDirective())
        registry = builder.build()

        assert registry.has("note")
        assert len(registry) == 10  # All admonition types

    def test_registry_get(self) -> None:
        """Test getting handlers from registry."""
        from patitas.directives import create_default_registry

        registry = create_default_registry()
        handler = registry.get("note")

        assert handler is not None
        assert "note" in handler.names


class TestDirectiveContracts:
    """Tests for directive contracts."""

    def test_tab_item_contract(self) -> None:
        """Test tab-item requires parent."""
        from patitas.directives import TAB_ITEM_CONTRACT

        # Should fail without parent
        violation = TAB_ITEM_CONTRACT.validate_parent("tab-item", None)
        assert violation is not None
        assert violation.violation_type == "missing_parent"

        # Should pass with correct parent
        violation = TAB_ITEM_CONTRACT.validate_parent("tab-item", "tab-set")
        assert violation is None

    def test_tab_set_contract(self) -> None:
        """Test tab-set allows only tab-item children."""
        from patitas.directives import TAB_SET_CONTRACT
        from patitas.nodes import Directive
        from patitas.location import SourceLocation
        from patitas.directives.options import DirectiveOptions

        loc = SourceLocation(1, 1)
        opts = DirectiveOptions()

        # Create valid tab-item child
        tab_item = Directive(loc, "tab-item", "Tab 1", opts, ())

        # Should pass with valid children
        violations = TAB_SET_CONTRACT.validate_children("tab-set", [tab_item])
        assert len(violations) == 0

    def test_dropdown_contract(self) -> None:
        """Test dropdown has no restrictions."""
        from patitas.directives import DROPDOWN_CONTRACT

        # Should have no requirements
        assert DROPDOWN_CONTRACT.requires_parent is None
        assert DROPDOWN_CONTRACT.allows_children is None


class TestAdmonitionDirective:
    """Tests for admonition directive."""

    def test_admonition_types(self) -> None:
        """Test all admonition types are supported."""
        from patitas.directives.builtins.admonition import ADMONITION_TYPES

        expected = {
            "note", "tip", "warning", "danger", "error",
            "info", "example", "success", "caution", "seealso"
        }
        assert ADMONITION_TYPES == expected

    def test_admonition_parse(self) -> None:
        """Test admonition parsing."""
        from patitas.directives.builtins import AdmonitionDirective
        from patitas.directives.options import AdmonitionOptions
        from patitas.location import SourceLocation

        directive = AdmonitionDirective()
        loc = SourceLocation(1, 1)
        opts = AdmonitionOptions()

        node = directive.parse(
            name="note",
            title="Custom Title",
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.name == "note"
        assert node.title == "Custom Title"

    def test_admonition_default_title(self) -> None:
        """Test admonition gets default title from type."""
        from patitas.directives.builtins import AdmonitionDirective
        from patitas.directives.options import AdmonitionOptions
        from patitas.location import SourceLocation

        directive = AdmonitionDirective()
        loc = SourceLocation(1, 1)
        opts = AdmonitionOptions()

        node = directive.parse(
            name="warning",
            title=None,  # No title provided
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.title == "Warning"  # Capitalized type


class TestDropdownDirective:
    """Tests for dropdown directive."""

    def test_dropdown_parse(self) -> None:
        """Test dropdown parsing."""
        from patitas.directives.builtins import DropdownDirective
        from patitas.directives.builtins.dropdown import DropdownOptions
        from patitas.location import SourceLocation

        directive = DropdownDirective()
        loc = SourceLocation(1, 1)
        opts = DropdownOptions(open=True, badge="New")

        node = directive.parse(
            name="dropdown",
            title="Click to expand",
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.name == "dropdown"
        assert node.title == "Click to expand"
        assert node.options.open is True
        assert node.options.badge == "New"


class TestTabsDirective:
    """Tests for tabs directive."""

    def test_tab_set_parse(self) -> None:
        """Test tab-set parsing."""
        from patitas.directives.builtins import TabSetDirective
        from patitas.directives.builtins.tabs import TabSetOptions
        from patitas.location import SourceLocation

        directive = TabSetDirective()
        loc = SourceLocation(1, 1)
        opts = TabSetOptions(sync="language")

        node = directive.parse(
            name="tab-set",
            title=None,
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.name == "tab-set"
        assert node.options.sync == "language"

    def test_tab_item_parse(self) -> None:
        """Test tab-item parsing."""
        from patitas.directives.builtins import TabItemDirective
        from patitas.directives.builtins.tabs import TabItemOptions
        from patitas.location import SourceLocation

        directive = TabItemDirective()
        loc = SourceLocation(1, 1)
        opts = TabItemOptions(selected=True, badge="Popular")

        node = directive.parse(
            name="tab-item",
            title="Python",
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.name == "tab-item"
        assert node.title == "Python"
        assert node.options.selected is True
        assert node.options.badge == "Popular"


class TestContainerDirective:
    """Tests for container directive."""

    def test_container_parse(self) -> None:
        """Test container parsing with class merging."""
        from patitas.directives.builtins import ContainerDirective
        from patitas.directives.builtins.container import ContainerOptions
        from patitas.location import SourceLocation

        directive = ContainerDirective()
        loc = SourceLocation(1, 1)
        opts = ContainerOptions(class_="extra")

        node = directive.parse(
            name="container",
            title="api-section",  # Title is used as class
            options=opts,
            content="",
            children=(),
            location=loc,
        )

        assert node.name == "container"
        assert node.title is None  # Title used for classes
        # Classes should be merged
        assert "api-section" in node.options.class_
        assert "extra" in node.options.class_
