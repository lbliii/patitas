"""Directive parsing for Patitas parser.

Handles MyST-style directive blocks with contract validation.
"""

from typing import TYPE_CHECKING

from patitas.nodes import Block, Directive
from patitas.tokens import TokenType

if TYPE_CHECKING:
    pass


class DirectiveParsingMixin:
    """Mixin for directive parsing with contract validation.

    Required Host Attributes:
        - _source: str
        - _current: Token | None
        - _directive_registry: DirectiveRegistry | None
        - _directive_stack: list[str]
        - _strict_contracts: bool

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_block() -> Block | None
    """

    # Required host attributes (documented, not declared, to avoid override conflicts)
    # _current: Token | None
    # _directive_registry: object | None
    # _directive_stack: list[str]
    # _strict_contracts: bool

    def _parse_directive(self) -> Directive:
        """Parse directive block (:::{name} ... :::).

        Returns Directive with typed options. If a handler is registered,
        uses the handler's options_class and parse() method. Otherwise,
        creates Directive directly with default DirectiveOptions.
        """
        from patitas.directives.options import DirectiveOptions

        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.DIRECTIVE_OPEN
        self._advance()

        # Get directive name
        name = ""
        if self._current and self._current.type == TokenType.DIRECTIVE_NAME:
            name = self._current.value
            self._advance()

        # Get optional title
        title: str | None = None
        if self._current and self._current.type == TokenType.DIRECTIVE_TITLE:
            title = self._current.value
            self._advance()

        # Parse raw options dict
        raw_options: dict[str, str] = {}
        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.DIRECTIVE_OPTION:
                # Parse key:value from token
                if ":" in token.value:
                    key, value = token.value.split(":", 1)
                    raw_options[key.strip()] = value.strip()
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # Skip blank lines in option section
                self._advance()
                break  # Options section ends at first blank line
            else:
                break

        # Get handler from registry (if available)
        handler = None
        if self._directive_registry:
            handler = self._directive_registry.get(name)

        # Validate parent contract BEFORE parsing children
        if handler and hasattr(handler, "contract") and handler.contract:
            parent_name = self._directive_stack[-1] if self._directive_stack else None
            violation = handler.contract.validate_parent(name, parent_name)
            if violation:
                from patitas.errors import DirectiveContractError
                from patitas.utils.logger import get_logger

                logger = get_logger(__name__)
                if self._strict_contracts and violation.violation_type != "suggested_parent":
                    raise DirectiveContractError(
                        name,
                        violation.message,
                    )
                else:
                    logger.warning(
                        "Directive contract violation: %s (parent=%s): %s",
                        name,
                        parent_name,
                        violation.message,
                    )

        # Parse options into typed object
        if handler and hasattr(handler, "options_class"):
            typed_options = handler.options_class.from_raw(raw_options)
        else:
            # No handler - use default DirectiveOptions
            typed_options = DirectiveOptions.from_raw(raw_options)

        # Check if handler needs raw content preserved
        preserves_raw_content = False
        if handler and hasattr(handler, "preserves_raw_content"):
            preserves_raw_content = handler.preserves_raw_content

        # Push onto stack before parsing children
        self._directive_stack.append(name)

        # Parse content (nested blocks)
        children: list[Block] = []
        raw_content: str | None = None
        try:
            if preserves_raw_content:
                # Extract verbatim source text instead of parsing blocks.
                # _parse_block() would consume list tokens, destroying the
                # original "* - Cell" structure that handlers like list-table
                # need to parse themselves.
                first_content_offset: int | None = None
                close_start_offset: int = len(self._source)

                while not self._at_end():
                    token = self._current
                    assert token is not None

                    if token.type == TokenType.DIRECTIVE_CLOSE:
                        close_start_offset = token._start_offset
                        self._advance()
                        break

                    if first_content_offset is None:
                        first_content_offset = token._start_offset

                    self._advance()

                if first_content_offset is not None:
                    content_line_start = self._source.rfind("\n", 0, first_content_offset) + 1
                    close_line_start = self._source.rfind("\n", 0, close_start_offset) + 1
                    raw_content = self._source[content_line_start:close_line_start]
                    raw_content = raw_content.strip("\n")
                else:
                    raw_content = ""
            else:
                while not self._at_end():
                    token = self._current
                    assert token is not None

                    if token.type == TokenType.DIRECTIVE_CLOSE:
                        self._advance()
                        break
                    elif token.type == TokenType.BLANK_LINE:
                        self._advance()
                        continue

                    block = self._parse_block()
                    if block is not None:
                        children.append(block)

                # Validate children contract AFTER parsing
                if handler and hasattr(handler, "contract") and handler.contract:
                    child_directives = [c for c in children if isinstance(c, Directive)]
                    violations = handler.contract.validate_children(name, child_directives)
                    if violations:
                        from patitas.errors import DirectiveContractError
                        from patitas.utils.logger import get_logger

                        logger = get_logger(__name__)
                        for violation in violations:
                            if self._strict_contracts:
                                raise DirectiveContractError(name, violation.message)
                            else:
                                logger.warning(
                                    "Directive contract violation: %s: %s",
                                    name,
                                    violation.message,
                                )
        finally:
            # Always pop from stack, even on error
            self._directive_stack.pop()

        # Use handler if available, otherwise create Directive directly
        if handler and hasattr(handler, "parse"):
            # Handler returns Directive with typed options
            directive = handler.parse(
                name=name,
                title=title,
                options=typed_options,
                content=raw_content or "",
                children=children,
                location=start_token.location,
            )
            # Ensure raw_content is set if handler requested it
            if preserves_raw_content and directive.raw_content is None:
                from dataclasses import replace

                directive = replace(directive, raw_content=raw_content)
            return directive
        else:
            # No handler - create Directive directly with typed options
            return Directive(
                location=start_token.location,
                name=name,
                title=title,
                options=typed_options,
                children=tuple(children),
                raw_content=raw_content,
            )
