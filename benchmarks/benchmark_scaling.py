"""Benchmark parse time vs document size (O(n) scaling validation).

Validates that parsing scales linearly with input size and catches regressions
in preserves_raw_content path for large documents.

Run with:
    pytest benchmarks/benchmark_scaling.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import Markdown, create_registry_with_defaults
    from patitas.directives.decorator import directive
    from patitas.stringbuilder import StringBuilder

    @directive("list-table", preserves_raw_content=True)
    def _render_list_table(node, children: str, sb: StringBuilder) -> None:
        sb.append(node.raw_content or "")

    def _md_with_list_table():
        builder = create_registry_with_defaults()
        builder.register(_render_list_table())
        return Markdown(plugins=["table"], directive_registry=builder.build())

    @pytest.mark.benchmark(group="parse-scaling")
    def test_benchmark_parse_10kb(benchmark, doc_10kb):
        """Benchmark parse of ~10KB document."""
        md = Markdown(plugins=["table"])

        def parse_doc():
            md(doc_10kb)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-scaling")
    def test_benchmark_parse_100kb(benchmark, doc_100kb):
        """Benchmark parse of ~100KB document."""
        md = Markdown(plugins=["table"])

        def parse_doc():
            md(doc_100kb)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-scaling")
    def test_benchmark_parse_500kb(benchmark, doc_500kb):
        """Benchmark parse of ~500KB document."""
        md = Markdown(plugins=["table"])

        def parse_doc():
            md(doc_500kb)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-scaling-list-table")
    def test_benchmark_parse_list_table_50kb(benchmark, list_table_doc_50kb):
        """Benchmark parse of ~50KB list-table doc (preserves_raw_content path)."""
        md = _md_with_list_table()

        def parse_doc():
            md(list_table_doc_50kb)

        benchmark(parse_doc)

except ImportError:
    pass  # pytest not available
