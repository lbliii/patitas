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

:::{steps}
:::{step} Immutable AST

All AST nodes are frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    children: tuple[Inline, ...]
```

Frozen = no mutation = no race conditions.

:::{/step}
:::{step} No shared state

Parser and renderer instances don't share mutable state:

```python
# Each call creates fresh instances
doc1 = parse(source1)  # Thread 1
doc2 = parse(source2)  # Thread 2 - no conflict
```

:::{/step}
:::{step} Thread-local configuration

Parse configuration uses Python's `ContextVar` (thread-local by design):

```python
from patitas import Markdown

# Each thread gets isolated configuration
md1 = Markdown(plugins=["table"])  # Thread 1
md2 = Markdown(plugins=["math"])    # Thread 2

# Concurrent parsing with different configs - safe!
html1 = md1("| a | b |")  # Uses tables config
html2 = md2("$x^2$")      # Uses math config (no conflict)
```

:::{/step}
:::{step} Extension points

Plugins and directive registries are configured per `Markdown` instance via `ParseConfig` (ContextVar). The `set_highlighter()` API uses module-level state — set it once at startup before any concurrent parsing; do not change it during parallel execution.

:::{/step}
:::{/steps}

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

## ContextVar Configuration

For advanced use cases, you can control configuration explicitly:

```python
from patitas import (
    Parser,
    ParseConfig,
    parse_config_context,
    set_parse_config,
    reset_parse_config,
)

# Option 1: Context manager (recommended)
with parse_config_context(ParseConfig(tables_enabled=True)):
    parser = Parser(source)
    doc = parser.parse()
# Config automatically reset after context

# Option 2: Manual control
set_parse_config(ParseConfig(math_enabled=True))
try:
    parser = Parser(source)
    doc = parser.parse()
finally:
    reset_parse_config()
```

The `Markdown` class handles this automatically—you only need explicit control when using `Parser` directly.

## Best Practices

### Do

- Create parser/renderer per thread or per call
- Use frozen AST nodes (default)
- Share source text (immutable strings are safe)
- Use `Markdown` class for automatic config management

### Don't

- Mutate AST nodes (they're frozen anyway)
- Share mutable registries across threads
- Use global mutable state
- Forget to reset config when using `set_parse_config()` directly

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

## Code References

| Pattern | File |
|---------|------|
| Immutable AST nodes | [src/patitas/nodes.py](https://github.com/lbliii/patitas/blob/main/src/patitas/nodes.py) |
| ParseConfig (ContextVar) | [src/patitas/config.py](https://github.com/lbliii/patitas/blob/main/src/patitas/config.py) |
| Markdown facade | [src/patitas/__init__.py](https://github.com/lbliii/patitas/blob/main/src/patitas/__init__.py) |
