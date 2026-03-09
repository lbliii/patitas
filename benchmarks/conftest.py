"""Benchmark fixtures and configuration."""

import json
from pathlib import Path

import pytest

# Sample markdown documents for benchmarking
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples as benchmark corpus."""
    spec_file = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    if not spec_file.exists():
        pytest.skip("CommonMark spec fixture not found")

    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


@pytest.fixture
def large_document() -> str:
    """Generate a large markdown document (~100KB)."""
    sections = [
        f"""
# Section {i}

This is paragraph {i} with **bold**, *italic*, and `code`.

- List item 1
- List item 2
- List item 3

```python
def function_{i}():
    return {i}
```

| Column A | Column B |
|----------|----------|
| Cell {i} | Data {i} |

> This is a blockquote in section {i}.
> It has multiple lines.

Here is a [link](https://example.com/{i}) and an image reference.

---
"""
        for i in range(100)
    ]
    return "\n".join(sections)


@pytest.fixture
def real_world_docs() -> list[str]:
    """Collection of real-world markdown patterns."""
    return [
        # Simple paragraph
        "Hello **world**!",
        # Headers and paragraphs
        """# Title

This is a paragraph with *emphasis* and **strong**.

## Subtitle

More content here.""",
        # Code blocks
        """# API Reference

```python
from mylib import Client

client = Client(api_key="xxx")
result = client.query("SELECT * FROM users")
```

The above code demonstrates basic usage.""",
        # Complex nesting
        """# Documentation

> **Note**: This is important.
>
> - Point 1
> - Point 2
>   - Nested point
>
> ```python
> code_in_quote = True
> ```

Continue reading below.""",
        # Tables
        """| Feature | Patitas | mistune | markdown-it-py |
|---------|---------|---------|----------------|
| Speed | Fast | Fast | Medium |
| Types | Yes | No | No |
| Safety | O(n) | Regex | Regex |""",
        # Links and images
        """Check out [our docs](https://docs.example.com) for more info.

![Logo](https://example.com/logo.png "Our Logo")

Contact us at <email@example.com> or visit https://example.com.""",
    ]


@pytest.fixture
def plugin_heavy_doc() -> str:
    """Document exercising tables, math, footnotes, strikethrough, task lists (~2KB)."""
    return """# Plugin-Heavy Document

| Feature | Patitas | mistune |
|---------|---------|---------|
| Tables | Yes | Yes |
| Math | $E = mc^2$ | Plugin |

Inline math: $x^2 + y^2 = z^2$ and block:

$$
\\int_0^1 x^2 \\, dx = \\frac{1}{3}
$$

Footnotes[^1] and strikethrough: ~~deleted~~ text.

Task list:
- [x] Completed item
- [ ] Pending item
- [ ] Another todo

[^1]: Footnote definition here.
"""


@pytest.fixture
def directive_heavy_doc() -> str:
    """Document with many MyST directives (admonition, tabs, dropdown). ~4KB."""
    block = """# Section

:::{note}
This is a note with **bold** and *italic*.
:::

:::{warning}
Important warning here.
:::

:::{tab-set}

:::{tab-item} Python
```python
def hello():
    print("world")
```
:::

:::{tab-item} JavaScript
```javascript
console.log("world");
```
:::
:::

:::{dropdown} Click to expand
Hidden content with a [link](https://example.com).
:::
"""
    return (block + "\n\n") * 15


@pytest.fixture
def preserves_raw_content_doc() -> str:
    """Document with list-table directives (preserves_raw_content=True path)."""
    block = """:::{list-table}
:header-rows: 1

* - Header 1
  - Header 2
  - Header 3
* - Cell A1
  - Cell A2
  - Cell A3
* - Cell B1
  - Cell B2
  - Cell B3
:::
"""
    return (block + "\n\n") * 20


@pytest.fixture
def frontmatter_docs() -> list[str]:
    """Documents with YAML frontmatter for parse_frontmatter benchmark."""
    return [
        """---
title: Hello World
weight: 10
tags: [a, b, c]
---

# Body content

Paragraph with **bold**.
""",
        """---
title: API Reference
description: Full API docs
---

```python
from lib import Client
```
""",
    ] * 50


def _scaled_document(target_kb: int) -> str:
    """Generate document of approximately target_kb size."""
    template = """
# Section {i}

Paragraph {i} with **bold** and *italic* and `code`.

- List item 1
- List item 2

| A | B |
|---|---|
| x | y |
"""
    section_len = len(template.format(i=0))
    count = max(1, (target_kb * 1024) // section_len)
    return "\n".join(template.format(i=i) for i in range(count))


@pytest.fixture
def doc_10kb() -> str:
    """~10KB document."""
    return _scaled_document(10)


@pytest.fixture
def doc_100kb() -> str:
    """~100KB document."""
    return _scaled_document(100)


@pytest.fixture
def doc_500kb() -> str:
    """~500KB document."""
    return _scaled_document(500)


def _list_table_scaled_doc(target_kb: int) -> str:
    """Generate document with list-table directives at target size."""
    block = """:::{list-table}
:header-rows: 1

* - H1
  - H2
  - H3
* - A1
  - A2
  - A3
* - B1
  - B2
  - B3
:::
"""
    block_len = len(block)
    count = max(1, (target_kb * 1024) // block_len)
    return (block + "\n\n") * count


@pytest.fixture
def list_table_doc_50kb() -> str:
    """~50KB document with list-table directives (preserves_raw_content path)."""
    return _list_table_scaled_doc(50)


def _code_heavy_doc(num_blocks: int) -> str:
    """Generate document with many code blocks (exercises excerpt first-line path)."""
    block = """# Section {i}

Paragraph before code.

```python
def function_{i}():
    '''Docstring with multiple lines.
    More docstring.
    '''
    return {i} * 2
```

Paragraph after code.

    indented_code_block_{i}
    another_line
"""
    return "\n".join(block.format(i=i) for i in range(num_blocks))


@pytest.fixture
def doc_with_many_code_blocks() -> str:
    """~20KB document with many fenced and indented code blocks."""
    return _code_heavy_doc(200)
