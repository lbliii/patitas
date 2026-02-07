"""Memory profiling for Patitas parsing.

Run with:
    uv run python -m memory_profiler benchmarks/memory_bench.py

Or for basic memory stats:
    uv run python benchmarks/memory_bench.py
"""

import gc
import json
import sys
from pathlib import Path

try:
    import tracemalloc
    TRACEMALLOC_AVAILABLE = True
except ImportError:
    TRACEMALLOC_AVAILABLE = False


def get_commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec_file = (
        Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    )
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")
    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


def measure_memory_basic() -> dict[str, int]:
    """Measure memory using basic sys.getsizeof approach."""
    from patitas import Markdown

    md = Markdown()
    docs = get_commonmark_corpus()

    # Force GC before measurement
    gc.collect()

    # Parse all documents
    results = []
    for doc in docs:
        result = md(doc)
        results.append(result)

    # Estimate memory usage
    return {
        "markdown_instance_size": sys.getsizeof(md),
        "docs_count": len(docs),
        "results_count": len(results),
    }


def measure_memory_tracemalloc() -> dict[str, int | float]:
    """Measure memory using tracemalloc."""
    if not TRACEMALLOC_AVAILABLE:
        return {"error": "tracemalloc not available"}

    from patitas import Markdown

    docs = get_commonmark_corpus()

    # Force GC and start tracing
    gc.collect()
    tracemalloc.start()

    # Create parser and parse all documents
    md = Markdown()
    results = []
    for doc in docs:
        result = md(doc)
        results.append(result)

    # Get memory snapshot
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Analyze top allocations
    top_stats = snapshot.statistics("lineno")

    total_size = sum(stat.size for stat in top_stats)
    total_count = sum(stat.count for stat in top_stats)

    return {
        "total_memory_bytes": total_size,
        "total_memory_mb": total_size / (1024 * 1024),
        "total_allocations": total_count,
        "docs_parsed": len(docs),
        "bytes_per_doc": total_size / len(docs) if docs else 0,
    }


def profile_with_memory_profiler() -> None:
    """Profile using memory_profiler if available."""
    try:
        from memory_profiler import profile as mem_profile
    except ImportError:
        print("memory_profiler not installed. Run: uv add memory-profiler")
        return

    @mem_profile
    def parse_corpus():
        from patitas import Markdown

        md = Markdown()
        docs = get_commonmark_corpus()
        results = []
        for doc in docs:
            result = md(doc)
            results.append(result)
        return results

    print("\nRunning memory_profiler...")
    parse_corpus()


def main() -> None:
    """Run memory profiling."""
    print("Patitas Memory Profiling")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}\n")

    # Basic memory stats
    print("Basic Memory Stats:")
    print("-" * 40)
    basic = measure_memory_basic()
    for key, value in basic.items():
        print(f"  {key}: {value}")

    # Tracemalloc stats
    if TRACEMALLOC_AVAILABLE:
        print("\nTracemalloc Stats:")
        print("-" * 40)
        trace = measure_memory_tracemalloc()
        for key, value in trace.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    # Detailed allocation analysis
    if TRACEMALLOC_AVAILABLE:
        print("\n" + "=" * 60)
        print("TOP 20 MEMORY ALLOCATIONS BY SIZE")
        print("=" * 60 + "\n")

        from patitas import Markdown

        docs = get_commonmark_corpus()

        gc.collect()
        tracemalloc.start()

        md = Markdown()
        for doc in docs:
            md(doc)

        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot.statistics("lineno")[:20]

        for stat in top_stats:
            print(f"  {stat}")

    # Suggest memory_profiler for detailed analysis
    print("\n" + "=" * 60)
    print("For line-by-line memory analysis:")
    print("  uv add memory-profiler")
    print("  uv run python -m memory_profiler benchmarks/memory_bench.py")


if __name__ == "__main__":
    main()
