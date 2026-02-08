"""Emphasis parsing for Patitas parser.

Implements CommonMark delimiter stack algorithm for emphasis/strong.
See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis

Thread Safety:
All methods are stateless or use instance-local state only.
Safe for concurrent use when each parser instance is used by one thread.

"""

from typing import TYPE_CHECKING

from patitas.parsing.charsets import (
    is_unicode_punctuation,
    is_unicode_whitespace,
)
from patitas.parsing.inline.match_registry import (
    MatchRegistry,
)
from patitas.parsing.inline.tokens import (
    DelimiterToken,
    InlineToken,
)

if TYPE_CHECKING:
    pass


class EmphasisMixin:
    """Mixin for emphasis delimiter processing.

    Implements CommonMark flanking rules and delimiter matching algorithm.
    Uses external MatchRegistry for match tracking (enables immutable tokens).

    Required Host Attributes: None

    Required Host Methods: None

    """

    def _is_left_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is left-flanking.

        Left-flanking: not followed by whitespace, and either:
        - not followed by punctuation, OR
        - preceded by whitespace or punctuation
        """
        if self._is_whitespace(after):
            return False
        if not self._is_punctuation(after):
            return True
        return self._is_whitespace(before) or self._is_punctuation(before)

    def _is_right_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is right-flanking.

        Right-flanking: not preceded by whitespace, and either:
        - not preceded by punctuation, OR
        - followed by whitespace or punctuation
        """
        if self._is_whitespace(before):
            return False
        if not self._is_punctuation(before):
            return True
        return self._is_whitespace(after) or self._is_punctuation(after)

    def _is_whitespace(self, char: str) -> bool:
        """Check if character is Unicode whitespace.

        CommonMark uses Unicode whitespace for emphasis flanking rules.
        Includes ASCII whitespace and Unicode category Zs.
        """
        return is_unicode_whitespace(char)

    def _is_punctuation(self, char: str) -> bool:
        """Check if character is Unicode punctuation.

        CommonMark uses Unicode punctuation for emphasis flanking rules.
        Includes ASCII punctuation and Unicode categories P* and S*.
        """
        return is_unicode_punctuation(char)

    def _process_emphasis(
        self,
        tokens: list[InlineToken],
        registry: MatchRegistry | None = None,
    ) -> MatchRegistry:
        """Process delimiter stack to match emphasis openers/closers.

        Implements CommonMark emphasis algorithm using external match tracking.
        Uses a Delimiter-Index to achieve O(n) average performance.

        Args:
            tokens: List of InlineToken NamedTuples from _tokenize_inline().
            registry: Optional MatchRegistry to use. If None, creates a new one.

        Returns:
            MatchRegistry containing all delimiter matches.
        """
        if registry is None:
            registry = MatchRegistry()

        # Delimiter-Index for O(1) opener lookup: char -> stack of active opener indices
        delim_index: dict[str, list[int]] = {"*": [], "_": [], "~": []}

        closer_idx = 0
        tokens_len = len(tokens)
        while closer_idx < tokens_len:
            closer = tokens[closer_idx]

            # Skip non-delimiter tokens (use isinstance for proper type narrowing)
            if not isinstance(closer, DelimiterToken):
                closer_idx += 1
                continue

            # If it can close, try to find an opener
            if closer.can_close and registry.is_active(closer_idx):
                stack = delim_index.get(closer.char, [])
                found_opener = False

                # Search backwards in the stack for a valid opener
                for i in range(len(stack) - 1, -1, -1):
                    opener_idx = stack[i]
                    opener = tokens[opener_idx]

                    # Type narrow opener (guaranteed to be DelimiterToken due to index structure)
                    if not isinstance(opener, DelimiterToken):
                        continue

                    if not registry.is_active(opener_idx):
                        continue

                    # opener.char is guaranteed to be closer.char due to index structure
                    opener_remaining = registry.remaining_count(opener_idx, opener.run_length)
                    closer_remaining = registry.remaining_count(closer_idx, closer.run_length)

                    # CommonMark "sum of delimiters" rule (Rule 3)
                    both_can_open_close = (opener.can_open and opener.can_close) or (
                        closer.can_open and closer.can_close
                    )
                    if (
                        both_can_open_close
                        and (opener_remaining + closer_remaining) % 3 == 0
                        and (opener_remaining % 3 != 0 or closer_remaining % 3 != 0)
                    ):
                        continue  # Rule 3 fail

                    # Match found!
                    found_opener = True
                    use_count = 2 if (opener_remaining >= 2 and closer_remaining >= 2) else 1
                    registry.record_match(opener_idx, closer_idx, use_count)

                    # Deactivate intermediate delimiters in both registry and index stacks
                    for mid_idx in range(opener_idx + 1, closer_idx):
                        if isinstance(tokens[mid_idx], DelimiterToken):
                            registry.deactivate(mid_idx)

                    # Clean up all stacks of intermediate delimiters (including other chars)
                    for d_char in delim_index:
                        d_stack = delim_index[d_char]
                        while d_stack and d_stack[-1] > opener_idx:
                            d_stack.pop()

                    # Update current opener status in registry and potentially remove from stack
                    if registry.remaining_count(opener_idx, opener.run_length) == 0:
                        registry.deactivate(opener_idx)
                        if stack and stack[-1] == opener_idx:
                            stack.pop()

                    if registry.remaining_count(closer_idx, closer.run_length) == 0:
                        registry.deactivate(closer_idx)

                    break  # Match made for this closer (at least one segment)

                if not found_opener:
                    # No opener found, deactivate closer if it can't also open
                    if not closer.can_open:
                        registry.deactivate(closer_idx)
                    else:
                        # Closer can't match now, but it's also an opener - add to index
                        stack.append(closer_idx)
                    closer_idx += 1
                elif registry.remaining_count(closer_idx, closer.run_length) > 0:
                    # Closer still has delimiters, continue from same position
                    pass
                else:
                    closer_idx += 1
            elif closer.can_open:
                # Delimiter can open but not close, add to index
                delim_index.get(closer.char, []).append(closer_idx)
                closer_idx += 1
            else:
                # Can neither open nor close (rare/impossible per CM flanking rules)
                closer_idx += 1

        return registry
