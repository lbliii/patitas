"""Profile large document parsing (500KB) to find scaling bottlenecks.

The scaling benchmark showed 50x size -> 400x time. This script profiles
the 500KB parse to identify hot paths.

Run with:
    uv run python -m cProfile -o profile_large.prof benchmarks/profile_large_doc.py
    uv run python -m snakeviz profile_large.prof

Or for inline stats:
    uv run python benchmarks/profile_large_doc.py
"""

import cProfile
import io
import pstats
import sys
from pathlib import Path


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


def parse_large_doc(iterations: int = 5) -> None:
    """Parse 500KB document multiple times."""
    from patitas import Markdown

    doc = _scaled_document(500)
    md = Markdown(plugins=["table"])

    for _ in range(iterations):
        md(doc)


def parse_list_table_large_doc(iterations: int = 5) -> None:
    """Parse large doc with many list-table directives (preserves_raw_content path)."""
    from patitas import Markdown, create_registry_with_defaults
    from patitas.directives.decorator import directive
    from patitas.stringbuilder import StringBuilder

    @directive("list-table", preserves_raw_content=True)
    def _render_list_table(node, children: str, sb: StringBuilder) -> None:
        sb.append(node.raw_content or "")

    builder = create_registry_with_defaults()
    builder.register(_render_list_table())
    md = Markdown(plugins=["table"], directive_registry=builder.build())

    # ~100KB of list-table directives
    doc = _list_table_scaled_doc(100)

    for _ in range(iterations):
        md(doc)


def main() -> None:
    """Run profiling and print results."""
    print("Patitas Large Document Profiling")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}\n")

    # Profile 500KB standard doc
    print("Profiling: 500KB document (tables, no directives)...")
    profiler = cProfile.Profile()
    profiler.enable()
    parse_large_doc(iterations=5)
    profiler.disable()

    print("\n" + "=" * 60)
    print("TOP 40 BY CUMULATIVE TIME (500KB standard doc)")
    print("=" * 60 + "\n")

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(40)
    print(s.getvalue())

    print("\n" + "=" * 60)
    print("TOP 40 BY SELF TIME (500KB standard doc)")
    print("=" * 60 + "\n")

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.TIME)
    ps.print_stats(40)
    print(s.getvalue())

    # Profile list-table heavy doc
    print("\n" + "=" * 60)
    print("Profiling: ~100KB list-table doc (preserves_raw_content path)...")
    print("=" * 60)

    profiler2 = cProfile.Profile()
    profiler2.enable()
    parse_list_table_large_doc(iterations=5)
    profiler2.disable()

    print("\nTOP 30 BY CUMULATIVE (list-table doc)")
    s = io.StringIO()
    ps = pstats.Stats(profiler2, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(30)
    print(s.getvalue())

    print("\nTo save profile for snakeviz:")
    print("  uv run python -m cProfile -o profile_large.prof benchmarks/profile_large_doc.py")
    print("  uv run python -m snakeviz profile_large.prof")


if __name__ == "__main__":
    main()
