"""Block quote classifier mixin."""

from collections.abc import Iterator

from patitas.tokens import Token, TokenType


class QuoteClassifierMixin:
    """Mixin providing block quote classification."""

    def _make_token(
        self,
        token_type: TokenType,
        value: str,
        start_pos: int,
        *,
        start_col: int | None = None,
        end_pos: int | None = None,
        line_indent: int = -1,
    ) -> Token:
        """Create token with raw coordinates. Implemented by Lexer."""
        raise NotImplementedError

    def _expand_tabs(self, text: str, start_col: int = 1) -> str:
        """Expand tabs. Implemented by Lexer."""
        raise NotImplementedError

    def _classify_block_quote(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        """Classify block quote marker(s) and emit tokens.

        A single line may carry many nested ``>`` markers (``> > > x``). Each marker
        is emitted as a ``BLOCK_QUOTE_MARKER`` token; the innermost content is then
        classified once.

        This is written as a LOOP rather than tail recursion. The original recursive
        form crashed with a ``RecursionError`` in the lexer on adversarial single-line
        input (hundreds of leading ``>``) BEFORE the parser's ``max_nesting_depth``
        guard could fire. Iterating peels one ``>`` per pass and emits identical
        tokens (same marker offsets, ``start_col``, ``line_indent``, and the same
        nested heading/list/fence/link-ref/thematic-break handling).

        Args:
            content: Content starting with >
            line_start: Absolute offset of the start of the line
            indent: Column position of the > marker (0-indexed)
        """
        from patitas.parsing.charsets import (
            FENCE_CHARS,
            THEMATIC_BREAK_CHARS,
        )

        # Expand tabs ONCE. After the first ``>`` is peeled, every subsequent level
        # operates on a suffix of this already-tab-free buffer, so re-expanding would
        # be a no-op. The original code re-expanded and re-sliced the full tail on
        # every level, which is O(n^2) on a single line of many ``>`` markers; the
        # index walk below keeps marker peeling amortized O(n).
        if len(content) <= 1:
            # Just ">" with nothing after it.
            marker_offset = line_start + indent
            yield self._make_token(
                TokenType.BLOCK_QUOTE_MARKER,
                ">",
                marker_offset,
                start_col=indent + 1,
                end_pos=marker_offset + 1,
                line_indent=indent,
            )
            return

        # ``buf`` is the tab-expanded content AFTER the first ``>`` (which sits at
        # column ``indent + 2``, 1-indexed). ``pos`` indexes into ``buf``; the
        # character ``buf[pos]`` lives at 1-indexed column ``indent + 2 + pos``.
        buf = self._expand_tabs(content[1:], start_col=indent + 2)
        buf_len = len(buf)
        pos = 0

        while True:
            # The > marker is at line_start + indent (for 0-3 spaces)
            marker_offset = line_start + indent

            # Yield the > marker for the current level.
            yield self._make_token(
                TokenType.BLOCK_QUOTE_MARKER,
                ">",
                marker_offset,
                start_col=indent + 1,
                end_pos=marker_offset + 1,
                line_indent=indent,
            )

            # Content after this ``>`` is buf[pos:]. Equivalent to the former
            # ``expanded_rest`` (already tab-expanded). Consume one optional space.
            if pos >= buf_len:
                return

            if buf[pos] == " ":
                # remaining == buf[pos + 1:]; sub_indent == indent + 2
                rem_start = pos + 1
                sub_indent = indent + 2
            else:
                rem_start = pos
                sub_indent = indent + 1

            if rem_start >= buf_len:
                return

            # ``stripped`` == buf[content_start:] with leading spaces removed.
            content_start = rem_start
            while content_start < buf_len and buf[content_start] == " ":
                content_start += 1
            if content_start >= buf_len:
                return

            leading_spaces = content_start - rem_start
            content_col = sub_indent + leading_spaces

            # Fast path for nested ``>`` on the same line: peel and continue WITHOUT
            # slicing the buffer. Equivalent to the former tail call
            # ``self._classify_block_quote(stripped, line_start, content_col)``.
            if buf[content_start] == ">":
                indent = content_col
                pos = content_start + 1
                continue

            # Innermost content reached: materialise the slices the classification
            # helpers below expect. This slice happens at most once per line.
            remaining = buf[rem_start:]
            stripped = buf[content_start:]

            # Check for block-level elements in remaining content
            # Note: Methods below are provided by other classifier mixins when composed
            if stripped.startswith("#"):
                token = self._try_classify_atx_heading(  # type: ignore[attr-defined]
                    stripped, line_start, content_col
                )
                if token:
                    yield token
                    return
            # Link reference definitions inside block quotes should be recognized
            if stripped.startswith("[") and not stripped.startswith("[^"):
                link_ref_token = self._try_classify_link_reference_def(  # type: ignore[attr-defined]
                    stripped, line_start, content_col
                )
                if link_ref_token:
                    yield link_ref_token
                    return

            if stripped[0] in THEMATIC_BREAK_CHARS:
                token = self._try_classify_thematic_break(  # type: ignore[attr-defined]
                    stripped, line_start, content_col
                )
                if token:
                    yield token
                    return

            if stripped[0] in FENCE_CHARS:
                # Don't change lexer mode - blockquote parser handles fence content
                token = self._try_classify_fence_start(  # type: ignore[attr-defined]
                    stripped, line_start, content_col, change_mode=False
                )
                if token:
                    yield token
                    return

            nested_tokens = self._try_classify_list_marker(  # type: ignore[attr-defined]
                stripped, line_start, content_col
            )
            if nested_tokens:
                yield from nested_tokens
                return

            # Link reference definitions inside block quotes are still global.
            if stripped.startswith("[") and not stripped.startswith("[^"):
                link_ref = self._try_classify_link_reference_def(  # type: ignore[attr-defined]
                    stripped, line_start, indent=leading_spaces
                )
                if link_ref is not None:
                    yield link_ref
                    return

            # Default: paragraph line
            # Use remaining content directly - don't add synthetic indentation.
            # The actual indentation is tracked via line_indent.
            content_offset = line_start + sub_indent

            yield self._make_token(
                TokenType.PARAGRAPH_LINE,
                remaining,
                content_offset,
                start_col=sub_indent + 1,
                line_indent=leading_spaces,  # Track actual leading spaces in content
            )
            return
