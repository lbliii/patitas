"""Parallel parsing benchmark for free-threading visibility.

Run with:
    python benchmarks/benchmark_parallel.py

Demonstrates near-linear thread scaling when parsing many documents in parallel
under Python 3.14t free-threading. Uses stdlib only (concurrent.futures, time, sys).
"""

import argparse
import json
import os
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def collect_env() -> dict[str, object]:
    """Capture the machine/runtime context needed to interpret a scaling run."""
    return {
        "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count() or 1,
    }


def get_commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec_file = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")
    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


def parse_doc(source: str):
    """Parse a single document (used by executor.map)."""
    from patitas import parse

    return parse(source)


def run_parallel_benchmark(docs: list[str], num_threads: int, iterations: int = 5) -> float:
    """Parse docs across num_threads, return mean wall-clock time in seconds."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_threads) as ex:
            list(ex.map(parse_doc, docs))
        times.append(time.perf_counter() - start)
    return sum(times) / len(times)


def main() -> None:
    """Run parallel parsing benchmark, print results, and optionally write JSON."""
    parser = argparse.ArgumentParser(description="Parallel parsing scaling benchmark.")
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write machine-readable results (env header + per-thread speedup) to PATH.",
    )
    args = parser.parse_args()

    from patitas import parse

    env = collect_env()
    if env["gil_enabled"]:
        print("Free-threaded build: No (GIL enabled)")
        print("\nRun with Python 3.14t (free-threading) to see parallel scaling.")
        print("Example: python3.14t benchmarks/benchmark_parallel.py")
    else:
        print(f"Free-threaded build: Yes ({env['python_version']})")

    # Load corpus; repeat to reach 1000 docs for scaling demo
    print("\nLoading CommonMark corpus...")
    all_docs = get_commonmark_corpus()
    n_docs = 1000
    docs = (all_docs * ((n_docs // len(all_docs)) + 1))[:n_docs]
    print(f"Using {n_docs} documents\n")

    print(f"Parallel parsing benchmark: {n_docs} documents\n")

    # Warmup
    for doc in docs[:10]:
        parse(doc)

    # Benchmark across thread counts
    results: list[tuple[int, float, float]] = []
    baseline_time: float | None = None

    for num_threads in [1, 2, 4, 8]:
        elapsed = run_parallel_benchmark(docs, num_threads)
        if baseline_time is None:
            baseline_time = elapsed
        speedup = baseline_time / elapsed
        results.append((num_threads, elapsed, speedup))

    # Print table
    print("  Threads    Time      Speedup")
    for num_threads, elapsed, speedup in results:
        print(f"  {num_threads:<10} {elapsed:.2f}s     {speedup:.2f}x")
    print()

    if args.json is not None:
        max_speedup = max((s for _, _, s in results), default=1.0)
        payload = {
            "env": env,
            "n_docs": n_docs,
            "results": [{"threads": t, "time_s": e, "speedup": s} for t, e, s in results],
            "max_speedup": max_speedup,
        }
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"Wrote scaling results to {args.json}")


if __name__ == "__main__":
    main()
