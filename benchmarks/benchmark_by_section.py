"""Benchmark Patitas by CommonMark spec section.

Identifies which CommonMark sections are slowest and provides
insights for targeted optimization.

Run with:
    uv run python benchmarks/benchmark_by_section.py
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SectionTiming:
    """Timing data for a CommonMark section."""

    section: str
    total_time_us: float
    doc_count: int
    avg_time_us: float


def get_commonmark_corpus_by_section() -> dict[str, list[tuple[int, str]]]:
    """Load CommonMark spec examples grouped by section.

    Returns:
        Dict mapping section name to list of (example_number, markdown_content).
    """
    spec_file = (
        Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    )
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")

    examples = json.loads(spec_file.read_text())
    by_section: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for ex in examples:
        section = ex.get("section", "Unknown")
        example_num = ex.get("example", 0)
        markdown = ex.get("markdown", "")
        by_section[section].append((example_num, markdown))

    return dict(by_section)


def benchmark_section(
    section_docs: list[tuple[int, str]],
    iterations: int = 100,
) -> tuple[float, list[float]]:
    """Benchmark parsing for a single section.

    Args:
        section_docs: List of (example_number, markdown) for the section.
        iterations: Number of iterations per document.

    Returns:
        (total_time_us, per_doc_times_us)
    """
    from patitas import Markdown

    md = Markdown()
    docs = [doc for _, doc in section_docs]

    # Warmup
    for doc in docs:
        md(doc)

    # Timed runs
    per_doc_times: list[float] = []

    for doc in docs:
        start = time.perf_counter()
        for _ in range(iterations):
            md(doc)
        elapsed = time.perf_counter() - start
        per_doc_times.append((elapsed / iterations) * 1_000_000)  # Convert to µs

    total_time = sum(per_doc_times)
    return total_time, per_doc_times


def main() -> None:
    """Run section-by-section benchmarks."""
    import sys

    print("Patitas Section-by-Section Benchmark")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}")

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"GIL enabled: {gil_enabled}\n")

    print("Loading CommonMark corpus by section...")
    sections = get_commonmark_corpus_by_section()
    total_docs = sum(len(docs) for docs in sections.values())
    print(f"Loaded {total_docs} documents in {len(sections)} sections\n")

    iterations = 100
    print(f"Running {iterations} iterations per document...\n")

    results: list[SectionTiming] = []

    for section_name, docs in sections.items():
        total_time, per_doc = benchmark_section(docs, iterations)
        avg_time = total_time / len(docs) if docs else 0

        results.append(
            SectionTiming(
                section=section_name,
                total_time_us=total_time,
                doc_count=len(docs),
                avg_time_us=avg_time,
            )
        )
        print(f"  {section_name:40} {avg_time:6.1f}µs/doc ({len(docs):3} docs)")

    # Sort by average time (slowest first)
    results.sort(key=lambda x: x.avg_time_us, reverse=True)

    print("\n" + "=" * 60)
    print("RESULTS: Sorted by average parse time (slowest first)")
    print("=" * 60)

    # Calculate overall average for comparison
    total_time = sum(r.total_time_us for r in results)
    total_docs_parsed = sum(r.doc_count for r in results)
    overall_avg = total_time / total_docs_parsed if total_docs_parsed else 0

    print(f"\nOverall average: {overall_avg:.1f}µs/doc\n")

    for r in results:
        ratio = r.avg_time_us / overall_avg if overall_avg else 0
        bar = "█" * min(int(ratio * 5), 20)
        print(f"{r.section:40} {r.avg_time_us:6.1f}µs/doc ({r.doc_count:3} docs) [{ratio:.1f}x] {bar}")

    # Summary of slowest sections
    print("\n" + "=" * 60)
    print("TOP 5 SLOWEST SECTIONS (optimization targets)")
    print("=" * 60)

    for i, r in enumerate(results[:5], 1):
        ratio = r.avg_time_us / overall_avg if overall_avg else 0
        print(f"  {i}. {r.section}: {r.avg_time_us:.1f}µs/doc ({ratio:.1f}x average)")


if __name__ == "__main__":
    main()
