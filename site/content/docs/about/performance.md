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

Regex-based parsers have unpredictable performance:

| Input Pattern | Regex Parser | State Machine |
|---------------|--------------|---------------|
| Normal text | Fast | Fast |
| Nested emphasis | Slower | Fast |
| Pathological input | **Exponential** | Fast |

State machines guarantee O(n) regardless of input.

## Benchmarks

Tested on MacBook Pro M3, Python 3.14t:

| Document Size | Patitas | mistune | Speedup |
|---------------|---------|---------|---------|
| Small (1KB) | 0.2ms | 0.3ms | 1.5x |
| Medium (10KB) | 1.8ms | 2.8ms | 1.6x |
| Large (100KB) | 15ms | 25ms | 1.7x |
| Pathological | 20ms | >10s | 500x+ |

## Optimization Strategies

### 1. Zero-Copy Text

The renderer extracts text directly from source using slices:

```python
# Instead of copying strings
text = source[start:end]  # Zero-copy slice
```

### 2. StringBuilder

Output uses `StringBuilder` for O(n) concatenation:

```python
# O(n) total
builder = StringBuilder()
for part in parts:
    builder.append(part)
result = str(builder)  # Single allocation
```

### 3. Frozen Dataclasses with Slots

```python
@dataclass(frozen=True, slots=True)
class Node:
    # 40% less memory than regular classes
    # Faster attribute access
```

### 4. Tuple Children

Using tuples instead of lists:

```python
children: tuple[Inline, ...]  # Immutable, hashable
```

## Memory Usage

| Component | Per Node | Notes |
|-----------|----------|-------|
| Heading | ~120 bytes | Plus children |
| Paragraph | ~100 bytes | Plus children |
| Text | ~80 bytes | Plus string |
| SourceLocation | ~48 bytes | Optional |

## Free-Threading Performance

With Python 3.14t (GIL disabled):

| Threads | Documents | Time | Speedup |
|---------|-----------|------|---------|
| 1 | 1000 | 1.5s | 1x |
| 4 | 1000 | 0.4s | 3.75x |
| 8 | 1000 | 0.25s | 6x |

Near-linear scaling due to no shared mutable state.

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
