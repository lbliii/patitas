"""Core inline parsing for Patitas parser.

Provides the main inline tokenization and AST building logic.

Thread Safety:
All methods are stateless or use instance-local state only.
Safe for concurrent use when each parser instance is used by one thread.

"""

from typing import TYPE_CHECKING

from patitas.nodes import (
    CodeSpan,
    Emphasis,
    Inline,
    LineBreak,
    SoftBreak,
    Strikethrough,
    Strong,
    Text,
)
from patitas.parsing.charsets import (
    ASCII_PUNCTUATION,
    DIGITS,
    HEX_DIGITS,
    INLINE_SPECIAL,
)
from patitas.parsing.inline.match_registry import (
    MatchRegistry,
)
from patitas.parsing.inline.tokens import (
    CodeSpanToken,
    DelimiterToken,
    HardBreakToken,
    InlineToken,
    NodeToken,
    SoftBreakToken,
    TextToken,
)

if TYPE_CHECKING:
    from patitas.location import SourceLocation


class InlineParsingCoreMixin:
    """Core inline parsing methods.

    Required Host Attributes:
        - _math_enabled: bool
        - _strikethrough_enabled: bool
        - _footnotes_enabled: bool
        - _link_refs: dict[str, tuple[str, str]]

    Required Host Methods (from other mixins):
        - _is_left_flanking(before, after, delim) -> bool
        - _is_right_flanking(before, after, delim) -> bool
        - _is_punctuation(char) -> bool
        - _process_emphasis(tokens, registry) -> MatchRegistry
        - _try_parse_footnote_ref(text, pos, location) -> tuple | None
        - _try_parse_link(text, pos, location) -> tuple | None
        - _try_parse_image(text, pos, location) -> tuple | None
        - _try_parse_autolink(text, pos, location) -> tuple | None
        - _try_parse_html_inline(text, pos, location) -> tuple | None
        - _try_parse_role(text, pos, location) -> tuple | None
        - _try_parse_math(text, pos, location) -> tuple | None

    """

    # Required host attributes (documented, not declared, to avoid override conflicts)
    # _math_enabled: bool
    # _strikethrough_enabled: bool
    # _footnotes_enabled: bool
    # _link_refs: dict[str, tuple[str, str]]

    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]:
        """Parse inline content using CommonMark delimiter stack algorithm.

        This implements the proper flanking delimiter rules for emphasis/strong.
        See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis
        """
        if not text:
            return ()

        # Phase 1: Tokenize into typed token objects
        tokens = self._tokenize_inline(text, location)

        # Phase 2: Process delimiter stack to match openers/closers
        # Uses external registry (tokens are immutable)
        registry = self._process_emphasis(tokens)

        # Phase 3: Build AST from processed tokens using registry
        return self._build_inline_ast(tokens, registry, location)

    def _tokenize_inline(self, text: str, location: SourceLocation) -> list[InlineToken]:
        """Tokenize inline content into typed token objects.

        Returns list of InlineToken NamedTuples for type safety and performance.
        """
        tokens: list[InlineToken] = []
        pos = 0
        text_len = len(text)  # Cache length for hot loop
        tokens_append = tokens.append  # Local reference for speed

        while pos < text_len:
            char = text[pos]

            # Code span: `code` - handle first to avoid delimiter confusion
            if char == "`":
                count = 0
                while pos < text_len and text[pos] == "`":
                    count += 1
                    pos += 1

                # Find closing backticks
                close_pos = self._find_code_span_close(text, pos, count)
                if close_pos != -1:
                    code = text[pos:close_pos]
                    # CommonMark 6.3: "Line endings are converted to spaces"
                    code = code.replace("\n", " ")
                    # Normalize: strip one space from each end if both present
                    # But not if it's all spaces
                    code_len = len(code)
                    if code_len >= 2 and code[0] == " " and code[-1] == " " and code.strip():
                        code = code[1:-1]
                    tokens_append(CodeSpanToken(code=code))
                    pos = close_pos + count
                else:
                    tokens_append(TextToken(content="`" * count))
                continue

            # Emphasis delimiters: * or _
            if char in "*_":
                delim_start = pos
                delim_char = char
                count = 0
                while pos < text_len and text[pos] == delim_char:
                    count += 1
                    pos += 1

                # Determine flanking status (CommonMark rules)
                before = text[delim_start - 1] if delim_start > 0 else " "
                after = text[pos] if pos < text_len else " "

                left_flanking = self._is_left_flanking(before, after, delim_char)
                right_flanking = self._is_right_flanking(before, after, delim_char)

                # For underscore, additional rules apply
                if delim_char == "_":
                    can_open = left_flanking and (
                        not right_flanking or self._is_punctuation(before)
                    )
                    can_close = right_flanking and (
                        not left_flanking or self._is_punctuation(after)
                    )
                else:
                    can_open = left_flanking
                    can_close = right_flanking

                tokens_append(
                    DelimiterToken(
                        char=delim_char,  # type: ignore[arg-type]
                        run_length=count,
                        can_open=can_open,
                        can_close=can_close,
                    )
                )
                continue

            # Link or footnote reference: [text](url) or [^id]
            if char == "[":
                # Check for footnote reference: [^id]
                if self._footnotes_enabled and pos + 1 < text_len and text[pos + 1] == "^":
                    fn_result = self._try_parse_footnote_ref(text, pos, location)
                    if fn_result:
                        node, new_pos = fn_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue

                # Try regular link
                link_result = self._try_parse_link(text, pos, location)
                if link_result:
                    node, new_pos = link_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                tokens_append(TextToken(content="["))
                pos += 1
                continue

            # Image: ![alt](url)
            if char == "!":
                if pos + 1 < text_len and text[pos + 1] == "[":
                    img_result = self._try_parse_image(text, pos, location)
                    if img_result:
                        node, new_pos = img_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue
                # Not an image, emit ! as literal text
                tokens_append(TextToken(content="!"))
                pos += 1
                continue

            # Hard break: \ at end of line
            if char == "\\" and pos + 1 < text_len and text[pos + 1] == "\n":
                tokens_append(HardBreakToken())
                pos += 2  # Move past \ and newline
                # CommonMark 6.9: Skip leading spaces on continuation line
                while pos < text_len and text[pos] == " ":
                    pos += 1
                continue

            # Soft break or hard break (two+ trailing spaces)
            if char == "\n":
                # Check for two or more trailing spaces before this newline
                # CommonMark 6.11: "A line break that is preceded by two or more
                # spaces... is parsed as a hard line break"
                space_count = 0
                check_pos = pos - 1
                while check_pos >= 0 and text[check_pos] == " ":
                    space_count += 1
                    check_pos -= 1

                if space_count >= 2:
                    # Remove trailing spaces from previous text token
                    if tokens and isinstance(tokens[-1], TextToken):
                        content = tokens[-1].content.rstrip(" ")
                        if content:
                            tokens[-1] = TextToken(content=content)
                        else:
                            tokens.pop()
                    tokens_append(HardBreakToken())
                    pos += 1  # Move past newline
                    # CommonMark 6.9: Skip leading spaces on continuation line
                    while pos < text_len and text[pos] == " ":
                        pos += 1
                else:
                    # Soft break: also strip single trailing space and skip leading spaces
                    # CommonMark 6.10: Interior spaces are preserved in paragraphs,
                    # but trailing/leading spaces around line breaks are stripped
                    if space_count == 1 and tokens and isinstance(tokens[-1], TextToken):
                        content = tokens[-1].content.rstrip(" ")
                        if content:
                            tokens[-1] = TextToken(content=content)
                        else:
                            tokens.pop()
                    tokens_append(SoftBreakToken())
                    pos += 1  # Move past newline
                    # Skip leading spaces on continuation line
                    while pos < text_len and text[pos] == " ":
                        pos += 1
                continue

            # Escaped character
            if char == "\\":
                if pos + 1 < text_len:
                    next_char = text[pos + 1]
                    if next_char in ASCII_PUNCTUATION:
                        # CommonMark: any ASCII punctuation can be escaped
                        tokens_append(TextToken(content=next_char))
                        pos += 2
                        continue
                    else:
                        # Backslash before non-punctuation: emit literal backslash
                        tokens_append(TextToken(content="\\"))
                        pos += 1
                        continue
                else:
                    # Backslash at end of text: emit literal backslash
                    tokens_append(TextToken(content="\\"))
                    pos += 1
                    continue

            # Autolink or HTML inline: <...>
            if char == "<":
                # Try autolink first (CommonMark 6.7): <https://...> or <email@...>
                autolink_result = self._try_parse_autolink(text, pos, location)
                if autolink_result:
                    node, new_pos = autolink_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue

                # Then try HTML inline: <tag>
                html_result = self._try_parse_html_inline(text, pos, location)
                if html_result:
                    node, new_pos = html_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                else:
                    # Not valid autolink or HTML, emit < as literal text
                    tokens_append(TextToken(content="<"))
                    pos += 1
                    continue

            # Role: {role}`content`
            if char == "{":
                role_result = self._try_parse_role(text, pos, location)
                if role_result:
                    node, new_pos = role_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                else:
                    # Not a valid role, emit { as literal text
                    tokens_append(TextToken(content="{"))
                    pos += 1
                    continue

            # Strikethrough: ~~text~~ (when enabled)
            if char == "~":
                if self._strikethrough_enabled and pos + 1 < text_len and text[pos + 1] == "~":
                    # Found ~~, treat as delimiter
                    pos += 2

                    # Determine flanking status
                    before = text[pos - 3] if pos > 2 else " "
                    after = text[pos] if pos < text_len else " "

                    left_flanking = self._is_left_flanking(before, after, "~")
                    right_flanking = self._is_right_flanking(before, after, "~")

                    tokens_append(
                        DelimiterToken(
                            char="~",
                            run_length=2,
                            can_open=left_flanking,
                            can_close=right_flanking,
                        )
                    )
                    continue
                # Strikethrough disabled or single ~, emit as text
                tokens_append(TextToken(content="~"))
                pos += 1
                continue

            # Math: $inline$ or $$block$$ (when enabled)
            if char == "$":
                if self._math_enabled:
                    math_result = self._try_parse_math(text, pos, location)
                    if math_result:
                        node, new_pos = math_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue
                # Math disabled or not valid math, emit $ as literal text
                tokens_append(TextToken(content="$"))
                pos += 1
                continue

            # Entity references: &name; or &#digits; or &#xhex;
            if char == "&":
                entity_result = self._try_parse_entity(text, pos)
                if entity_result:
                    decoded, new_pos = entity_result
                    tokens_append(TextToken(content=decoded))
                    pos = new_pos
                    continue
                # Not a valid entity, emit & as literal text
                tokens_append(TextToken(content="&"))
                pos += 1
                continue

            # Regular text - accumulate using frozenset lookup (O(1) per char)
            text_start = pos
            while pos < text_len and text[pos] not in INLINE_SPECIAL:
                pos += 1
            if pos > text_start:
                tokens_append(TextToken(content=text[text_start:pos]))

        return tokens

    def _find_code_span_close(self, text: str, start: int, backtick_count: int) -> int:
        """Find closing backticks for code span."""
        pos = start
        text_len = len(text)
        while True:
            idx = text.find("`", pos)
            if idx == -1:
                return -1
            # Count consecutive backticks
            count = 0
            check_pos = idx
            while check_pos < text_len and text[check_pos] == "`":
                count += 1
                check_pos += 1
            if count == backtick_count:
                return idx
            pos = check_pos

    def _try_parse_entity(self, text: str, pos: int) -> tuple[str, int] | None:
        """Try to parse an HTML entity reference at position.

        CommonMark 6.2: Entity and numeric character references.
        Supports:
        - Named entities: &amp; &nbsp; &copy; etc.
        - Decimal: &#digits; (1-7 digits, value <= 0x10FFFF)
        - Hexadecimal: &#xhex; or &#Xhex; (1-6 hex digits)

        Returns:
            Tuple of (decoded_char, new_position) if valid, None otherwise.
        """
        import html

        text_len = len(text)
        if pos >= text_len or text[pos] != "&":
            return None

        # Look for the closing semicolon (max 32 chars for named entities)
        end = pos + 1
        max_end = min(pos + 33, text_len)

        # Check for numeric reference
        if end < text_len and text[end] == "#":
            end += 1
            if end >= text_len:
                return None

            # Hexadecimal: &#x or &#X
            if text[end] in "xX":
                end += 1
                hex_start = end
                while end < text_len and text[end] in HEX_DIGITS:
                    end += 1
                # CommonMark: 1-6 hex digits
                hex_len = end - hex_start
                if hex_len < 1 or hex_len > 6:
                    return None
                if end >= text_len or text[end] != ";":
                    return None
                # Parse and validate
                try:
                    codepoint = int(text[hex_start:end], 16)
                    if codepoint == 0:
                        decoded = "\ufffd"  # Null becomes replacement char
                    elif codepoint > 0x10FFFF:
                        decoded = "\ufffd"  # Out of range
                    else:
                        decoded = chr(codepoint)
                    return decoded, end + 1
                except (ValueError, OverflowError):
                    return None

            # Decimal: &#digits
            dec_start = end
            while end < text_len and text[end] in DIGITS:
                end += 1
            # CommonMark: 1-7 decimal digits
            dec_len = end - dec_start
            if dec_len < 1 or dec_len > 7:
                return None
            if end >= text_len or text[end] != ";":
                return None
            # Parse and validate
            try:
                codepoint = int(text[dec_start:end])
                if codepoint == 0:
                    decoded = "\ufffd"  # Null becomes replacement char
                elif codepoint > 0x10FFFF:
                    decoded = "\ufffd"  # Out of range
                else:
                    decoded = chr(codepoint)
                return decoded, end + 1
            except (ValueError, OverflowError):
                return None

        # Named entity: &name;
        # Name must start with a letter and contain only alphanumeric chars
        if end < text_len and text[end].isalpha():
            while end < max_end and text[end].isalnum():
                end += 1
            if end < text_len and text[end] == ";":
                entity = text[pos : end + 1]
                # Use Python's html.unescape to decode
                decoded = html.unescape(entity)
                # If it wasn't decoded (unknown entity), return None
                if decoded == entity:
                    return None
                return decoded, end + 1

        return None

    def _build_inline_ast(
        self,
        tokens: list[InlineToken],
        registry: MatchRegistry,
        location: SourceLocation,
        start: int = 0,
        end: int | None = None,
    ) -> tuple[Inline, ...]:
        """Build AST from processed tokens using match registry.

        Uses pattern matching for type-safe token dispatch.
        Uses index bounds instead of list slicing to avoid allocations.

        Args:
            tokens: List of InlineToken NamedTuples from _tokenize_inline().
            registry: MatchRegistry containing delimiter matches.
            location: Source location for node creation.
            start: Start index in tokens (inclusive). Default 0.
            end: End index in tokens (exclusive). Default len(tokens).

        Returns:
            Tuple of Inline nodes.
        """
        if end is None:
            end = len(tokens)

        result: list[Inline] = []
        idx = start

        while idx < end:
            token = tokens[idx]
            # Registry uses original indices (same as token list indices)
            registry_idx = idx

            match token:
                case TextToken(content=content):
                    result.append(Text(location=location, content=content))
                    idx += 1

                case CodeSpanToken(code=code):
                    result.append(CodeSpan(location=location, code=code))
                    idx += 1

                case NodeToken(node=node):
                    result.append(node)  # type: ignore[arg-type]
                    idx += 1

                case HardBreakToken():
                    result.append(LineBreak(location=location))
                    idx += 1

                case SoftBreakToken():
                    result.append(SoftBreak(location=location))
                    idx += 1

                case DelimiterToken(char=delim_char, run_length=original_count):
                    # Check if this delimiter is an opener with matches
                    # Use registry_idx for lookup since registry uses original indices
                    all_matches = registry.get_matches_for_opener(registry_idx)
                    if all_matches and all_matches[0].closer_idx > registry_idx:
                        # This is an opener - build nested emphasis/strong/strikethrough
                        # Sort matches by closer_idx to handle multiple closers correctly
                        # Example: __foo_ bar_ has opener 0 matching closers 2 and 4
                        # We need to process innermost (closest closer) first
                        sorted_matches = sorted(all_matches, key=lambda m: m.closer_idx)

                        # Calculate consumed delimiters (sum of all matches)
                        consumed = sum(m.match_count for m in all_matches)
                        opener_remaining = original_count - consumed

                        # Emit remaining unused opener delimiters as text BEFORE emphasis
                        if opener_remaining > 0:
                            result.append(
                                Text(location=location, content=delim_char * opener_remaining)
                            )

                        # Check if all matches have the SAME closer (e.g., ***text***)
                        # vs different closers (e.g., __foo_ bar_)
                        unique_closers = {m.closer_idx for m in sorted_matches}

                        if len(unique_closers) == 1:
                            # All matches share the same closer (e.g., ***text***)
                            closer_idx_in_tokens = sorted_matches[0].closer_idx

                            # Get closer remaining - use registry to check TOTAL consumption
                            # A closer may be shared by multiple openers (e.g., *foo *bar**)
                            closer_remaining = 0
                            if closer_idx_in_tokens < end:
                                closer_token = tokens[closer_idx_in_tokens]
                                if isinstance(closer_token, DelimiterToken):
                                    # Use registry's remaining_count which tracks total consumption
                                    closer_remaining = registry.remaining_count(
                                        closer_idx_in_tokens, closer_token.run_length
                                    )

                            # Build children between opener and closer (no slicing!)
                            children = self._build_inline_ast(
                                tokens,
                                registry,
                                location,
                                start=idx + 1,
                                end=closer_idx_in_tokens,
                            )

                            # Wrap from innermost to outermost
                            for match_info in sorted_matches:
                                match_count = match_info.match_count
                                if delim_char == "~":
                                    node: Inline = Strikethrough(
                                        location=location, children=children
                                    )
                                elif match_count == 2:
                                    node = Strong(location=location, children=children)
                                else:
                                    node = Emphasis(location=location, children=children)
                                children = (node,)

                            result.append(children[0])

                            if closer_remaining > 0:
                                result.append(
                                    Text(location=location, content=delim_char * closer_remaining)
                                )

                            idx = closer_idx_in_tokens + 1
                        else:
                            # Multiple different closers (e.g., __foo_ bar_)
                            # Process from innermost (closest) to outermost (farthest)
                            # Each match wraps progressively more content

                            # Find the outermost closer for skipping past at the end
                            outermost_closer_idx = sorted_matches[-1].closer_idx

                            # Get outermost closer remaining
                            outermost_closer_remaining = 0
                            if outermost_closer_idx < end:
                                closer_token = tokens[outermost_closer_idx]
                                if isinstance(closer_token, DelimiterToken):
                                    # Each match uses delimiters from both opener and closer
                                    # But closers are different, so only the last match uses
                                    # the outermost closer
                                    outermost_closer_remaining = (
                                        closer_token.run_length - sorted_matches[-1].match_count
                                    )

                            # Build content progressively
                            # Start from opener+1, build to first closer
                            # Then build from first closer+1 to second closer
                            # etc., wrapping each segment with the appropriate emphasis

                            accumulated_children: tuple[Inline, ...] = ()
                            prev_boundary = idx + 1  # Start right after opener

                            for match_info in sorted_matches:
                                closer_idx_in_tokens = match_info.closer_idx
                                match_count = match_info.match_count

                                # Build content from prev_boundary to this closer (no slicing!)
                                if prev_boundary < closer_idx_in_tokens:
                                    segment_children = self._build_inline_ast(
                                        tokens,
                                        registry,
                                        location,
                                        start=prev_boundary,
                                        end=closer_idx_in_tokens,
                                    )
                                else:
                                    segment_children = ()

                                # Combine accumulated children with this segment
                                combined_children = accumulated_children + segment_children

                                # Wrap in emphasis/strong
                                if delim_char == "~":
                                    node = Strikethrough(
                                        location=location, children=combined_children
                                    )
                                elif match_count == 2:
                                    node = Strong(location=location, children=combined_children)
                                else:
                                    node = Emphasis(location=location, children=combined_children)

                                # This becomes the accumulated children for the next outer match
                                accumulated_children = (node,)

                                # Next segment starts after this closer
                                prev_boundary = closer_idx_in_tokens + 1

                            # Add the final wrapped result
                            if accumulated_children:
                                result.append(accumulated_children[0])

                            if outermost_closer_remaining > 0:
                                result.append(
                                    Text(
                                        location=location,
                                        content=delim_char * outermost_closer_remaining,
                                    )
                                )

                            idx = outermost_closer_idx + 1
                    else:
                        # Unmatched delimiter - emit as text
                        remaining = registry.remaining_count(registry_idx, original_count)
                        if remaining > 0:
                            result.append(Text(location=location, content=delim_char * remaining))
                        idx += 1

                case _:
                    # Unknown token type, skip
                    idx += 1

        return tuple(result)
