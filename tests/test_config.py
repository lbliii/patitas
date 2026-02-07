"""Tests for ContextVar-based parse configuration.

Validates thread isolation, context manager behavior, and config inheritance
for sub-parsers.
"""

from threading import Thread

import pytest

from patitas import (
    Markdown,
    ParseConfig,
    Parser,
    get_parse_config,
    parse,
    parse_config_context,
    reset_parse_config,
    set_parse_config,
)
from patitas.nodes import Table


class TestParseConfigDataclass:
    """Test ParseConfig frozen dataclass behavior."""

    def test_default_values(self) -> None:
        """Default config has all extensions disabled."""
        config = ParseConfig()
        assert config.tables_enabled is False
        assert config.strikethrough_enabled is False
        assert config.task_lists_enabled is False
        assert config.footnotes_enabled is False
        assert config.math_enabled is False
        assert config.autolinks_enabled is False
        assert config.directive_registry is None
        assert config.strict_contracts is False
        assert config.text_transformer is None

    def test_immutability(self) -> None:
        """Config is frozen and cannot be modified."""
        config = ParseConfig()
        with pytest.raises(AttributeError):
            config.tables_enabled = True  # type: ignore[misc]

    def test_custom_values(self) -> None:
        """Config can be created with custom values."""
        config = ParseConfig(
            tables_enabled=True,
            math_enabled=True,
            strict_contracts=True,
        )
        assert config.tables_enabled is True
        assert config.math_enabled is True
        assert config.strict_contracts is True
        assert config.strikethrough_enabled is False  # Still default


class TestContextVarFunctions:
    """Test get/set/reset functions."""

    def teardown_method(self) -> None:
        """Reset config after each test."""
        reset_parse_config()

    def test_default_config(self) -> None:
        """Default config is returned when not explicitly set."""
        config = get_parse_config()
        assert config.tables_enabled is False
        assert config.math_enabled is False

    def test_set_and_get(self) -> None:
        """set_parse_config() changes the current config."""
        custom_config = ParseConfig(tables_enabled=True, math_enabled=True)
        set_parse_config(custom_config)

        config = get_parse_config()
        assert config.tables_enabled is True
        assert config.math_enabled is True

    def test_reset_restores_default(self) -> None:
        """reset_parse_config() restores default values."""
        set_parse_config(ParseConfig(tables_enabled=True))
        reset_parse_config()

        config = get_parse_config()
        assert config.tables_enabled is False


class TestParseConfigContext:
    """Test parse_config_context context manager."""

    def test_context_sets_config(self) -> None:
        """Context manager sets config within the block."""
        with parse_config_context(ParseConfig(tables_enabled=True)):
            assert get_parse_config().tables_enabled is True
        # Restored after context
        assert get_parse_config().tables_enabled is False

    def test_nested_contexts(self) -> None:
        """Nested context managers work correctly."""
        with parse_config_context(ParseConfig(tables_enabled=True)):
            assert get_parse_config().tables_enabled is True
            assert get_parse_config().math_enabled is False

            with parse_config_context(ParseConfig(math_enabled=True)):
                # Inner context changes
                assert get_parse_config().math_enabled is True
                # But tables_enabled is now False (new config)
                assert get_parse_config().tables_enabled is False

            # Outer context restored
            assert get_parse_config().tables_enabled is True
            assert get_parse_config().math_enabled is False

        # Default restored
        assert get_parse_config().tables_enabled is False
        assert get_parse_config().math_enabled is False

    def test_context_restores_on_exception(self) -> None:
        """Context manager restores config even if exception is raised."""
        with pytest.raises(ValueError, match="test"):
            with parse_config_context(ParseConfig(tables_enabled=True)):
                assert get_parse_config().tables_enabled is True
                raise ValueError("test")

        # Config is restored despite exception
        assert get_parse_config().tables_enabled is False


class TestThreadIsolation:
    """Test thread-local configuration isolation."""

    def test_thread_isolation(self) -> None:
        """Each thread sees its own config."""
        results: dict[int, dict[str, bool]] = {}

        def worker(thread_id: int, config: ParseConfig) -> None:
            set_parse_config(config)
            parser = Parser("# Test")
            results[thread_id] = {
                "tables": parser._tables_enabled,
                "math": parser._math_enabled,
            }

        configs = [
            ParseConfig(tables_enabled=True, math_enabled=True),
            ParseConfig(tables_enabled=False, math_enabled=True),
            ParseConfig(tables_enabled=True, math_enabled=False),
            ParseConfig(tables_enabled=False, math_enabled=False),
        ]

        threads = [Thread(target=worker, args=(i, c)) for i, c in enumerate(configs)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify each thread saw its own config
        assert results[0] == {"tables": True, "math": True}
        assert results[1] == {"tables": False, "math": True}
        assert results[2] == {"tables": True, "math": False}
        assert results[3] == {"tables": False, "math": False}

    def test_concurrent_markdown_instances(self) -> None:
        """Multiple Markdown instances in threads have isolated config."""
        results: dict[int, str] = {}
        source = "| a | b |\n|---|---|\n| 1 | 2 |"

        def worker(thread_id: int, with_tables: bool) -> None:
            plugins = ["table"] if with_tables else []
            md = Markdown(plugins=plugins)
            results[thread_id] = md(source)

        threads = [
            Thread(target=worker, args=(0, True)),
            Thread(target=worker, args=(1, False)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Thread 0 (tables enabled) should have table HTML
        assert "<table>" in results[0]
        # Thread 1 (tables disabled) should NOT have table HTML
        assert "<table>" not in results[1]


class TestParserConfigInheritance:
    """Test that sub-parsers inherit config via ContextVar."""

    def teardown_method(self) -> None:
        """Reset config after each test."""
        reset_parse_config()

    def test_parser_reads_from_contextvar(self) -> None:
        """Parser reads config from ContextVar, not instance attributes."""
        set_parse_config(ParseConfig(tables_enabled=True, math_enabled=True))

        parser = Parser("# Test")
        assert parser._tables_enabled is True
        assert parser._math_enabled is True

        # Change config
        set_parse_config(ParseConfig(tables_enabled=False))
        assert parser._tables_enabled is False  # Reflects new config!

    def test_sub_parser_inherits_config(self) -> None:
        """Sub-parsers automatically inherit config from ContextVar."""
        source = "> | a | b |\n> |---|---|\n> | 1 | 2 |"

        # Use Markdown class which sets ContextVar
        md = Markdown(plugins=["table"])
        doc = md.parse(source)

        # Block quote should contain a table (parsed by sub-parser)
        blockquote = doc.children[0]
        assert blockquote.__class__.__name__ == "BlockQuote"
        # Sub-parser should have parsed the table
        assert len(blockquote.children) > 0


class TestMarkdownConfigIntegration:
    """Test Markdown class config integration."""

    def test_markdown_builds_config_from_plugins(self) -> None:
        """Markdown class builds config from plugins list."""
        md = Markdown(
            plugins=["table", "math", "strikethrough", "task_lists", "footnotes", "autolinks"]
        )
        # Config is built and stored
        assert md._config.tables_enabled is True
        assert md._config.math_enabled is True
        assert md._config.strikethrough_enabled is True
        assert md._config.task_lists_enabled is True
        assert md._config.footnotes_enabled is True
        assert md._config.autolinks_enabled is True

    def test_markdown_sets_contextvar_during_call(self) -> None:
        """Markdown sets ContextVar during __call__."""
        md = Markdown(plugins=["table"])

        # Before calling, config should be default
        assert get_parse_config().tables_enabled is False

        # During call, config is set (we can't easily test this mid-call,
        # but we can verify by checking that tables are parsed)
        result = md("| a | b |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in result

        # After call, config is reset to default
        assert get_parse_config().tables_enabled is False

    def test_parse_function_sets_contextvar(self) -> None:
        """Top-level parse() function sets ContextVar."""
        # Before parse, config is default
        assert get_parse_config().tables_enabled is False

        # parse() sets config
        doc = parse("# Hello")

        # After parse, config is reset
        assert get_parse_config().tables_enabled is False

    def test_tables_with_markdown_class(self) -> None:
        """Tables are parsed when enabled via Markdown plugins."""
        md = Markdown(plugins=["table"])
        doc = md.parse("| a | b |\n|---|---|\n| 1 | 2 |")

        # Should have a table
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], Table)

    def test_tables_disabled_by_default(self) -> None:
        """Tables are NOT parsed when plugins not specified."""
        md = Markdown()  # No plugins
        doc = md.parse("| a | b |\n|---|---|\n| 1 | 2 |")

        # Should be a paragraph, not a table
        assert len(doc.children) == 1
        assert doc.children[0].__class__.__name__ == "Paragraph"


class TestParserSlotReduction:
    """Verify Parser slot count reduction."""

    def test_parser_slot_count(self) -> None:
        """Parser has reduced slot count (9 vs 18 before)."""
        assert len(Parser.__slots__) == 9

    def test_parser_has_required_slots(self) -> None:
        """Parser has all required per-parse state slots."""
        required_slots = {
            "_source",
            "_tokens",
            "_pos",
            "_current",
            "_source_file",
            "_directive_stack",
            "_link_refs",
            "_containers",
            "_allow_setext_headings",
        }
        assert set(Parser.__slots__) == required_slots

    def test_parser_no_config_slots(self) -> None:
        """Parser does NOT have config slots (they're now properties)."""
        config_slots = {
            "_tables_enabled",
            "_strikethrough_enabled",
            "_task_lists_enabled",
            "_footnotes_enabled",
            "_math_enabled",
            "_autolinks_enabled",
            "_directive_registry",
            "_strict_contracts",
            "_text_transformer",
        }
        parser_slots = set(Parser.__slots__)
        assert config_slots.isdisjoint(parser_slots), "Config should be properties, not slots"
