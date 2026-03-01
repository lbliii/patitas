"""Tests for parse_frontmatter and extract_body."""

from patitas import extract_body, parse_frontmatter


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_basic_frontmatter(self) -> None:
        """Parse basic YAML frontmatter."""
        content = "---\ntitle: Hello\nauthor: Jane\n---\n\nBody content"
        meta, body = parse_frontmatter(content)

        assert meta == {"title": "Hello", "author": "Jane"}
        assert body == "Body content"

    def test_no_frontmatter(self) -> None:
        """Content without frontmatter returns empty dict."""
        content = "# Just a heading\n\nSome text."
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == content

    def test_empty_frontmatter(self) -> None:
        """Empty frontmatter block returns empty dict."""
        content = "---\n---\nBody"
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == "Body"

    def test_frontmatter_with_lists(self) -> None:
        """Frontmatter with YAML lists."""
        content = "---\ntags:\n  - python\n  - testing\n---\n\nContent"
        meta, _body = parse_frontmatter(content)

        assert meta == {"tags": ["python", "testing"]}

    def test_frontmatter_with_nested_dict(self) -> None:
        """Frontmatter with nested dictionaries."""
        content = "---\nmeta:\n  og_title: Test\n  og_image: /img.png\n---\nBody"
        meta, _body = parse_frontmatter(content)

        assert meta == {"meta": {"og_title": "Test", "og_image": "/img.png"}}

    def test_invalid_yaml_returns_body_only(self) -> None:
        """Invalid YAML returns empty dict and body with frontmatter stripped."""
        content = "---\ntitle: [unclosed bracket\n---\nBody"
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == "Body"

    def test_unclosed_frontmatter(self) -> None:
        """Unclosed frontmatter (no closing ---) returns content as-is."""
        content = "---\ntitle: No closing delimiter"
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == content

    def test_numeric_normalization_weight(self) -> None:
        """weight is coerced to float."""
        content = "---\nweight: 10\ntitle: Test\n---\nBody"
        meta, _body = parse_frontmatter(content)

        assert meta["weight"] == 10.0
        assert meta["title"] == "Test"

    def test_numeric_normalization_order(self) -> None:
        """order is coerced to float."""
        content = "---\norder: 5\ntitle: Test\n---\nBody"
        meta, _body = parse_frontmatter(content)

        assert meta["order"] == 5.0

    def test_numeric_normalization_priority(self) -> None:
        """priority is coerced to float."""
        content = "---\npriority: 1\ntitle: Test\n---\nBody"
        meta, _body = parse_frontmatter(content)

        assert meta["priority"] == 1.0

    def test_numeric_from_string(self) -> None:
        """String numeric values are coerced when possible."""
        content = "---\nweight: \"10\"\ntitle: Test\n---\nBody"
        meta, _body = parse_frontmatter(content)

        assert meta["weight"] == 10.0

    def test_non_dict_yaml_returns_body(self) -> None:
        """YAML that parses to non-dict (e.g. string) returns body."""
        content = "---\njust a string\n---\nBody"
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == "Body"


class TestExtractBody:
    """Tests for extract_body function."""

    def test_normal_frontmatter(self) -> None:
        """Extract content from normal frontmatter."""
        content = "---\ntitle: Test\n---\n\nActual content here."
        result = extract_body(content)

        assert result == "Actual content here."

    def test_empty_frontmatter(self) -> None:
        """Extract content from empty frontmatter."""
        content = "---\n---\nContent after"
        result = extract_body(content)

        assert result == "Content after"

    def test_no_frontmatter(self) -> None:
        """Content without frontmatter returned as-is (stripped)."""
        content = "# Heading\n\nNo frontmatter"
        result = extract_body(content)

        assert result == content.strip()

    def test_unclosed_frontmatter(self) -> None:
        """Unclosed frontmatter returns everything after first ---."""
        content = "---\nThis has no closing delimiter"
        result = extract_body(content)

        assert "This has no closing delimiter" in result

    def test_content_with_dashes(self) -> None:
        """Content with --- in body handled correctly."""
        content = "---\ntitle: Test\n---\n\n# Heading\n\n---\n\nMore content"
        result = extract_body(content)

        assert "# Heading" in result
        assert "---" in result
        assert "More content" in result
