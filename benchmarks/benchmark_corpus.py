"""Corpus benchmarks split into spec-edge-cases vs real-world groups.

The CommonMark spec corpus is adversarial by design (tiny, edge-case-dense
examples), which understates throughput on ordinary prose. These benchmarks
separate the two so each can be tracked — and compared to other parsers — on its
own terms.

Run with:
    pytest benchmarks/benchmark_corpus.py -v --benchmark-only
"""

import pytest

from patitas import Markdown


@pytest.mark.benchmark(group="spec-edge-cases")
def test_benchmark_spec_edge_cases(benchmark, commonmark_corpus):
    """Throughput on the adversarial CommonMark spec corpus (edge cases)."""
    md = Markdown()

    def run():
        for doc in commonmark_corpus:
            md(doc)

    benchmark(run)


@pytest.mark.benchmark(group="real-world")
def test_benchmark_real_world(benchmark, real_world_corpus):
    """Throughput on representative real-world docs (README, guide, changelog)."""
    md = Markdown(plugins=["table"])

    def run():
        for doc in real_world_corpus:
            md(doc)

    benchmark(run)


@pytest.mark.benchmark(group="real-world")
def test_benchmark_real_world_parse_only(benchmark, real_world_corpus):
    """Parse-only (AST, no render) throughput on real-world docs."""
    md = Markdown(plugins=["table"])

    def run():
        for doc in real_world_corpus:
            md.parse(doc)

    benchmark(run)
