"""AST Visitor and Transformer for Patitas.

Provides a base visitor class with match-based dispatch and an immutable
transform function for rewriting frozen ASTs.

Example — collect all headings:

    class HeadingCollector(BaseVisitor[None]):
        def __init__(self) -> None:
            self.headings: list[Heading] = []

        def visit_heading(self, node: Heading) -> None:
            self.headings.append(node)

    collector = HeadingCollector()
    collector.visit(doc)

Example — shift heading levels:

    def shift_headings(node: Node) -> Node:
        if isinstance(node, Heading):
            new_level = min(node.level + 1, 6)
            return dataclasses.replace(node, level=new_level)
        return node

    new_doc = transform(doc, shift_headings)

Thread Safety:
    Visitors are NOT shared across threads by default (they may accumulate
    mutable state). Create a new visitor per thread. The transform function
    is pure — safe to call from any thread.

"""

import dataclasses
from collections.abc import Callable

from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Directive,
    Document,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Node,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)


class BaseVisitor[T]:
    """Base AST visitor with match-based dispatch.

    Subclass and override ``visit_*`` methods for node types you care about.
    Unhandled node types fall through to ``visit_default``. Children are
    walked automatically after the ``visit_*`` call.

    Type parameter ``T`` is the return type of visit methods (use ``None``
    for side-effect-only visitors).

    """

    def visit(self, node: Node) -> T:
        """Dispatch to the appropriate ``visit_*`` method.

        Walks children automatically after the visit method returns.

        """
        result = self._dispatch(node)
        self._walk_children(node)
        return result

    def visit_default(self, node: Node) -> T:
        """Called for node types without a specific ``visit_*`` method.

        Override this for catch-all behavior. Default returns None
        (suitable for ``BaseVisitor[None]``).

        """
        return None  # type: ignore[return-value]

    # -- Block visitors --------------------------------------------------------

    def visit_document(self, node: Document) -> T:
        return self.visit_default(node)

    def visit_heading(self, node: Heading) -> T:
        return self.visit_default(node)

    def visit_paragraph(self, node: Paragraph) -> T:
        return self.visit_default(node)

    def visit_fenced_code(self, node: FencedCode) -> T:
        return self.visit_default(node)

    def visit_indented_code(self, node: IndentedCode) -> T:
        return self.visit_default(node)

    def visit_block_quote(self, node: BlockQuote) -> T:
        return self.visit_default(node)

    def visit_list(self, node: List) -> T:
        return self.visit_default(node)

    def visit_list_item(self, node: ListItem) -> T:
        return self.visit_default(node)

    def visit_thematic_break(self, node: ThematicBreak) -> T:
        return self.visit_default(node)

    def visit_html_block(self, node: HtmlBlock) -> T:
        return self.visit_default(node)

    def visit_directive(self, node: Directive) -> T:  # type: ignore[type-arg]
        return self.visit_default(node)

    def visit_table(self, node: Table) -> T:
        return self.visit_default(node)

    def visit_table_row(self, node: TableRow) -> T:
        return self.visit_default(node)

    def visit_table_cell(self, node: TableCell) -> T:
        return self.visit_default(node)

    def visit_math_block(self, node: MathBlock) -> T:
        return self.visit_default(node)

    def visit_footnote_def(self, node: FootnoteDef) -> T:
        return self.visit_default(node)

    # -- Inline visitors -------------------------------------------------------

    def visit_text(self, node: Text) -> T:
        return self.visit_default(node)

    def visit_emphasis(self, node: Emphasis) -> T:
        return self.visit_default(node)

    def visit_strong(self, node: Strong) -> T:
        return self.visit_default(node)

    def visit_strikethrough(self, node: Strikethrough) -> T:
        return self.visit_default(node)

    def visit_link(self, node: Link) -> T:
        return self.visit_default(node)

    def visit_image(self, node: Image) -> T:
        return self.visit_default(node)

    def visit_code_span(self, node: CodeSpan) -> T:
        return self.visit_default(node)

    def visit_line_break(self, node: LineBreak) -> T:
        return self.visit_default(node)

    def visit_soft_break(self, node: SoftBreak) -> T:
        return self.visit_default(node)

    def visit_html_inline(self, node: HtmlInline) -> T:
        return self.visit_default(node)

    def visit_role(self, node: Role) -> T:
        return self.visit_default(node)

    def visit_math(self, node: Math) -> T:
        return self.visit_default(node)

    def visit_footnote_ref(self, node: FootnoteRef) -> T:
        return self.visit_default(node)

    # -- Internal dispatch -----------------------------------------------------

    def _dispatch(self, node: Node) -> T:
        """Match-based dispatch to visit_* methods."""
        match node:
            case Document():
                return self.visit_document(node)
            case Heading():
                return self.visit_heading(node)
            case Paragraph():
                return self.visit_paragraph(node)
            case FencedCode():
                return self.visit_fenced_code(node)
            case IndentedCode():
                return self.visit_indented_code(node)
            case BlockQuote():
                return self.visit_block_quote(node)
            case List():
                return self.visit_list(node)
            case ListItem():
                return self.visit_list_item(node)
            case ThematicBreak():
                return self.visit_thematic_break(node)
            case HtmlBlock():
                return self.visit_html_block(node)
            case Directive():
                return self.visit_directive(node)
            case Table():
                return self.visit_table(node)
            case TableRow():
                return self.visit_table_row(node)
            case TableCell():
                return self.visit_table_cell(node)
            case MathBlock():
                return self.visit_math_block(node)
            case FootnoteDef():
                return self.visit_footnote_def(node)
            case Text():
                return self.visit_text(node)
            case Emphasis():
                return self.visit_emphasis(node)
            case Strong():
                return self.visit_strong(node)
            case Strikethrough():
                return self.visit_strikethrough(node)
            case Link():
                return self.visit_link(node)
            case Image():
                return self.visit_image(node)
            case CodeSpan():
                return self.visit_code_span(node)
            case LineBreak():
                return self.visit_line_break(node)
            case SoftBreak():
                return self.visit_soft_break(node)
            case HtmlInline():
                return self.visit_html_inline(node)
            case Role():
                return self.visit_role(node)
            case Math():
                return self.visit_math(node)
            case FootnoteRef():
                return self.visit_footnote_ref(node)
            case _:
                return self.visit_default(node)

    def _walk_children(self, node: Node) -> None:
        """Recursively visit child nodes."""
        match node:
            case Document(children=children):
                for child in children:
                    self.visit(child)
            case Heading(children=children):
                for child in children:
                    self.visit(child)
            case Paragraph(children=children):
                for child in children:
                    self.visit(child)
            case BlockQuote(children=children):
                for child in children:
                    self.visit(child)
            case ListItem(children=children):
                for child in children:
                    self.visit(child)
            case List(items=items):
                for item in items:
                    self.visit(item)
            case Directive(children=children):
                for child in children:
                    self.visit(child)
            case FootnoteDef(children=children):
                for child in children:
                    self.visit(child)
            case Emphasis(children=children):
                for child in children:
                    self.visit(child)
            case Strong(children=children):
                for child in children:
                    self.visit(child)
            case Strikethrough(children=children):
                for child in children:
                    self.visit(child)
            case Link(children=children):
                for child in children:
                    self.visit(child)
            case Table(head=head, body=body):
                for row in head:
                    self.visit(row)
                for row in body:
                    self.visit(row)
            case TableRow(cells=cells):
                for cell in cells:
                    self.visit(cell)
            case TableCell(children=children):
                for child in children:
                    self.visit(child)
            case _:
                pass  # Leaf nodes: no children


def transform(doc: Document, fn: Callable[[Node], Node | None]) -> Document:
    """Apply a function to every node in the AST, returning a new tree.

    The function ``fn`` is called bottom-up: children are transformed first,
    then the parent is transformed with its new children. This ensures ``fn``
    always receives nodes with already-transformed children.

    Return ``None`` from ``fn`` to remove a node from the tree. The root
    Document cannot be removed; returning None for it raises TypeError.

    Since all nodes are frozen dataclasses, this produces a new immutable tree.
    The original tree is untouched.

    Args:
        doc: The document to transform.
        fn: Function that receives a node and returns a (possibly new) node,
            or None to remove the node from the tree.

    Returns:
        A new Document with the transformation applied.

    """
    result = _transform_node(doc, fn)
    if result is None or not isinstance(result, Document):
        msg = "transform fn must return a Document for the root (cannot remove root)"
        raise TypeError(msg)
    return result


def _transform_node(node: Node, fn: Callable[[Node], Node | None]) -> Node | None:
    """Transform a single node bottom-up: children first, then self."""
    transformed = _transform_children(node, fn)
    return fn(transformed)


def _transform_children(node: Node, fn: Callable[[Node], Node | None]) -> Node:
    """Produce a new node with children transformed; filter out None (removed) nodes."""

    def _filtered(children: tuple[Node, ...]) -> tuple[Node, ...]:
        return tuple(
            result for c in children
            if (result := _transform_node(c, fn)) is not None
        )

    match node:
        case Document(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Heading(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Paragraph(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case BlockQuote(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case ListItem(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case List(items=items):
            new_items = _filtered(items)
            if new_items != items:
                return dataclasses.replace(node, items=new_items)
        case Directive(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case FootnoteDef(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Emphasis(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Strong(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Strikethrough(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Link(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case Table(head=head, body=body):
            new_head = _filtered(head)
            new_body = _filtered(body)
            if new_head != head or new_body != body:
                return dataclasses.replace(node, head=new_head, body=new_body)
        case TableRow(cells=cells):
            new_cells = _filtered(cells)
            if new_cells != cells:
                return dataclasses.replace(node, cells=new_cells)
        case TableCell(children=children):
            new_children = _filtered(children)
            if new_children != children:
                return dataclasses.replace(node, children=new_children)
        case _:
            pass  # Leaf nodes: return as-is

    return node
