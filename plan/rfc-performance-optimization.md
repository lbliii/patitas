# RFC: Patitas Performance Optimization

**Status**: Draft  
**Created**: 2026-01-12  
**Updated**: 2026-01-12  
**Author**: Performance Analysis  

---

## Executive Summary

Profiling reveals Patitas is ~60% slower than mistune on the CommonMark corpus. This RFC proposes targeted optimizations to close the gap while preserving Patitas's core value: typed AST, O(n) guarantees, and thread safety.

**Current State (Python 3.14t, 652 CommonMark examples):**

| Parser | Single Thread | vs. mistune |
|--------|---------------|-------------|
| mistune | 11ms | baseline |
| Patitas | 17ms | +60% slower |
| markdown-it-py | 20ms | +80% slower |

**Target**: Reduce gap to <30% slower while maintaining all safety guarantees.

**Key Insight**: The parser phase (56% of time) is the main bottleneck, not the lexer or renderer. Optimizations should focus on inline parsing, emphasis matching, and AST construction.

---

## 1. Profiling Data

### 1.1 Time Breakdown

```
Patitas Pipeline (17ms total):
├── Lexer:      4.4ms (26%)
├── Parser:     9.6ms (56%)  ← Main bottleneck
└── Renderer:   2.0ms (12%)  ← Already fast
```

### 1.2 Function Call Analysis

| Metric | Patitas | mistune | Delta |
|--------|---------|---------|-------|
| Total calls | 782K | 629K | +24% |
| `len()` calls | 114K | — | Hot path |
| `isinstance()` | ~50K | — | Type checking |

### 1.3 Slowest CommonMark Sections

| Section | µs/doc | vs. Average | Root Cause |
|---------|--------|-------------|------------|
| Lists | 54 | 2.5x | Complex nesting rules |
| Block quotes | 40 | 1.9x | Lazy continuation |
| List items | 40 | 1.9x | Tight/loose detection |
| Link ref defs | 29 | 1.4x | Multi-line parsing |
| Average | 21 | 1.0x | — |

### 1.4 Top Functions by Self-Time

```
_scan_block()         17ms (8.8%)  - Block lexer scanning
_tokenize_inline()    10ms (5.2%)  - Inline tokenization
_build_inline_ast()    9ms (4.6%)  - AST construction ← Underestimated bottleneck
_parse_paragraph()     8ms (4.1%)  - Paragraph handling
len()                  7ms (3.6%)  - Length checks (114K calls!)
_process_emphasis()    7ms (3.6%)  - Emphasis matching
```

### 1.5 Code Audit Findings

**Already Optimized:**
- `Lexer.__init__` caches `self._source_len = len(source)` ✅
- `_tokenize_inline()` caches `text_len = len(text)` and `tokens_append = tokens.append` ✅

**Not Yet Optimized:**
- `_peek()` and `_advance()` use `len(self._source)` instead of `self._source_len` (`lexer/core.py:289, 301`).
- `_calc_indent()` caches length locally but could use early exit.
- `SourceLocation.unknown()` creates new object on every call (`location.py:89`).
- `_process_emphasis()` uses O(n²) backward search (`parsing/inline/emphasis.py:130`).
- Numerous `len()` calls in hot loops within `parsing/blocks/core.py` (lines 228, 285) and `parsing/inline/links.py` (lines 111, 136, 212).

---

## 2. Proposed Optimizations

### Phase 1: Low-Hanging Fruit (Est. 10-15% improvement)

#### 2.1 Fix `_peek()` and `_advance()` to Use Cached Length

**Problem**: These methods call `len(self._source)` despite `_source_len` being cached.

**Current Code** (`lexer/core.py:289-301`):
```python
def _peek(self) -> str:
    if self._pos >= len(self._source):  # ← Should use self._source_len
        return ""
    return self._source[self._pos]

def _advance(self) -> str:
    if self._pos >= len(self._source):  # ← Should use self._source_len
        return ""
    ...
```

**Solution**:
```python
def _peek(self) -> str:
    if self._pos >= self._source_len:
        return ""
    return self._source[self._pos]

def _advance(self) -> str:
    if self._pos >= self._source_len:
        return ""
    ...
```

**Files**: `lexer/core.py`  
**Effort**: Trivial  
**Impact**: ~1-2%

#### 2.2 Cache `len()` in Remaining Hot Loops

**Problem**: Some loops still call `len()` repeatedly.

**Files to audit**: `lexer/scanners/block.py`, `parsing/blocks/list/*.py`  
**Effort**: Low  
**Impact**: ~1-2%

#### 2.3 Singleton `SourceLocation.unknown()`

**Problem**: `SourceLocation.unknown()` creates new object each call.

**Current Code** (`location.py:83-89`):
```python
@classmethod
def unknown(cls) -> SourceLocation:
    return cls(lineno=0, col_offset=0)  # New allocation every call
```

**Solution**: Module-level singleton (thread-safe since SourceLocation is frozen):
```python
# Module-level singleton (created once at import)
_UNKNOWN_LOCATION: SourceLocation | None = None

@classmethod
def unknown(cls) -> SourceLocation:
    global _UNKNOWN_LOCATION
    if _UNKNOWN_LOCATION is None:
        _UNKNOWN_LOCATION = cls(lineno=0, col_offset=0)
    return _UNKNOWN_LOCATION
```

**Thread Safety**: SourceLocation is `frozen=True`, so sharing the singleton is safe. The lazy initialization has a benign race condition (worst case: two identical objects created, one discarded).

**Effort**: Trivial  
**Impact**: ~1% (depends on usage frequency)

#### 2.4 Local Variable Caching in Tight Loops

**Problem**: Attribute lookups in loops (`self._pos`, `self._source`).

**Solution**: Cache as local variables at function entry.

```python
# Before
def _scan_block(self):
    line_start = self._pos
    line_end = self._find_line_end()
    line = self._source[line_start:line_end]

# After
def _scan_block(self):
    pos = self._pos  # Local cache
    source = self._source
    source_len = self._source_len
    line_start = pos
    line_end = self._find_line_end()
    line = source[line_start:line_end]
```

**Files**: `lexer/core.py`, `lexer/scanners/block.py`  
**Effort**: Low  
**Impact**: ~2-3%

#### 2.5 Replace `isinstance()` with Type Tags

**Problem**: ~50K `isinstance()` calls for type dispatch.

**Current Code** (`parsing/inline/emphasis.py:134`):
```python
if not isinstance(opener, DelimiterToken):
    opener_idx -= 1
    continue
```

**Solution**: Add integer type tag to InlineToken for O(1) dispatch:
```python
# In tokens.py
TOKEN_TEXT = 0
TOKEN_DELIMITER = 1
TOKEN_CODE_SPAN = 2
# ...

class InlineToken(NamedTuple):
    tag: int  # Type discriminator
    # ... other fields

# Usage
if token.tag != TOKEN_DELIMITER:
    continue
```

**Tradeoff**: Slightly less Pythonic, but integer comparison is ~3x faster than `isinstance()`.  
**Effort**: Medium (touches multiple files)  
**Impact**: ~2-3%

---

### Phase 2: Structural Optimizations (Est. 15-25% improvement)

#### 2.6 Lazy SourceLocation Construction

**Problem**: Every Token creates a SourceLocation (7 fields) even if never accessed.

**Design Constraint**: Token is `frozen=True` for thread safety. `@cached_property` is incompatible with frozen dataclasses.

**Solution**: Store offsets directly; use `object.__setattr__` for lazy caching:

```python
@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    _start_offset: int
    _end_offset: int
    _lineno: int
    _col: int
    line_indent: int = -1
    _source_file: str | None = None
    _location_cache: SourceLocation | None = field(default=None, repr=False, compare=False)
    
    @property
    def location(self) -> SourceLocation:
        if self._location_cache is not None:
            return self._location_cache
        loc = SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            offset=self._start_offset,
            end_offset=self._end_offset,
            source_file=self._source_file,
        )
        # Safe mutation of frozen dataclass cache field
        object.__setattr__(self, '_location_cache', loc)
        return loc
```

**Thread Safety**: The cache write is idempotent (same value computed each time), so concurrent writes are safe.

**Alternative**: If the `object.__setattr__` pattern is unacceptable, provide a non-lazy `TokenWithLocation` variant for debugging/LSP use cases.

**Effort**: Medium  
**Impact**: ~5-8%

#### 2.7 List Parsing Fast Path

**Problem**: Lists are 2.5x slower than average. The current implementation in `parsing/blocks/list/mixin.py` involves complex indentation tracking, container stacks, and normalization of misclassified indented code.

**Solution**: Detect and fast-path simple, non-nested lists.

**Simple List Criteria** (all must be true):
1. All items use the same marker type (all `-`, all `*`, or all `1.`).
2. All items start at column 0 (no nested list).
3. No blank lines between items (tight list).
4. Each item is a single line (no continuation or sub-blocks).
5. No items start with `>` (would be block quote).

**Detection & Strategy**:
- Perform a "dry run" scan of the `LIST_ITEM_MARKER` tokens to ensure they meet the criteria.
- If they do, skip the `ContainerStack` overhead and directly yield `ListItem` nodes with single `Paragraph` children.
- This bypasses the expensive normalization logic in `mixin.py:198-217`.

**Effort**: Medium  
**Impact**: ~5-8% (lists are 8% of corpus time)

#### 2.8 Emphasis Algorithm Optimization

**Problem**: `_process_emphasis()` uses O(n²) backward search for openers.

**Current Code** (`parsing/inline/emphasis.py:127-130`):
```python
# Look backwards for matching opener
opener_idx = closer_idx - 1
while opener_idx >= 0:
    opener = tokens[opener_idx]
    ...
```

**Solution**: Pre-index openers by delimiter character for O(1) lookup:

```python
def _process_emphasis(self, tokens: list[InlineToken], registry: MatchRegistry | None = None) -> MatchRegistry:
    if registry is None:
        registry = MatchRegistry()
    
    # Pre-index openers by delimiter type (O(n) setup)
    openers_by_char: dict[str, list[int]] = {'*': [], '_': [], '~': []}
    
    for i, tok in enumerate(tokens):
        if isinstance(tok, DelimiterToken) and tok.can_open:
            openers_by_char.get(tok.char, []).append(i)
    
    # Process closers
    for closer_idx, closer in enumerate(tokens):
        if not isinstance(closer, DelimiterToken) or not closer.can_close:
            continue
        if not registry.is_active(closer_idx):
            continue
        
        # Search only relevant openers (O(k) where k = openers of same type)
        candidates = openers_by_char.get(closer.char, [])
        
        # Binary search or reverse iteration for closest opener before closer
        for opener_idx in reversed(candidates):
            if opener_idx >= closer_idx:
                continue
            if not registry.is_active(opener_idx):
                continue
            
            opener = tokens[opener_idx]
            # ... rest of matching logic
```

**Complexity**: Reduces worst-case from O(n²) to O(n·k) where k = average openers per delimiter type.

**Effort**: Medium  
**Impact**: ~2-5% (emphasis is 3.6% of time, but pathological cases improve dramatically)

---

### Phase 3: Higher-Effort Optimizations (Est. 10-20% improvement)

#### 2.9 Block Quote Fast Path

**Problem**: Block quotes are 1.9x slower than average.

**Simple Block Quote Criteria**:
1. No nested block quotes (`>>`)
2. No lazy continuation (every line starts with `>`)
3. Content is simple paragraphs (no lists, code blocks, etc.)

**Implementation**: Similar pattern to list fast path.

**Effort**: Medium  
**Impact**: ~3-5%

#### 2.10 Inline Token Stream & AST Optimization

**Problem**: `_tokenize_inline()` creates many small NamedTuple objects, and `_build_inline_ast()` is a recursive bottleneck due to its heavy `match` statement and slicing operations (`parsing/inline/core.py:555`).

**Solution**: 
1. **Token Stream**: Use parallel arrays (types, starts, ends, flags) instead of object lists to reduce allocation and improve cache locality.
2. **AST Iteration**: Convert the recursive `_build_inline_ast` to an iterative stack-based approach where possible, or optimize the slicing by using `memoryview` or passing start/end indices instead of creating new list slices.

```python
# Instead of:
children = self._build_inline_ast(tokens[idx + 1 : closer_local_idx], ...)
# Use indices to avoid slicing:
children = self._build_inline_ast(tokens, registry, location, start=idx+1, end=closer_local_idx)
```

**Tradeoff**: Less ergonomic API, requires updating `_build_inline_ast()`.  
**Effort**: High  
**Impact**: ~10-15%

**Recommendation**: Profile `_build_inline_ast()` first. The recursive pattern matching may be the actual bottleneck, not token allocation.

#### 2.11 Token Pooling / Reuse

**Problem**: ~16K Token objects allocated per corpus parse.

**Original Solution**: Pool and reuse Token objects.

**⚠️ Thread Safety Concern**: Tokens are `frozen=True` to ensure thread safety. Pooling requires mutable objects during acquisition, which:
1. Breaks the frozen guarantee during pool operations
2. Requires careful synchronization in free-threaded Python
3. Could leak mutable tokens if exceptions occur

**Revised Recommendation**: **Defer to P3 or remove**. The complexity and thread-safety risk outweigh the ~5-10% improvement. Lazy SourceLocation (2.6) addresses the same allocation overhead more safely.

**Alternative**: If pooling is still desired, use a thread-local pool to avoid synchronization:
```python
import threading

_token_pool = threading.local()

def get_pool() -> TokenPool:
    if not hasattr(_token_pool, 'pool'):
        _token_pool.pool = TokenPool()
    return _token_pool.pool
```

**Effort**: High  
**Impact**: ~5-10%  
**Priority**: P3 (consider removing)

---

### Phase 4: Architecture Changes (Deferred to v2.0)

#### 2.12 Single-Pass Lexer-Parser

**Recommendation**: Do NOT implement. Violates Patitas's design goals.

#### 2.13 Optional Source Locations

**Problem**: Source locations add overhead even when not needed.

**Solution**: Make source location tracking optional.

```python
md = Markdown(track_locations=False)  # Fast mode
md = Markdown(track_locations=True)   # Full mode (default)
```

**Tradeoff**: Two code paths to maintain.  
**Effort**: High  
**Impact**: ~10-15%  
**Recommendation**: Defer to v2.0

---

## 3. Implementation Plan

### 3.1 Priority Matrix

| Optimization | Effort | Impact | Priority | Risk |
|--------------|--------|--------|----------|------|
| 2.1 Fix `_peek()`/`_advance()` | Trivial | 1-2% | **P0** | None |
| 2.2 Audit remaining `len()` calls | Low | 1-2% | **P0** | None |
| 2.3 Singleton `unknown()` | Trivial | 1% | **P0** | None |
| 2.4 Local var caching | Low | 2-3% | **P0** | None |
| 2.5 Type tags for `isinstance()` | Medium | 2-3% | **P1** | Low |
| 2.6 Lazy SourceLocation | Medium | 5-8% | **P1** | Low |
| 2.7 List fast path | Medium | 5-8% | **P1** | Medium |
| 2.8 Emphasis pre-indexing | Medium | 2-5% | **P1** | Low |
| 2.9 Block quote fast path | Medium | 3-5% | **P2** | Medium |
| 2.10 Inline token stream | High | 10-15% | **P2** | Medium |
| 2.11 Token pooling | High | 5-10% | **P3** | High |
| 2.13 Optional locations | High | 10-15% | **v2.0** | Medium |

### 3.2 Milestones

**Milestone 1 (P0)**: +5-8% improvement
- Fix `_peek()` and `_advance()` to use `_source_len`
- Audit and fix remaining `len()` calls
- Implement `SourceLocation.unknown()` singleton
- Add local variable caching in hot paths
- **Timeline**: 1-2 days
- **Deliverable**: PR with benchmarks before/after

**Milestone 2 (P1)**: +12-20% improvement (cumulative)
- Add type tags for inline tokens
- Implement lazy SourceLocation
- Add list parsing fast path
- Optimize emphasis algorithm with pre-indexing
- **Timeline**: 1 week
- **Deliverable**: PR per optimization with benchmarks

**Milestone 3 (P2)**: +20-30% improvement (cumulative)
- Add block quote fast path
- Implement inline token stream (profile first!)
- **Timeline**: 2-3 weeks
- **Deliverable**: PR with memory profiling

**Cumulative Target**: 25-40% improvement → Patitas within 20-35% of mistune

---

## 4. Benchmarking Requirements

### 4.1 Required Benchmark Scripts

The following scripts must exist before optimization work begins:

| Script | Purpose | Status |
|--------|---------|--------|
| `benchmark_vs_mistune.py` | Full corpus comparison | ✅ Exists |
| `benchmark_by_section.py` | Per-section timing | ❌ TODO |
| `profile_parse.py` | cProfile wrapper | ❌ TODO |
| `memory_bench.py` | Memory profiling | ❌ TODO |
| `line_profile.py` | Line-level profiling | ❌ TODO |
| `report_results.py` | Write JSON/Markdown summary for docs | ❌ TODO |

### 4.2 Benchmark Commands

```bash
# Full CommonMark corpus
uv run python benchmarks/benchmark_vs_mistune.py

# Section-specific benchmarks (TODO: create this)
uv run python benchmarks/benchmark_by_section.py

# CPU profiling
uv run python -m cProfile -o profile.prof benchmarks/profile_parse.py
uv run python -m snakeviz profile.prof

# Line profiling (requires line_profiler)
uv run kernprof -l -v benchmarks/line_profile.py

# Memory profiling
uv run python -m memory_profiler benchmarks/memory_bench.py

# Threaded benchmark (Python 3.14t only)
uv run python benchmarks/benchmark_vs_mistune.py --threads=4
```

### 4.3 Regression Testing Protocol

Every optimization PR must:

1. **Pass full test suite**: `uv run pytest tests/`
2. **Pass CommonMark spec**: `uv run pytest tests/test_commonmark_spec.py`
3. **Show measurable improvement**: >1% on target metric
4. **Not regress other metrics**: <2% slowdown on unrelated benchmarks
5. **Include before/after data**: In PR description

### 4.4 Profiling Checklist

Before implementing any P1+ optimization:

- [ ] Run cProfile on full corpus
- [ ] Identify top 10 functions by cumulative time
- [ ] Run line_profiler on suspected bottleneck
- [ ] Document findings in PR

### 4.5 Documentation and Reporting

- [ ] Regenerate benchmark results after each milestone and update `benchmarks/README.md` with current numbers (no stale “Patitas faster” claim).
- [ ] Publish machine specs, Python version, and command invocations with every reported number.
- [ ] Export results to JSON via `report_results.py` so CI can diff and gate on regressions.

---

## 5. Non-Goals

The following are explicitly **not** goals of this optimization effort:

1. **Matching mistune's speed** — Would require sacrificing typed AST or safety
2. **Single-pass architecture** — Violates separation of concerns
3. **Dropping CommonMark compliance** — Core requirement
4. **Making source locations optional** — Deferred to v2.0
5. **Regex-based lexer** — Would reintroduce ReDoS vulnerability
6. **Mutable tokens** — Would break thread safety guarantees

---

## 6. Success Criteria

| Metric | Current | Target | Stretch |
|--------|---------|--------|---------|
| vs. mistune (single) | +60% | +30% | +20% |
| vs. mistune (4 threads) | +60% | +30% | +20% |
| Function calls | 782K | 650K | 600K |
| `len()` calls | 114K | <50K | <30K |
| `isinstance()` calls | ~50K | <20K | 0 (use type tags) |
| CommonMark pass rate | 652/652 | 652/652 | 652/652 |
| Test suite | Pass | Pass | Pass |

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Optimizations break CommonMark | Medium | High | Comprehensive test suite, run spec tests on every PR |
| Micro-optimizations hurt readability | High | Medium | Document thoroughly, prefer clarity over cleverness |
| Diminishing returns | Medium | Low | Stop at "good enough", measure each change |
| Thread safety regression | Low | High | Run threaded benchmarks, avoid mutable shared state |
| Fast paths miss edge cases | Medium | High | Extensive test coverage for fast path criteria |
| Memory regression from caching | Low | Medium | Memory profiling on each optimization |

---

## 8. Open Questions

1. **Is 30% slower acceptable?** For Bengal's use case (static site generation), yes. For hot-path web services, consider the optional fast mode in v2.0.

2. **Should `_build_inline_ast()` be profiled before inline token stream?** Yes. The recursive pattern matching may be the actual bottleneck. Add action item to profile before implementing 2.10.

3. **Benchmark corpus representativeness?** CommonMark spec examples may not reflect real-world document distribution. 
   - **Improvement**: Add a "real world" benchmark using actual documentation files (Bengal docs, Python docs, etc.).
   - **Data Collection**: Use the `example-sites/` directory in the Bengal repo as a source for realistic test data.

4. **Type tags vs. pattern matching?** Python 3.10+ pattern matching is expressive but may have overhead. 
   - **Improvement**: Benchmark the `match` statement in `_build_inline_ast` against a `tag`-based `if/elif` chain. If the tag-based approach is significantly faster, adopt it for both `InlineToken` and the AST builder.

---

## 9. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-12 | Token pooling moved to P3 | Thread safety concerns outweigh benefit |
| 2026-01-12 | Added type tag optimization | Addresses 50K isinstance() calls |
| 2026-01-12 | Specified simple list criteria | Enables safe fast path implementation |
| 2026-01-12 | Lazy SourceLocation design revised | Original incompatible with frozen dataclass |

---

## Appendix A: Raw Profiling Data

```
Python 3.14.0 (free-threading)
652 CommonMark examples, 5 iterations

Patitas parse-only:  15.1ms (88%)
Patitas render:       2.0ms (12%)
Patitas total:       17.1ms

mistune total:       11.0ms

Patitas overhead:     4.1ms (37% slower than mistune total)
```

## Appendix B: Section Timing Details

```
Lists                              54µs/doc  ( 26 docs)
Block quotes                       40µs/doc  ( 25 docs)
List items                         40µs/doc  ( 48 docs)
Link reference definitions         29µs/doc  ( 27 docs)
Setext headings                    27µs/doc  ( 27 docs)
Links                              27µs/doc  ( 90 docs)
Backslash escapes                  26µs/doc  ( 13 docs)
Images                             25µs/doc  ( 22 docs)
ATX headings                       22µs/doc  ( 18 docs)
Emphasis and strong emphasis       21µs/doc  (132 docs)
```

## Appendix C: Code Locations for Optimization

| Optimization | Primary Files |
|--------------|---------------|
| 2.1 Fix `_peek()`/`_advance()` | `src/patitas/lexer/core.py:289-313` |
| 2.3 Singleton `unknown()` | `src/patitas/location.py:83-89` |
| 2.6 Lazy SourceLocation | `src/patitas/tokens.py:113-160` |
| 2.7 List fast path | `src/patitas/parsing/blocks/list/` |
| 2.8 Emphasis optimization | `src/patitas/parsing/inline/emphasis.py:86-199` |
| 2.10 Inline token stream | `src/patitas/parsing/inline/tokens.py`, `core.py` |

## Appendix D: References

- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [CommonMark Spec 0.31.2](https://spec.commonmark.org/0.31.2/)
- [mistune source](https://github.com/lepture/mistune)
- [markdown-it-py source](https://github.com/executablebooks/markdown-it-py)
- [PEP 709 – Inlined comprehensions](https://peps.python.org/pep-0709/) (Python 3.12+)
- [Free-threaded Python](https://docs.python.org/3.14/whatsnew/3.13.html#free-threaded-cpython) (Python 3.13+)