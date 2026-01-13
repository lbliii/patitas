"""CommonMark 0.31.2 Specification Compliance Tests.

This module runs the official CommonMark spec tests against Patitas.
The spec.json contains 652 examples from the CommonMark specification.

Usage:
# Run all spec tests
pytest tests/test_commonmark_spec.py -v -m commonmark

# Run specific section
pytest tests/test_commonmark_spec.py -k "Emphasis" -m commonmark

# Run single example
pytest tests/test_commonmark_spec.py -k "example_042" -m commonmark

Baseline Tracking:
The baseline pass rate is tracked in this file. Update after each sprint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any


# Load the CommonMark spec
SPEC_PATH = Path(__file__).parent / "fixtures" / "commonmark_spec_0_31_2.json"


def _load_spec() -> list[dict[str, Any]]:
    """Load spec tests, returning empty list if fixture not found."""
    if not SPEC_PATH.exists():
        return []
    return json.loads(SPEC_PATH.read_text())


SPEC_TESTS: list[dict[str, Any]] = _load_spec()


def normalize_html(html_string: str) -> str:
    """Normalize HTML for comparison.

    CommonMark spec allows variation in:
    - Attribute ordering
    - Self-closing tag style (<br> vs <br />)
    - Whitespace handling
    - Entity encoding

    This normalizer makes comparisons more forgiving while still
    validating semantic correctness.
    """
    result = html_string.strip()

    # Normalize self-closing tags: <br /> -> <br>
    result = re.sub(r"<(br|hr|img)(\s[^>]*)?\s*/?>", r"<\1\2>", result)

    # Normalize empty self-closing: <tag /> -> <tag>
    result = re.sub(r"\s*/>", ">", result)

    # Normalize multiple spaces to single space
    result = re.sub(r" +", " ", result)

    # Normalize line endings
    result = result.replace("\r\n", "\n")

    # Normalize attribute quoting: unquoted -> double-quoted
    result = re.sub(r'=([^"\'\s>]+)(?=[\s>])', r'="\1"', result)

    # Sort attributes alphabetically for consistent comparison
    def sort_attrs(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs_str = match.group(2)
        if not attrs_str:
            return match.group(0)

        # Parse attributes
        attr_pattern = re.compile(r'(\w+)=("[^"]*"|\'[^\']*\'|[^\s>]+)')
        attrs = attr_pattern.findall(attrs_str)
        if not attrs:
            return match.group(0)

        # Sort by attribute name
        attrs.sort(key=lambda x: x[0])
        sorted_attrs = " ".join(f"{k}={v}" for k, v in attrs)
        return f"<{tag} {sorted_attrs}>"

    result = re.sub(r"<(\w+)(\s[^>]+)>", sort_attrs, result)

    return result


def normalize_for_comparison(expected: str, actual: str) -> tuple[str, str]:
    """Normalize both expected and actual HTML for comparison."""
    expected = normalize_html(expected)
    actual = normalize_html(actual)

    # Patitas uses <br /> with space, spec uses <br>
    # Both are valid HTML5
    actual = actual.replace("<br />", "<br>")
    actual = actual.replace("<hr />", "<hr>")

    # Patitas adds id attributes to headings for anchor links (extension)
    # Strip these for spec comparison since CommonMark doesn't require them
    actual = re.sub(r'<(h[1-6])\s+id="[^"]*">', r"<\1>", actual)

    return expected, actual


# Track which sections have known issues - skip entire sections
KNOWN_ISSUES: dict[str, str] = {
    # Add sections with known issues here
}

# Track specific examples that are expected to fail
XFAIL_EXAMPLES: dict[int, str] = {
    # Add specific example numbers with known issues here
}


def pytest_generate_tests(metafunc: Any) -> None:
    """Generate test parameters from spec examples."""
    if "example" in metafunc.fixturenames:
        if not SPEC_TESTS:
            metafunc.parametrize("example", [{}], ids=["no_spec_found"])
            return
        ids = [
            f"example_{ex['example']:03d}_{ex['section'].replace(' ', '_')}" for ex in SPEC_TESTS
        ]
        metafunc.parametrize("example", SPEC_TESTS, ids=ids)


@pytest.mark.commonmark
class TestCommonMarkSpec:
    """Official CommonMark 0.31.2 specification tests."""

    def test_commonmark_example(self, example: dict[str, Any]) -> None:
        """Test a single CommonMark spec example.

        Args:
            example: Dict with 'markdown', 'html', 'example', 'section' keys
        """
        if not example:
            pytest.skip("CommonMark spec fixture not found")

        # Import here to avoid import errors if parser not fully implemented
        try:
            from patitas.nodes import Document, SourceLocation
            from patitas.parser import Parser
            from patitas.renderers.html import HtmlRenderer
        except ImportError as e:
            pytest.skip(f"Parser not fully implemented: {e}")

        markdown = example["markdown"]
        expected_html = example["html"]
        example_num = example["example"]
        section = example["section"]

        # Check for known issues at section level
        if section in KNOWN_ISSUES:
            pytest.skip(f"Section '{section}': {KNOWN_ISSUES[section]}")

        # Check for specific xfail examples
        if example_num in XFAIL_EXAMPLES:
            pytest.xfail(XFAIL_EXAMPLES[example_num])

        # Parse and render
        try:
            parser = Parser(markdown)
            blocks = parser.parse()
            # Wrap blocks in a Document node (as Markdown.parse() does)
            loc = SourceLocation(
                lineno=1,
                col_offset=1,
                offset=0,
                end_offset=len(markdown),
                source_file=None,
            )
            doc = Document(location=loc, children=tuple(blocks))
            renderer = HtmlRenderer(source=markdown)
            actual_html = renderer.render(doc)
        except Exception as e:
            pytest.fail(f"Parser/renderer error: {e}")

        expected_norm, actual_norm = normalize_for_comparison(expected_html, actual_html)

        assert actual_norm == expected_norm, (
            f"\n\nExample {example_num} ({section}) failed:\n"
            f"\n--- Markdown ---\n{markdown!r}\n"
            f"\n--- Expected ---\n{expected_html!r}\n"
            f"\n--- Actual ---\n{actual_html!r}\n"
            f"\n--- Expected (normalized) ---\n{expected_norm!r}\n"
            f"\n--- Actual (normalized) ---\n{actual_norm!r}\n"
        )


@pytest.mark.commonmark
class TestSpecSections:
    """Tests organized by CommonMark spec sections."""

    @pytest.fixture
    def section_examples(self) -> dict[str, list[dict[str, Any]]]:
        """Group examples by section."""
        sections: dict[str, list[dict[str, Any]]] = {}
        for ex in SPEC_TESTS:
            section = ex["section"]
            if section not in sections:
                sections[section] = []
            sections[section].append(ex)
        return sections

    def test_section_count(self, section_examples: dict[str, list[dict[str, Any]]]) -> None:
        """Verify we have all expected sections."""
        if not SPEC_TESTS:
            pytest.skip("CommonMark spec fixture not found")

        # Core sections from the spec
        core_sections = {
            "Tabs",
            "Thematic breaks",
            "ATX headings",
            "Setext headings",
            "Indented code blocks",
            "Fenced code blocks",
            "HTML blocks",
            "Link reference definitions",
            "Paragraphs",
            "Blank lines",
            "Block quotes",
            "List items",
            "Lists",
            "Backslash escapes",
            "Entity and numeric character references",
            "Code spans",
            "Emphasis and strong emphasis",
            "Links",
            "Images",
            "Autolinks",
            "Raw HTML",
            "Hard line breaks",
            "Soft line breaks",
            "Textual content",
        }
        actual_sections = set(section_examples.keys())
        missing = core_sections - actual_sections
        assert not missing, f"Missing sections: {missing}"


@pytest.mark.commonmark
class TestBaseline:
    """Tests to establish and track baseline pass rate."""

    def test_total_examples(self) -> None:
        """Verify we have all 652 spec examples."""
        if not SPEC_TESTS:
            pytest.skip("CommonMark spec fixture not found")
        assert len(SPEC_TESTS) == 652, f"Expected 652 examples, got {len(SPEC_TESTS)}"

    def test_example_structure(self) -> None:
        """Verify example structure is correct."""
        if not SPEC_TESTS:
            pytest.skip("CommonMark spec fixture not found")
        for ex in SPEC_TESTS:
            assert "markdown" in ex
            assert "html" in ex
            assert "example" in ex
            assert "section" in ex
