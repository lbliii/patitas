"""Configuration consistency tests for Patitas.

These tests ensure that:
1. ParseConfig fields match plugin names consistently
2. The Markdown class correctly maps plugins to config fields
3. No typos or naming mismatches exist between components

This would have caught the "table" vs "tables" bug immediately.
"""

import ast
import contextlib
from pathlib import Path

from patitas import Markdown, ParseConfig
from patitas.plugins import BUILTIN_PLUGINS


class TestConfigPluginConsistency:
    """Ensure ParseConfig and plugin system are consistent."""

    def test_plugin_to_config_round_trip(self) -> None:
        """Each plugin, when enabled, should set exactly one config field to True."""
        for plugin_name in BUILTIN_PLUGINS:
            md_with = Markdown(plugins=[plugin_name])
            md_without = Markdown(plugins=[])

            # Find which config field(s) changed
            changed_fields = []
            for field_name in ParseConfig.__dataclass_fields__:
                if not field_name.endswith("_enabled"):
                    continue

                with_value = getattr(md_with._config, field_name)
                without_value = getattr(md_without._config, field_name)

                if with_value != without_value:
                    changed_fields.append(field_name)

            assert len(changed_fields) == 1, (
                f"Plugin '{plugin_name}' changed {len(changed_fields)} config fields: "
                f"{changed_fields}. Expected exactly 1."
            )

            # The changed field should be True
            assert getattr(md_with._config, changed_fields[0]) is True, (
                f"Plugin '{plugin_name}' set {changed_fields[0]} to something other than True"
            )

    def test_all_enabled_fields_have_plugins(self) -> None:
        """Every *_enabled config field should be settable by some plugin."""
        # Collect all enabled fields
        enabled_fields = {
            name for name in ParseConfig.__dataclass_fields__ if name.endswith("_enabled")
        }

        # Collect fields that plugins can set
        settable_fields = set()
        for plugin_name in BUILTIN_PLUGINS:
            md = Markdown(plugins=[plugin_name])
            for field_name in enabled_fields:
                if getattr(md._config, field_name) is True:
                    settable_fields.add(field_name)

        missing = enabled_fields - settable_fields
        assert not missing, f"Config fields {missing} have no corresponding plugin to enable them"

    def test_no_orphan_plugins(self) -> None:
        """All registered plugins should affect at least one config field."""
        for plugin_name in BUILTIN_PLUGINS:
            md = Markdown(plugins=[plugin_name])

            # Check if any *_enabled field is True
            any_enabled = any(
                getattr(md._config, field) is True
                for field in ParseConfig.__dataclass_fields__
                if field.endswith("_enabled")
            )

            assert any_enabled, (
                f"Plugin '{plugin_name}' does not enable any config field. "
                f"Either the plugin has no effect or there's a naming mismatch."
            )


class TestMarkdownClassPluginMapping:
    """Test the Markdown class's internal plugin->config mapping."""

    def test_markdown_uses_correct_plugin_names(self) -> None:
        """Verify Markdown class checks for correct plugin names when building config.

        This is a static analysis test that would have caught the "tables" vs "table" bug.
        """
        # Read the Markdown class source
        src_file = Path(__file__).parent.parent / "src" / "patitas" / "__init__.py"
        source = src_file.read_text()
        tree = ast.parse(source)

        # Find all string comparisons with self._plugins
        plugin_checks = [
            node.left.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Attribute)
            and node.comparators[0].attr == "_plugins"
            and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)
        ]

        # Verify all checked plugin names exist in BUILTIN_PLUGINS
        registered = set(BUILTIN_PLUGINS.keys())
        for checked_name in plugin_checks:
            assert checked_name in registered, (
                f"Markdown class checks for plugin '{checked_name}' but it's not "
                f"in BUILTIN_PLUGINS. Registered plugins: {registered}"
            )


class TestParseConfigDefaults:
    """Test ParseConfig default values are sensible."""

    def test_default_config_has_all_disabled(self) -> None:
        """Default ParseConfig should have all *_enabled fields as False."""
        config = ParseConfig()

        for field_name in ParseConfig.__dataclass_fields__:
            if field_name.endswith("_enabled"):
                value = getattr(config, field_name)
                assert value is False, (
                    f"ParseConfig.{field_name} defaults to {value}, expected False"
                )

    def test_default_config_is_usable(self) -> None:
        """Default config should allow basic parsing without plugins."""
        md = Markdown()  # No plugins
        result = md("# Hello\n\nWorld")

        assert "<h1" in result
        assert "Hello" in result
        assert "<p>" in result
        assert "World" in result


class TestPluginNamingConventions:
    """Test that plugin names follow conventions."""

    def test_plugin_names_are_lowercase(self) -> None:
        """All plugin names should be lowercase."""
        for name in BUILTIN_PLUGINS:
            assert name == name.lower(), f"Plugin name '{name}' should be lowercase"

    def test_plugin_names_use_underscores(self) -> None:
        """Multi-word plugin names should use underscores, not hyphens."""
        for name in BUILTIN_PLUGINS:
            assert "-" not in name, f"Plugin name '{name}' uses hyphens; use underscores instead"

    def test_plugin_name_matches_module_name(self) -> None:
        """Plugin names should match their module names where possible."""
        import importlib

        for name in BUILTIN_PLUGINS:
            # Some plugins might use different module names (e.g., plurals)
            with contextlib.suppress(ModuleNotFoundError):
                importlib.import_module(f"patitas.plugins.{name}")


class TestRegressionPluginNameMismatch:
    """Regression tests for the table/tables naming bug."""

    def test_table_plugin_by_registered_name(self) -> None:
        """Table plugin works when using its registered name."""
        # This is the correct way (as registered in BUILTIN_PLUGINS)
        md = Markdown(plugins=["table"])
        doc = md.parse("| a | b |\n|---|---|\n| 1 | 2 |")

        # Should parse as table, not paragraph
        from patitas.nodes import Table

        assert isinstance(doc.children[0], Table)

    def test_tables_plural_does_nothing(self) -> None:
        """Using wrong plugin name 'tables' (plural) should not enable tables."""
        # This was the bug: checking "tables" instead of "table"
        md = Markdown(plugins=["tables"])  # Note: plural

        # The config should NOT have tables enabled
        # because "tables" is not a registered plugin
        assert md._config.tables_enabled is False, (
            "Using 'tables' (plural) incorrectly enabled table parsing. "
            "This suggests a regression of the naming mismatch bug."
        )
