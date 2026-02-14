"""Bengal-focused optimization experiments.

Tests proposed optimizations for Patitas when used in Bengal (SSG):
1. Inline parse memoization - cache _parse_inline across a batch
2. Pre-lexer fast path - skip lexer for plain-text docs
3. Parse cache - cache (content_hash, config) -> AST for unchanged content
4. Token coalescing - merge adjacent PARAGRAPH_LINE tokens
5. Bulk line classification - deferred (requires lexer refactor)

Run:
    PYTHONPATH=src python benchmarks/experiment_bengal_optimizations.py
"""

import hashlib
import json
import sys
import time
from pathlib import Path

# Markdown special chars that trigger parsing (block or inline)
_MD_SPECIAL = frozenset("#*_`[\\>-|~+:")


def get_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    return [ex["markdown"] for ex in json.loads(spec.read_text())]


# ---------------------------------------------------------------------------
# Experiment 1: Inline parse memoization
# ---------------------------------------------------------------------------


def _bench_inline_memoization(docs: list[str], iters: int = 8) -> float:
    """With inline memoization: cache _parse_inline by text across batch."""
    from patitas import Markdown, set_parse_config, reset_parse_config
    from patitas.config import ParseConfig
    from patitas.directives.registry import create_default_registry

    registry = create_default_registry()
    cache: dict[str, tuple] = {}

    # We need to inject the cache. ParseConfig is frozen, so we use a
    # ContextVar for the cache and patch the parser.
    from contextvars import ContextVar

    _inline_cache: ContextVar[dict | None] = ContextVar("experiment_inline_cache", default=None)

    # Subclass Parser to use cache
    from patitas.parser import Parser
    from patitas.location import SourceLocation

    class CachedInlineParser(Parser):
        def _parse_inline(self, text: str, location: SourceLocation) -> tuple:
            c = _inline_cache.get()
            if c is not None:
                if text in c:
                    return c[text]
                result = super()._parse_inline(text, location)
                c[text] = result
                return result
            return super()._parse_inline(text, location)

    # Monkey-patch parse to use our parser
    from patitas import parse
    from patitas.nodes import Document

    def parse_with_cache(source: str, source_file: str | None = None) -> Document:
        config = ParseConfig(directive_registry=registry)
        set_parse_config(config)
        _inline_cache.set(cache)
        try:
            parser = CachedInlineParser(source, source_file=source_file)
            blocks = parser.parse()
            loc = SourceLocation(
                lineno=1,
                col_offset=1,
                offset=0,
                end_offset=len(source),
                source_file=source_file,
            )
            return Document(location=loc, children=tuple(blocks))
        finally:
            reset_parse_config()
            _inline_cache.set(None)

    def parse_all() -> float:
        cache.clear()
        start = time.perf_counter()
        for d in docs:
            parse_with_cache(d)
        return time.perf_counter() - start

    times = [parse_all() for _ in range(iters)]
    avg_ms = sum(times) / len(times) * 1000
    hits = len(cache)
    print(f"  inline_memo: {avg_ms:.2f}ms  cache_entries={hits}")
    return avg_ms


# ---------------------------------------------------------------------------
# Experiment 2: Pre-lexer fast path
# ---------------------------------------------------------------------------


def _is_plain_text(source: str) -> bool:
    """True if source has no markdown special chars (quick scan)."""
    return not any(c in _MD_SPECIAL for c in source)


def _bench_prelexer_fastpath(docs: list[str], iters: int = 8) -> tuple[float, int]:
    """Measure: how many docs qualify for plain-text fast path, and time savings."""
    from patitas import parse
    from patitas.nodes import Document, Paragraph, Text
    from patitas.location import SourceLocation

    plain_count = sum(1 for d in docs if _is_plain_text(d))

    def parse_with_fastpath(source: str) -> Document:
        if _is_plain_text(source):
            loc = SourceLocation(1, 1, 0, len(source), None)
            para = Paragraph(
                location=loc,
                children=(Text(content=source.strip(), location=loc),)
                if source.strip()
                else (),
            )
            return Document(location=loc, children=(para,))
        return parse(source)

    def parse_all() -> float:
        start = time.perf_counter()
        for d in docs:
            parse_with_fastpath(d)
        return time.perf_counter() - start

    times = [parse_all() for _ in range(iters)]
    avg_ms = sum(times) / len(times) * 1000
    print(f"  prelexer_fastpath: {avg_ms:.2f}ms  plain_docs={plain_count}/{len(docs)}")
    return avg_ms, plain_count


# ---------------------------------------------------------------------------
# Experiment 3: Parse cache
# ---------------------------------------------------------------------------


def _bench_parse_cache(docs: list[str], iters: int = 8) -> float:
    """Simulate incremental build: 1st pass populates cache, 2nd pass all hits."""
    from patitas import parse
    from patitas.nodes import Document

    cache: dict[str, Document] = {}

    def content_hash(source: str) -> str:
        return hashlib.sha256(source.encode()).hexdigest()

    def parse_with_cache(source: str) -> Document:
        h = content_hash(source)
        if h in cache:
            return cache[h]
        doc = parse(source)
        cache[h] = doc
        return doc

    # Simulate 2-pass build (like Bengal: discover, then render)
    def two_pass() -> float:
        cache.clear()
        start = time.perf_counter()
        for d in docs:
            parse_with_cache(d)
        for d in docs:
            parse_with_cache(d)
        return time.perf_counter() - start

    times = [two_pass() for _ in range(iters)]
    avg_ms = sum(times) / len(times) * 1000
    print(f"  parse_cache (2-pass): {avg_ms:.2f}ms  unique_docs={len(cache)}")
    return avg_ms


# ---------------------------------------------------------------------------
# Experiment 4: Token coalescing
# ---------------------------------------------------------------------------


def _coalesce_paragraph_lines(tokens: list) -> list:
    """Merge adjacent PARAGRAPH_LINE tokens into one (for ultra_fast path only)."""
    from patitas.tokens import Token, TokenType

    result: list = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type != TokenType.PARAGRAPH_LINE:
            result.append(tok)
            i += 1
            continue
        lines = [tok.value.lstrip()]
        first = tok
        i += 1
        while i < len(tokens) and tokens[i].type == TokenType.PARAGRAPH_LINE:
            lines.append(tokens[i].value.lstrip())
            i += 1
        last = tokens[i - 1]
        merged_value = "\n".join(lines).rstrip()
        merged = Token(
            TokenType.PARAGRAPH_LINE,
            merged_value,
            first._lineno,
            first._col,
            first._start_offset,
            last._end_offset,
            line_indent=first.line_indent,
            _end_lineno=last._end_lineno,
            _end_col=last._end_col,
            _source_file=first._source_file,
        )
        result.append(merged)
    return result


def _bench_token_coalescing(docs: list[str], iters: int = 8) -> float:
    """Parse with coalesced PARAGRAPH_LINE tokens (ultra_fast path only)."""
    from patitas.lexer import Lexer
    from patitas.parser import Parser
    from patitas.config import set_parse_config, reset_parse_config
    from patitas.directives.registry import create_default_registry
    from patitas.parsing.ultra_fast import can_use_ultra_fast, parse_ultra_simple
    from patitas.nodes import Document
    from patitas.location import SourceLocation
    from patitas.config import ParseConfig

    config = ParseConfig(directive_registry=create_default_registry())
    set_parse_config(config)

    def parse_coalesced(source: str) -> Document:
        lexer = Lexer(source)
        tokens = list(lexer.tokenize())
        if can_use_ultra_fast(tokens):
            coalesced = _coalesce_paragraph_lines(tokens)
            parser = Parser(source)
            parser._config_cache = config
            parser._tokens = coalesced
            parser._tokens_len = len(coalesced)
            parser._pos = 0
            parser._current = coalesced[0] if coalesced else None
            blocks = parse_ultra_simple(coalesced, parser._parse_inline)
        else:
            parser = Parser(source)
            blocks = parser.parse()
        loc = SourceLocation(1, 1, 0, len(source), None)
        return Document(location=loc, children=tuple(blocks))

    def parse_all() -> float:
        start = time.perf_counter()
        for d in docs:
            parse_coalesced(d)
        return time.perf_counter() - start

    try:
        times = [parse_all() for _ in range(iters)]
        avg_ms = sum(times) / len(times) * 1000
        print(f"  token_coalescing: {avg_ms:.2f}ms")
        return avg_ms
    finally:
        reset_parse_config()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    docs = get_corpus()
    print(f"Bengal optimization experiments")
    print(f"Corpus: {len(docs)} docs, Python {sys.version.split()[0]}")
    print()

    # Baseline
    print("1. Baseline (no optimizations)")
    from patitas import Markdown

    md = Markdown()

    def baseline() -> float:
        start = time.perf_counter()
        for d in docs:
            md.parse(d)
        return time.perf_counter() - start

    baseline_times = [baseline() for _ in range(8)]
    baseline_ms = sum(baseline_times) / len(baseline_times) * 1000
    print(f"  baseline: {baseline_ms:.2f}ms")
    print()

    # Experiments (each prints details)
    print("2. Inline parse memoization")
    memo_ms = _bench_inline_memoization(docs)
    print()

    print("3. Pre-lexer fast path (plain-text skip)")
    fastpath_ms, plain_count = _bench_prelexer_fastpath(docs)
    print()

    print("4. Parse cache (2-pass incremental)")
    cache_ms = _bench_parse_cache(docs)
    print()

    print("5. Token coalescing")
    coal_ms = _bench_token_coalescing(docs)
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY (vs baseline)")
    print("=" * 60)
    pct_memo = (baseline_ms - memo_ms) / baseline_ms * 100 if baseline_ms else 0
    print(f"  Inline memo:  {memo_ms:.2f}ms  ({pct_memo:+.1f}%)")
    pct_fast = (baseline_ms - fastpath_ms) / baseline_ms * 100 if baseline_ms else 0
    print(f"  Pre-lexer:    {fastpath_ms:.2f}ms  ({pct_fast:+.1f}%)  plain={plain_count}/{len(docs)}")
    two_pass = baseline_ms * 2
    pct_cache = (two_pass - cache_ms) / two_pass * 100 if two_pass else 0
    print(f"  Parse cache:  {cache_ms:.2f}ms (2-pass, {pct_cache:.0f}% vs 2x baseline)")
    pct_coal = (baseline_ms - coal_ms) / baseline_ms * 100 if baseline_ms else 0
    print(f"  Coalescing:   {coal_ms:.2f}ms  ({pct_coal:+.1f}%)")


if __name__ == "__main__":
    main()
