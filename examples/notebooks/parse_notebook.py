"""Parse Jupyter notebooks with zero dependencies — stdlib JSON only."""

from pathlib import Path

from patitas import parse_notebook

# Run from repo root: python examples/notebooks/parse_notebook.py
script_dir = Path(__file__).resolve().parent
nb_path = script_dir / "sample-notebook.ipynb"
content = nb_path.read_text()

markdown_content, metadata = parse_notebook(content, nb_path)

print("Metadata:", metadata.get("title", "(from filename)"))
print("Type:", metadata.get("type"))
print("Kernel:", metadata.get("notebook", {}).get("kernel_name"))
print("Cells:", metadata.get("notebook", {}).get("cell_count"))
print()
print("Converted Markdown (first 300 chars):")
print(markdown_content[:300] + "..." if len(markdown_content) > 300 else markdown_content)
