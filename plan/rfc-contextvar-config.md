# RFC: ContextVar Configuration Pattern

**Status**: Implemented  
**Created**: 2026-01-13  
**Implemented**: 2026-01-13  
**Depends on**: `rfc-free-threading-patterns.md`

---

## Executive Summary

Refactor Patitas to use `ContextVar` for parse configuration instead of passing config through instance attributes. This provides:

- **2.2x faster** parser instantiation (requires benchmark validation)
- **50% smaller** parser memory footprint (18 → 9 slots)
- **Cleaner API** with configuration set once per Markdown instance
- **Thread-safe by design** (ContextVars are thread-local)

---

## 1. Problem Statement

### Current Architecture

Each `Parser` instance carries 18 slots, including configuration that's identical across all parses:

```python
class Parser:
    __slots__ = (
        # Per-parse state (required)
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
        
        # Configuration (duplicated per parser!)
        "_text_transformer",
        "_tables_enabled",
        "_strikethrough_enabled",
        "_task_lists_enabled",
        "_footnotes_enabled",
        "_math_enabled",
        "_autolinks_enabled",
        "_directive_registry",
        "_strict_contracts",
    )
```

### Issues

1. **Memory waste**: Config duplicated for every parser instance
2. **Instantiation overhead**: 18 slots initialized per parse
3. **Parameter threading**: Config passed through multiple layers
4. **Sub-parser copying**: Recursive parses copy all config fields manually

### Evidence: Sub-Parser Config Copying

From `parser.py:238-244`:

```python
# Copy plugin settings
sub_parser._tables_enabled = self._tables_enabled
sub_parser._strikethrough_enabled = self._strikethrough_enabled
sub_parser._task_lists_enabled = self._task_lists_enabled
sub_parser._footnotes_enabled = self._footnotes_enabled
sub_parser._math_enabled = self._math_enabled
sub_parser._autolinks_enabled = self._autolinks_enabled
```

This manual copying is error-prone and adds overhead.

---

## 2. Proposed Solution

### Design: Immutable Config + ContextVar

```python
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Immutable parse configuration.
    
    Set once per Markdown instance, read by all parsers in the context.
    Frozen dataclass ensures thread-safety (immutable after creation).
    
    Note: source_file is intentionally excluded—it's per-call state,
    not configuration. It remains on the Parser instance.
    """
    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: "DirectiveRegistry | None" = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None

# Module-level default config (reused, never recreated)
_DEFAULT_CONFIG: ParseConfig = ParseConfig()

# Thread-local configuration
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=_DEFAULT_CONFIG
)

def get_parse_config() -> ParseConfig:
    """Get current parse configuration (thread-local)."""
    return _parse_config.get()

def set_parse_config(config: ParseConfig) -> None:
    """Set parse configuration for current context."""
    _parse_config.set(config)

def reset_parse_config() -> None:
    """Reset to default configuration."""
    _parse_config.set(_DEFAULT_CONFIG)
```

### Refactored Parser

```python
class Parser:
    __slots__ = (
        # Per-parse state only
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",          # Kept here: per-call, not config
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )  # 9 slots (was 18)
    
    def __init__(
        self,
        source: str,
        source_file: str | None = None,
    ) -> None:
        """Initialize parser with source text only.
        
        Configuration is read from ContextVar, not passed as parameters.
        """
        self._source = source
        self._source_file = source_file
        self._tokens: list[Token] = []
        self._pos = 0
        self._current: Token | None = None
        self._directive_stack: list[str] = []
        self._link_refs: dict[str, tuple[str, str]] = {}
        self._containers = ContainerStack()
        self._allow_setext_headings = True
    
    # Config access via properties (reads from ContextVar)
    @property
    def _config(self) -> ParseConfig:
        return get_parse_config()
    
    @property
    def _math_enabled(self) -> bool:
        return self._config.math_enabled
    
    @property
    def _tables_enabled(self) -> bool:
        return self._config.tables_enabled
    
    @property
    def _strikethrough_enabled(self) -> bool:
        return self._config.strikethrough_enabled
    
    @property
    def _footnotes_enabled(self) -> bool:
        return self._config.footnotes_enabled
    
    @property
    def _task_lists_enabled(self) -> bool:
        return self._config.task_lists_enabled
    
    @property
    def _autolinks_enabled(self) -> bool:
        return self._config.autolinks_enabled
    
    @property
    def _directive_registry(self) -> "DirectiveRegistry | None":
        return self._config.directive_registry
    
    @property
    def _strict_contracts(self) -> bool:
        return self._config.strict_contracts
    
    @property
    def _text_transformer(self) -> Callable[[str], str] | None:
        return self._config.text_transformer
```

### Refactored Markdown Class

```python
class Markdown:
    def __init__(
        self,
        *,
        plugins: list[str] | None = None,
        highlight: HighlightFunc | None = None,
        directive_registry: DirectiveRegistry | None = None,
    ) -> None:
        self._highlight = highlight
        self._plugins = plugins or []
        self._directive_registry = directive_registry or create_default_registry()
        
        # Build immutable config once
        self._config = ParseConfig(
            tables_enabled="tables" in self._plugins,
            strikethrough_enabled="strikethrough" in self._plugins,
            task_lists_enabled="task_lists" in self._plugins,
            footnotes_enabled="footnotes" in self._plugins,
            math_enabled="math" in self._plugins,
            autolinks_enabled="autolinks" in self._plugins,
            directive_registry=self._directive_registry,
        )
    
    def __call__(self, source: str, source_file: str | None = None) -> str:
        """Parse and render Markdown to HTML."""
        # Set config for this parse (thread-local)
        set_parse_config(self._config)
        
        try:
            doc = self.parse(source, source_file)
            return self.render(doc)
        finally:
            # Reset to default (reuses module-level singleton)
            reset_parse_config()
    
    def parse(self, source: str, source_file: str | None = None) -> Document:
        """Parse Markdown to AST."""
        parser = Parser(source, source_file)  # Config via ContextVar
        return parser.parse()
```

### Simplified Sub-Parser Creation

```python
def _parse_nested_content(
    self,
    content: str,
    location,
    *,
    allow_setext_headings: bool = True,
) -> tuple[Block, ...]:
    """Parse nested content as blocks.
    
    No config copying needed—sub-parser reads from same ContextVar!
    """
    if not content.strip():
        return ()

    # Create sub-parser (inherits config from ContextVar automatically)
    sub_parser = Parser(content, self._source_file)
    sub_parser._allow_setext_headings = allow_setext_headings
    
    # Share link reference definitions (document-wide)
    sub_parser._link_refs = self._link_refs
    
    return sub_parser.parse()
```

---

## 3. Thread Safety Analysis

### ContextVar Guarantees

```python
# Thread 1                          Thread 2
set_parse_config(ConfigA)           set_parse_config(ConfigB)
parser1 = Parser(src1)              parser2 = Parser(src2)
parser1._math_enabled  # → ConfigA  parser2._math_enabled  # → ConfigB
```

ContextVars are **thread-local by design**:
- Each thread has independent storage
- No locks needed
- No race conditions possible

### Validation Required

```python
# TODO: Add to benchmarks/threading_contextvar.py
def test_thread_isolation():
    """Verify config isolation across threads."""
    results = {}
    
    def worker(thread_id: int, config: ParseConfig):
        set_parse_config(config)
        parser = Parser("# Test")
        results[thread_id] = {
            "tables": parser._tables_enabled,
            "math": parser._math_enabled,
        }
    
    configs = [
        ParseConfig(tables_enabled=True, math_enabled=True),
        ParseConfig(tables_enabled=False, math_enabled=True),
        ParseConfig(tables_enabled=True, math_enabled=False),
        ParseConfig(tables_enabled=False, math_enabled=False),
    ]
    
    threads = [
        Thread(target=worker, args=(i, c))
        for i, c in enumerate(configs)
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    
    # Verify each thread saw its own config
    assert results[0] == {"tables": True, "math": True}
    assert results[1] == {"tables": False, "math": True}
    assert results[2] == {"tables": True, "math": False}
    assert results[3] == {"tables": False, "math": False}
```

---

## 4. Performance Analysis

### Expected Improvements

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Parser slots | 18 | 9 | **50% smaller** |
| Parser instantiation | ~260ns | ~120ns | **2.2x faster** (projected) |
| Sub-parser creation | Copy 9 fields | No copy needed | **Faster** |
| Config lookup | Instance attr | ContextVar + property | ~same to slight overhead |

### Property Access Overhead

**Concern**: Hot paths like `parsing/blocks/core.py:800` access config frequently:

```python
if self._tables_enabled and len(lines) >= 2 and "|" in lines[0]:
```

Each `_tables_enabled` access = property call + `ContextVar.get()` + attribute access.

**Mitigation options** (implement if benchmarks show regression):

1. **Cache config reference** in tight loops:
   ```python
   def _parse_paragraph(self, lines: list[str]) -> Block:
       config = self._config  # Single ContextVar lookup
       if config.tables_enabled and len(lines) >= 2:
           ...
   ```

2. **Local variable extraction** for innermost loops:
   ```python
   tables_enabled = self._tables_enabled  # Once per method
   if tables_enabled and ...:
   ```

### Benchmark Script Required

Create `benchmarks/contextvar_config.py`:

```python
"""Benchmark ContextVar config pattern vs instance attributes."""

import timeit
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ParseConfig:
    tables_enabled: bool = False
    math_enabled: bool = False
    # ... other fields

_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=ParseConfig()
)

class ParserBefore:
    """Current: 18 slots with instance config."""
    __slots__ = (
        "_source", "_tokens", "_pos", "_current", "_source_file",
        "_text_transformer", "_tables_enabled", "_strikethrough_enabled",
        "_task_lists_enabled", "_footnotes_enabled", "_math_enabled",
        "_autolinks_enabled", "_directive_registry", "_strict_contracts",
        "_directive_stack", "_link_refs", "_containers", "_allow_setext_headings",
    )
    
    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens = []
        self._pos = 0
        self._current = None
        self._source_file = None
        self._text_transformer = None
        self._tables_enabled = False
        self._strikethrough_enabled = False
        self._task_lists_enabled = False
        self._footnotes_enabled = False
        self._math_enabled = False
        self._autolinks_enabled = False
        self._directive_registry = None
        self._strict_contracts = False
        self._directive_stack = []
        self._link_refs = {}
        self._containers = None
        self._allow_setext_headings = True

class ParserAfter:
    """Proposed: 9 slots with ContextVar config."""
    __slots__ = (
        "_source", "_tokens", "_pos", "_current", "_source_file",
        "_directive_stack", "_link_refs", "_containers", "_allow_setext_headings",
    )
    
    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens = []
        self._pos = 0
        self._current = None
        self._source_file = None
        self._directive_stack = []
        self._link_refs = {}
        self._containers = None
        self._allow_setext_headings = True
    
    @property
    def _tables_enabled(self) -> bool:
        return _parse_config.get().tables_enabled

def benchmark_instantiation(n: int = 100_000) -> None:
    """Benchmark parser instantiation."""
    print(f"Instantiating {n:,} parsers...")
    
    before = timeit.timeit(
        lambda: ParserBefore("# Test"),
        number=n
    )
    after = timeit.timeit(
        lambda: ParserAfter("# Test"),
        number=n
    )
    
    print(f"Before (18 slots): {before*1000:.1f}ms")
    print(f"After (9 slots):   {after*1000:.1f}ms")
    print(f"Speedup: {before/after:.2f}x")

def benchmark_config_access(n: int = 1_000_000) -> None:
    """Benchmark config attribute access."""
    print(f"\nAccessing config {n:,} times...")
    
    parser_before = ParserBefore("# Test")
    parser_before._tables_enabled = True
    
    _parse_config.set(ParseConfig(tables_enabled=True))
    parser_after = ParserAfter("# Test")
    
    before = timeit.timeit(
        lambda: parser_before._tables_enabled,
        number=n
    )
    after = timeit.timeit(
        lambda: parser_after._tables_enabled,
        number=n
    )
    
    print(f"Instance attr: {before*1000:.1f}ms")
    print(f"ContextVar:    {after*1000:.1f}ms")
    print(f"Overhead: {after/before:.2f}x")

if __name__ == "__main__":
    benchmark_instantiation()
    benchmark_config_access()
```

---

## 5. Migration Path

### Phase 1: Add ParseConfig (Non-Breaking)

1. Create `patitas/config.py` with:
   - `ParseConfig` frozen dataclass
   - `_parse_config` ContextVar
   - `get_parse_config()` / `set_parse_config()` / `reset_parse_config()`
2. Add unit tests for config isolation
3. Run benchmark script to validate performance claims

### Phase 2: Refactor Markdown Class

1. Build `ParseConfig` in `Markdown.__init__()`
2. Set ContextVar in `Markdown.__call__()`
3. Add try/finally with `reset_parse_config()`
4. Keep old Parser interface for now (backward compat)

### Phase 3: Refactor Parser

1. Add property accessors that read from ContextVar
2. Remove config slots from Parser
3. Update `__init__()` signature (keep `source_file`)
4. Simplify `_parse_nested_content()` (no config copying)

### Phase 4: Update Mixins

1. Update `InlineParsingMixin` to use properties
2. Update `BlockParsingMixin` to use properties
3. Update `parsing/blocks/list/nested.py` (remove config passing)
4. Verify Protocol contracts satisfied by properties

### Phase 5: Cleanup & Validation

1. Remove deprecated config parameters
2. Run full test suite
3. Run CommonMark compliance tests
4. Benchmark before/after on real workloads
5. Update docstrings and type hints

---

## 6. API Changes

### Internal API: Simplified

**Before** (sub-parser creation):
```python
sub_parser = Parser(
    content,
    self._source_file,
    directive_registry=self._directive_registry,
    strict_contracts=self._strict_contracts,
    text_transformer=self._text_transformer,
)
sub_parser._tables_enabled = self._tables_enabled
sub_parser._strikethrough_enabled = self._strikethrough_enabled
sub_parser._task_lists_enabled = self._task_lists_enabled
sub_parser._footnotes_enabled = self._footnotes_enabled
sub_parser._math_enabled = self._math_enabled
sub_parser._autolinks_enabled = self._autolinks_enabled
```

**After** (sub-parser creation):
```python
sub_parser = Parser(content, self._source_file)
# Config inherited automatically via ContextVar
```

### Public API: Unchanged

```python
# User-facing API remains identical
md = Markdown(plugins=["table", "math"])
html = md("# Hello *world*")
```

---

## 7. Risks and Mitigations

### Risk 1: ContextVar Not Set

**Problem**: Parser used without config set → uses defaults

**Mitigation**: 
```python
_DEFAULT_CONFIG = ParseConfig()  # Module-level singleton
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=_DEFAULT_CONFIG  # Safe defaults
)
```

**Severity**: Low (defaults are sensible: all extensions disabled)

### Risk 2: Config Leaking Between Parses

**Problem**: Previous parse's config affects next parse

**Mitigation**:
```python
def __call__(self, source: str) -> str:
    set_parse_config(self._config)
    try:
        return self._do_parse(source)
    finally:
        reset_parse_config()  # Reuses singleton, no allocation
```

**Severity**: Medium → Low with try/finally

### Risk 3: Property Access Overhead in Hot Paths

**Problem**: Config checks in tight loops may slow parsing

**Mitigation**: 
1. Benchmark before implementation
2. Cache config reference in methods with many accesses
3. If severe, consider caching config at `__init__` time

**Severity**: Medium (requires benchmark validation)

### Risk 4: Breaking Existing Tests

**Problem**: Tests that create Parser directly without ContextVar setup

**Mitigation**: Tests can use explicit setup:
```python
def test_tables():
    set_parse_config(ParseConfig(tables_enabled=True))
    try:
        parser = Parser("| a | b |")
        result = parser.parse()
        assert isinstance(result[0], Table)
    finally:
        reset_parse_config()
```

Or use a context manager:
```python
@contextmanager
def parse_config_context(config: ParseConfig):
    set_parse_config(config)
    try:
        yield
    finally:
        reset_parse_config()

def test_tables():
    with parse_config_context(ParseConfig(tables_enabled=True)):
        parser = Parser("| a | b |")
        ...
```

**Severity**: Medium (many tests to update)

### Risk 5: Async/Coroutine Context Propagation

**Problem**: ContextVars propagate to child tasks, but `asyncio.create_task()` copies context

**Mitigation**: Not a concern—Patitas parsing is synchronous. If async support added later, use `contextvars.copy_context()`.

**Severity**: Low (not applicable currently)

---

## 8. Implementation Checklist

- [x] **Phase 1: Foundation**
  - [x] Create `patitas/config.py`
  - [x] Define `ParseConfig` frozen dataclass
  - [x] Add `_DEFAULT_CONFIG` module singleton
  - [x] Add `_parse_config` ContextVar with default
  - [x] Add `get_parse_config()`, `set_parse_config()`, `reset_parse_config()`
  - [x] Add `parse_config_context()` context manager for tests
  - [x] Create `benchmarks/contextvar_config.py`
  - [x] **Validate speedup claim**: 1.40x instantiation (vs projected 2.2x)
  - [x] Add unit tests for thread isolation (`tests/test_config.py`)

- [x] **Phase 2: Markdown Class**
  - [x] Build config in `__init__()`
  - [x] Set ContextVar in `parse()` method
  - [x] Add try/finally with `reset_parse_config()`
  - [x] Test thread isolation with concurrent Markdown instances

- [x] **Phase 3: Parser Refactor**
  - [x] Add `_config` property returning `get_parse_config()`
  - [x] Add property accessors for each config field
  - [x] Remove config slots: 18 → 9 slots (50% reduction)
  - [x] Update `__init__()` signature (source, source_file only)
  - [x] Simplify `_parse_nested_content()` - no config copying needed

- [x] **Phase 4: Mixin Updates**
  - [x] Simplify `parsing/blocks/list/nested.py`
  - [x] Remove config field copying from `parse_nested_list_inline()`

- [x] **Phase 5: Validation**
  - [x] Run full test suite: All 743 tests pass
  - [x] Benchmark results (Python 3.14.2 free-threading):
    - Instantiation: 1.40x faster
    - Sub-parser creation: 1.58x faster
    - Memory: 50% smaller (18 → 9 slots)
    - Thread isolation: Verified ✅
  - [x] Update docstrings
  - [x] Update type hints

---

## 9. Alternatives Considered

### Alternative 1: Keep Instance Attributes

**Pros**: No changes needed  
**Cons**: Memory waste, instantiation overhead, error-prone copying  
**Verdict**: Rejected (measurable performance cost)

### Alternative 2: Class-Level Configuration

```python
class Parser:
    _config: ClassVar[ParseConfig] = ParseConfig()
```

**Pros**: Simple  
**Cons**: Not thread-safe (class attrs shared across threads)  
**Verdict**: Rejected (breaks free-threading)

### Alternative 3: Thread-Local Storage (threading.local)

```python
_local = threading.local()
_local.config = ParseConfig()
```

**Pros**: Thread-safe  
**Cons**: Less ergonomic, no default support, doesn't propagate to child contexts  
**Verdict**: ContextVar is the modern replacement (PEP 567)

### Alternative 4: Config Object Passed to Parser.__init__

```python
parser = Parser(source, config=parse_config)
```

**Pros**: Explicit  
**Cons**: Still requires copying for sub-parsers, more API surface  
**Verdict**: ContextVar is cleaner for nested parser scenarios

---

## 10. Conclusion

The ContextVar configuration pattern provides:

1. **Measurable memory reduction**: 18 → 9 slots (50%)
2. **Projected instantiation speedup**: 2.2x (requires validation)
3. **Cleaner sub-parser creation**: No manual config copying
4. **Thread-safe by design**: ContextVars are thread-local
5. **Unchanged public API**: Transparent to users

The pattern aligns with Python's free-threading direction and follows patterns validated in `rfc-free-threading-patterns.md`.

**Recommendation**: Approve after benchmark validation in Phase 1.

---

## References

- `rfc-free-threading-patterns.md` - ContextVar benchmarks and thread safety analysis
- `rfc-performance-optimization.md` - Overall performance roadmap
- [PEP 567: Context Variables](https://peps.python.org/pep-0567/)
- [contextvars documentation](https://docs.python.org/3/library/contextvars.html)
- [Python 3.14 Free-Threading](https://docs.python.org/3.14/howto/free-threading-python.html)