"""Property-based tests for Patitas plugins using Hypothesis.

These tests verify invariants that should hold for any combination of plugins:
1. Any subset of plugins can be enabled together
2. Plugin combinations are deterministic
3. Parsing never crashes regardless of plugin combination

Property-based testing finds edge cases that example-based tests miss.
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from patitas import Markdown
from patitas.plugins import BUILTIN_PLUGINS

# Strategy for generating plugin lists
plugin_names = st.sampled_from(list(BUILTIN_PLUGINS.keys()))
plugin_lists = st.lists(plugin_names, max_size=len(BUILTIN_PLUGINS), unique=True)
plugin_lists_with_all = st.one_of(
    plugin_lists,
    st.just(["all"]),
    st.lists(st.sampled_from([*list(BUILTIN_PLUGINS.keys()), "all"]), max_size=7, unique=True),
)


class TestPluginCombinationProperties:
    """Property-based tests for plugin combinations."""

    @given(plugins=plugin_lists)
    @settings(max_examples=50)
    def test_any_plugin_combination_creates_valid_markdown(self, plugins: list[str]) -> None:
        """Any combination of valid plugins should create a working Markdown instance."""
        md = Markdown(plugins=plugins)

        # Should be able to parse basic markdown
        result = md("# Hello\n\nWorld")
        assert "<h1" in result
        assert "Hello" in result

    @given(plugins=plugin_lists)
    @settings(max_examples=50)
    def test_plugin_enablement_is_deterministic(self, plugins: list[str]) -> None:
        """Same plugins should always produce same config."""
        md1 = Markdown(plugins=plugins)
        md2 = Markdown(plugins=plugins)

        # Compare all _enabled fields
        for field in md1._config.__dataclass_fields__:
            if field.endswith("_enabled"):
                v1 = getattr(md1._config, field)
                v2 = getattr(md2._config, field)
                assert v1 == v2, f"Non-deterministic: {field} was {v1} then {v2}"

    @given(plugins=plugin_lists)
    @settings(max_examples=50)
    def test_enabled_count_matches_plugin_count(self, plugins: list[str]) -> None:
        """Number of enabled features should match number of plugins."""
        md = Markdown(plugins=plugins)

        enabled_count = sum(
            1
            for field in md._config.__dataclass_fields__
            if field.endswith("_enabled") and getattr(md._config, field)
        )

        assert enabled_count == len(plugins), (
            f"Enabled {enabled_count} features but passed {len(plugins)} plugins: {plugins}"
        )

    @given(plugins=plugin_lists_with_all)
    @settings(max_examples=30)
    def test_all_plugin_with_others_enables_all(self, plugins: list[str]) -> None:
        """If 'all' is in plugins, all features should be enabled."""
        assume("all" in plugins)

        md = Markdown(plugins=plugins)

        # All _enabled fields should be True
        for field in md._config.__dataclass_fields__:
            if field.endswith("_enabled"):
                value = getattr(md._config, field)
                assert value is True, (
                    f"With 'all' in plugins, {field} should be True but was {value}"
                )


class TestConfigWithRandomPlugins:
    """Test that config is correctly set with any plugin combination."""

    @given(plugins=plugin_lists_with_all)
    @settings(max_examples=30)
    def test_config_correctly_set(self, plugins: list[str]) -> None:
        """Config should be correctly set regardless of plugin combination."""
        md = Markdown(plugins=plugins)

        # If "all" is in plugins, everything should be enabled
        if "all" in plugins:
            assert md._config.tables_enabled
            assert md._config.math_enabled
            assert md._config.strikethrough_enabled
            assert md._config.footnotes_enabled
            assert md._config.task_lists_enabled
            assert md._config.autolinks_enabled
        else:
            # Each specific plugin should enable its feature
            assert md._config.tables_enabled == ("table" in plugins)
            assert md._config.math_enabled == ("math" in plugins)
            assert md._config.strikethrough_enabled == ("strikethrough" in plugins)
            assert md._config.footnotes_enabled == ("footnotes" in plugins)
            assert md._config.task_lists_enabled == ("task_lists" in plugins)
            assert md._config.autolinks_enabled == ("autolinks" in plugins)


class TestPluginOrderIndependence:
    """Verify plugin order doesn't affect behavior."""

    @given(plugins=plugin_lists)
    @settings(max_examples=30)
    def test_plugin_order_doesnt_matter_for_config(self, plugins: list[str]) -> None:
        """Plugin order should not affect which features are enabled."""
        assume(len(plugins) > 1)

        md_forward = Markdown(plugins=plugins)
        md_reverse = Markdown(plugins=list(reversed(plugins)))

        # Compare all _enabled fields
        for field in md_forward._config.__dataclass_fields__:
            if field.endswith("_enabled"):
                v_fwd = getattr(md_forward._config, field)
                v_rev = getattr(md_reverse._config, field)
                assert v_fwd == v_rev, (
                    f"Order matters for {field}: forward={v_fwd}, reverse={v_rev}"
                )
