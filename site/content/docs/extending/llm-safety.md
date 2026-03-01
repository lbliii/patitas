---
title: LLM Safety
description: Sanitize and render Markdown for LLM context (RAG, retrieval)
draft: false
weight: 35
lang: en
type: doc
tags:
- extending
- llm
- sanitize
- safety
- rag
keywords:
- llm
- sanitize
- render_llm
- rag
- safety
- retrieval
category: how-to
icon: shield-check
---

# LLM Safety

When sending Markdown to an LLM (RAG retrieval, user-provided docs, context windows),
you should sanitize untrusted content and render to a safe, structured format. Patitas
provides a parse → sanitize → render pipeline for this.

## Pipeline

```python
from patitas import parse, sanitize, render_llm
from patitas.sanitize import llm_safe

# 1. Parse
doc = parse(user_content)

# 2. Sanitize (strip HTML, dangerous URLs, zero-width chars)
clean = sanitize(doc, policy=llm_safe)

# 3. Render to LLM-friendly plain text
safe_text = render_llm(clean, source=user_content)
```

## What Gets Removed

The `llm_safe` policy strips:

- **HTML** — All `HtmlBlock` and `HtmlInline` nodes (prevents script injection, hidden content)
- **Dangerous URLs** — Links and images with `javascript:`, `data:`, `vbscript:` schemes
- **Zero-width / bidi characters** — Trojan Source mitigation (invisible Unicode that can
  change display order or hide malicious content)

## Pre-built Policies

| Policy | Strips | Use case |
|--------|--------|----------|
| `llm_safe` | HTML, dangerous URLs, zero-width | Default for LLM context |
| `web_safe` | llm_safe + HTML comments stripped | Web display of user content |
| `strict` | llm_safe + images (→ alt text) + raw code blocks | Maximum reduction |

```python
from patitas.sanitize import llm_safe, web_safe, strict

clean = sanitize(doc, policy=llm_safe)   # RAG, retrieval
clean = sanitize(doc, policy=web_safe)  # User content on web
clean = sanitize(doc, policy=strict)    # Minimal text only
```

## Custom Policies

Compose policies with the `|` operator:

```python
from patitas.sanitize import strip_html, strip_dangerous_urls, normalize_unicode, allow_url_schemes

# Only https and mailto
custom = strip_html | strip_dangerous_urls | normalize_unicode | allow_url_schemes("https", "mailto")
clean = sanitize(doc, policy=custom)
```

Available building blocks: `strip_html`, `strip_html_comments`, `strip_dangerous_urls`,
`normalize_unicode`, `strip_images`, `strip_raw_code`, `allow_url_schemes(*schemes)`.

## render_llm Output

`render_llm()` produces structured plain text with explicit labels:

- Code blocks: `[code:python]\n...\n[/code]`
- Math: `[math] ... [/math]`
- Images: `[image: alt text]`
- HtmlBlock / HtmlInline: skipped (not rendered)

No raw HTML is emitted. The format is predictable and parseable for downstream tools.

## Example

Run the full pipeline:

```bash
python examples/llm_safety/llm_safe_context.py
```

This demonstrates parse → sanitize → render_llm on sample content with HTML, dangerous
links, and zero-width characters.

## See Also

- [API Reference](/docs/reference/api/) — `render_llm()`, `sanitize()`, `Policy`
- [Examples](https://github.com/lbliii/patitas/tree/main/examples) — Runnable examples in the repo
