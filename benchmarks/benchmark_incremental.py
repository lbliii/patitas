"""Benchmark incremental parsing vs full parse.

Compares parse_incremental (O(change)) vs full parse for small edits
in a large document.

Run with:
    pytest benchmarks/benchmark_incremental.py -v --benchmark-only
"""

try:
    import pytest

    from patitas import parse
    from patitas.incremental import parse_incremental

    @pytest.mark.benchmark(group="parse-incremental")
    def test_benchmark_parse_incremental_small_edit(benchmark, large_document):
        """Benchmark parse_incremental for a 1-char edit in large doc."""
        previous = parse(large_document)
        edit_offset = min(5000, len(large_document) - 1)
        new_source = (
            large_document[:edit_offset]
            + "x"
            + large_document[edit_offset + 1 :]
        )
        edit_start = edit_offset
        edit_end = edit_offset + 1
        new_length = 1

        def incremental_parse():
            parse_incremental(
                new_source,
                previous,
                edit_start,
                edit_end,
                new_length,
            )

        benchmark(incremental_parse)

    @pytest.mark.benchmark(group="parse-incremental")
    def test_benchmark_full_parse(benchmark, large_document):
        """Benchmark full parse of large doc (baseline for ratio)."""
        # Use same edited doc as incremental for fair comparison
        edit_offset = min(5000, len(large_document) - 1)
        new_source = (
            large_document[:edit_offset]
            + "x"
            + large_document[edit_offset + 1 :]
        )

        def full_parse():
            parse(new_source)

        benchmark(full_parse)

except ImportError:
    pass  # pytest not available
