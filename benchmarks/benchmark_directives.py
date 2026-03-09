"""Benchmark directive-heavy content (admonition, tabs, list-table).

Critical for Bengal SSG which uses many MyST-style directives.

Run with:
    pytest benchmarks/benchmark_directives.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import Markdown, create_registry_with_defaults
    from patitas.directives.decorator import directive
    from patitas.stringbuilder import StringBuilder

    @directive("list-table", preserves_raw_content=True)
    def _render_list_table(node, children: str, sb: StringBuilder) -> None:
        sb.append(node.raw_content or "")

    def _make_markdown_with_list_table() -> Markdown:
        builder = create_registry_with_defaults()
        builder.register(_render_list_table())
        return Markdown(directive_registry=builder.build())

    @pytest.mark.benchmark(group="parse-directives")
    def test_benchmark_directive_heavy(benchmark, directive_heavy_doc):
        """Benchmark parsing document with many admonition, tab-set, dropdown directives."""
        md = Markdown()

        def parse_doc():
            md(directive_heavy_doc)

        benchmark(parse_doc)

    @pytest.mark.benchmark(group="parse-preserves-raw")
    def test_benchmark_preserves_raw_content(benchmark, preserves_raw_content_doc):
        """Benchmark parsing document with list-table (preserves_raw_content=True path)."""
        md = _make_markdown_with_list_table()

        def parse_doc():
            md(preserves_raw_content_doc)

        benchmark(parse_doc)

except ImportError:
    pass  # pytest not available
