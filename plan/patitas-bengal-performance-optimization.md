# Patitas/Bengal Performance Optimization Plan

**Status**: In progress  
**Context**: Benchmark analysis showed sub-linear scaling (50× size → 400× time) and identified preserves_raw_content rfind as a potential bottleneck for large documents with list-table directives.

## Completed

### 1. Line index for preserves_raw_content (Patitas)

**Problem**: `rfind("\n", 0, offset)` is O(offset) per directive. For a 500KB doc with 20 list-table directives, this could scan millions of characters.

**Solution**: Lazy line index built once, O(log n) lookup via bisect.

- **token_nav.py**: Added `_line_start_for_offset()` using bisect on lazy-built `_line_starts` list
- **directive.py**: Replaced two `rfind` calls with `_line_start_for_offset()`
- **parser.py**: Added `_line_starts` slot, init to None, reset in `_reinit`

**Impact**: O(offset) → O(log lines) per lookup. For 500KB doc (~20K lines), each lookup drops from ~500K comparisons to ~14.

### 2. Fix str.split bottleneck in list indent (Patitas)

**Problem**: `_calculate_actual_content_indent` in list/mixin.py and `calculate_content_indent` in indent.py used:
- `source[line_start_pos:].split("\n")[0]` — O(rest of doc) per list item; 40K items × 500KB = massive
- `marker_stripped.split()[0] if marker_stripped.split() else marker_stripped` — double split

**Solution**:
- Replace split with `find("\n", line_start_pos)` + slice: O(line length) per item
- Use `_line_start_for_offset` in mixin (reuse line index)
- Cache `marker_stripped.split()` in a variable

**Impact**: 500KB parse ~31s → ~6s (~5× faster). str.split no longer in top 40 profile entries.

### 3. Phase breakdown and list-table scaling benchmarks

- **benchmark_phase_breakdown.py**: Parse-only vs render-only vs full pipeline (10KB, 500KB)
- **benchmark_scaling.py**: Added `parse-scaling-list-table` for preserves_raw_content path at 50KB

## Remaining Work

### 4. Bengal: Use parse_many for batch rendering

Bengal's rendering iterates pages and parses each with `_md(content)`. The Patitas backend has `parse_many()` for parallel parsing. Evaluate whether the render orchestrator can batch-parse modified pages and pass pre-parsed AST to render.

### 5. Bengal: AST caching for unchanged content

`experiment_bengal_optimizations.py` showed parse cache (content_hash → AST) helps incremental builds. Bengal's BuildCache could store AST for unchanged pages; on incremental build, skip parse for cache hits.

### 6. Inline parse memoization (experimental)

`experiment_bengal_optimizations.py` showed inline memoization (cache `_parse_inline` by text across batch) can reduce redundant work. Requires careful integration with ContextVar config.

### 7. CI regression thresholds

Add pytest-benchmark `--benchmark-compare` or custom threshold checks so CI fails if key benchmarks regress by >1.5×.

## References

- `benchmarks/profile_large_doc.py` — cProfile 500KB + list-table profiling
- `benchmarks/benchmark_phase_breakdown.py` — Parse vs render phase timing
- `benchmarks/benchmark_scaling.py` — Document size scaling + list-table
- `benchmarks/benchmark_directives.py` — Directive-heavy and preserves_raw_content
- `benchmarks/experiment_bengal_optimizations.py` — Bengal-focused experiments
