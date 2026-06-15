"""LintContext — the single immutable argument passed to every lint rule.

A :class:`LintContext` carries BOTH the parsed :class:`~patitas.nodes.Document`
AND the raw source string, plus two derived values computed eagerly at
construction: the source split into lines and the full document-order sequence
of AST nodes. AST-oriented rules read ``ctx.headings()`` /
``ctx.nodes_of_type(...)``; line-oriented rules read ``ctx.lines``.

Thread Safety:
    ``LintContext`` is a frozen, slotted dataclass. Its derived state
    (``_lines`` and ``_nodes``) is computed once in ``__post_init__`` via
    ``object.__setattr__`` BEFORE the context is ever shared, so the instance
    is fully immutable and race-free thereafter. Safe to share across threads
    within a run.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from patitas.nodes import Heading, Node
from patitas.visitor import BaseVisitor

if TYPE_CHECKING:
    from patitas.nodes import Document


class _NodeCollector(BaseVisitor[None]):
    """Collect every node in document order via a single AST walk.

    Instantiated fresh per :class:`LintContext` construction (never shared),
    honoring the :class:`~patitas.visitor.BaseVisitor` per-call contract. Because
    ``BaseVisitor.visit`` dispatches then walks children, ``visit_default`` is
    invoked for every node in document order.

    """

    __slots__ = ("nodes",)

    def __init__(self) -> None:
        """Initialize with an empty accumulator."""
        self.nodes: list[Node] = []

    def visit_default(self, node: Node) -> None:
        """Append every visited node (catch-all for all node types)."""
        self.nodes.append(node)


@dataclass(frozen=True, slots=True)
class LintContext:
    """Immutable context handed to each rule's ``check`` method.

    Attributes:
        document: The parsed AST root.
        source: The raw Markdown source (empty string if unavailable).
        source_file: Optional source file path, propagated into diagnostics.

    """

    document: Document
    source: str = ""
    source_file: str | None = None
    _lines: tuple[str, ...] = field(default=(), init=False, repr=False, compare=False)
    _nodes: tuple[Node, ...] = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Eagerly compute derived line and node sequences.

        Uses ``object.__setattr__`` (the sanctioned escape hatch for frozen
        dataclasses) to populate the private slots. Splitting on ``"\\n"`` —
        NOT ``str.splitlines()`` — keeps synthesized line numbers in lockstep
        with the parser, which also counts ``"\\n"`` boundaries (``splitlines``
        over-splits on form-feed/vertical-tab/Unicode separators).
        """
        object.__setattr__(self, "_lines", tuple(self.source.split("\n")))
        collector = _NodeCollector()
        collector.visit(self.document)
        object.__setattr__(self, "_nodes", tuple(collector.nodes))

    @property
    def lines(self) -> tuple[str, ...]:
        """Source split on ``"\\n"`` (1-indexed line N is ``lines[N - 1]``)."""
        return self._lines

    def nodes_of_type[N: Node](self, node_type: type[N]) -> tuple[N, ...]:
        """Return all nodes of ``node_type`` in document order.

        Filters the prebuilt document-order node sequence, so rules never spin
        up their own AST walk.

        Args:
            node_type: The node class to filter for (e.g. ``Link``).

        Returns:
            A tuple of matching nodes in document order.

        """
        return tuple(n for n in self._nodes if isinstance(n, node_type))

    def headings(self) -> tuple[Heading, ...]:
        """Return all :class:`~patitas.nodes.Heading` nodes in document order.

        Sugar for ``nodes_of_type(Heading)``.

        Returns:
            A tuple of headings in document order.

        """
        return self.nodes_of_type(Heading)
