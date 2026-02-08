"""Tests for patitas.profiling — parse profiling API."""

from patitas import parse
from patitas.profiling import (
    ParseAccumulator,
    get_parse_accumulator,
    profiled_parse,
)


class TestGetParseAccumulator:
    def test_returns_none_when_disabled(self) -> None:
        assert get_parse_accumulator() is None

    def test_returns_none_outside_context(self) -> None:
        with profiled_parse():
            pass
        assert get_parse_accumulator() is None


class TestProfiledParse:
    def test_yields_accumulator(self) -> None:
        with profiled_parse() as acc:
            assert isinstance(acc, ParseAccumulator)

    def test_accumulator_available_inside_context(self) -> None:
        with profiled_parse() as acc:
            assert get_parse_accumulator() is acc

    def test_records_parse_call(self) -> None:
        with profiled_parse() as acc:
            parse("# Hello")
        assert acc.parse_calls == 1
        assert acc.source_length == len("# Hello")
        assert acc.node_count > 0

    def test_records_multiple_parse_calls(self) -> None:
        with profiled_parse() as acc:
            parse("# One")
            parse("# Two")
            parse("# Three")
        assert acc.parse_calls == 3

    def test_total_duration_positive(self) -> None:
        with profiled_parse() as acc:
            parse("# Hello **World**")
        assert acc.total_duration_ms > 0


class TestSummary:
    def test_empty_summary(self) -> None:
        acc = ParseAccumulator()
        summary = acc.summary()
        assert summary["parse_calls"] == 0
        assert summary["source_length"] == 0
        assert summary["node_count"] == 0

    def test_summary_after_parse(self) -> None:
        with profiled_parse() as acc:
            parse("# Hello\n\nWorld")
        summary = acc.summary()
        assert summary["parse_calls"] == 1
        assert summary["source_length"] > 0
        assert "total_ms" in summary
