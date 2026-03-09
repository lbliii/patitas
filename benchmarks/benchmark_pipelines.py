"""Benchmark pipeline operations: render_llm, parse_frontmatter, sanitize.

Covers RAG/LLM workflows and SSG frontmatter parsing.

Run with:
    pytest benchmarks/benchmark_pipelines.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import parse, parse_frontmatter, render_llm, sanitize
    from patitas.sanitize import llm_safe

    @pytest.mark.benchmark(group="render-llm")
    def test_benchmark_render_llm(benchmark, commonmark_corpus):
        """Benchmark render_llm on pre-parsed docs (LLM output path)."""
        docs = [parse(doc) for doc in commonmark_corpus]

        def render_all():
            for doc in docs:
                render_llm(doc)

        benchmark(render_all)

    @pytest.mark.benchmark(group="parse-frontmatter")
    def test_benchmark_parse_frontmatter(benchmark, frontmatter_docs):
        """Benchmark parse_frontmatter on docs with YAML frontmatter."""

        def parse_all():
            for content in frontmatter_docs:
                parse_frontmatter(content)

        benchmark(parse_all)

    @pytest.mark.benchmark(group="parse-sanitize-render-llm")
    def test_benchmark_llm_pipeline(benchmark, commonmark_corpus):
        """Benchmark full RAG pipeline: parse -> sanitize -> render_llm."""

        def pipeline():
            for content in commonmark_corpus:
                doc = parse(content)
                clean = sanitize(doc, policy=llm_safe)
                render_llm(clean)

        benchmark(pipeline)

except ImportError:
    pass  # pytest not available
