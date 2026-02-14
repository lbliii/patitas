"""Benchmark Patitas against mistune.

Run with:
    pytest benchmarks/benchmark_vs_mistune.py -v --benchmark-only

Or for quick comparison:
    python benchmarks/benchmark_vs_mistune.py
"""

import json
import time
from pathlib import Path


def get_commonmark_corpus() -> list[str]:
    """Load CommonMark spec examples."""
    spec_file = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    if not spec_file.exists():
        raise FileNotFoundError(f"CommonMark spec not found: {spec_file}")
    examples = json.loads(spec_file.read_text())
    return [ex["markdown"] for ex in examples]


def benchmark_patitas(docs: list[str], iterations: int = 10) -> float:
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

    return elapsed / iterations


def benchmark_mistune(docs: list[str], iterations: int = 10) -> float:
    """Benchmark mistune parser."""
    try:
        import mistune
    except ImportError:
        print("mistune not installed. Run: pip install mistune")
        return float("inf")

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

    return elapsed / iterations


def benchmark_markdown_it(docs: list[str], iterations: int = 10) -> float:
    """Benchmark markdown-it-py parser."""
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        print("markdown-it-py not installed. Run: pip install markdown-it-py")
        return float("inf")

    md = MarkdownIt()

    # Warmup
    for doc in docs[:10]:
        md.render(doc)

    # Timed runs
    start = time.perf_counter()
    for _ in range(iterations):
        for doc in docs:
            md.render(doc)
    elapsed = time.perf_counter() - start

    return elapsed / iterations


def benchmark_threaded(
    name: str,
    make_parser,
    docs: list[str],
    num_threads: int = 4,
    iterations: int = 5,
) -> float | None:
    """Benchmark parser with multiple threads (Python 3.14t free-threading)."""
    import concurrent.futures
    import sys

    # Check if free-threading is available
    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    if gil_enabled:
        return None  # Skip threaded benchmark if GIL is enabled

    parsers = [make_parser() for _ in range(num_threads)]
    chunks = [docs[i::num_threads] for i in range(num_threads)]

    def work(args: tuple[int, list[str]]) -> None:
        idx, chunk = args
        parser = parsers[idx]
        for d in chunk:
            parser(d)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
            list(ex.map(work, enumerate(chunks)))
        times.append(time.perf_counter() - start)

    return sum(times) / len(times)


def main() -> None:
    """Run benchmarks and print results."""
    import sys

    print("Loading CommonMark corpus (652 examples)...")
    docs = get_commonmark_corpus()
    print(f"Loaded {len(docs)} documents")
    print(f"Python {sys.version.split()[0]}")

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"GIL enabled: {gil_enabled}\n")

    iterations = 10
    print(f"Running {iterations} iterations each...\n")

    # Run benchmarks
    print("Benchmarking Patitas...")
    patitas_time = benchmark_patitas(docs, iterations)

    print("Benchmarking mistune...")
    mistune_time = benchmark_mistune(docs, iterations)

    print("Benchmarking markdown-it-py...")
    markdown_it_time = benchmark_markdown_it(docs, iterations)

    # Results
    print("\n" + "=" * 60)
    print("RESULTS: Parse 652 CommonMark examples (single thread)")
    print("=" * 60)

    results = [
        ("Patitas", patitas_time),
        ("mistune", mistune_time),
        ("markdown-it-py", markdown_it_time),
    ]

    # Sort by time
    results.sort(key=lambda x: x[1])
    baseline = results[0][1]

    for name, time_val in results:
        if time_val == float("inf"):
            print(f"{name:20} not installed")
        else:
            ratio = time_val / baseline if baseline > 0 else 0
            ms = time_val * 1000
            print(f"{name:20} {ms:8.2f}ms  ({ratio:.2f}x)")

    # Multi-threaded benchmarks (Python 3.14t only)
    if not gil_enabled:
        print("\n" + "=" * 60)
        print("RESULTS: Parse 652 CommonMark examples (4 threads)")
        print("=" * 60)

        import mistune

        from patitas import Markdown

        patitas_threaded = benchmark_threaded("Patitas", Markdown, docs)
        mistune_threaded = benchmark_threaded("mistune", mistune.create_markdown, docs)

        # markdown-it-py crashes under free-threading
        try:
            from markdown_it import MarkdownIt

            mdit_threaded = benchmark_threaded("markdown-it-py", MarkdownIt, docs)
        except Exception:
            mdit_threaded = None

        if patitas_threaded:
            speedup = patitas_time / patitas_threaded
            print(f"{'Patitas':20} {patitas_threaded * 1000:8.2f}ms  (speedup: {speedup:.1f}x)")
        if mistune_threaded:
            speedup = mistune_time / mistune_threaded
            print(f"{'mistune':20} {mistune_threaded * 1000:8.2f}ms  (speedup: {speedup:.1f}x)")
        if mdit_threaded:
            print(f"{'markdown-it-py':20} {mdit_threaded * 1000:8.2f}ms")
        else:
            print(f"{'markdown-it-py':20} CRASH (not thread-safe)")

    print()

    # Patitas vs mistune comparison
    if mistune_time != float("inf") and patitas_time < mistune_time:
        improvement = ((mistune_time - patitas_time) / mistune_time) * 100
        print(f"✅ Patitas is {improvement:.0f}% faster than mistune")
    elif mistune_time != float("inf"):
        slower = ((patitas_time - mistune_time) / mistune_time) * 100
        print(f"⚠️  Patitas is {slower:.0f}% slower than mistune")

    print("\nNote: Patitas prioritizes safety (O(n) guarantee, typed AST) over raw speed.")


# pytest-benchmark integration
try:
    import pytest

    @pytest.mark.benchmark(group="parse-corpus")
    def test_benchmark_patitas(benchmark, commonmark_corpus):
        """Benchmark Patitas on CommonMark corpus."""
        from patitas import Markdown

        md = Markdown()

        def parse_all():
            for doc in commonmark_corpus:
                md(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-corpus")
    def test_benchmark_mistune(benchmark, commonmark_corpus):
        """Benchmark mistune on CommonMark corpus."""
        try:
            import mistune
        except ImportError:
            pytest.skip("mistune not installed")

        md = mistune.create_markdown()

        def parse_all():
            for doc in commonmark_corpus:
                md(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-corpus")
    def test_benchmark_markdown_it(benchmark, commonmark_corpus):
        """Benchmark markdown-it-py on CommonMark corpus."""
        try:
            from markdown_it import MarkdownIt
        except ImportError:
            pytest.skip("markdown-it-py not installed")

        md = MarkdownIt()

        def parse_all():
            for doc in commonmark_corpus:
                md.render(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-large-doc")
    def test_benchmark_patitas_large_document(benchmark, large_document):
        """Benchmark Patitas on ~100KB document with tables."""
        from patitas import Markdown

        md = Markdown(plugins=["table"])

        def parse_doc():
            md(large_document)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-large-doc")
    def test_benchmark_mistune_large_document(benchmark, large_document):
        """Benchmark mistune on ~100KB document."""
        try:
            import mistune
        except ImportError:
            pytest.skip("mistune not installed")

        md = mistune.create_markdown()

        def parse_doc():
            md(large_document)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-real-world")
    def test_benchmark_patitas_real_world(benchmark, real_world_docs):
        """Benchmark Patitas on real-world document patterns."""
        from patitas import Markdown

        md = Markdown(plugins=["table", "autolinks"])

        def parse_all():
            for doc in real_world_docs:
                md(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-real-world")
    def test_benchmark_mistune_real_world(benchmark, real_world_docs):
        """Benchmark mistune on real-world document patterns."""
        try:
            import mistune
        except ImportError:
            pytest.skip("mistune not installed")

        md = mistune.create_markdown()

        def parse_all():
            for doc in real_world_docs:
                md(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-only")
    def test_benchmark_patitas_parse_only(benchmark, commonmark_corpus):
        """Benchmark Patitas parse() only, no render."""
        from patitas import parse

        def parse_all():
            for doc in commonmark_corpus:
                parse(doc)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="render-only")
    def test_benchmark_patitas_render_only(benchmark, commonmark_corpus):
        """Benchmark Patitas render() only on pre-parsed docs."""
        from patitas import parse, render

        docs = [parse(doc) for doc in commonmark_corpus]

        def render_all():
            for doc in docs:
                render(doc)

        benchmark(render_all)

    @pytest.mark.benchmark(group="parse-plugins")
    def test_benchmark_patitas_plugins_all(benchmark, plugin_heavy_doc):
        """Benchmark Patitas with all plugins enabled."""
        from patitas import Markdown

        md = Markdown(plugins=["all"])

        def parse_doc():
            md(plugin_heavy_doc)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-plugins")
    def test_benchmark_mistune_plugins(benchmark, plugin_heavy_doc):
        """Benchmark mistune on plugin-heavy document."""
        try:
            import mistune
        except ImportError:
            pytest.skip("mistune not installed")

        md = mistune.create_markdown()

        def parse_doc():
            md(plugin_heavy_doc)

        benchmark(parse_doc)

except ImportError:
    pass  # pytest not available


if __name__ == "__main__":
    main()
