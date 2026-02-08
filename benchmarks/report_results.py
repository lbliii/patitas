"""Generate benchmark reports in JSON and Markdown format.

Run with:
    uv run python benchmarks/report_results.py

Outputs:
    benchmarks/results/latest.json
    benchmarks/results/latest.md
"""

import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class BenchmarkResult:
    """Single benchmark measurement."""

    name: str
    time_ms: float
    iterations: int
    docs_count: int
    ms_per_doc: float


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    timestamp: str
    python_version: str
    platform: str
    gil_enabled: bool
    patitas_version: str
    results: list[BenchmarkResult]
    summary: dict[str, float]


def get_commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec_file = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")
    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


def benchmark_patitas(docs: list[str], iterations: int = 10) -> BenchmarkResult:
    """Benchmark Patitas parser."""
    from patitas import Markdown

    md = Markdown()

    # Warmup
    for doc in docs[:10]:
        md(doc)

    # Timed runs
    start = time.perf_counter()
    for _ in range(iterations):
        for doc in docs:
            md(doc)
    elapsed = time.perf_counter() - start

    iterations * len(docs)
    avg_time = elapsed / iterations

    return BenchmarkResult(
        name="patitas",
        time_ms=avg_time * 1000,
        iterations=iterations,
        docs_count=len(docs),
        ms_per_doc=(avg_time * 1000) / len(docs),
    )


def benchmark_mistune(docs: list[str], iterations: int = 10) -> BenchmarkResult | None:
    """Benchmark mistune parser."""
    try:
        import mistune
    except ImportError:
        return None

    md = mistune.create_markdown()

    # Warmup
    for doc in docs[:10]:
        md(doc)

    # Timed runs
    start = time.perf_counter()
    for _ in range(iterations):
        for doc in docs:
            md(doc)
    elapsed = time.perf_counter() - start

    avg_time = elapsed / iterations

    return BenchmarkResult(
        name="mistune",
        time_ms=avg_time * 1000,
        iterations=iterations,
        docs_count=len(docs),
        ms_per_doc=(avg_time * 1000) / len(docs),
    )


def get_patitas_version() -> str:
    """Get Patitas version string."""
    try:
        from patitas import __version__

        return __version__
    except ImportError:
        return "unknown"


def generate_report(results: list[BenchmarkResult]) -> BenchmarkReport:
    """Generate a complete benchmark report."""
    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()

    # Calculate summary stats
    patitas_result = next((r for r in results if r.name == "patitas"), None)
    mistune_result = next((r for r in results if r.name == "mistune"), None)

    summary: dict[str, float] = {}
    if patitas_result:
        summary["patitas_ms"] = patitas_result.time_ms
        summary["patitas_ms_per_doc"] = patitas_result.ms_per_doc
    if mistune_result:
        summary["mistune_ms"] = mistune_result.time_ms
        summary["mistune_ms_per_doc"] = mistune_result.ms_per_doc
    if patitas_result and mistune_result:
        ratio = patitas_result.time_ms / mistune_result.time_ms
        summary["patitas_vs_mistune_ratio"] = ratio
        summary["patitas_slower_percent"] = (ratio - 1) * 100

    return BenchmarkReport(
        timestamp=datetime.now(UTC).isoformat(),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        gil_enabled=gil_enabled,
        patitas_version=get_patitas_version(),
        results=results,
        summary=summary,
    )


def save_json(report: BenchmarkReport, path: Path) -> None:
    """Save report as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": report.timestamp,
        "python_version": report.python_version,
        "platform": report.platform,
        "gil_enabled": report.gil_enabled,
        "patitas_version": report.patitas_version,
        "results": [asdict(r) for r in report.results],
        "summary": report.summary,
    }

    path.write_text(json.dumps(data, indent=2))
    print(f"Saved JSON report: {path}")


def save_markdown(report: BenchmarkReport, path: Path) -> None:
    """Save report as Markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Patitas Benchmark Results",
        "",
        f"**Generated**: {report.timestamp}",
        f"**Python**: {report.python_version}",
        f"**Platform**: {report.platform}",
        f"**GIL Enabled**: {report.gil_enabled}",
        f"**Patitas Version**: {report.patitas_version}",
        "",
        "## Results",
        "",
        "| Parser | Time (ms) | ms/doc | vs. Baseline |",
        "|--------|-----------|--------|--------------|",
    ]

    # Find baseline (mistune if available, else first result)
    baseline = next((r for r in report.results if r.name == "mistune"), report.results[0])

    for r in report.results:
        ratio = r.time_ms / baseline.time_ms if baseline.time_ms > 0 else 1.0
        lines.append(f"| {r.name} | {r.time_ms:.2f} | {r.ms_per_doc:.4f} | {ratio:.2f}x |")

    lines.extend(
        [
            "",
            "## Summary",
            "",
        ]
    )

    if "patitas_slower_percent" in report.summary:
        pct = report.summary["patitas_slower_percent"]
        if pct > 0:
            lines.append(f"- Patitas is **{pct:.0f}% slower** than mistune")
        else:
            lines.append(f"- Patitas is **{-pct:.0f}% faster** than mistune")

    lines.extend(
        [
            "",
            "---",
            "",
            "*Note: Patitas prioritizes safety (O(n) guarantee, typed AST) over raw speed.*",
        ]
    )

    path.write_text("\n".join(lines))
    print(f"Saved Markdown report: {path}")


def main() -> None:
    """Run benchmarks and generate reports."""
    print("Patitas Benchmark Report Generator")
    print("=" * 60)
    print(f"Python {sys.version.split()[0]}\n")

    print("Loading CommonMark corpus...")
    docs = get_commonmark_corpus()
    print(f"Loaded {len(docs)} documents\n")

    iterations = 10
    print(f"Running {iterations} iterations each...\n")

    results: list[BenchmarkResult] = []

    # Benchmark Patitas
    print("Benchmarking Patitas...")
    patitas_result = benchmark_patitas(docs, iterations)
    results.append(patitas_result)
    print(f"  Patitas: {patitas_result.time_ms:.2f}ms")

    # Benchmark mistune (if available)
    print("Benchmarking mistune...")
    mistune_result = benchmark_mistune(docs, iterations)
    if mistune_result:
        results.append(mistune_result)
        print(f"  mistune: {mistune_result.time_ms:.2f}ms")
    else:
        print("  mistune not installed")

    # Generate report
    print("\nGenerating report...")
    report = generate_report(results)

    # Save reports
    results_dir = Path(__file__).parent / "results"
    save_json(report, results_dir / "latest.json")
    save_markdown(report, results_dir / "latest.md")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if "patitas_slower_percent" in report.summary:
        pct = report.summary["patitas_slower_percent"]
        if pct > 0:
            print(f"\n⚠️  Patitas is {pct:.0f}% slower than mistune")
        else:
            print(f"\n✅ Patitas is {-pct:.0f}% faster than mistune")

    print(f"\nReports saved to: {results_dir}/")


if __name__ == "__main__":
    main()
