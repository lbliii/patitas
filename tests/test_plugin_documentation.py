"""Documentation validation tests for Patitas plugins.

These tests verify that:
1. Docstring examples actually work (doctests)
2. Documentation code blocks use correct plugin names
3. The "all" plugin is documented and works

These tests would have caught:
- The "all" plugin being documented but not implemented
- The "tables" vs "table" typo in documentation
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from patitas import Markdown
from patitas.plugins import BUILTIN_PLUGINS


class TestDocstringExamples:
    """Verify docstring examples create valid configurations."""

    def test_plugins_init_docstring_all_example(self) -> None:
        """The >>> md = Markdown(plugins=["all"]) example should work."""
        # This exact example appears in plugins/__init__.py docstring
        md = Markdown(plugins=["all"])
        
        # All plugins should be enabled
        assert md._config.tables_enabled, "plugins=['all'] should enable tables"
        assert md._config.math_enabled, "plugins=['all'] should enable math"
        assert md._config.strikethrough_enabled, "plugins=['all'] should enable strikethrough"
        assert md._config.footnotes_enabled, "plugins=['all'] should enable footnotes"
        assert md._config.task_lists_enabled, "plugins=['all'] should enable task_lists"
        assert md._config.autolinks_enabled, "plugins=['all'] should enable autolinks"

    def test_plugins_init_docstring_specific_example(self) -> None:
        """The >>> md = Markdown(plugins=["table", "strikethrough", "math"]) example."""
        md = Markdown(plugins=["table", "strikethrough", "math"])
        
        # These should be enabled
        assert md._config.tables_enabled
        assert md._config.strikethrough_enabled
        assert md._config.math_enabled
        
        # These should NOT be enabled
        assert not md._config.footnotes_enabled
        assert not md._config.task_lists_enabled
        assert not md._config.autolinks_enabled


class TestDocumentationCodeBlocks:
    """Verify documentation uses correct plugin names.
    
    This is a static analysis test that scans documentation files for
    Python code blocks and checks they use valid plugin names.
    """

    # Pattern to find plugins=["..."] in code
    PLUGIN_PATTERN = re.compile(r'plugins\s*=\s*\[([^\]]+)\]')
    
    # Known valid plugin names (including "all")
    VALID_PLUGINS = set(BUILTIN_PLUGINS.keys()) | {"all"}
    
    # Common typos to catch
    KNOWN_TYPOS = {
        "tables": "table",
        "table_list": "task_lists",
        "tasklists": "task_lists",
        "task_list": "task_lists",
        "footnote": "footnotes",
        "autolink": "autolinks",
        "strike": "strikethrough",
        "del": "strikethrough",
    }

    def _extract_plugin_names_from_file(self, filepath: Path) -> list[tuple[int, str]]:
        """Extract plugin names from a file, returns (line_number, plugin_name) tuples."""
        findings = []
        content = filepath.read_text()
        
        for i, line in enumerate(content.split("\n"), start=1):
            match = self.PLUGIN_PATTERN.search(line)
            if match:
                # Parse the list contents
                list_content = match.group(1)
                # Extract quoted strings
                for plugin_match in re.finditer(r'["\'](\w+)["\']', list_content):
                    findings.append((i, plugin_match.group(1)))
        
        return findings

    def test_source_files_use_valid_plugin_names(self) -> None:
        """Source files should not contain KNOWN TYPOS of plugin names.
        
        Only checks for known typos (like 'tables' instead of 'table'),
        not arbitrary strings which may be used for other purposes.
        """
        src_dir = Path(__file__).parent.parent / "src" / "patitas"
        
        errors = []
        for pyfile in src_dir.rglob("*.py"):
            # Skip test files
            if "test" in pyfile.name.lower():
                continue
            for line_num, plugin_name in self._extract_plugin_names_from_file(pyfile):
                # Only flag KNOWN TYPOS
                if plugin_name in self.KNOWN_TYPOS:
                    correct = self.KNOWN_TYPOS[plugin_name]
                    errors.append(
                        f"{pyfile.relative_to(src_dir.parent)}:{line_num}: "
                        f"Plugin typo '{plugin_name}' (should be '{correct}')"
                    )
        
        assert not errors, "Plugin typos found:\n" + "\n".join(errors)

    def test_docs_use_valid_plugin_names(self) -> None:
        """Documentation files should use valid plugin names.
        
        Only checks for KNOWN TYPOS of real plugin names, not arbitrary strings
        which may be example/custom plugin names in documentation.
        """
        site_dir = Path(__file__).parent.parent / "site" / "content"
        
        if not site_dir.exists():
            pytest.skip("Site directory not found")
        
        errors = []
        for mdfile in site_dir.rglob("*.md"):
            for line_num, plugin_name in self._extract_plugin_names_from_file(mdfile):
                # Only flag KNOWN TYPOS (likely mistakes), not arbitrary names
                # (which may be custom plugin examples in docs)
                if plugin_name in self.KNOWN_TYPOS:
                    correct = self.KNOWN_TYPOS[plugin_name]
                    errors.append(
                        f"{mdfile.relative_to(site_dir)}:{line_num}: "
                        f"Plugin typo '{plugin_name}' (should be '{correct}')"
                    )
        
        if errors:
            pytest.fail("Plugin typos in docs:\n" + "\n".join(errors))


class TestCommonTypoRegression:
    """Regression tests for common plugin name typos.
    
    These tests explicitly verify that common typos do NOT work,
    which documents the expected behavior and catches regressions.
    """

    @pytest.mark.parametrize("typo,correct", [
        ("tables", "table"),
        ("tasklists", "task_lists"),
        ("task_list", "task_lists"),
        ("footnote", "footnotes"),
        ("autolink", "autolinks"),
    ])
    def test_common_typos_do_not_enable_features(self, typo: str, correct: str) -> None:
        """Common typos should not accidentally enable plugins."""
        md_typo = Markdown(plugins=[typo])
        md_correct = Markdown(plugins=[correct])
        
        # The typo version should have all plugins disabled
        # (unless the typo happens to match a real plugin)
        if typo not in BUILTIN_PLUGINS:
            # Count enabled features
            typo_enabled = sum(
                1 for field in md_typo._config.__dataclass_fields__
                if field.endswith("_enabled") and getattr(md_typo._config, field)
            )
            assert typo_enabled == 0, (
                f"Typo '{typo}' unexpectedly enabled {typo_enabled} features. "
                f"This may indicate the typo was added as an alias."
            )
        
        # The correct version should have exactly one plugin enabled
        correct_enabled = sum(
            1 for field in md_correct._config.__dataclass_fields__
            if field.endswith("_enabled") and getattr(md_correct._config, field)
        )
        assert correct_enabled == 1, (
            f"Correct plugin '{correct}' enabled {correct_enabled} features, expected 1"
        )


class TestAllPluginEdgeCases:
    """Test edge cases for the "all" plugin shortcut."""

    def test_all_with_other_plugins_still_works(self) -> None:
        """plugins=["all", "table"] should still enable all plugins."""
        md = Markdown(plugins=["all", "table"])
        
        # All should still be enabled
        assert md._config.tables_enabled
        assert md._config.math_enabled
        assert md._config.strikethrough_enabled

    def test_all_expands_to_current_builtin_plugins(self) -> None:
        """plugins=["all"] should expand to exactly the current BUILTIN_PLUGINS."""
        md = Markdown(plugins=["all"])
        
        # The internal _plugins list should contain all builtin plugin names
        for plugin_name in BUILTIN_PLUGINS:
            assert plugin_name in md._plugins, (
                f"Plugin '{plugin_name}' not in _plugins after 'all' expansion"
            )

    def test_all_plugin_not_in_builtin_registry(self) -> None:
        """'all' should not be a registered plugin itself."""
        assert "all" not in BUILTIN_PLUGINS, (
            "'all' should be a special shortcut, not a registered plugin"
        )

    def test_all_enables_same_features_as_explicit_list(self) -> None:
        """plugins=["all"] should enable same features as listing all plugins."""
        md_all = Markdown(plugins=["all"])
        md_explicit = Markdown(plugins=list(BUILTIN_PLUGINS.keys()))
        
        # Compare all _enabled fields
        for field in md_all._config.__dataclass_fields__:
            if field.endswith("_enabled"):
                all_value = getattr(md_all._config, field)
                explicit_value = getattr(md_explicit._config, field)
                assert all_value == explicit_value, (
                    f"Mismatch for {field}: 'all'={all_value}, explicit={explicit_value}"
                )
