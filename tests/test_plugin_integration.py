"""Plugin integration tests for Patitas.

These tests verify that:
1. Plugin names are consistent across the codebase
2. Each plugin actually enables its feature when used
3. Plugin protocol is properly implemented

These tests would have caught the "table" vs "tables" naming mismatch.
"""

from __future__ import annotations

import pytest

from patitas import Markdown, ParseConfig
from patitas.nodes import (
    FootnoteDef,
    FootnoteRef,
    List,
    Math,
    MathBlock,
    Strikethrough,
    Table,
)
from patitas.plugins import BUILTIN_PLUGINS, PatitasPlugin


class TestPluginNameConsistency:
    """Verify plugin names are consistent across the codebase."""

    # Mapping of plugin names to their corresponding ParseConfig fields
    PLUGIN_CONFIG_MAPPING = {
        "table": "tables_enabled",
        "strikethrough": "strikethrough_enabled",
        "task_lists": "task_lists_enabled",
        "footnotes": "footnotes_enabled",
        "math": "math_enabled",
        "autolinks": "autolinks_enabled",
    }

    def test_all_plugins_have_config_mapping(self) -> None:
        """Every registered plugin should have a corresponding config field."""
        for plugin_name in BUILTIN_PLUGINS:
            assert plugin_name in self.PLUGIN_CONFIG_MAPPING, (
                f"Plugin '{plugin_name}' has no corresponding ParseConfig field mapping. "
                f"Add it to PLUGIN_CONFIG_MAPPING."
            )

    def test_plugin_names_match_registration(self) -> None:
        """Plugin.name property should match its registration name."""
        for name, plugin_class in BUILTIN_PLUGINS.items():
            instance = plugin_class()
            assert instance.name == name, (
                f"Plugin registered as '{name}' but .name returns '{instance.name}'"
            )

    def test_markdown_class_recognizes_all_plugins(self) -> None:
        """Markdown class should enable features for all registered plugins."""
        for plugin_name, config_field in self.PLUGIN_CONFIG_MAPPING.items():
            md = Markdown(plugins=[plugin_name])
            config_value = getattr(md._config, config_field)
            assert config_value is True, (
                f"Markdown(plugins=['{plugin_name}']) did not set "
                f"ParseConfig.{config_field} to True (got {config_value})"
            )

    def test_all_config_fields_have_plugins(self) -> None:
        """Every boolean config field should have a corresponding plugin."""
        config = ParseConfig()
        boolean_fields = [
            name for name in config.__dataclass_fields__
            if name.endswith("_enabled")
        ]
        
        mapped_fields = set(self.PLUGIN_CONFIG_MAPPING.values())
        for field in boolean_fields:
            assert field in mapped_fields, (
                f"ParseConfig.{field} has no corresponding plugin"
            )


class TestPluginProtocolCompliance:
    """Verify all plugins implement the PatitasPlugin protocol."""

    def test_all_plugins_implement_protocol(self) -> None:
        """All registered plugins should implement PatitasPlugin."""
        for name, plugin_class in BUILTIN_PLUGINS.items():
            # Check that it's runtime checkable
            instance = plugin_class()
            assert isinstance(instance, PatitasPlugin), (
                f"Plugin '{name}' does not implement PatitasPlugin protocol"
            )

    def test_all_plugins_have_name_property(self) -> None:
        """All plugins must have a name property that returns a string."""
        for name, plugin_class in BUILTIN_PLUGINS.items():
            instance = plugin_class()
            assert hasattr(instance, "name"), (
                f"Plugin '{name}' missing 'name' property"
            )
            assert isinstance(instance.name, str), (
                f"Plugin '{name}'.name should be str, got {type(instance.name)}"
            )


class TestPluginFeatureEnablement:
    """Verify each plugin actually enables its feature."""

    def test_table_plugin_enables_tables(self) -> None:
        """Table plugin should enable GFM table parsing."""
        md = Markdown(plugins=["table"])
        doc = md.parse("| a | b |\n|---|---|\n| 1 | 2 |")
        
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], Table), (
            f"Expected Table, got {type(doc.children[0]).__name__}"
        )

    def test_strikethrough_plugin_enables_strikethrough(self) -> None:
        """Strikethrough plugin should enable ~~text~~ parsing."""
        md = Markdown(plugins=["strikethrough"])
        doc = md.parse("~~deleted~~")
        
        para = doc.children[0]
        assert any(
            isinstance(child, Strikethrough) for child in para.children
        ), "Strikethrough not parsed"

    def test_math_plugin_enables_inline_math(self) -> None:
        """Math plugin should enable $math$ parsing."""
        md = Markdown(plugins=["math"])
        doc = md.parse("$E = mc^2$")
        
        para = doc.children[0]
        assert any(
            isinstance(child, Math) for child in para.children
        ), "Inline math not parsed"

    def test_footnotes_plugin_enables_footnotes(self) -> None:
        """Footnotes plugin should enable [^ref] parsing."""
        md = Markdown(plugins=["footnotes"])
        doc = md.parse("Text[^1]\n\n[^1]: Footnote")
        
        # Should have both reference and definition
        para = doc.children[0]
        has_ref = any(
            isinstance(child, FootnoteRef) for child in para.children
        )
        has_def = any(
            isinstance(child, FootnoteDef) for child in doc.children
        )
        assert has_ref, "Footnote reference not parsed"
        assert has_def, "Footnote definition not parsed"

    def test_task_lists_plugin_enables_checkboxes(self) -> None:
        """Task lists plugin should enable - [ ] parsing."""
        md = Markdown(plugins=["task_lists"])
        doc = md.parse("- [ ] todo\n- [x] done")
        
        list_node = doc.children[0]
        assert isinstance(list_node, List), f"Expected List, got {type(list_node)}"
        checked_values = [item.checked for item in list_node.items]
        assert checked_values == [False, True], (
            f"Expected [False, True], got {checked_values}"
        )


class TestPluginCombinations:
    """Test that multiple plugins work together correctly."""

    def test_all_plugins_together(self) -> None:
        """All plugins should work when enabled together."""
        md = Markdown(plugins=[
            "table", "strikethrough", "math", 
            "footnotes", "task_lists", "autolinks"
        ])
        
        # Verify all are enabled
        config = md._config
        assert config.tables_enabled
        assert config.strikethrough_enabled
        assert config.math_enabled
        assert config.footnotes_enabled
        assert config.task_lists_enabled
        assert config.autolinks_enabled

    def test_all_plugin_shortcut(self) -> None:
        """Using plugins=["all"] should enable all built-in plugins."""
        md = Markdown(plugins=["all"])
        
        # Verify all are enabled
        config = md._config
        assert config.tables_enabled
        assert config.strikethrough_enabled
        assert config.math_enabled
        assert config.footnotes_enabled
        assert config.task_lists_enabled
        assert config.autolinks_enabled
        
        # Verify table parsing actually works
        doc = md.parse("| a | b |\n|---|---|\n| 1 | 2 |")
        assert isinstance(doc.children[0], Table)

    def test_plugins_dont_interfere(self) -> None:
        """Enabling one plugin shouldn't affect others."""
        md1 = Markdown(plugins=["table"])
        md2 = Markdown(plugins=["math"])
        
        # Table should only be enabled in md1
        assert md1._config.tables_enabled is True
        assert md1._config.math_enabled is False
        
        # Math should only be enabled in md2
        assert md2._config.tables_enabled is False
        assert md2._config.math_enabled is True


class TestPluginErrorHandling:
    """Test plugin error handling."""

    def test_unknown_plugin_name_in_markdown(self) -> None:
        """Unknown plugin names should not crash, just be ignored."""
        # Currently Markdown silently ignores unknown plugins
        # This test documents the behavior
        md = Markdown(plugins=["nonexistent_plugin"])
        # Should not raise, just won't enable anything special
        result = md("# Test")
        assert "<h1" in result

    def test_empty_plugin_list(self) -> None:
        """Empty plugin list should work (default config)."""
        md = Markdown(plugins=[])
        config = md._config
        
        # All should be disabled
        assert config.tables_enabled is False
        assert config.strikethrough_enabled is False
        assert config.math_enabled is False
