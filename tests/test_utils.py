"""Tests for Patitas utility modules."""

from __future__ import annotations


class TestSlugify:
    """Tests for slugify function."""

    def test_basic_slugify(self) -> None:
        from patitas.utils.text import slugify

        assert slugify("Hello World") == "hello-world"
        assert slugify("Hello World!") == "hello-world"
        assert slugify("Test & Code") == "test-code"

    def test_html_entities(self) -> None:
        from patitas.utils.text import slugify

        assert slugify("Test &amp; Code") == "test-code"
        assert slugify("&lt;script&gt;") == "script"

    def test_unicode(self) -> None:
        from patitas.utils.text import slugify

        assert slugify("Café") == "café"
        assert slugify("你好世界") == "你好世界"

    def test_max_length(self) -> None:
        from patitas.utils.text import slugify

        result = slugify("Very Long Title Here", max_length=10)
        assert len(result) <= 10
        assert result == "very-long"

    def test_custom_separator(self) -> None:
        from patitas.utils.text import slugify

        assert slugify("hello world", separator="_") == "hello_world"

    def test_empty_string(self) -> None:
        from patitas.utils.text import slugify

        assert slugify("") == ""


class TestHashStr:
    """Tests for hash_str function."""

    def test_basic_hash(self) -> None:
        from patitas.utils.hashing import hash_str

        result = hash_str("hello")
        assert len(result) == 64  # SHA256 hex length
        assert result.startswith("2cf24dba")  # Known hash prefix

    def test_truncated_hash(self) -> None:
        from patitas.utils.hashing import hash_str

        result = hash_str("hello", truncate=16)
        assert len(result) == 16
        assert result == "2cf24dba5fb0a30e"

    def test_consistent_hash(self) -> None:
        from patitas.utils.hashing import hash_str

        # Same input should always produce same output
        assert hash_str("test") == hash_str("test")

    def test_different_inputs(self) -> None:
        from patitas.utils.hashing import hash_str

        assert hash_str("a") != hash_str("b")


class TestLogger:
    """Tests for logger module."""

    def test_get_logger(self) -> None:
        from patitas.utils.logger import get_logger

        logger = get_logger("mymodule")
        assert logger.name == "patitas.mymodule"

    def test_logger_with_patitas_prefix(self) -> None:
        from patitas.utils.logger import get_logger

        logger = get_logger("patitas.parser")
        assert logger.name == "patitas.parser"


class TestErrors:
    """Tests for error classes."""

    def test_patitas_error(self) -> None:
        from patitas.errors import PatitasError

        error = PatitasError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_parse_error_with_location(self) -> None:
        from patitas.errors import ParseError

        error = ParseError("Invalid syntax", lineno=10, col_offset=5)
        assert "10:5" in str(error)
        assert "Invalid syntax" in str(error)

    def test_parse_error_with_file(self) -> None:
        from patitas.errors import ParseError

        error = ParseError("Invalid syntax", lineno=10, source_file="test.md")
        assert "test.md" in str(error)

    def test_directive_contract_error(self) -> None:
        from patitas.errors import DirectiveContractError

        error = DirectiveContractError("note", "Missing required option", lineno=5)
        assert "note" in str(error)
        assert "line 5" in str(error)

    def test_plugin_error(self) -> None:
        from patitas.errors import PluginError

        error = PluginError("table", "Failed to initialize")
        assert "table" in str(error)
        assert "Failed to initialize" in str(error)
