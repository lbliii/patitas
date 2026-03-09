"""Benchmark excerpt extraction (meta descriptions, first-line from code blocks).

Exercises the split-first-line path in excerpt.py (FencedCode, IndentedCode).

Run with:
    pytest benchmarks/benchmark_excerpt.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import parse, extract_excerpt

    @pytest.mark.benchmark(group="excerpt")
    def test_benchmark_extract_excerpt_code_heavy(benchmark, doc_with_many_code_blocks):
        """extract_excerpt on doc with many code blocks (split first-line path)."""
        doc = parse(doc_with_many_code_blocks)

        def do_extract():
            extract_excerpt(doc)

        benchmark(do_extract)

    @pytest.mark.benchmark(group="excerpt")
    def test_benchmark_extract_excerpt_commonmark(benchmark, commonmark_corpus):
        """extract_excerpt on CommonMark corpus (parse + extract per doc)."""
        docs = [parse(md) for md in commonmark_corpus]

        def do_extract_all():
            for d in docs:
                extract_excerpt(d)

        benchmark(do_extract_all)

except ImportError:
    pass  # pytest not available
