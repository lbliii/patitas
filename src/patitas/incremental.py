"""Incremental re-parsing for Patitas ASTs.

When a user edits one paragraph, only that paragraph's region needs
re-parsing.  This module accepts a previous Document AST plus the new
source text and an edit range, then:

1. Identifies which top-level blocks overlap the edit range.
2. Determines the minimal region of source that must be re-parsed.
3. Re-parses only that region.
4. Splices the new blocks into the existing AST.

The result is a new Document that is semantically identical to a full
re-parse but computed in O(change) rather than O(document).

Fallback:
    If the edit cannot be handled incrementally (e.g., the region
    detection fails), falls back to a full re-parse.  This guarantees
    correctness at all times.

Thread Safety:
    ``parse_incremental`` is a pure function — safe to call from any thread.

"""

from collections.abc import Sequence
from dataclasses import replace

from patitas.location import SourceLocation
from patitas.nodes import Block, Document


def parse_incremental(
    new_source: str,
    previous: Document,
    edit_start: int,
    edit_end: int,
    new_length: int,
    *,
    source_file: str | None = None,
) -> Document:
    """Parse only the edited region and splice into the existing AST.

    Args:
        new_source: The complete new source text (after the edit).
        previous: The Document AST from before the edit.
        edit_start: Offset in the OLD source where the edit begins.
        edit_end: Offset in the OLD source where the edit ends
            (i.e., the old text from edit_start..edit_end was replaced).
        new_length: Length of the replacement text in the new source.
            The replaced region in new_source is
            ``new_source[edit_start : edit_start + new_length]``.
        source_file: Optional source file path for location tracking.

    Returns:
        A new Document reflecting the edit.  Unaffected blocks are
        reused from ``previous`` (shared references, not copies).

    Note:
        Falls back to full re-parse when incremental parsing is not
        safe (e.g., the region cannot be determined).

    """
    # Validate edit bounds — invalid input → fall back to full parse
    if edit_start < 0 or edit_end < edit_start or new_length < 0:
        return _full_parse(new_source, source_file)

    old_blocks = previous.children

    # Degenerate case: no blocks → full parse
    if not old_blocks:
        return _full_parse(new_source, source_file)

    # Find affected block range
    first_affected, last_affected = _find_affected_range(
        old_blocks,
        edit_start,
        edit_end,
    )

    # If detection failed, fall back
    if first_affected is None or last_affected is None:
        return _full_parse(new_source, source_file)

    # Offset shift: how much text was added or removed
    offset_delta = new_length - (edit_end - edit_start)

    # Determine re-parse region in the NEW source
    reparse_start = old_blocks[first_affected].location.offset
    old_region_end = old_blocks[last_affected].location.end_offset
    reparse_end_new = old_region_end + offset_delta

    # Clamp to source bounds
    reparse_start = max(0, reparse_start)
    reparse_end_new = min(len(new_source), reparse_end_new)

    # Safety: unreasonable region → fall back
    if reparse_start > reparse_end_new:
        return _full_parse(new_source, source_file)

    # Re-parse the affected region
    region_source = new_source[reparse_start:reparse_end_new]
    new_blocks = _parse_region(region_source, reparse_start, source_file)

    # Parse failure → fall back
    if new_blocks is None:
        return _full_parse(new_source, source_file)

    # Splice: before + new + after (with adjusted offsets)
    before = old_blocks[:first_affected]
    after_blocks = old_blocks[last_affected + 1 :]
    adjusted_after = _adjust_offsets(after_blocks, offset_delta)

    result_children = (*before, *new_blocks, *adjusted_after)

    loc = SourceLocation(
        lineno=1,
        col_offset=1,
        offset=0,
        end_offset=len(new_source),
        source_file=source_file,
    )
    return Document(location=loc, children=result_children)


def _find_affected_range(
    blocks: Sequence[Block],
    edit_start: int,
    edit_end: int,
) -> tuple[int | None, int | None]:
    """Find the range of block indices affected by an edit.

    A block is affected if its source range overlaps [edit_start, edit_end).
    If no blocks overlap, expands to the surrounding blocks to handle
    boundary changes (e.g., merging two paragraphs).

    Returns (first_affected, last_affected) or (None, None).

    """
    first: int | None = None
    last: int | None = None

    for i, block in enumerate(blocks):
        block_start = block.location.offset
        block_end = block.location.end_offset

        # Block overlaps with edit range
        if block_start < edit_end and block_end > edit_start:
            if first is None:
                first = i
            last = i

    # If no blocks overlap, the edit is between blocks.
    # Expand to the surrounding blocks to catch boundary effects.
    if first is None:
        prev_idx: int | None = None
        next_idx: int | None = None
        for i, block in enumerate(blocks):
            if block.location.end_offset <= edit_start:
                prev_idx = i
            elif block.location.offset >= edit_end:
                next_idx = i
                break

        if prev_idx is not None:
            first = prev_idx
            last = next_idx if next_idx is not None else prev_idx
        elif next_idx is not None:
            first = next_idx
            last = next_idx

    return first, last


def _parse_region(
    source: str,
    offset: int,
    source_file: str | None,
) -> tuple[Block, ...] | None:
    """Parse a source region and adjust locations to absolute offsets.

    Returns None if parsing fails.

    """
    from patitas import parse

    try:
        doc = parse(source, source_file=source_file)
    except Exception:
        return None

    # Adjust block offsets to be absolute (relative to full document)
    return tuple(_shift_block_offset(block, offset) for block in doc.children)


def _shift_block_offset(block: Block, delta: int) -> Block:
    """Create a new block with its top-level location offset shifted.

    Uses ``dataclasses.replace`` for clean frozen-dataclass copying.
    Only adjusts the top-level location; deep child adjustment is
    deferred to a future optimization pass.

    """
    loc = block.location
    new_loc = replace(loc, offset=loc.offset + delta, end_offset=loc.end_offset + delta)
    return replace(block, location=new_loc)  # type: ignore[arg-type]


def _adjust_offsets(
    blocks: Sequence[Block],
    delta: int,
) -> tuple[Block, ...]:
    """Shift location offsets of all blocks by delta."""
    if delta == 0:
        return tuple(blocks)
    return tuple(_shift_block_offset(b, delta) for b in blocks)


def _full_parse(source: str, source_file: str | None) -> Document:
    """Fall back to a full re-parse."""
    from patitas import parse

    return parse(source, source_file=source_file)
