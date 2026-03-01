"""LLM-safe markdown pipeline — sanitize and render for model consumption.

Shows the full pipeline: parse → sanitize → render_llm. Use this when
sending markdown context to an LLM (e.g. RAG retrieval, user-provided docs).

Run::

    python examples/llm_safety/llm_safe_context.py

"""

from patitas import parse, render_llm, sanitize
from patitas.sanitize import llm_safe

# Simulated user content (could come from DB, API, untrusted input)
raw = """# Getting Started

Welcome! Here's a [link](https://example.com) and a [trick](javascript:alert(1)).

<div>Raw HTML block</div>

Some **bold** and *italic* text. Zero-width: hello\u200bworld.

```python
def greet():
    print("Hello")
```
"""

print("=== Raw (unsafe) ===")
print(raw)
print()

# Parse → sanitize → render for LLM
doc = parse(raw)
clean = sanitize(doc, policy=llm_safe)
safe_text = render_llm(clean, source=raw)

print("=== LLM-safe (sanitized + structured) ===")
print(safe_text)
print()

print("Removed: HTML blocks, javascript: links, zero-width unicode")
print("Output: markdown-like plain text with [code:lang], [image:alt] labels")
