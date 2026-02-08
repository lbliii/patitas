"""Benchmark ContextVar config pattern vs instance attributes.

Validates the performance claims from rfc-contextvar-config.md:
- 2.2x faster parser instantiation (18 → 9 slots)
- Config access overhead comparison

Run:
    python -m benchmarks.contextvar_config

"""

import gc
import statistics
import sys
import timeit
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Thread


@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Simulated parse configuration (frozen for thread-safety)."""

    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: object | None = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None


_DEFAULT_CONFIG = ParseConfig()
_parse_config: ContextVar[ParseConfig] = ContextVar(
    "parse_config",
    default=_DEFAULT_CONFIG,
)


class ParserBefore:
    """Current: 18 slots with instance config."""

    __slots__ = (
        "_allow_setext_headings",
        "_autolinks_enabled",
        "_containers",
        "_current",
        "_directive_registry",
        "_directive_stack",
        "_footnotes_enabled",
        "_link_refs",
        "_math_enabled",
        "_pos",
        "_source",
        "_source_file",
        "_strict_contracts",
        "_strikethrough_enabled",
        "_tables_enabled",
        "_task_lists_enabled",
        "_text_transformer",
        "_tokens",
    )

    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens: list[object] = []
        self._pos = 0
        self._current: object | None = None
        self._source_file: str | None = None
        self._text_transformer: Callable[[str], str] | None = None
        self._tables_enabled = False
        self._strikethrough_enabled = False
        self._task_lists_enabled = False
        self._footnotes_enabled = False
        self._math_enabled = False
        self._autolinks_enabled = False
        self._directive_registry: object | None = None
        self._strict_contracts = False
        self._directive_stack: list[str] = []
        self._link_refs: dict[str, tuple[str, str]] = {}
        self._containers: object | None = None
        self._allow_setext_headings = True


class ParserAfter:
    """Proposed: 9 slots with ContextVar config."""

    __slots__ = (
        "_allow_setext_headings",
        "_containers",
        "_current",
        "_directive_stack",
        "_link_refs",
        "_pos",
        "_source",
        "_source_file",
        "_tokens",
    )

    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens: list[object] = []
        self._pos = 0
        self._current: object | None = None
        self._source_file: str | None = None
        self._directive_stack: list[str] = []
        self._link_refs: dict[str, tuple[str, str]] = {}
        self._containers: object | None = None
        self._allow_setext_headings = True

    @property
    def _config(self) -> ParseConfig:
        return _parse_config.get()

    @property
    def _tables_enabled(self) -> bool:
        return self._config.tables_enabled

    @property
    def _strikethrough_enabled(self) -> bool:
        return self._config.strikethrough_enabled

    @property
    def _task_lists_enabled(self) -> bool:
        return self._config.task_lists_enabled

    @property
    def _footnotes_enabled(self) -> bool:
        return self._config.footnotes_enabled

    @property
    def _math_enabled(self) -> bool:
        return self._config.math_enabled

    @property
    def _autolinks_enabled(self) -> bool:
        return self._config.autolinks_enabled

    @property
    def _directive_registry(self) -> object | None:
        return self._config.directive_registry

    @property
    def _strict_contracts(self) -> bool:
        return self._config.strict_contracts

    @property
    def _text_transformer(self) -> Callable[[str], str] | None:
        return self._config.text_transformer


class ParserAfterCached:
    """Alternative: Cache config reference to avoid repeated ContextVar lookups."""

    __slots__ = (
        "_allow_setext_headings",
        "_cached_config",  # Cache the config at init time
        "_containers",
        "_current",
        "_directive_stack",
        "_link_refs",
        "_pos",
        "_source",
        "_source_file",
        "_tokens",
    )

    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens: list[object] = []
        self._pos = 0
        self._current: object | None = None
        self._source_file: str | None = None
        self._directive_stack: list[str] = []
        self._link_refs: dict[str, tuple[str, str]] = {}
        self._containers: object | None = None
        self._allow_setext_headings = True
        self._cached_config = _parse_config.get()  # Cache once at init

    @property
    def _tables_enabled(self) -> bool:
        return self._cached_config.tables_enabled

    @property
    def _math_enabled(self) -> bool:
        return self._cached_config.math_enabled


def benchmark_instantiation(n: int = 100_000) -> dict[str, float]:
    """Benchmark parser instantiation."""
    print(f"\n{'='*60}")
    print(f"Parser Instantiation Benchmark (n={n:,})")
    print("=" * 60)

    # Disable GC for consistent results
    gc.disable()

    before_times = []
    after_times = []

    # Run multiple trials
    for _trial in range(5):
        before = timeit.timeit(lambda: ParserBefore("# Test"), number=n)
        after = timeit.timeit(lambda: ParserAfter("# Test"), number=n)
        before_times.append(before)
        after_times.append(after)

    gc.enable()

    before_avg = statistics.mean(before_times)
    after_avg = statistics.mean(after_times)

    before_std = statistics.stdev(before_times) * 1000
    after_std = statistics.stdev(after_times) * 1000
    print(f"\nBefore (18 slots): {before_avg*1000:.2f}ms (±{before_std:.2f}ms)")
    print(f"After (9 slots):   {after_avg*1000:.2f}ms (±{after_std:.2f}ms)")
    print(f"Speedup: {before_avg/after_avg:.2f}x")
    print(f"Per-instance: {before_avg/n*1e9:.1f}ns → {after_avg/n*1e9:.1f}ns")

    return {
        "before_ms": before_avg * 1000,
        "after_ms": after_avg * 1000,
        "speedup": before_avg / after_avg,
    }


def benchmark_config_access(n: int = 1_000_000) -> dict[str, float]:
    """Benchmark config attribute access."""
    print(f"\n{'='*60}")
    print(f"Config Access Benchmark (n={n:,})")
    print("=" * 60)

    parser_before = ParserBefore("# Test")
    parser_before._tables_enabled = True

    _parse_config.set(ParseConfig(tables_enabled=True))
    parser_after = ParserAfter("# Test")
    parser_after_cached = ParserAfterCached("# Test")

    gc.disable()

    before = timeit.timeit(lambda: parser_before._tables_enabled, number=n)
    after = timeit.timeit(lambda: parser_after._tables_enabled, number=n)
    after_cached = timeit.timeit(lambda: parser_after_cached._tables_enabled, number=n)

    gc.enable()

    print(f"\nInstance attr:    {before*1000:.2f}ms ({before/n*1e9:.1f}ns/access)")
    print(f"ContextVar:       {after*1000:.2f}ms ({after/n*1e9:.1f}ns/access)")
    print(f"Cached config:    {after_cached*1000:.2f}ms ({after_cached/n*1e9:.1f}ns/access)")
    print(f"ContextVar overhead: {after/before:.2f}x")
    print(f"Cached overhead:     {after_cached/before:.2f}x")

    return {
        "instance_attr_ms": before * 1000,
        "contextvar_ms": after * 1000,
        "cached_ms": after_cached * 1000,
        "contextvar_overhead": after / before,
        "cached_overhead": after_cached / before,
    }


def benchmark_sub_parser_creation(n: int = 50_000) -> dict[str, float]:
    """Benchmark sub-parser creation (simulates nested content parsing)."""
    print(f"\n{'='*60}")
    print(f"Sub-Parser Creation Benchmark (n={n:,})")
    print("=" * 60)

    def create_sub_parser_before(parent: ParserBefore) -> ParserBefore:
        sub = ParserBefore("nested content")
        # Copy all config fields (as in current implementation)
        sub._tables_enabled = parent._tables_enabled
        sub._strikethrough_enabled = parent._strikethrough_enabled
        sub._task_lists_enabled = parent._task_lists_enabled
        sub._footnotes_enabled = parent._footnotes_enabled
        sub._math_enabled = parent._math_enabled
        sub._autolinks_enabled = parent._autolinks_enabled
        sub._directive_registry = parent._directive_registry
        sub._strict_contracts = parent._strict_contracts
        sub._text_transformer = parent._text_transformer
        sub._link_refs = parent._link_refs  # Shared
        return sub

    def create_sub_parser_after(parent: ParserAfter) -> ParserAfter:
        sub = ParserAfter("nested content")
        # No config copying needed! Config is inherited via ContextVar
        sub._link_refs = parent._link_refs  # Shared (still needed)
        return sub

    parent_before = ParserBefore("# Parent")
    parent_before._tables_enabled = True
    parent_before._math_enabled = True

    _parse_config.set(ParseConfig(tables_enabled=True, math_enabled=True))
    parent_after = ParserAfter("# Parent")

    gc.disable()

    before = timeit.timeit(lambda: create_sub_parser_before(parent_before), number=n)
    after = timeit.timeit(lambda: create_sub_parser_after(parent_after), number=n)

    gc.enable()

    print(f"\nBefore (copy 9 fields): {before*1000:.2f}ms")
    print(f"After (no copy):        {after*1000:.2f}ms")
    print(f"Speedup: {before/after:.2f}x")

    return {"before_ms": before * 1000, "after_ms": after * 1000, "speedup": before / after}


def benchmark_thread_isolation() -> None:
    """Verify config isolation across threads."""
    print(f"\n{'='*60}")
    print("Thread Isolation Test")
    print("=" * 60)

    results: dict[int, dict[str, bool]] = {}
    errors: list[str] = []

    def worker(thread_id: int, config: ParseConfig) -> None:
        _parse_config.set(config)
        parser = ParserAfter("# Test")
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

    threads = [Thread(target=worker, args=(i, c)) for i, c in enumerate(configs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify each thread saw its own config
    expected = [
        {"tables": True, "math": True},
        {"tables": False, "math": True},
        {"tables": True, "math": False},
        {"tables": False, "math": False},
    ]

    print("\nResults:")
    result_list = [results.get(i, {}) for i in range(4)]
    for i, (exp, got) in enumerate(zip(expected, result_list, strict=True)):
        status = "✅" if exp == got else "❌"
        print(f"  Thread {i}: expected={exp}, got={got} {status}")
        if exp != got:
            errors.append(f"Thread {i} mismatch")

    if errors:
        print(f"\n❌ FAILED: {len(errors)} thread(s) had wrong config")
    else:
        print("\n✅ PASSED: All threads saw correct isolated config")


def benchmark_memory_footprint() -> None:
    """Compare memory footprint of parsers."""
    print(f"\n{'='*60}")
    print("Memory Footprint Comparison")
    print("=" * 60)

    before_slots = len(ParserBefore.__slots__)
    after_slots = len(ParserAfter.__slots__)
    after_cached_slots = len(ParserAfterCached.__slots__)

    print("\nSlot counts:")
    print(f"  Before:       {before_slots} slots")
    print(f"  After:        {after_slots} slots")
    print(f"  After+cache:  {after_cached_slots} slots")
    pct = (1 - after_slots / before_slots) * 100
    print(f"\nReduction: {before_slots} → {after_slots} ({pct:.0f}% smaller)")

    # Estimate memory per instance (rough approximation)
    # Each slot is ~8 bytes for the pointer + object overhead
    print("\nEstimated per-instance overhead:")
    print(f"  Before: ~{before_slots * 8} bytes for slot pointers")
    print(f"  After:  ~{after_slots * 8} bytes for slot pointers")


def main() -> None:
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print("Patitas ContextVar Configuration Benchmark Suite")
    print("=" * 60)
    print(f"Python {sys.version}")

    results = {}

    # Memory footprint (informational)
    benchmark_memory_footprint()

    # Thread isolation (correctness test)
    benchmark_thread_isolation()

    # Performance benchmarks
    results["instantiation"] = benchmark_instantiation()
    results["config_access"] = benchmark_config_access()
    results["sub_parser"] = benchmark_sub_parser_creation()

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print("=" * 60)
    print(f"\nInstantiation speedup: {results['instantiation']['speedup']:.2f}x")
    print(f"Sub-parser creation:   {results['sub_parser']['speedup']:.2f}x faster")
    print(f"Config access overhead: {results['config_access']['contextvar_overhead']:.2f}x")
    print(f"  (cached variant):     {results['config_access']['cached_overhead']:.2f}x")

    # RFC validation
    print(f"\n{'='*60}")
    print("RFC Claim Validation")
    print("=" * 60)
    inst_speedup = results["instantiation"]["speedup"]
    target_speedup = 2.2

    if inst_speedup >= target_speedup * 0.8:  # Allow 20% variance
        print(f"✅ Instantiation speedup: {inst_speedup:.2f}x (target: {target_speedup}x)")
    else:
        print(f"⚠️ Instantiation speedup: {inst_speedup:.2f}x (target: {target_speedup}x)")
        print("   Note: Actual speedup may vary by platform/Python version")

    print("✅ Memory reduction: 18 → 9 slots (50%)")


if __name__ == "__main__":
    main()
