"""Diagnostic and Severity types for the lint framework.

This is a leaf data module: it depends only on the standard library and
:class:`patitas.location.SourceLocation`, so it can be imported without pulling
in the runner, the registry, or any rules.

Thread Safety:
    Both :class:`Severity` and :class:`Diagnostic` are immutable. ``Severity``
    is a plain enum; ``Diagnostic`` is a frozen, slotted dataclass. Both are
    safe to share across threads.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patitas.location import SourceLocation


class Severity(Enum):
    """Severity level of a lint :class:`Diagnostic`.

    A plain :class:`enum.Enum` (matching the codebase's plain-Enum precedent,
    e.g. ``TokenType``/``LexerMode``). It is deliberately NOT an ``IntEnum``:
    that avoids accidental integer coercion (``Severity.ERROR != 1``). The
    LSP ``DiagnosticSeverity`` integer is available explicitly via
    :meth:`to_lsp`.

    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def to_lsp(self) -> int:
        """Return the LSP ``DiagnosticSeverity`` integer for this severity.

        The Language Server Protocol numbers severities 1 (Error), 2 (Warning),
        3 (Information), 4 (Hint). This maps the three lint severities onto the
        first three.

        Returns:
            The LSP severity integer: ERROR -> 1, WARNING -> 2, INFO -> 3.

        """
        match self:
            case Severity.ERROR:
                return 1
            case Severity.WARNING:
                return 2
            case Severity.INFO:
                return 3


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A single lint finding.

    Reuses the existing :class:`patitas.location.SourceLocation` verbatim for
    positions — it never introduces a new position type and never extends
    ``Node``. For AST-oriented rules the location is the offending node's
    ``node.location``; for line-oriented rules (e.g. trailing whitespace) the
    rule synthesizes its own ``SourceLocation``.

    The runner stamps :attr:`rule_id` and :attr:`severity` from the emitting
    rule's class metadata, so they can never drift from the producing rule.

    Attributes:
        rule_id: Kebab-case id of the rule that produced this diagnostic.
        message: Human-readable, single-line description of the violation.
        location: Position of the violation (reuses ``SourceLocation``).
        severity: Effective severity of this occurrence.

    Thread Safety:
        Frozen and slotted; safe to share across threads.

    """

    rule_id: str
    message: str
    location: SourceLocation
    severity: Severity = field(default=Severity.WARNING)

    def __str__(self) -> str:
        """Format as ``file:line:col: [rule-id] message``.

        Delegates position formatting to :meth:`SourceLocation.__str__`, so the
        ``file:`` prefix is omitted when ``source_file`` is unset. Mirrors the
        ``ParseError`` "file:line:col: message" shape.

        Returns:
            A single-line, ready-to-print diagnostic string.

        """
        return f"{self.location}: [{self.rule_id}] {self.message}"

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON/LSP-friendly dict.

        Named ``to_dict`` to match the established ``serialization.py``
        convention. ``severity`` is serialized to its enum ``.value`` string.

        Returns:
            A dict with the rule id, message, severity value, and position
            fields (line/col plus the full location offsets).

        """
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.location.lineno,
            "col": self.location.col_offset,
            "offset": self.location.offset,
            "end_offset": self.location.end_offset,
            "end_line": self.location.end_lineno,
            "end_col": self.location.end_col_offset,
            "source_file": self.location.source_file,
        }
