---
title: Performance
description: Benchmarks and optimization strategies
draft: false
weight: 20
lang: en
type: doc
tags:
- performance
- benchmarks
keywords:
- performance
- benchmarks
- speed
- optimization
category: explanation
icon: zap
---

# Performance

Patitas is designed for consistent, predictable performance.

## Why State Machine?

State machines guarantee O(n) regardless of input:

| Input Pattern | Patitas |
|---------------|---------|
| Normal text | Fast |
| Nested emphasis | Fast |
| Pathological input | Fast |

## Benchmarks

Run benchmarks to get current results:

```bash
pytest benchmarks/benchmark_vs_mistune.py benchmarks/benchmark_incremental.py -v --benchmark-only
python benchmarks/benchmark_parallel.py   # Free-threading scaling demo
```

**652 CommonMark examples (single thread):** typically low tens of milliseconds on
Python 3.14. Run the benchmark locally for a number that matches your hardware and
installed comparator packages.

**Large document (~100KB):** environment-sensitive; use
`benchmarks/benchmark_scaling.py` or the full benchmark suite for current data.

**Incremental parsing:** For a 1-char edit in a ~100KB doc, `parse_incremental`
can be roughly 200x faster than full re-parse in the bundled benchmark.

**Pathological input:** Patitas completes in O(n) regardless of input.

## Optimization Strategies

:::{steps}
:::{step} Zero-copy text

The renderer extracts text directly from source using slices:

```python
# Instead of copying strings
text = source[start:end]  # Zero-copy slice
```

:::{/step}
:::{step} StringBuilder

Output uses `StringBuilder` for O(n) concatenation:

```python
# O(n) total
builder = StringBuilder()
for part in parts:
    builder.append(part)
result = str(builder)  # Single allocation
```

:::{/step}
:::{step} Frozen dataclasses with slots

```python
@dataclass(frozen=True, slots=True)
class Node:
    # 40% less memory than regular classes
    # Faster attribute access
```

:::{/step}
:::{step} Tuple children

Using tuples instead of lists:

```python
children: tuple[Inline, ...]  # Immutable, hashable
```

:::{/step}
:::{step} Parse cache

Content-addressed cache avoids re-parsing unchanged content. Key is
`(content_hash, config_hash)`; value is `Document`. Use for incremental builds,
undo/revert, or duplicate content:

```python
from patitas import parse, DictParseCache

cache = DictParseCache()
for source in sources:
    doc = parse(source, cache=cache)  # Duplicates hit cache
```

On a 2-pass build over the same content, the second pass is effectively free.
`DictParseCache` is not thread-safe; for parallel parsing, use a cache with
internal locking. See [API Reference](/docs/reference/api/#parse-cache).

:::{/step}
:::{/steps}

## Memory Usage

| Component | Per Node | Notes |
|-----------|----------|-------|
| Heading | ~120 bytes | Plus children |
| Paragraph | ~100 bytes | Plus children |
| Text | ~80 bytes | Plus string |
| SourceLocation | ~48 bytes | Optional |

## Free-Threading Performance

With Python 3.14t (GIL disabled), speedups depend on corpus shape, document
count, CPU, and scheduler behavior. Measure your workload instead of treating
one example as a guarantee. A recent local run on Python 3.14.2 with 1,000
CommonMark documents produced:

| Threads | Documents | Time | Speedup |
|---------|-----------|------|---------|
| 1 | 1000 | 0.07s | 1.00x |
| 2 | 1000 | 0.05s | 1.42x |
| 4 | 1000 | 0.04s | 1.64x |
| 8 | 1000 | 0.04s | 1.75x |

Patitas is structured to avoid shared mutable parser state; actual scaling still
depends on the runtime and workload.

## Profiling Your Workload

Patitas includes a built-in profiler for measuring parse performance in your
own application. It adds zero overhead when disabled — the hot path is a
single `None` check.

### profiled_parse()

Wrap any code that calls `parse()` in a `profiled_parse()` context manager:

```python
from patitas import parse
from patitas.profiling import profiled_parse

with profiled_parse() as metrics:
    doc = parse(source)

summary = metrics.summary()
print(summary)
# {"total_ms": 1.2, "source_length": 1774, "node_count": 23, "parse_calls": 1}
```

The accumulator tracks total time, source length, top-level node count, and
number of `parse()` calls. Use it to profile batch operations:

```python
with profiled_parse() as metrics:
    for path in markdown_files:
        doc = parse(path.read_text())

summary = metrics.summary()
print(f"{summary['parse_calls']} files in {summary['total_ms']:.1f} ms")
print(f"Throughput: {summary['source_length'] / summary['total_ms']:,.0f} chars/ms")
```

### Thread safety

Each thread gets its own accumulator via `ContextVar`. Profiling in one
thread never affects another:

```python
from concurrent.futures import ThreadPoolExecutor

def parse_with_profiling(source: str) -> dict:
    with profiled_parse() as metrics:
        parse(source)
    return metrics.summary()

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(parse_with_profiling, sources))
# Each result has independent metrics
```

### When to use it

- **Site builds** — identify which pages are slow
- **Live preview** — measure parse latency per keystroke
- **CI pipelines** — track parse time regressions across commits
- **Framework integration** — expose timing to build orchestrators
