"""Tests for Parser._reinit() method.

The _reinit() method enables parser pooling by allowing reuse of Parser
instances without reallocation.
"""


from patitas.config import ParseConfig, parse_config_context
from patitas.parser import Parser


class TestParserReinit:
    """Test Parser._reinit() for pooling support."""

    def test_reinit_resets_source(self):
        """_reinit should reset source for new parse."""
        parser = Parser("# First")
        ast1 = parser.parse()

        parser._reinit("# Second")
        ast2 = parser.parse()

        # Should get different results
        assert ast1[0].children[0].content == "First"
        assert ast2[0].children[0].content == "Second"

    def test_reinit_clears_link_refs(self):
        """_reinit should clear link reference definitions."""
        source1 = "[link][ref]\n\n[ref]: http://example.com"
        parser = Parser(source1)
        parser.parse()

        # Link refs should be populated
        assert "ref" in parser._link_refs

        # Reinit with new source
        parser._reinit("# No links here")
        parser.parse()

        # Link refs should be cleared
        assert len(parser._link_refs) == 0

    def test_reinit_clears_directive_stack(self):
        """_reinit should clear directive stack."""
        parser = Parser("# Test")
        parser._directive_stack = ["note", "warning"]  # Simulate state

        parser._reinit("# Fresh")

        assert parser._directive_stack == []

    def test_reinit_resets_position(self):
        """_reinit should reset token position."""
        parser = Parser("# Test")
        parser.parse()  # This advances position

        parser._reinit("# New")

        assert parser._pos == 0
        assert parser._current is None

    def test_reinit_updates_source_file(self):
        """_reinit should update source file path."""
        parser = Parser("# Test", "old.md")

        parser._reinit("# New", "new.md")

        assert parser._source_file == "new.md"

    def test_reinit_with_none_source_file(self):
        """_reinit should handle None source file."""
        parser = Parser("# Test", "old.md")

        parser._reinit("# New")

        assert parser._source_file is None

    def test_reinit_allows_repeated_parsing(self):
        """Parser should work correctly after multiple _reinit calls."""
        parser = Parser("# One")

        results = []
        for text in ["# Two", "# Three", "# Four"]:
            parser._reinit(text)
            ast = parser.parse()
            results.append(ast[0].children[0].content)

        assert results == ["Two", "Three", "Four"]

    def test_reinit_with_config_context(self):
        """_reinit should work with ContextVar config."""
        parser = Parser("| A | B |\n|---|---|\n| 1 | 2 |")

        with parse_config_context(ParseConfig(tables_enabled=True)):
            ast1 = parser.parse()

            parser._reinit("| X | Y |\n|---|---|\n| 3 | 4 |")
            ast2 = parser.parse()

        # Both should parse as tables
        assert ast1[0].__class__.__name__ == "Table"
        assert ast2[0].__class__.__name__ == "Table"
