---
title: Thread Safety
description: Free-threading and concurrency support
draft: false
weight: 30
lang: en
type: doc
tags:
- thread-safety
- concurrency
keywords:
- threads
- concurrency
- free-threading
- gil
category: explanation
icon: lock
---

# Thread Safety

Patitas is designed for Python 3.14t free-threading.

## Design Principles

### 1. Immutable AST

All AST nodes are frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    children: tuple[Inline, ...]
```

Frozen = no mutation = no race conditions.

### 2. No Shared State

Parser and renderer instances don't share mutable state:

```python
# Each call creates fresh instances
doc1 = parse(source1)  # Thread 1
doc2 = parse(source2)  # Thread 2 - no conflict
```

### 3. Thread-Local Where Needed

Global extension points use thread-local storage:

```python
# Safe for concurrent use
set_highlighter(my_highlighter)
```

## Concurrent Parsing

Parse multiple documents in parallel:

```python
import concurrent.futures
from patitas import parse

documents = ["# Doc 1", "# Doc 2", "# Doc 3"]

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(parse, documents))
```

## Concurrent Rendering

Render multiple ASTs in parallel:

```python
from patitas import render

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(render, doc, source=src)
        for doc, src in zip(docs, sources)
    ]
    htmls = [f.result() for f in futures]
```

## Best Practices

### Do

- Create parser/renderer per thread or per call
- Use frozen AST nodes (default)
- Share source text (immutable strings are safe)

### Don't

- Mutate AST nodes (they're frozen anyway)
- Share mutable registries across threads
- Use global mutable state

## Python 3.14t

Patitas is built for PEP 703 (free-threading):

```python
# pyproject.toml
[tool.maturin]
module-name = "patitas._core"

# Declares GIL-free compatibility
# _Py_mod_gil = 0 (if there were C extensions)
```

Run with GIL disabled:

```bash
PYTHON_GIL=0 python -c "from patitas import parse; parse('# Test')"
```
