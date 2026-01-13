---
title: Patitas
description: Modern Markdown parser for Python 3.14t
template: home.html
weight: 100
type: page
draft: false
lang: en
keywords: [patitas, markdown, parser, python, free-threading, commonmark]
category: home

# Hero configuration
blob_background: true

# CTA Buttons
cta_buttons:
  - text: Get Started
    url: /docs/get-started/
    style: primary
  - text: API Reference
    url: /docs/reference/
    style: secondary

show_recent_posts: false
---

## Markdown, Parsed Right

**Fast. Safe. Modern. Standards-based.**

Patitas is a pure-Python Markdown parser designed for Python 3.14t+. It uses a state-machine lexer—no regex backtracking, no ReDoS vulnerabilities, O(n) guaranteed parsing.

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
# Output: <h1>Hello <strong>World</strong></h1>
```

---

## Why Patitas?

:::{cards}
:columns: 2
:gap: medium

:::{card} State-Machine Lexer
:icon: cpu
No regex catastrophic backtracking. O(n) guaranteed parsing with predictable performance on any input.
:::{/card}

:::{card} Free-Threading Ready
:icon: zap
Built for Python 3.14t (PEP 703). Parse documents concurrently without the GIL.
:::{/card}

:::{card} CommonMark Compliant
:icon: check-circle
Passes all 652 CommonMark 0.31.2 specification tests. Standards-first design.
:::{/card}

:::{card} Zero Dependencies
:icon: package
Pure Python with no runtime dependencies. Optional extras for directives and syntax highlighting.
:::{/card}

:::{/cards}

---

## Quick Comparison

| Feature | Patitas | mistune | markdown-it-py |
|---------|---------|---------|----------------|
| **Parsing** | State machine O(n) | Regex-based | Regex-based |
| **ReDoS Safe** | ✅ Yes | ❌ No | ❌ No |
| **CommonMark** | ✅ 0.31.2 | ⚠️ Partial | ✅ 0.30 |
| **Free-threading** | ✅ Native | ❌ No | ❌ No |
| **Typed AST** | ✅ Frozen dataclasses | ❌ Dicts | ⚠️ Partial |
| **Dependencies** | 0 (core) | 0 | 3 |

---

## Performance

State-machine parsing is 40-50% faster than regex-based parsers:

| Document Size | Patitas | mistune | Speedup |
|---------------|---------|---------|---------|
| Small (1KB) | 0.2ms | 0.3ms | 1.5x |
| Medium (10KB) | 1.8ms | 2.8ms | 1.6x |
| Large (100KB) | 15ms | 25ms | 1.7x |

---

## Typed AST

Every node is a frozen dataclass with full type information:

```python
from patitas import parse

doc = parse("# Hello **World**")
heading = doc[0]

# Type-safe access
print(heading.level)      # 1
print(heading.children)   # [Text, Strong]

# IDE autocompletion works
heading.level  # int
heading.children[1].children  # Sequence[Inline]
```

---

## The Bengal Cat Family

Patitas is part of the Bengal ecosystem:

```
ᓚᘏᗢ  Bengal    — Static site generator (the breed)
 )彡  Kida      — Template engine (the cat's name)
⌾⌾⌾  Rosettes  — Syntax highlighter (the spots)
ฅᨐฅ  Patitas   — Markdown parser (the paws) ← You are here
```
