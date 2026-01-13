---
title: Get Started
description: Install Patitas and parse your first Markdown document
draft: false
weight: 10
lang: en
type: doc
tags:
- onboarding
- quickstart
keywords:
- getting started
- installation
- quickstart
category: onboarding
cascade:
  type: doc
icon: arrow-clockwise
---

# Get Started

## Install

```bash
pip install patitas
```

Requires Python 3.14 or later. See [[docs/get-started/installation|installation]] for alternative methods.

## Parse Markdown

```python
from patitas import parse, render

# Parse to typed AST
doc = parse("# Hello **World**")

# Render to HTML
html = render(doc, source="# Hello **World**")
print(html)
# Output: <h1>Hello <strong>World</strong></h1>
```

## All-in-One

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
print(html)
# Output: <h1>Hello <strong>World</strong></h1>
```

## What's Next?

:::{cards}
:columns: 1-2-3
:gap: medium

:::{card} Quickstart
:icon: zap
:link: ./quickstart
:description: Complete walkthrough in 2 minutes
:badge: Start Here
Parse, render, and explore the AST.
:::{/card}

:::{card} Syntax Guide
:icon: code
:link: ../syntax/
:description: Markdown syntax reference
Learn inline, blocks, links, and code.
:::{/card}

:::{card} Directives
:icon: layers
:link: ../directives/
:description: MyST-style extensions
Add admonitions, tabs, and dropdowns.
:::{/card}

:::{/cards}

## Quick Links

- [[docs/reference/api|API Reference]] — parse, render, Markdown class
- [[docs/syntax/inline|Inline Syntax]] — emphasis, links, code
- [[docs/about/architecture|Architecture]] — lexer, parser, renderer
