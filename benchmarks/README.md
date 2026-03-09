# Benchmarks

Performance comparison of Patitas against other Python Markdown parsers.

## Quick Comparison

```bash
python benchmarks/benchmark_vs_mistune.py
```

## With pytest-benchmark

```bash
# Install benchmark dependencies
pip install pytest-benchmark mistune markdown-it-py

# Run all benchmarks
pytest benchmarks/benchmark_vs_mistune.py benchmarks/benchmark_incremental.py benchmarks/benchmark_directives.py benchmarks/benchmark_pipelines.py benchmarks/benchmark_scaling.py benchmarks/benchmark_phase_breakdown.py benchmarks/benchmark_excerpt.py -v --benchmark-only --benchmark-group-by=group

# CI: run key benchmarks and check thresholds
pytest benchmarks/benchmark_scaling.py benchmarks/benchmark_phase_breakdown.py benchmarks/benchmark_excerpt.py -v --benchmark-only --benchmark-json=benchmarks/ci_results.json -q && python benchmarks/check_thresholds.py
```

## Benchmark Groups

| Group | What it measures |
|-------|------------------|
| `parse-corpus` | 652 CommonMark examples (parse+render) |
| `parse-large-doc` | ~100KB document with tables |
| `parse-real-world` | Real-world document patterns |
| `parse-plugins` | Plugin-heavy doc (tables, math, footnotes, etc.) |
| `parse-directives` | Directive-heavy doc (admonition, tabs, dropdown) |
| `parse-preserves-raw` | list-table directives (preserves_raw_content path) |
| `parse-scaling` | Parse time vs doc size (10KB, 100KB, 500KB) |
| `phase-breakdown` | Parse-only vs render-only vs full pipeline |
| `parse-scaling-list-table` | Parse time for list-table directives (preserves_raw_content path) |
| `excerpt` | extract_excerpt on code-heavy and CommonMark corpus |
| `parse-only` | Parse to AST only (no render) |
| `render-only` | Render pre-parsed AST to HTML |
| `render-llm` | Render AST to LLM-friendly plain text |
| `parse-frontmatter` | YAML frontmatter parsing |
| `parse-sanitize-render-llm` | Full RAG pipeline (parse → sanitize → render_llm) |
| `parse-incremental` | Incremental re-parse vs full parse |

## Methodology

### Corpus

- **CommonMark Spec**: 652 examples from CommonMark 0.31.2
- **Large Document**: ~100KB generated markdown with varied syntax
- **Real-world**: Collection of common markdown patterns
- **Plugin-heavy**: Document with tables, math, footnotes, strikethrough, task lists
- **Directive-heavy**: Many admonition, tab-set, dropdown directives (~4KB)
- **Preserves-raw**: list-table directives (preserves_raw_content path)
- **Frontmatter**: Documents with YAML frontmatter
- **Scaling**: 10KB, 100KB, 500KB documents for O(n) validation

### Parsers Compared

| Parser | Notes |
|--------|-------|
| Patitas | This library — typed AST, ReDoS-proof |
| mistune | Fast, popular |
| markdown-it-py | CommonMark compliant, crashes under free-threading |

## Results

Run benchmarks to generate current results:

```bash
python benchmarks/benchmark_vs_mistune.py
```

Typical output (results vary by environment):

```
RESULTS: Parse 652 CommonMark examples
============================================================
mistune                 ~12ms  (1.0x)
Patitas                 ~26ms  (2.1x)
markdown-it-py          ~26ms  (2.1x)
```

**Incremental parsing** — for a 1-char edit in a ~100KB doc: `parse_incremental` ~160µs vs full `parse` ~32ms (~200x faster).

## Why Patitas Prioritizes Safety

1. **Hand-written lexer**: O(n) guaranteed — no regex backtracking
2. **Zero-copy code blocks**: AST stores offsets, not content copies
3. **StringBuilder pattern**: O(n) string building vs concatenation
4. **Immutable AST**: No defensive copying, safe to share
5. **Incremental re-parse**: O(change) for editor workflows

## Reproducibility

All benchmarks run on:
- Python 3.14+
- 10 iterations minimum, median reported
- Warmup runs excluded

To reproduce:
```bash
git clone https://github.com/lbliii/patitas
cd patitas
uv sync --group dev
pip install mistune markdown-it-py
python benchmarks/benchmark_vs_mistune.py
```
