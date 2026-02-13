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

## The Bengal Ecosystem

A structured reactive stack — every layer written in pure Python for 3.14t free-threading.

| | | | |
|--:|---|---|---|
| **ᓚᘏᗢ** | [Bengal](https://github.com/lbliii/bengal) | Static site generator | [Docs](https://lbliii.github.io/bengal/) |
| **∿∿** | [Purr](https://github.com/lbliii/purr) | Content runtime | — |
| **⌁⌁** | [Chirp](https://github.com/lbliii/chirp) | Web framework | [Docs](https://lbliii.github.io/chirp/) |
| **=^..^=** | [Pounce](https://github.com/lbliii/pounce) | ASGI server | [Docs](https://lbliii.github.io/pounce/) |
| **)彡** | [Kida](https://github.com/lbliii/kida) | Template engine | [Docs](https://lbliii.github.io/kida/) |
| **ฅᨐฅ** | **Patitas** | Markdown parser ← You are here | [Docs](https://lbliii.github.io/patitas/) |
| **⌾⌾⌾** | [Rosettes](https://github.com/lbliii/rosettes) | Syntax highlighter | [Docs](https://lbliii.github.io/rosettes/) |

Python-native. Free-threading ready. No npm required.
