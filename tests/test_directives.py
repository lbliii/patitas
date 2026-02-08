"""Tests for the directive system."""

import threading
from dataclasses import dataclass


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
        from patitas.directives.options import DirectiveOptions
        from patitas.location import SourceLocation
        from patitas.nodes import Directive

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
            "note",
            "tip",
            "warning",
            "danger",
            "error",
            "info",
            "example",
            "success",
            "caution",
            "seealso",
        }
        assert expected == ADMONITION_TYPES

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


# =============================================================================
# NEW TESTS: Edge cases that would have caught the bugs
# =============================================================================


class TestContractEdgeCases:
    """Edge case tests for directive contracts.

    These tests would have caught Bug #1 (empty children validation).
    """

    def test_requires_children_empty_list(self) -> None:
        """Empty children should violate requires_children contract."""
        from patitas.directives import DirectiveContract

        contract = DirectiveContract(requires_children=("step",))

        # Empty children should be a violation!
        violations = contract.validate_children("steps", [])

        assert len(violations) == 1
        assert violations[0].violation_type == "missing_required_child"
        assert violations[0].actual is None  # No children provided

    def test_requires_children_wrong_type(self) -> None:
        """Wrong child type should violate requires_children contract."""
        from patitas.directives import DirectiveContract
        from patitas.directives.options import DirectiveOptions
        from patitas.location import SourceLocation
        from patitas.nodes import Directive

        contract = DirectiveContract(requires_children=("step",))
        loc = SourceLocation(1, 1)
        opts = DirectiveOptions()
        wrong_child = Directive(loc, "other", None, opts, ())

        violations = contract.validate_children("steps", [wrong_child])

        assert len(violations) == 1
        assert violations[0].violation_type == "missing_required_child"

    def test_steps_contract_requires_children(self) -> None:
        """STEPS_CONTRACT should require step children."""
        from patitas.directives import STEPS_CONTRACT

        # This would have caught Bug #8
        assert STEPS_CONTRACT.requires_children is not None
        assert "step" in STEPS_CONTRACT.requires_children

    def test_max_children_validation(self) -> None:
        """max_children should be enforced."""
        from patitas.directives import DirectiveContract
        from patitas.directives.options import DirectiveOptions
        from patitas.location import SourceLocation
        from patitas.nodes import Directive

        contract = DirectiveContract(max_children=2)
        loc = SourceLocation(1, 1)
        opts = DirectiveOptions()
        children = [Directive(loc, f"child{i}", None, opts, ()) for i in range(3)]

        violations = contract.validate_children("parent", children)

        assert len(violations) == 1
        assert violations[0].violation_type == "too_many_children"


class TestOptionsCoercion:
    """Tests for option value coercion.

    These tests would have caught Bug #2 (None string not coerced).
    """

    def test_none_string_coerced_to_none(self) -> None:
        """String 'None' should be coerced to Python None."""
        from patitas.directives.builtins.dropdown import DropdownOptions

        opts = DropdownOptions.from_raw({"icon": "None"})
        assert opts.icon is None

    def test_null_string_coerced_to_none(self) -> None:
        """String 'null' should be coerced to Python None."""
        from patitas.directives.builtins.dropdown import DropdownOptions

        opts = DropdownOptions.from_raw({"badge": "null"})
        assert opts.badge is None

    def test_none_case_insensitive(self) -> None:
        """None coercion should be case-insensitive."""
        from patitas.directives.builtins.dropdown import DropdownOptions

        for value in ["None", "NONE", "none", "Null", "NULL"]:
            opts = DropdownOptions.from_raw({"icon": value})
            assert opts.icon is None, f"'{value}' should coerce to None"

    def test_actual_value_not_coerced(self) -> None:
        """Actual string values should not be coerced to None."""
        from patitas.directives.builtins.dropdown import DropdownOptions

        opts = DropdownOptions.from_raw({"icon": "github", "badge": "New"})
        assert opts.icon == "github"
        assert opts.badge == "New"

    def test_bool_coercion(self) -> None:
        """Boolean options should coerce correctly."""
        from patitas.directives.options import AdmonitionOptions

        # True values
        for value in ["true", "True", "TRUE", "yes", "1", ""]:
            opts = AdmonitionOptions.from_raw({"collapsible": value})
            assert opts.collapsible is True, f"'{value}' should coerce to True"

        # False values
        for value in ["false", "False", "no", "0", "anything"]:
            opts = AdmonitionOptions.from_raw({"collapsible": value})
            assert opts.collapsible is False, f"'{value}' should coerce to False"

    def test_int_coercion(self) -> None:
        """Integer options should coerce correctly."""
        from patitas.directives.options import CodeBlockOptions

        opts = CodeBlockOptions.from_raw({"lineno_start": "42"})
        assert opts.lineno_start == 42
        assert isinstance(opts.lineno_start, int)

    def test_int_coercion_invalid(self) -> None:
        """Invalid integer should raise ValueError."""
        import pytest

        from patitas.directives.options import CodeBlockOptions

        with pytest.raises(ValueError, match="Invalid integer"):
            CodeBlockOptions.from_raw({"lineno_start": "not_a_number"})

    def test_class_alias(self) -> None:
        """'class' should be aliased to 'class_'."""
        from patitas.directives.options import StyledOptions

        opts = StyledOptions.from_raw({"class": "my-class"})
        assert opts.class_ == "my-class"


class TestIconResolverThreadSafety:
    """Thread safety tests for icon resolver.

    These tests would have caught Bug #7 (thread-unsafe icon resolver).
    """

    def test_concurrent_get_icon(self) -> None:
        """get_icon should be safe to call concurrently."""
        from patitas.icons import get_icon, set_icon_resolver

        set_icon_resolver(lambda name: f"<svg>{name}</svg>")
        results: list[str | None] = []
        errors: list[Exception] = []

        def worker(icon_name: str) -> None:
            try:
                for _ in range(100):
                    result = get_icon(icon_name)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"icon{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 1000

    def test_set_resolver_during_reads(self) -> None:
        """Setting resolver while reading should not crash."""
        from patitas.icons import get_icon, set_icon_resolver

        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(100):
                    get_icon("test")
            except Exception as e:
                errors.append(e)

        def writer() -> None:
            try:
                for i in range(100):
                    set_icon_resolver(lambda n, i=i: f"<svg>{n}-{i}</svg>")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads.append(threading.Thread(target=writer))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestDecoratorTyping:
    """Tests for @directive decorator.

    These tests verify proper typing (Bug #3 and #4).
    """

    def test_function_decorator(self) -> None:
        """Function decorator should create valid handler."""
        from patitas.directives.decorator import directive
        from patitas.directives.options import DirectiveOptions
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        @directive("test-fn")
        def render_test(node, children: str, sb: StringBuilder) -> None:
            sb.append(f"<test>{children}</test>")

        # Should have required attributes
        assert hasattr(render_test, "names")
        assert render_test.names == ("test-fn",)
        assert hasattr(render_test, "token_type")
        assert render_test.token_type == "test-fn"
        assert hasattr(render_test, "options_class")

        # Should be instantiable
        handler = render_test()

        # Should have parse and render methods
        assert hasattr(handler, "parse")
        assert hasattr(handler, "render")

        # Parse should work
        loc = SourceLocation(1, 1)
        opts = DirectiveOptions()
        node = handler.parse("test-fn", "Title", opts, "", [], loc)
        assert node.name == "test-fn"

        # Render should work
        sb = StringBuilder()
        handler.render(node, "content", sb)
        assert sb.build() == "<test>content</test>"

    def test_class_decorator(self) -> None:
        """Class decorator should add attributes."""
        from patitas.directives.decorator import directive
        from patitas.directives.options import StyledOptions
        from patitas.stringbuilder import StringBuilder

        @directive("test-cls", options=StyledOptions)
        class TestDirective:
            def render(self, node, children: str, sb: StringBuilder) -> None:
                sb.append(f"<div>{children}</div>")

        assert TestDirective.names == ("test-cls",)
        assert TestDirective.options_class is StyledOptions

    def test_decorator_preserves_raw_content(self) -> None:
        """preserves_raw_content should be passed through."""
        from patitas.directives.decorator import directive
        from patitas.directives.options import DirectiveOptions
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        @directive("raw-test", preserves_raw_content=True)
        def render_raw(node, children: str, sb: StringBuilder) -> None:
            sb.append(node.raw_content or "")

        handler = render_raw()
        loc = SourceLocation(1, 1)
        opts = DirectiveOptions()
        node = handler.parse("raw-test", None, opts, "raw content here", [], loc)

        assert node.raw_content == "raw content here"


class TestProtocolCompliance:
    """Tests verifying handlers comply with DirectiveHandler protocol.

    These tests would have caught Bug #5 (protocol variance).
    """

    def test_admonition_satisfies_protocol(self) -> None:
        """AdmonitionDirective should satisfy DirectiveHandler protocol."""
        from patitas.directives.builtins import AdmonitionDirective
        from patitas.directives.protocol import DirectiveHandler

        handler = AdmonitionDirective()

        # Check protocol compliance
        assert isinstance(handler, DirectiveHandler)

    def test_all_builtins_satisfy_protocol(self) -> None:
        """All builtin directives should satisfy DirectiveHandler protocol."""
        from patitas.directives.builtins import (
            AdmonitionDirective,
            ContainerDirective,
            DropdownDirective,
            TabItemDirective,
            TabSetDirective,
        )
        from patitas.directives.protocol import DirectiveHandler

        handlers = [
            AdmonitionDirective(),
            ContainerDirective(),
            DropdownDirective(),
            TabSetDirective(),
            TabItemDirective(),
        ]

        for handler in handlers:
            assert isinstance(handler, DirectiveHandler), (
                f"{type(handler).__name__} should satisfy DirectiveHandler"
            )

    def test_custom_handler_with_subclass_options(self) -> None:
        """Custom handlers with specific options should work with registry."""

        from patitas.directives import DirectiveRegistryBuilder
        from patitas.directives.options import StyledOptions
        from patitas.nodes import Directive

        @dataclass(frozen=True, slots=True)
        class CustomOptions(StyledOptions):
            custom_field: str | None = None

        class CustomDirective:
            names = ("custom",)
            token_type = "custom"
            contract = None
            options_class = CustomOptions
            preserves_raw_content = False

            def parse(self, name, title, options, content, children, location):
                return Directive(location, name, title, options, tuple(children))

            def render(self, node, rendered_children, sb):
                sb.append(f"<custom>{rendered_children}</custom>")

        # Should be registerable without type errors
        builder = DirectiveRegistryBuilder()
        builder.register(CustomDirective())
        registry = builder.build()

        assert registry.has("custom")


class TestContractViolationMessages:
    """Tests for contract violation message quality."""

    def test_missing_parent_suggestion(self) -> None:
        """Violation should suggest wrapping in parent."""
        from patitas.directives import TAB_ITEM_CONTRACT

        violation = TAB_ITEM_CONTRACT.validate_parent("tab-item", None)
        assert violation is not None

        suggestion = violation.suggestion
        assert suggestion is not None
        assert "tab-set" in suggestion or "tabs" in suggestion

    def test_missing_child_suggestion(self) -> None:
        """Violation should suggest adding required child."""
        from patitas.directives import DirectiveContract

        contract = DirectiveContract(requires_children=("item",))
        violations = contract.validate_children("list", [])

        assert len(violations) == 1
        suggestion = violations[0].suggestion
        assert suggestion is not None
        assert "item" in suggestion
