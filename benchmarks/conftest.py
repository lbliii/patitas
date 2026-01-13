"""Benchmark fixtures and configuration."""

from __future__ import annotations

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
    sections = []
    for i in range(100):
        sections.append(f"""
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
""")
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
