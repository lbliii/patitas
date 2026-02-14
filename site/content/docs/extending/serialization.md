---
title: Serialization
description: Cache and transfer AST as dict or JSON
draft: false
weight: 25
lang: en
type: doc
tags:
- extending
- serialization
- caching
keywords:
- serialization
- to_dict
- from_dict
- to_json
- from_json
- cache
- ast
category: how-to
icon: database
---

# Serialization

Convert Patitas AST nodes to/from JSON-compatible dicts and strings. Output is
deterministic (sorted keys) for cache-key stability.

## Quick Start

```python
from patitas import parse, to_dict, from_dict, to_json, from_json

doc = parse("# Hello **World**")

# Dict format (in-memory, for caching)
data = to_dict(doc)
restored = from_dict(data)
assert doc == restored

# JSON format (persistence, wire transfer)
json_str = to_json(doc)
restored = from_json(json_str)
assert doc == restored
```

## Dict vs JSON

| Format | Use case |
|--------|----------|
| **to_dict / from_dict** | In-memory caching, inspect/modify before JSON, framework integration |
| **to_json / from_json** | Persistence to disk, wire transfer (SSE, HTTP), human inspection |

Dict is the canonical format — `to_json` serializes the dict, `from_json`
deserializes and passes to `from_dict`. Use dict when you need to store in a
cache backend (Redis, memcached) or pass through Python without a string round-trip.

## Caching Parsed ASTs

Cache the AST to skip re-parsing when only templates or downstream config change.
Bengal uses this for incremental builds.

```python
from patitas import parse, to_dict, from_dict, render

def get_or_parse(cache: dict, source: str, cache_key: str):
    if cache_key in cache:
        data = cache[cache_key]
        doc = from_dict(data)
        return doc, cache[cache_key + ":html"]

    doc = parse(source)
    cache[cache_key] = to_dict(doc)
    html = render(doc, source=source)
    cache[cache_key + ":html"] = html
    return doc, html
```

Deterministic output means the same source always produces the same dict, so
cache keys are stable.

## Wire Transfer

Send AST over HTTP or SSE for live preview, collaborative editing, or
server-side rendering:

```python
import json
from patitas import parse, to_dict, from_dict

# Server: serialize to JSON
doc = parse(markdown_source)
payload = json.dumps(to_dict(doc))

# Client: deserialize
data = json.loads(payload)
doc = from_dict(data)
```

## Format

The dict format includes a `_type` discriminator for each node:

```python
from patitas import parse, to_dict

doc = parse("# Hello")
data = to_dict(doc)
# data == {"_type": "Document", "children": [...], "location": {...}}
```

Nested nodes (Heading, Paragraph, etc.) also have `_type`. Use `from_dict`
to reconstruct — do not rely on the schema for custom parsing.

## Thread Safety

All serialization functions are pure — no shared state. Safe to call from any
thread.
