"""
Jupyter notebook (.ipynb) parser for Patitas.

Parses nbformat 4.x JSON to (markdown_content, metadata) in the same shape
as Markdown files with frontmatter. Zero dependencies — uses stdlib json only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_notebook(
    content: str,
    source_path: Path | str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Parse a Jupyter notebook (.ipynb) to Markdown content and metadata.

    Args:
        content: Raw JSON content of the .ipynb file (caller handles I/O)
        source_path: Optional path for title fallback when notebook has no title

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        json.JSONDecodeError: If content is not valid JSON
        ValueError: If nbformat is 3 or older
    """
    nb = json.loads(content)

    nbformat = nb.get("nbformat", 0)
    if nbformat < 4:
        raise ValueError(f"Notebook format {nbformat} not supported. Convert to nbformat 4 or 5.")

    metadata = _extract_metadata(nb, source_path)
    markdown_content = _cells_to_markdown(nb)

    return markdown_content, metadata


def _extract_metadata(nb: dict[str, Any], source_path: Path | str | None) -> dict[str, Any]:
    """Extract metadata from notebook for frontmatter-like use."""
    nb_meta = nb.get("metadata", {})

    # Jupyter Book / JupyterLab conventions
    title = nb_meta.get("title")
    if not title:
        jt = nb_meta.get("jupytext", {})
        if isinstance(jt, dict):
            tr = jt.get("text_representation", {})
            if isinstance(tr, dict):
                title = tr.get("display_name")
    if isinstance(title, dict):
        title = title.get("display_name")
    if not title and source_path:
        stem = Path(source_path).stem
        title = stem.replace("-", " ").replace("_", " ").title() or stem
    if not title:
        title = "Untitled"

    metadata: dict[str, Any] = {
        "title": title,
        "type": "notebook",
        "notebook": {
            "cell_count": len(nb.get("cells", [])),
            "kernel_name": nb_meta.get("kernelspec", {}).get("name", ""),
            "language_version": nb_meta.get("kernelspec", {}).get("language", ""),
        },
    }

    for key in ("date", "tags", "authors", "summary", "description"):
        if key in nb_meta and nb_meta[key] is not None:
            metadata[key] = nb_meta[key]

    if "jupytext" in nb_meta:
        jt = nb_meta["jupytext"]
        if isinstance(jt, dict) and "formats" in jt:
            metadata.setdefault("format", "ipynb")

    return metadata


def _cells_to_markdown(nb: dict[str, Any]) -> str:
    """Convert notebook cells to Markdown string."""
    parts: list[str] = []
    cells = nb.get("cells", [])

    for cell in cells:
        cell_type = cell.get("cell_type", "code")
        source = cell.get("source", [])
        if isinstance(source, str):
            source = [source]
        text = "".join(source).rstrip()

        if cell_type == "markdown":
            if text:
                parts.append(text)
                parts.append("\n\n")
        elif cell_type == "code":
            lang = _infer_code_language(cell)
            parts.append(f"```{lang}\n{text}\n```\n\n")
            for output in cell.get("outputs", []):
                out_md = _output_to_markdown(output)
                if out_md:
                    parts.append(out_md)
                    parts.append("\n\n")
        elif cell_type == "raw" and text:
            parts.append(text)
            parts.append("\n\n")

    return "".join(parts).rstrip()


def _output_to_markdown(output: dict[str, Any]) -> str:
    """Convert a single output to Markdown/HTML."""
    output_type = output.get("output_type", "")
    data = output.get("data", {})
    text = output.get("text", [])

    if output_type == "stream":
        content = text if isinstance(text, str) else ("".join(text) if text else "")
        if content.strip():
            return f'<div class="nb-output"><pre>{_escape_html(content)}</pre></div>'
        return ""

    if output_type in ("execute_result", "display_data"):
        for mime in ("image/png", "image/jpeg", "image/gif", "image/svg+xml"):
            if mime in data:
                b64 = data[mime]
                if isinstance(b64, list):
                    b64 = "".join(b64)
                return (
                    f'<div class="nb-output nb-output--image">'
                    f'<img src="data:{mime};base64,{b64}" alt="output" />'
                    f"</div>"
                )
        if "text/html" in data:
            html = data["text/html"]
            html = "".join(html) if isinstance(html, list) else html
            if html.strip():
                return f'<div class="nb-output nb-output--html">{html}</div>'
        if "text/plain" in data:
            plain = data["text/plain"]
            plain = "".join(plain) if isinstance(plain, list) else plain
            if plain.strip():
                return f'<div class="nb-output"><pre>{_escape_html(plain)}</pre></div>'
        return ""

    if output_type == "error":
        ename = output.get("ename", "Error")
        evalue = output.get("evalue", "")
        traceback = output.get("traceback", [])
        tb_text = "\n".join(traceback) if traceback else f"{ename}: {evalue}"
        return (
            f'<div class="nb-output nb-output--error">'
            f'<pre class="notebook-error">{_escape_html(tb_text)}</pre>'
            f"</div>"
        )

    return ""


def _infer_code_language(cell: dict[str, Any]) -> str:
    """Infer language for code cell from metadata."""
    meta = cell.get("metadata", {})
    lang = meta.get("language", "") or meta.get("jupytext", {}).get("language_id", "")
    if isinstance(lang, str) and lang:
        return lang
    return "python"


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
