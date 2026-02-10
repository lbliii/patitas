"""Tests for Patitas utility modules."""


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

    def test_max_length_zero(self) -> None:
        """Edge case: max_length=0 should return empty string."""
        from patitas.utils.text import slugify

        assert slugify("hello world", max_length=0) == ""

    def test_max_length_negative(self) -> None:
        """Edge case: negative max_length follows Python slice semantics."""
        from patitas.utils.text import slugify

        # Negative values follow Python slice semantics (remove from end)
        # "hello"[:-1] == "hell"
        assert slugify("hello", max_length=-1) == "hell"
        assert slugify("hello", max_length=-2) == "hel"


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

    def test_truncate_zero(self) -> None:
        """Edge case: truncate=0 should return empty string."""
        from patitas.utils.hashing import hash_str

        assert hash_str("hello", truncate=0) == ""


class TestHashBytes:
    """Tests for hash_bytes function."""

    def test_basic_hash(self) -> None:
        from patitas.utils.hashing import hash_bytes

        result = hash_bytes(b"hello")
        assert len(result) == 64  # SHA256 hex length
        assert result.startswith("2cf24dba")  # Known hash prefix

    def test_truncated_hash(self) -> None:
        from patitas.utils.hashing import hash_bytes

        assert hash_bytes(b"hello", truncate=8) == "2cf24dba"

    def test_truncate_zero(self) -> None:
        """Edge case: truncate=0 should return empty string."""
        from patitas.utils.hashing import hash_bytes

        assert hash_bytes(b"hello", truncate=0) == ""

    def test_consistent_hash(self) -> None:
        from patitas.utils.hashing import hash_bytes

        assert hash_bytes(b"test") == hash_bytes(b"test")


class TestSubtreeHash:
    """Tests for deterministic subtree hashing."""

    def test_same_subtree_same_hash(self) -> None:
        from patitas.location import SourceLocation
        from patitas.nodes import Paragraph, Text
        from patitas.utils.hashing import subtree_hash

        loc = SourceLocation(lineno=1, col_offset=0)
        a = Paragraph(location=loc, children=(Text(location=loc, content="hello"),))
        b = Paragraph(location=loc, children=(Text(location=loc, content="hello"),))
        assert subtree_hash(a) == subtree_hash(b)

    def test_different_subtree_different_hash(self) -> None:
        from patitas.location import SourceLocation
        from patitas.nodes import Paragraph, Text
        from patitas.utils.hashing import subtree_hash

        loc = SourceLocation(lineno=1, col_offset=0)
        a = Paragraph(location=loc, children=(Text(location=loc, content="hello"),))
        b = Paragraph(location=loc, children=(Text(location=loc, content="world"),))
        assert subtree_hash(a) != subtree_hash(b)


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

    def test_logger_name_starting_with_patitas_not_submodule(self) -> None:
        """Names starting with 'patitas' but not submodules should get prefix."""
        from patitas.utils.logger import get_logger

        # This was a bug - patitas_other incorrectly matched startswith("patitas")
        logger = get_logger("patitas_other")
        assert logger.name == "patitas.patitas_other"

    def test_logger_exact_patitas_name(self) -> None:
        """The exact name 'patitas' should not get double-prefixed."""
        from patitas.utils.logger import get_logger

        logger = get_logger("patitas")
        assert logger.name == "patitas"


class TestEscapeHtml:
    """Tests for escape_html function."""

    def test_basic_escape(self) -> None:
        from patitas.utils.text import escape_html

        assert escape_html("<script>") == "&lt;script&gt;"

    def test_escape_quotes(self) -> None:
        from patitas.utils.text import escape_html

        assert escape_html('a="b"') == "a=&quot;b&quot;"
        assert escape_html("a='b'") == "a=&#x27;b&#x27;"

    def test_escape_ampersand(self) -> None:
        from patitas.utils.text import escape_html

        assert escape_html("a & b") == "a &amp; b"

    def test_escape_empty(self) -> None:
        from patitas.utils.text import escape_html

        assert escape_html("") == ""

    def test_escape_xss_payload(self) -> None:
        """Verify common XSS payloads are properly escaped."""
        from patitas.utils.text import escape_html

        payload = "<script>alert('xss')</script>"
        escaped = escape_html(payload)
        assert "<script>" not in escaped
        assert "'" not in escaped


class TestUtilsPublicAPI:
    """Tests for the public API of the utils package."""

    def test_all_exports_importable(self) -> None:
        """All items in __all__ should be importable from patitas.utils."""
        import patitas.utils as utils

        for name in utils.__all__:
            assert hasattr(utils, name), f"{name} in __all__ but not importable"

    def test_expected_exports(self) -> None:
        """Verify expected functions are exported."""
        from patitas.utils import (
            escape_html,
            get_logger,
            hash_bytes,
            hash_str,
            slugify,
            subtree_hash,
        )

        # Verify they're callable
        assert callable(escape_html)
        assert callable(get_logger)
        assert callable(hash_bytes)
        assert callable(hash_str)
        assert callable(slugify)
        assert callable(subtree_hash)


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
