"""Tests for ParseConfig.from_dict() method.

The from_dict() method enables framework integration by allowing
config creation from dictionaries.
"""

import pytest

from patitas.config import ParseConfig


class TestParseConfigFromDict:
    """Test ParseConfig.from_dict() factory method."""

    def test_from_dict_basic(self):
        """from_dict should create config with specified values."""
        config = ParseConfig.from_dict({
            "tables_enabled": True,
            "math_enabled": True,
        })
        
        assert config.tables_enabled is True
        assert config.math_enabled is True
        # Defaults should still apply
        assert config.strikethrough_enabled is False

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict should silently ignore unknown keys."""
        config = ParseConfig.from_dict({
            "tables_enabled": True,
            "unknown_key": "ignored",
            "another_unknown": 42,
        })
        
        assert config.tables_enabled is True
        # Should not raise, just ignore

    def test_from_dict_empty(self):
        """from_dict with empty dict should return default config."""
        config = ParseConfig.from_dict({})
        default = ParseConfig()
        
        assert config.tables_enabled == default.tables_enabled
        assert config.math_enabled == default.math_enabled
        assert config.strikethrough_enabled == default.strikethrough_enabled

    def test_from_dict_all_fields(self):
        """from_dict should support all ParseConfig fields."""
        config = ParseConfig.from_dict({
            "tables_enabled": True,
            "strikethrough_enabled": True,
            "task_lists_enabled": True,
            "footnotes_enabled": True,
            "math_enabled": True,
            "autolinks_enabled": True,
            "strict_contracts": True,
        })
        
        assert config.tables_enabled is True
        assert config.strikethrough_enabled is True
        assert config.task_lists_enabled is True
        assert config.footnotes_enabled is True
        assert config.math_enabled is True
        assert config.autolinks_enabled is True
        assert config.strict_contracts is True

    def test_from_dict_with_directive_registry(self):
        """from_dict should support directive_registry field."""
        # Use a mock registry (just needs to be non-None)
        mock_registry = object()
        
        config = ParseConfig.from_dict({
            "directive_registry": mock_registry,
        })
        
        assert config.directive_registry is mock_registry

    def test_from_dict_with_text_transformer(self):
        """from_dict should support text_transformer field."""
        def my_transformer(text: str) -> str:
            return text.upper()
        
        config = ParseConfig.from_dict({
            "text_transformer": my_transformer,
        })
        
        assert config.text_transformer is my_transformer

    def test_from_dict_returns_frozen_config(self):
        """from_dict should return immutable (frozen) config."""
        config = ParseConfig.from_dict({"tables_enabled": True})
        
        with pytest.raises(AttributeError):
            config.tables_enabled = False  # type: ignore

    def test_from_dict_partial_override(self):
        """from_dict should only override specified fields."""
        config = ParseConfig.from_dict({
            "tables_enabled": True,
            # Other fields not specified
        })
        
        # Specified field
        assert config.tables_enabled is True
        # Defaults for unspecified fields
        assert config.strikethrough_enabled is False
        assert config.math_enabled is False
