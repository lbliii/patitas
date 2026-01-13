"""cProfile wrapper for Patitas parsing.

Run with:
    uv run python -m cProfile -o profile.prof benchmarks/profile_parse.py
    uv run python -m snakeviz profile.prof

Or for direct profiling:
    uv run python benchmarks/profile_parse.py
"""

from __future__ import annotations

import cProfile
import io
import json
import pstats
import sys
from pathlib import Path


def get_commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec_file = (
        Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    )
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")
    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


def parse_corpus(iterations: int = 10) -> None:
    """Parse the CommonMark corpus multiple times."""
    from patitas import Markdown

    md = Markdown()
    docs = get_commonmark_corpus()

    for _ in range(iterations):
        for doc in docs:
            md(doc)


def main() -> None:
    """Run profiling and print results."""
    print("Patitas Profiling")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}")

    iterations = 10
    print(f"\nParsing CommonMark corpus {iterations}x...")

    # Profile the parsing
    profiler = cProfile.Profile()
    profiler.enable()

    parse_corpus(iterations)

    profiler.disable()

    # Print stats
    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 60 + "\n")

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(30)
    print(s.getvalue())

    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY TOTAL (SELF) TIME")
    print("=" * 60 + "\n")

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.TIME)
    ps.print_stats(30)
    print(s.getvalue())

    # Print call counts for hot functions
    print("\n" + "=" * 60)
    print("CALL COUNTS FOR HOT FUNCTIONS")
    print("=" * 60 + "\n")

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CALLS)
    ps.print_stats(30)
    print(s.getvalue())

    print("\nTo visualize with snakeviz:")
    print("  uv run python -m cProfile -o profile.prof benchmarks/profile_parse.py")
    print("  uv run python -m snakeviz profile.prof")


if __name__ == "__main__":
    main()
