"""Line-level profiling for Patitas parsing.

Run with:
    uv run kernprof -l -v benchmarks/line_profile.py

Or install line_profiler:
    uv add line-profiler
"""

import json
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


# Try to import line_profiler
try:
    from line_profiler import profile
except ImportError:
    # Fallback decorator that does nothing
    def profile(func):  # type: ignore[misc]
        return func


@profile
def parse_inline_content(md, text: str, location) -> tuple:
    """Profile inline parsing (commonly called)."""
    return md._parser._parse_inline(text, location)


@profile
def parse_document(md, text: str) -> object:
    """Profile full document parsing."""
    return md(text)


@profile
def tokenize_source(text: str) -> list:
    """Profile lexer tokenization."""
    from patitas.lexer.core import Lexer

    lexer = Lexer(text)
    return list(lexer.tokenize())


def main() -> None:
    """Run line profiling."""
    import sys

    print("Patitas Line-Level Profiling")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}\n")

    from patitas import Markdown
    from patitas.location import SourceLocation

    docs = get_commonmark_corpus()
    md = Markdown()

    iterations = 5
    print(f"Parsing {len(docs)} documents {iterations}x...")

    # Profile document parsing
    for _ in range(iterations):
        for doc in docs:
            parse_document(md, doc)

    # Profile tokenization separately
    print(f"\nTokenizing {len(docs)} documents {iterations}x...")
    for _ in range(iterations):
        for doc in docs:
            tokenize_source(doc)

    # Profile inline parsing on sample content
    print("\nParsing inline content...")
    loc = SourceLocation.unknown()
    sample_texts = [
        "**bold** and *italic* text",
        "[link](url) and ![image](img.png)",
        "`code` and ~~strikethrough~~",
        "Plain text with no formatting",
        "Complex: **_nested_ emphasis**",
    ]

    for _ in range(iterations * 100):
        for text in sample_texts:
            parse_inline_content(md, text, loc)

    print("\n" + "=" * 60)
    print("To see line-by-line profiling:")
    print("  uv add line-profiler")
    print("  uv run kernprof -l -v benchmarks/line_profile.py")
    print("\nThe @profile decorator marks functions for line profiling.")
    print("When run with kernprof, you'll see time spent on each line.")


if __name__ == "__main__":
    main()
