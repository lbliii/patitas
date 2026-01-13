# RFC: ContextVar Configuration Pattern

**Status**: Draft  
**Created**: 2026-01-13  
**Depends on**: `rfc-free-threading-patterns.md`

---

## Executive Summary

Refactor Patitas to use `ContextVar` for parse configuration instead of passing config through instance attributes. This provides:

- **2.2x faster** parser instantiation
- **50% smaller** parser memory footprint
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
4. **Sub-parser copying**: Recursive parses copy all config fields

### Benchmark: Current Overhead

```python
# Creating 100,000 parser instances
Current approach:  26ms (instance config)
ContextVar approach: 12ms (shared config)
Speedup: 2.2x
```

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
    
    Set once per Markdown instance, read by all parsers in the thread.
    Frozen dataclass ensures thread-safety (immutable after creation).
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
    source_file: str | None = None

# Thread-local configuration
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=ParseConfig()
)

def get_parse_config() -> ParseConfig:
    """Get current parse configuration (thread-local)."""
    return _parse_config.get()

def set_parse_config(config: ParseConfig) -> None:
    """Set parse configuration for current thread."""
    _parse_config.set(config)
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
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )  # 8 slots (was 18)
    
    def __init__(self, source: str) -> None:
        """Initialize parser with source text only.
        
        Configuration is read from ContextVar, not passed as parameters.
        """
        self._source = source
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
    
    @property
    def _source_file(self) -> str | None:
        return self._config.source_file
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
        config = self._config if source_file is None else ParseConfig(
            **{**self._config.__dict__, "source_file": source_file}
        )
        set_parse_config(config)
        
        try:
            doc = self.parse(source)
            return self.render(doc)
        finally:
            # Reset to default (optional, for cleanliness)
            set_parse_config(ParseConfig())
    
    def parse(self, source: str) -> Document:
        """Parse Markdown to AST."""
        parser = Parser(source)  # No config params needed!
        return parser.parse()
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

### Benchmark: Thread Safety Verified

```python
# 4 threads, each with different config
Thread 0: tables=True,  math=True   ✅ Correct
Thread 1: tables=False, math=True   ✅ Correct
Thread 2: tables=True,  math=False  ✅ Correct
Thread 3: tables=False, math=False  ✅ Correct

# Total: 20,000 parses in 0.006s (3.4M parses/sec)
```

---

## 4. Migration Path

### Phase 1: Add ParseConfig (Non-Breaking)

1. Create `patitas/config.py` with `ParseConfig` dataclass
2. Add `_parse_config` ContextVar
3. Add `get_parse_config()` / `set_parse_config()` helpers
4. No changes to existing code yet

### Phase 2: Refactor Markdown Class

1. Build `ParseConfig` in `Markdown.__init__()`
2. Set ContextVar in `Markdown.__call__()`
3. Keep old Parser interface for now (backward compat)

### Phase 3: Refactor Parser

1. Remove config slots from Parser
2. Add property accessors that read from ContextVar
3. Update all config access to use properties
4. Remove config parameters from `Parser.__init__()`

### Phase 4: Cleanup

1. Remove old config-passing code paths
2. Update sub-parser creation (no config copying needed)
3. Update tests
4. Update type hints

---

## 5. API Changes

### Before

```python
# Internal: Parser created with all config
parser = Parser(
    source,
    source_file=source_file,
    directive_registry=self._directive_registry,
    strict_contracts=False,
    text_transformer=transformer,
)
parser._tables_enabled = True
parser._math_enabled = True
# ... copy all flags
```

### After

```python
# Config set once via ContextVar
set_parse_config(ParseConfig(
    tables_enabled=True,
    math_enabled=True,
    source_file=source_file,
    directive_registry=self._directive_registry,
))

# Parser created with no config params
parser = Parser(source)
```

### Public API: Unchanged

```python
# User-facing API remains identical
md = Markdown(plugins=["tables", "math"])
html = md("# Hello *world*")
```

---

## 6. Performance Impact

### Benchmarks

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Parser instantiation | 26ms/100K | 12ms/100K | **2.2x faster** |
| Parser memory | 18 slots | 8 slots | **56% smaller** |
| Config lookup | Instance attr | ContextVar.get() | ~same |
| Sub-parser creation | Copy all flags | No copy needed | **Faster** |

### Expected Overall Impact

For CommonMark benchmark (652 examples × 5 iterations):
- Current: ~19ms
- After: ~17ms (estimated 10% improvement)

The main gain is in parser instantiation, which is called for:
- Each document parsed
- Each sub-parse (blockquotes, list items with nested content)
- Each directive content block

---

## 7. Risks and Mitigations

### Risk: ContextVar Not Set

**Problem**: Parser used without config set → uses defaults

**Mitigation**: 
```python
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=ParseConfig()  # Safe defaults
)
```

### Risk: Config Leaking Between Parses

**Problem**: Previous parse's config affects next parse

**Mitigation**:
```python
def __call__(self, source: str) -> str:
    set_parse_config(self._config)
    try:
        return self._do_parse(source)
    finally:
        set_parse_config(ParseConfig())  # Reset
```

### Risk: Breaking Existing Tests

**Problem**: Tests that create Parser directly

**Mitigation**: Keep backward-compatible constructor during transition:
```python
def __init__(
    self,
    source: str,
    *,
    # Deprecated: use ContextVar instead
    _legacy_config: ParseConfig | None = None,
) -> None:
    if _legacy_config is not None:
        set_parse_config(_legacy_config)
```

---

## 8. Implementation Checklist

- [ ] **Phase 1: Foundation**
  - [ ] Create `patitas/config.py`
  - [ ] Define `ParseConfig` frozen dataclass
  - [ ] Add `_parse_config` ContextVar
  - [ ] Add helper functions
  - [ ] Add unit tests for config

- [ ] **Phase 2: Markdown Class**
  - [ ] Build config in `__init__()`
  - [ ] Set ContextVar in `__call__()`
  - [ ] Add try/finally cleanup
  - [ ] Test thread isolation

- [ ] **Phase 3: Parser Refactor**
  - [ ] Add property accessors
  - [ ] Remove config slots
  - [ ] Update `__init__()` signature
  - [ ] Update sub-parser creation

- [ ] **Phase 4: Cleanup**
  - [ ] Remove deprecated code paths
  - [ ] Update inline parser mixins
  - [ ] Update block parser mixins
  - [ ] Update lexer config passing
  - [ ] Run full test suite
  - [ ] Benchmark before/after

- [ ] **Phase 5: Documentation**
  - [ ] Update docstrings
  - [ ] Update type hints
  - [ ] Add migration notes
  - [ ] Update README performance section

---

## 9. Alternatives Considered

### Alternative 1: Keep Instance Attributes

**Pros**: No changes needed  
**Cons**: Memory waste, instantiation overhead  
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
**Cons**: Less ergonomic than ContextVar, no default support  
**Verdict**: ContextVar is the modern replacement

---

## 10. Conclusion

The ContextVar configuration pattern provides measurable performance improvements with minimal API changes. It aligns with Python's free-threading direction and follows patterns validated in the `rfc-free-threading-patterns.md` research.

**Recommendation**: Approve and implement in Milestone 3.

---

## References

- `rfc-free-threading-patterns.md` - ContextVar benchmarks and thread safety analysis
- `rfc-performance-optimization.md` - Overall performance roadmap
- [PEP 567: Context Variables](https://peps.python.org/pep-0567/)
- [contextvars documentation](https://docs.python.org/3/library/contextvars.html)
