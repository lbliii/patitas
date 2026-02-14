"""Unit tests for notebook parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from patitas.notebook import parse_notebook


def test_parse_minimal_notebook() -> None:
    """Parse minimal notebook with markdown and code cells."""
    nb_content = """{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": ["# Hello", "\\n", "World"]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["print(42)"],
      "outputs": []
    }
  ],
  "metadata": {
    "kernelspec": {"name": "python3", "language": "python"}
  },
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert "Hello" in content
    assert "World" in content
    assert "```python" in content
    assert "print(42)" in content
    assert metadata["type"] == "notebook"
    assert metadata["notebook"]["kernel_name"] == "python3"
    assert metadata["notebook"]["cell_count"] == 2


def test_parse_with_pre_read_content() -> None:
    """Parser accepts content directly (no I/O)."""
    nb_content = """{
  "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Test"]}],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert "# Test" in content
    assert metadata["type"] == "notebook"


def test_parse_with_outputs() -> None:
    """Parse code cell with stream and execute_result outputs."""
    nb_content = """{
  "cells": [
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["print('hi')"],
      "outputs": [
        {"output_type": "stream", "name": "stdout", "text": "hi\\n"},
        {"output_type": "execute_result", "execution_count": 1, "data": {"text/plain": "42"}, "metadata": {}}
      ]
    }
  ],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert "<pre>hi" in content or "hi" in content
    assert "42" in content
    assert "```python" in content


def test_parse_with_error_output() -> None:
    """Parse code cell with error output."""
    nb_content = """{
  "cells": [
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["1/0"],
      "outputs": [
        {"output_type": "error", "ename": "ZeroDivisionError", "evalue": "division by zero", "traceback": []}
      ]
    }
  ],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert "notebook-error" in content
    assert "ZeroDivisionError" in content
    assert "division by zero" in content


def test_metadata_extraction() -> None:
    """Extract kernelspec, jupytext, and title from metadata."""
    nb_content = """{
  "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Doc"]}],
  "metadata": {
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "title": "My Notebook",
    "jupytext": {"formats": "ipynb,md"}
  },
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert metadata["title"] == "My Notebook"
    assert metadata["notebook"]["kernel_name"] == "python3"
    assert metadata["notebook"]["language_version"] == "python"
    assert metadata.get("format") == "ipynb"


def test_title_fallback_from_source_path() -> None:
    """Title falls back to humanized source path stem when not in metadata."""
    nb_content = """{
  "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Doc"]}],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content, source_path=Path("content/demo-notebook.ipynb"))

    assert metadata["title"] == "Demo Notebook"


def test_infer_code_language() -> None:
    """Infer language from cell metadata."""
    nb_content = """{
  "cells": [
    {
      "cell_type": "code",
      "metadata": {"language": "javascript"},
      "source": ["console.log(1)"],
      "outputs": []
    }
  ],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    content, metadata = parse_notebook(nb_content)

    assert "```javascript" in content
    assert "console.log(1)" in content


def test_nbformat_3_raises() -> None:
    """Older nbformat 3 raises clear error."""
    nb_content = """{
  "cells": [],
  "metadata": {},
  "nbformat": 3,
  "nbformat_minor": 0
}
"""
    with pytest.raises(ValueError, match="Notebook format 3 not supported"):
        parse_notebook(nb_content)


def test_invalid_json_raises() -> None:
    """Invalid JSON raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        parse_notebook("not valid json")
