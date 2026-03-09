"""Benchmark parse vs render phase breakdown.

Measures where time is spent: lex+parse vs render. Useful for identifying
whether optimizations should target parsing or rendering.

Run with:
    pytest benchmarks/benchmark_phase_breakdown.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import Markdown

    @pytest.mark.benchmark(group="phase-breakdown")
    def test_benchmark_parse_only_10kb(benchmark, doc_10kb):
        """Parse-only (lex+parse) for ~10KB doc."""
        md = Markdown(plugins=["table"])

        def do_parse():
            md.parse(doc_10kb)

        benchmark(do_parse)

    @pytest.mark.benchmark(group="phase-breakdown")
    def test_benchmark_render_only_10kb(benchmark, doc_10kb):
        """Render-only for pre-parsed ~10KB doc."""
        md = Markdown(plugins=["table"])
        doc = md.parse(doc_10kb)

        def do_render():
            md.render(doc, source=doc_10kb)

        benchmark(do_render)

    @pytest.mark.benchmark(group="phase-breakdown")
    def test_benchmark_full_pipeline_10kb(benchmark, doc_10kb):
        """Full pipeline (parse + render) for ~10KB doc."""
        md = Markdown(plugins=["table"])

        def do_full():
            doc = md.parse(doc_10kb)
            md.render(doc, source=doc_10kb)

        benchmark(do_full)

    @pytest.mark.benchmark(group="phase-breakdown")
    def test_benchmark_parse_only_500kb(benchmark, doc_500kb):
        """Parse-only (lex+parse) for ~500KB doc."""
        md = Markdown(plugins=["table"])

        def do_parse():
            md.parse(doc_500kb)

        benchmark(do_parse)

    @pytest.mark.benchmark(group="phase-breakdown")
    def test_benchmark_render_only_500kb(benchmark, doc_500kb):
        """Render-only for pre-parsed ~500KB doc."""
        md = Markdown(plugins=["table"])
        doc = md.parse(doc_500kb)

        def do_render():
            md.render(doc, source=doc_500kb)

        benchmark(do_render)

except ImportError:
    pass  # pytest not available
