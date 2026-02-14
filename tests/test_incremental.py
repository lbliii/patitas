"""Tests for patitas.incremental — incremental re-parsing."""

import threading

from patitas import parse
from patitas.incremental import (
    _adjust_offsets,
    _find_affected_range,
    _shift_block_offset,
    parse_incremental,
)
from patitas.location import SourceLocation
from patitas.nodes import Document, Heading, Paragraph, Text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _loc(offset: int, end_offset: int) -> SourceLocation:
    return SourceLocation(lineno=1, col_offset=1, offset=offset, end_offset=end_offset)


def _paragraph(text: str, offset: int, end_offset: int) -> Paragraph:
    loc = _loc(offset, end_offset)
    return Paragraph(location=loc, children=(Text(location=loc, content=text),))


def _heading(text: str, offset: int, end_offset: int, *, level: int = 1) -> Heading:
    loc = _loc(offset, end_offset)
    return Heading(
        location=loc,
        level=level,  # type: ignore[arg-type]
        children=(Text(location=loc, content=text),),
    )


def _doc(*children: object) -> Document:
    end = (
        max(c.location.end_offset for c in children)  # type: ignore[union-attr]
        if children
        else 0
    )
    return Document(
        location=SourceLocation(lineno=1, col_offset=1, offset=0, end_offset=end),
        children=tuple(children),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# _find_affected_range
# ---------------------------------------------------------------------------


class TestFindAffectedRange:
    """Tests for _find_affected_range — identifies which blocks overlap an edit."""

    def test_edit_inside_single_block(self) -> None:
        blocks = (
            _paragraph("aaa", 0, 10),
            _paragraph("bbb", 15, 25),
            _paragraph("ccc", 30, 40),
        )
        first, last = _find_affected_range(blocks, 16, 20)
        assert first == 1
        assert last == 1

    def test_edit_spanning_two_blocks(self) -> None:
        blocks = (
            _paragraph("aaa", 0, 10),
            _paragraph("bbb", 15, 25),
            _paragraph("ccc", 30, 40),
        )
        first, last = _find_affected_range(blocks, 8, 18)
        assert first == 0
        assert last == 1

    def test_edit_spanning_all_blocks(self) -> None:
        blocks = (
            _paragraph("aaa", 0, 10),
            _paragraph("bbb", 15, 25),
        )
        first, last = _find_affected_range(blocks, 0, 30)
        assert first == 0
        assert last == 1

    def test_edit_between_blocks_expands_to_neighbors(self) -> None:
        blocks = (
            _paragraph("aaa", 0, 10),
            _paragraph("bbb", 20, 30),
        )
        # Edit is in the gap (10..20)
        first, last = _find_affected_range(blocks, 12, 14)
        assert first == 0
        assert last == 1

    def test_edit_after_all_blocks(self) -> None:
        blocks = (_paragraph("aaa", 0, 10),)
        first, last = _find_affected_range(blocks, 15, 18)
        assert first == 0
        assert last == 0

    def test_edit_before_all_blocks(self) -> None:
        blocks = (_paragraph("aaa", 10, 20),)
        first, last = _find_affected_range(blocks, 2, 5)
        assert first == 0
        assert last == 0

    def test_empty_blocks(self) -> None:
        first, last = _find_affected_range((), 0, 5)
        assert first is None
        assert last is None


# ---------------------------------------------------------------------------
# _shift_block_offset / _adjust_offsets
# ---------------------------------------------------------------------------


class TestShiftBlockOffset:
    """Tests for location offset shifting on frozen nodes."""

    def test_positive_delta(self) -> None:
        block = _paragraph("hello", 10, 20)
        shifted = _shift_block_offset(block, 5)
        assert shifted.location.offset == 15
        assert shifted.location.end_offset == 25
        # Content unchanged
        assert isinstance(shifted, Paragraph)
        assert shifted.children[0].content == "hello"

    def test_negative_delta(self) -> None:
        block = _paragraph("hello", 20, 30)
        shifted = _shift_block_offset(block, -5)
        assert shifted.location.offset == 15
        assert shifted.location.end_offset == 25

    def test_zero_delta_returns_equal(self) -> None:
        block = _paragraph("hello", 10, 20)
        shifted = _shift_block_offset(block, 0)
        assert shifted.location.offset == 10
        assert shifted.location.end_offset == 20

    def test_adjust_offsets_zero_delta_returns_tuple(self) -> None:
        blocks = (_paragraph("a", 0, 5), _paragraph("b", 10, 15))
        result = _adjust_offsets(blocks, 0)
        assert result == blocks

    def test_adjust_offsets_positive(self) -> None:
        blocks = (_paragraph("a", 10, 15), _paragraph("b", 20, 25))
        result = _adjust_offsets(blocks, 3)
        assert result[0].location.offset == 13
        assert result[0].location.end_offset == 18
        assert result[1].location.offset == 23
        assert result[1].location.end_offset == 28


# ---------------------------------------------------------------------------
# parse_incremental — integration tests using real parsing
# ---------------------------------------------------------------------------


class TestParseIncremental:
    """Integration tests that compare incremental results to full re-parse."""

    def test_modify_middle_paragraph(self) -> None:
        old_source = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n"
        new_source = "# Title\n\nFirst paragraph.\n\nModified paragraph.\n\nThird paragraph.\n"

        old_doc = parse(old_source)
        edit_start = old_source.index("Second")
        edit_end = edit_start + len("Second paragraph.")
        new_length = len("Modified paragraph.")

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        # Compare to full parse
        full = parse(new_source)

        assert isinstance(result, Document)
        assert len(result.children) == len(full.children)

    def test_insert_text_in_paragraph(self) -> None:
        old_source = "Hello world.\n"
        new_source = "Hello beautiful world.\n"

        old_doc = parse(old_source)
        edit_start = 6  # after "Hello "
        edit_end = 6  # insertion (no old text removed)
        new_length = len("beautiful ")

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        full = parse(new_source)
        assert len(result.children) == len(full.children)

    def test_delete_paragraph(self) -> None:
        old_source = "First.\n\nSecond.\n\nThird.\n"
        # Remove "Second.\n\n"
        new_source = "First.\n\nThird.\n"

        old_doc = parse(old_source)
        edit_start = old_source.index("Second")
        edit_end = old_source.index("Third")
        new_length = 0  # deletion

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        full = parse(new_source)
        assert len(result.children) == len(full.children)

    def test_invalid_edit_bounds_falls_back_to_full_parse(self) -> None:
        """Invalid edit_start/edit_end/new_length → full re-parse."""
        source = "Hello world.\n"
        doc = parse(source)
        # edit_start > edit_end, negative new_length, etc. → fallback
        result = parse_incremental(source, doc, 5, 3, 0)  # invalid: start > end
        assert len(result.children) == len(doc.children)
        result = parse_incremental(source, doc, -1, 5, 0)  # invalid: negative start
        assert len(result.children) == len(doc.children)

    def test_empty_previous_falls_back_to_full_parse(self) -> None:
        new_source = "Hello world.\n"
        empty = Document(
            location=SourceLocation(lineno=1, col_offset=1, offset=0, end_offset=0),
            children=(),
        )

        result = parse_incremental(new_source, empty, 0, 0, len(new_source))
        full = parse(new_source)
        assert len(result.children) == len(full.children)

    def test_append_new_paragraph_at_end(self) -> None:
        old_source = "First.\n"
        new_source = "First.\n\nAdded.\n"

        old_doc = parse(old_source)
        edit_start = len(old_source)
        edit_end = len(old_source)
        new_length = len("\nAdded.\n")

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        full = parse(new_source)
        assert len(result.children) == len(full.children)

    def test_modify_heading(self) -> None:
        old_source = "# Old Title\n\nContent.\n"
        new_source = "# New Title\n\nContent.\n"

        old_doc = parse(old_source)
        edit_start = 2  # after "# "
        edit_end = 2 + len("Old Title")
        new_length = len("New Title")

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        full = parse(new_source)
        assert len(result.children) == len(full.children)

    def test_source_file_propagated(self) -> None:
        old_source = "Hello.\n"
        new_source = "World.\n"

        old_doc = parse(old_source, source_file="test.md")

        result = parse_incremental(
            new_source,
            old_doc,
            0,
            len(old_source),
            len(new_source),
            source_file="test.md",
        )
        assert result.location.source_file == "test.md"

    def test_result_is_valid_document(self) -> None:
        old_source = "A.\n\nB.\n\nC.\n"
        new_source = "A.\n\nX.\n\nC.\n"

        old_doc = parse(old_source)
        edit_start = old_source.index("B")
        edit_end = edit_start + 1
        new_length = 1  # replace "B" with "X"

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        assert isinstance(result, Document)
        assert result.location.offset == 0
        assert result.location.end_offset == len(new_source)

    def test_preserves_unaffected_blocks(self) -> None:
        """Blocks before the edit should be reused (same object identity)."""
        old_source = "# Title\n\nFirst.\n\nSecond.\n"
        new_source = "# Title\n\nFirst.\n\nChanged.\n"

        old_doc = parse(old_source)
        edit_start = old_source.index("Second")
        edit_end = edit_start + len("Second.")
        new_length = len("Changed.")

        result = parse_incremental(
            new_source,
            old_doc,
            edit_start,
            edit_end,
            new_length,
        )

        # First two blocks (heading and first paragraph) should be reused
        assert result.children[0] is old_doc.children[0]
        assert result.children[1] is old_doc.children[1]


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestIncrementalThreadSafety:
    """Verify parse_incremental is safe to call from multiple threads."""

    def test_concurrent_incremental_parses(self) -> None:
        base = "# Title\n\nParagraph one.\n\nParagraph two.\n"
        old_doc = parse(base)
        results: list[Document | None] = [None] * 10
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                new_text = f"Modified {idx}."
                new_source = f"# Title\n\nParagraph one.\n\n{new_text}\n"
                edit_start = base.index("Paragraph two")
                edit_end = edit_start + len("Paragraph two.")
                new_length = len(new_text)

                result = parse_incremental(
                    new_source,
                    old_doc,
                    edit_start,
                    edit_end,
                    new_length,
                )
                results[idx] = result
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors in threads: {errors}"
        for i, r in enumerate(results):
            assert r is not None, f"Thread {i} produced no result"
            assert isinstance(r, Document)
            assert len(r.children) >= 2
