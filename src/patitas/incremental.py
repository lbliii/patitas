"""Incremental re-parsing for Patitas ASTs.

When a user edits one paragraph, only that paragraph's region needs
re-parsing.  This module accepts a previous Document AST plus the new
source text and an edit range, then:

1. Identifies which top-level blocks overlap the edit range.
2. Determines the minimal region of source that must be re-parsed.
3. Re-parses only that region.
4. Splices the new blocks into the existing AST.

The result is a new Document that is structurally and offset-wise
equivalent to a full re-parse, computed in O(change) rather than
O(document).  Re-parsed blocks have their full node tree (the top-level
block ``location`` *and* every descendant inline/nested ``location``,
plus ``FencedCode`` ``source_start``/``source_end``) shifted to absolute
offsets, and blocks after the edit are shifted by the edit delta.  This
keeps source maps, LSP positions, and diagnostics accurate without a
full re-parse.

Custom registries:
    ``parse_incremental`` accepts ``directive_registry`` so the re-parsed
    region honors custom directives exactly like ``parse()``.  Inline
    roles are resolved at *render* time, not parse time, so there is no
    parse-time role registry -- this mirrors ``parse()``'s own signature.

Fallback:
    If the edit cannot be handled incrementally (e.g., the region
    detection fails or the partial re-parse raises), falls back to a
    full re-parse.  This guarantees correctness at all times.  If the
    fallback full re-parse *also* fails, the error is propagated (with
    any original partial-parse error chained as ``__cause__``) rather
    than silently swallowed.

Thread Safety:
    ``parse_incremental`` is a pure function -- safe to call from any thread.

"""

from collections.abc import Sequence
from dataclasses import fields, replace
from typing import TYPE_CHECKING

from patitas.location import SourceLocation
from patitas.nodes import Block, Document, FencedCode, Node

if TYPE_CHECKING:
    from patitas.directives.registry import DirectiveRegistry


def parse_incremental(
    new_source: str,
    previous: Document,
    edit_start: int,
    edit_end: int,
    new_length: int,
    *,
    source_file: str | None = None,
    directive_registry: DirectiveRegistry | None = None,
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
        directive_registry: Custom directive registry (uses defaults if
            None), matching :func:`patitas.parse`.  The re-parsed region
            honors it exactly like a full parse.

    Returns:
        A new Document reflecting the edit.  Unaffected blocks are
        reused from ``previous`` (shared references, not copies).  Blocks
        after the edit are shifted by the edit delta, and re-parsed blocks
        have their entire node tree (including inline/nested locations and
        ``FencedCode`` source offsets) shifted to absolute positions, so
        the result is offset-wise equivalent to a full re-parse.

    Raises:
        Exception: If incremental parsing is unsafe and the fallback full
            re-parse also fails, the full-parse error propagates (with any
            partial-parse error chained as ``__cause__``).

    Note:
        Falls back to a full re-parse when incremental parsing is not
        safe (e.g., the region cannot be determined or the partial parse
        raises).  The fallback never hides a *full*-parse failure.

    """
    # Validate edit bounds -- invalid input -> fall back to full parse
    if edit_start < 0 or edit_end < edit_start or new_length < 0:
        return _full_parse(new_source, source_file, directive_registry)

    old_blocks = previous.children

    # Degenerate case: no blocks -> full parse
    if not old_blocks:
        return _full_parse(new_source, source_file, directive_registry)

    # Find affected block range
    first_affected, last_affected = _find_affected_range(
        old_blocks,
        edit_start,
        edit_end,
    )

    # If detection failed, fall back
    if first_affected is None or last_affected is None:
        return _full_parse(new_source, source_file, directive_registry)

    # Offset shift: how much text was added or removed
    offset_delta = new_length - (edit_end - edit_start)

    # Determine re-parse region in the NEW source
    reparse_start = old_blocks[first_affected].location.offset
    old_region_end = old_blocks[last_affected].location.end_offset
    reparse_end_new = old_region_end + offset_delta

    # Clamp to source bounds
    reparse_start = max(0, reparse_start)
    reparse_end_new = min(len(new_source), reparse_end_new)

    # Safety: unreasonable region -> fall back
    if reparse_start > reparse_end_new:
        return _full_parse(new_source, source_file, directive_registry)

    # Re-parse the affected region
    region_source = new_source[reparse_start:reparse_end_new]
    new_blocks, region_error = _parse_region(
        region_source, reparse_start, source_file, directive_registry
    )

    # Parse failure -> fall back (chaining the partial-parse error so the
    # fallback can surface it if the full re-parse also fails).
    if new_blocks is None:
        return _full_parse(new_source, source_file, directive_registry, region_error)

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
    directive_registry: DirectiveRegistry | None,
) -> tuple[tuple[Block, ...] | None, Exception | None]:
    """Parse a source region and adjust locations to absolute offsets.

    Returns ``(blocks, None)`` on success or ``(None, error)`` when the
    partial parse raises.  Returning the captured exception (instead of
    swallowing it) lets the caller chain it onto a fallback failure so
    errors are never fully opaque.

    """
    from patitas import parse

    try:
        doc = parse(source, source_file=source_file, directive_registry=directive_registry)
    except Exception as exc:
        return None, exc

    # Adjust the full node tree of each block to absolute offsets so inline
    # and nested locations match a full re-parse, not just the top-level block.
    return tuple(_shift_node(block, offset) for block in doc.children), None


def _shift_node[N: Node](node: N, delta: int) -> N:
    """Return a copy of ``node`` with its entire subtree shifted by ``delta``.

    Shifts ``location`` (offset/end_offset) on every node, ``FencedCode``
    ``source_start``/``source_end`` (which index into source text), and
    recurses into every child node held in dataclass fields (single nodes
    and tuples of nodes, including tuples-of-tuples such as ``Table`` rows).

    Uses ``dataclasses.replace`` for clean frozen-dataclass copying.

    """
    if delta == 0:
        return node

    changes: dict[str, object] = {}

    loc = node.location
    changes["location"] = replace(loc, offset=loc.offset + delta, end_offset=loc.end_offset + delta)

    if isinstance(node, FencedCode) and node.content_override is None:
        # source_start/source_end index into the original source text;
        # content_override (nested contexts) holds content directly and
        # is intentionally left untouched.
        changes["source_start"] = node.source_start + delta
        changes["source_end"] = node.source_end + delta

    for field in fields(node):
        if field.name == "location":
            continue
        value = getattr(node, field.name)
        shifted = _shift_field_value(value, delta)
        if shifted is not value:
            changes[field.name] = shifted

    return replace(node, **changes)  # type: ignore[arg-type]


def _shift_field_value(value: object, delta: int) -> object:
    """Recursively shift any nodes reachable through a dataclass field value.

    Handles single nodes and (possibly nested) tuples of nodes.  Non-node
    values (strings, ints, options objects, ...) are returned unchanged so
    the caller can skip them via identity comparison.

    """
    if isinstance(value, Node):
        return _shift_node(value, delta)
    if isinstance(value, tuple):
        if not value:
            return value
        shifted_items = tuple(_shift_field_value(item, delta) for item in value)
        # Preserve identity when nothing inside changed.
        if all(a is b for a, b in zip(shifted_items, value, strict=True)):
            return value
        return shifted_items
    return value


def _shift_block_offset(block: Block, delta: int) -> Block:
    """Shift a block and its entire subtree by ``delta``.

    Thin wrapper over :func:`_shift_node` kept for the call-site/test
    surface.  Unlike earlier versions, this adjusts *all* descendant
    locations (inline and nested), not just the top-level block location,
    so incremental results match a full parse.

    """
    return _shift_node(block, delta)


def _adjust_offsets(
    blocks: Sequence[Block],
    delta: int,
) -> tuple[Block, ...]:
    """Shift location offsets of all blocks (and their subtrees) by delta."""
    if delta == 0:
        return tuple(blocks)
    return tuple(_shift_node(b, delta) for b in blocks)


def _full_parse(
    source: str,
    source_file: str | None,
    directive_registry: DirectiveRegistry | None = None,
    cause: Exception | None = None,
) -> Document:
    """Fall back to a full re-parse.

    If the full re-parse itself fails, the error is *not* swallowed: it
    propagates, with any earlier partial-parse error chained as
    ``__cause__`` so the recoverable-vs-fatal distinction stays visible.

    """
    from patitas import parse

    try:
        return parse(source, source_file=source_file, directive_registry=directive_registry)
    except Exception as exc:
        if cause is not None and exc.__cause__ is None and exc is not cause:
            raise exc from cause
        raise
