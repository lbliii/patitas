"""Tests for content-addressed parse cache."""

from patitas import (
    DictParseCache,
    Document,
    Markdown,
    ParseConfig,
    hash_config,
    hash_content,
    parse,
)
from patitas.nodes import Heading, Paragraph


class TestDictParseCache:
    """Tests for DictParseCache."""

    def test_get_returns_none_when_empty(self) -> None:
        """Cache returns None when no entry exists."""
        cache = DictParseCache()
        assert cache.get("abc123", "config1") is None

    def test_put_then_get_returns_doc(self) -> None:
        """Put then get returns the stored document."""
        from patitas.location import SourceLocation

        cache = DictParseCache()
        loc = SourceLocation(1, 1, 0, 5, None)
        doc = Document(location=loc, children=())
        cache.put("abc123", "config1", doc)
        assert cache.get("abc123", "config1") is doc

    def test_different_keys_return_none(self) -> None:
        """Different content_hash or config_hash returns None."""
        from patitas.location import SourceLocation

        cache = DictParseCache()
        loc = SourceLocation(1, 1, 0, 5, None)
        doc = Document(location=loc, children=())
        cache.put("abc123", "config1", doc)
        assert cache.get("xyz789", "config1") is None
        assert cache.get("abc123", "config2") is None


class TestHashHelpers:
    """Tests for hash_content and hash_config."""

    def test_hash_content_deterministic(self) -> None:
        """Same content produces same hash."""
        h1 = hash_content("# Hello")
        h2 = hash_content("# Hello")
        assert h1 == h2

    def test_hash_content_different_for_different_input(self) -> None:
        """Different content produces different hash."""
        h1 = hash_content("# Hello")
        h2 = hash_content("# World")
        assert h1 != h2

    def test_hash_config_different_for_different_plugins(self) -> None:
        """Different config produces different hash."""
        config1 = ParseConfig(tables_enabled=False)
        config2 = ParseConfig(tables_enabled=True)
        h1 = hash_config(config1)
        h2 = hash_config(config2)
        assert h1 != h2

    def test_hash_config_empty_when_text_transformer_set(self) -> None:
        """hash_config returns empty string when text_transformer is set."""
        config = ParseConfig(text_transformer=lambda s: s.upper())
        assert hash_config(config) == ""


class TestParseWithCache:
    """Tests for parse() with cache."""

    def test_first_call_parses_second_hits_cache(self) -> None:
        """Second parse of same source hits cache."""
        cache = DictParseCache()
        doc1 = parse("# Hello", cache=cache)
        doc2 = parse("# Hello", cache=cache)
        assert doc1 is doc2
        assert len(doc1.children) == 1
        assert isinstance(doc1.children[0], Heading)

    def test_different_content_parses_both(self) -> None:
        """Different content produces different documents."""
        cache = DictParseCache()
        doc1 = parse("# Hello", cache=cache)
        doc2 = parse("# World", cache=cache)
        assert doc1 is not doc2
        assert doc1.children[0].children[0].content == "Hello"
        assert doc2.children[0].children[0].content == "World"


class TestMarkdownParseWithCache:
    """Tests for Markdown.parse() with cache."""

    def test_cache_hit_on_second_parse(self) -> None:
        """Second parse of same source hits cache."""
        md = Markdown()
        cache = DictParseCache()
        doc1 = md.parse("# Test", cache=cache)
        doc2 = md.parse("# Test", cache=cache)
        assert doc1 is doc2


class TestMarkdownParseManyWithCache:
    """Tests for Markdown.parse_many() with cache."""

    def test_duplicate_sources_hit_cache(self) -> None:
        """Duplicate sources in list hit cache on second occurrence."""
        md = Markdown()
        cache = DictParseCache()
        sources = ["# Doc 1", "# Doc 1", "# Doc 2", "# Doc 1"]
        docs = md.parse_many(sources, cache=cache)
        assert len(docs) == 4
        # First and second "Doc 1" should be same object (cache hit)
        assert docs[0] is docs[1]
        assert docs[0] is docs[3]
        # Doc 2 is different
        assert docs[2] is not docs[0]


class TestConfigHashCacheIsolation:
    """Tests that different configs use different cache entries."""

    def test_different_markdown_instances_different_cache_entries(self) -> None:
        """Different Markdown configs (e.g. tables on/off) use different entries."""
        cache = DictParseCache()
        md_basic = Markdown()
        md_tables = Markdown(plugins=["table"])

        # Full GFM table - with tables plugin: Table; without: Paragraph
        table_md = "| a | b |\n|---|---|\n| 1 | 2 |"

        doc1 = md_basic.parse(table_md, cache=cache)
        doc2 = md_tables.parse(table_md, cache=cache)

        # Different configs -> different cache entries -> different doc objects
        assert doc1 is not doc2
        from patitas.nodes import Table

        assert isinstance(doc2.children[0], Table)
        assert isinstance(doc1.children[0], Paragraph)
