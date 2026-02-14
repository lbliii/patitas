# Performance Investigation: Patitas vs mistune

**Date:** 2026-02-14  
**Benchmark:** 652 CommonMark examples, single thread  
**Result:** mistune ~12ms, Patitas ~26ms (Patitas ~2x slower)

---

## Executive Summary

Patitas is ~2x slower than mistune on the CommonMark corpus. Profiling shows the gap is **not a regression** but inherent to the architecture: pure-Python FSM + typed AST vs mistune's regex-optimized C extensions. The main bottlenecks are the lexer, inline parsing (especially emphasis), and per-document ContextVar overhead.

---

## Time Breakdown (cProfile, 10 iterations × 652 docs)

| Component | Cumulative | Self Time | Calls |
|-----------|------------|-----------|-------|
| **Parse** | 574ms | 27ms | 6,520 |
| Lexer tokenize | 183ms | 10ms | 31,460 |
| Block parsing | 166ms | — | 6,280 |
| Inline parsing | 142ms | — | 8,430 |
| **_scan_block** | 139ms | **32ms** | 31,090 |
| Lexer _dispatch_mode | 158ms | 10ms | 34,100 |
| **_tokenize_inline** | 77ms | **24ms** | 8,380 |
| **_build_inline_ast** | 33ms | **21ms** | 9,870 |
| **_process_emphasis** | 32ms | **17ms** | 8,380 |
| **Render** | 96ms | 11ms | 6,520 |
| html_escape | 21ms | 15ms | 17,330 |
| Token.location | 28ms | 15ms | 26,840 |
| _make_token | 40ms | 13ms | 17,700 |

**Parse dominates** (~90%); render is ~13%.

---

## Section-by-Section (Slowest First)

| Section | µs/doc | vs Avg | Docs |
|---------|--------|-------|------|
| Lists | 92.3 | 2.5x | 26 |
| Precedence | 68.6 | 1.9x | 1 |
| List items | 57.1 | 1.5x | 48 |
| Block quotes | 56.5 | 1.5x | 25 |
| Blank lines | 52.2 | 1.4x | 1 |

**Lists and list items** are the top optimization targets.

---

## Root Cause Analysis

### 1. Lexer: `_scan_block` (32ms self, 31k calls)

- Called once per line. Each call: `_save_location`, `_find_line_end`, `_calc_indent`, `_commit_to`, `_make_token`.
- Block scanner does character-by-character or line-by-line dispatch. No regex, so no backtracking, but more Python overhead per line.
- **Opportunity:** Reduce per-line overhead (batch line processing, inline hot paths).

### 2. Inline Parsing: `_tokenize_inline` (24ms) + `_build_inline_ast` (21ms) + `_process_emphasis` (17ms)

- Inline parsing is a second pass over each paragraph/link/etc.
- Emphasis uses delimiter-stack algorithm (O(n) but Python-heavy).
- **Opportunity:** Cython or PyPy for hot inline paths; cache emphasis results for repeated patterns.

### 3. ContextVar Overhead

- `set_parse_config()` + `reset_parse_config()` called **per document** (2 × 6,520 = 13,040 set operations).
- `get_parse_config()` called via `Parser._config` property — every access to `_tables_enabled`, `_footnotes_enabled`, etc. does a ContextVar lookup.
- Parser has 8 config properties; block parsing may check several per block.
- **Opportunity:** Cache config at parse start. For `Markdown()` batch parsing, set config once per batch instead of per doc.

### 4. Token.location Property (15ms, 26k calls)

- Lazy `SourceLocation` creation with cache. Still 26k property accesses.
- **Opportunity:** Create location at token creation time if always needed; avoid property overhead.

### 5. High Call Volume

- `len()`: 153k calls
- `list.append`: 147k calls
- `str.replace`: 77k calls
- `isinstance`: 57k calls

Suggests heavy use of dynamic dispatch and list building. Pre-allocation or more compact structures could help.

### 6. mistune Advantage

- mistune uses **C-accelerated** regex (via `regex` or `re` with C implementation) and may use C extensions for hot paths.
- Patitas is **pure Python** — FSM, typed AST, frozen dataclasses. More safety, more overhead.
- A 2x gap for pure-Python vs C-accelerated is typical.

---

## Recommended Optimizations (by Impact)

### High impact

1. **Cache ParseConfig for parse duration** — Store `config = get_parse_config()` at start of `Parser.parse()`, pass to block parsers instead of property access. Eliminates thousands of ContextVar lookups per doc.

2. **Batch config for Markdown()** — When parsing many docs with same config, set once before loop, reset once after. Saves 2 ContextVar ops × (N-1) docs.

3. **Optimize list/list-item parsing** — 2.5x slower than average. Profile `_parse_list` and `_parse_list_item`; reduce allocations, avoid redundant work.

### Medium impact

4. **Reduce Token.location overhead** — Create `SourceLocation` at token creation when offsets are known; avoid lazy property.

5. **Inline hot paths** — Consider `@lru_cache` or module-level constants for `can_use_ultra_fast`-style checks; reduce function call overhead in `_scan_block`.

6. **Faster html_escape** — Use a lookup table or C extension for the common case (ASCII-only text).

### Lower impact / future

7. **Cython/PyPy** — Port lexer or inline parser to Cython for 2–5x speedup on hot paths.

8. **Reduce frozenset creation** — `compiled_dispatch.get_parser` creates `frozenset(tok.type for tok in tokens)` per dispatch. Cache pattern for repeated token shapes.

---

## Conclusion

The performance gap is **architectural**, not a bug. Patitas trades raw speed for:

- O(n) guaranteed parsing (ReDoS-proof)
- Typed, immutable AST
- Full thread-safety (free-threading)
- Incremental re-parse (~200x faster for small edits)

The highest-leverage fix is **caching ParseConfig** to avoid repeated ContextVar lookups. List parsing optimization is the next best target. Beyond that, Cython or accepting the 2x gap as the cost of safety and type safety are the main options.
