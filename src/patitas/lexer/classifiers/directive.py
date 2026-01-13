"""Directive classifier mixin."""

from __future__ import annotations

from collections.abc import Iterator

from patitas.lexer.modes import LexerMode
from patitas.tokens import Token, TokenType


class DirectiveClassifierMixin:
    """Mixin providing MyST-style directive classification.

    Handles :::{name} and ::::{name} syntax with nesting support.

    """

    # These will be set by the Lexer class
    _mode: LexerMode
    _directive_stack: list[tuple[int, str]]

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

    def _try_classify_directive_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        """Try to classify content as directive start.

        Detects :::{name} or ::::{name} syntax (MyST-style fenced directives).
        Supports:
        - Nested directives via colon count (:::: > :::)
        - Named closers (:::{/name})
        - Optional title after name

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Returns:
            Iterator of tokens if valid directive, None otherwise.
        """
        if not content.startswith(":::"):
            return None

        # Count opening colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Must have { immediately after colons
        if pos >= len(content) or content[pos] != "{":
            return None

        # Find matching }
        pos += 1  # Skip {
        brace_end = content.find("}", pos)
        if brace_end == -1:
            return None

        name = content[pos:brace_end].strip()

        # Check for named closer: {/name}
        is_closer = name.startswith("/")
        if is_closer:
            name = name[1:].strip()

        # Get optional title (rest of line after })
        title = content[brace_end + 1 :].rstrip("\n").strip()

        # Generate tokens
        return self._emit_directive_tokens(
            colon_count=colon_count,
            name=name,
            title=title,
            is_closer=is_closer,
            line_start=line_start,
            indent=indent,
        )

    def _emit_directive_tokens(
        self,
        colon_count: int,
        name: str,
        title: str,
        is_closer: bool,
        line_start: int,
        indent: int = 0,
    ) -> Iterator[Token]:
        """Emit directive tokens and update state.

        Args:
            colon_count: Number of colons in the fence
            name: Directive name
            title: Optional title after the name
            is_closer: Whether this is a named closer (:::{/name})
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Yields:
            DIRECTIVE_OPEN/CLOSE, DIRECTIVE_NAME, and optionally DIRECTIVE_TITLE tokens.
        """
        if is_closer:
            # Named closer: :::{/name}
            yield self._make_token(
                TokenType.DIRECTIVE_CLOSE, f":::{{{name}}}", line_start, line_indent=indent
            )

            # Pop from directive stack if matching
            if self._directive_stack:
                stack_count, stack_name = self._directive_stack[-1]
                if stack_name == name and colon_count >= stack_count:
                    self._directive_stack.pop()
                    if not self._directive_stack:
                        self._mode = LexerMode.BLOCK
        else:
            # Directive open
            yield self._make_token(
                TokenType.DIRECTIVE_OPEN, ":" * colon_count, line_start, line_indent=indent
            )
            yield self._make_token(
                TokenType.DIRECTIVE_NAME, name, line_start, line_indent=indent
            )
            if title:
                yield self._make_token(
                    TokenType.DIRECTIVE_TITLE, title, line_start, line_indent=indent
                )

            # Push to directive stack and switch mode
            self._directive_stack.append((colon_count, name))
            self._mode = LexerMode.DIRECTIVE

    def _try_classify_directive_close(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        """Check if content is a directive closing fence.

        Valid closing:
        - ::: (simple close, 3+ colons matching or exceeding opener)
        - :::{/name} (named close)

        Args:
            content: Line content starting with :::
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Returns:
            Iterator of tokens if valid close, None otherwise.
        """
        if not content.startswith(":::"):
            return None

        # Count colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Check for named closer
        rest = content[pos:].strip().rstrip("\n")

        if rest.startswith("{/"):
            # Named closer: :::{/name}
            brace_end = rest.find("}")
            if brace_end != -1:
                name = rest[2:brace_end].strip()
                remaining = rest[brace_end + 1 :].strip()
                if not remaining:  # No extra content after }
                    return self._emit_directive_close(colon_count, name, line_start, indent)

        elif rest == "" or rest.startswith("{"):
            # Simple close or check if it's a new directive
            if rest == "":
                # Simple close with just colons
                return self._emit_directive_close(colon_count, None, line_start, indent)

        return None

    def _emit_directive_close(
        self, colon_count: int, name: str | None, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        """Emit directive close token and update state.

        Args:
            colon_count: Number of colons in the closing fence
            name: Optional directive name for named closers
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Yields:
            DIRECTIVE_CLOSE token(s), or PARAGRAPH_LINE if not a valid close.
        """
        if not self._directive_stack:
            # No open directive, emit as plain text
            yield self._make_token(
                TokenType.PARAGRAPH_LINE, ":" * colon_count, line_start, line_indent=indent
            )
            return

        stack_count, stack_name = self._directive_stack[-1]

        # Check if this closes the current directive or an outer one
        if name is not None:
            # Named closer: find matching directive in stack
            match_index = -1
            for i in range(len(self._directive_stack) - 1, -1, -1):
                s_count, s_name = self._directive_stack[i]
                if s_name == name and colon_count >= s_count:
                    match_index = i
                    break

            if match_index != -1:
                # Close this and all nested directives
                # Emit a separate DIRECTIVE_CLOSE token for each popped level
                # so the recursive parser can correctly exit all nested loops.
                popped_count = 0
                while len(self._directive_stack) > match_index:
                    s_count, s_name = self._directive_stack.pop()
                    popped_count += 1
                    # Use the original name for the first token, simple colons for others
                    # OR just use simple colons for all to be consistent.
                    # The parser only cares about the token type to break the loop.
                    if popped_count == 1:
                        yield self._make_token(
                            TokenType.DIRECTIVE_CLOSE,
                            f":::{{{name}}}",
                            line_start,
                            line_indent=indent,
                        )
                    else:
                        yield self._make_token(
                            TokenType.DIRECTIVE_CLOSE,
                            ":" * s_count,
                            line_start,
                            line_indent=indent,
                        )

                if not self._directive_stack:
                    self._mode = LexerMode.BLOCK
                return
        else:
            # Simple close: closes the top directive
            if colon_count >= stack_count:
                self._directive_stack.pop()
                yield self._make_token(
                    TokenType.DIRECTIVE_CLOSE,
                    ":" * colon_count,
                    line_start,
                    line_indent=indent,
                )

                if not self._directive_stack:
                    self._mode = LexerMode.BLOCK
                return

        # Not a valid close for current directive, emit as content
        yield self._make_token(
            TokenType.PARAGRAPH_LINE, ":" * colon_count, line_start, line_indent=indent
        )

    def _try_classify_directive_option(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as directive option.

        Format: :key: value

        Args:
            content: Line content starting with :
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Returns:
            DIRECTIVE_OPTION token if valid, None otherwise.
        """
        if not content.startswith(":"):
            return None

        # Find second colon
        colon_pos = content.find(":", 1)
        if colon_pos == -1:
            return None

        key = content[1:colon_pos].strip()
        value = content[colon_pos + 1 :].rstrip("\n").strip()

        # Key must be a valid identifier (alphanumeric + - + _)
        if not key or not all(c.isalnum() or c in "-_" for c in key):
            return None

        return self._make_token(
            TokenType.DIRECTIVE_OPTION,
            f"{key}:{value}",
            line_start,
            line_indent=indent,
        )
