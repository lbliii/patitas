---
title: Quickstart
description: Parse your first Markdown document in 2 minutes
draft: false
weight: 20
lang: en
type: doc
tags:
- quickstart
- tutorial
keywords:
- quickstart
- getting started
- tutorial
category: onboarding
icon: zap
---

# Quickstart

Parse Markdown to a typed AST and render to HTML in 2 minutes.

## Step 1: Parse Markdown

```python
from patitas import parse

source = """
# Welcome

This is **bold** and *italic* text.

- Item one
- Item two
"""

doc = parse(source)
```

## Step 2: Explore the AST

```python
# doc is a tuple of Block nodes
print(len(doc))  # 3 (Heading, Paragraph, List)

# Access the heading
heading = doc[0]
print(heading.level)  # 1
print(heading.children)  # [Text("Welcome")]

# Access the paragraph
para = doc[1]
print(para.children)  # [Text, Strong, Text, Emphasis, Text]
```

## Step 3: Render to HTML

```python
from patitas import render

html = render(doc, source=source)
print(html)
```

Output:

```html
<h1>Welcome</h1>
<p>This is <strong>bold</strong> and <em>italic</em> text.</p>
<ul>
<li>Item one</li>
<li>Item two</li>
</ul>
```

## Step 4: All-in-One

For simple use cases, use the `Markdown` class:

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
print(html)
# <h1>Hello <strong>World</strong></h1>
```

## Next Steps

- [[docs/syntax/|Syntax Guide]] — Learn all Markdown syntax
- [[docs/reference/api|API Reference]] — Full API documentation
- [[docs/about/architecture|Architecture]] — How the parser works
