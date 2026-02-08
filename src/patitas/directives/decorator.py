"""@directive decorator for reducing directive boilerplate.

Provides a concise decorator API for creating directive handlers with
minimal boilerplate. Works with both functions and classes.

Example (function):
    >>> @directive("note", options=NoteOptions)
    >>> def render_note(node: Directive[NoteOptions], children: str, sb: StringBuilder) -> None:
    ...     sb.append(f'<div class="note">{children}</div>')

Example (class):
    >>> @directive("gallery", options=GalleryOptions, preserves_raw_content=True)
    >>> class GalleryDirective:
    ...     def render(self, node, children: str, sb: StringBuilder) -> None:
    ...         images = self._parse_images(node.raw_content)
    ...         ...
"""

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from patitas.directives.contracts import DirectiveContract
    from patitas.directives.options import DirectiveOptions
    from patitas.location import SourceLocation
    from patitas.nodes import Block, Directive
    from patitas.stringbuilder import StringBuilder

TOptions = TypeVar("TOptions", bound="DirectiveOptions")

# Type for the decorated function/class
RenderFunc = Callable[["Directive[Any]", str, "StringBuilder"], None]


def directive(
    *names: str,
    options: type[DirectiveOptions] | None = None,
    contract: DirectiveContract | None = None,
    preserves_raw_content: bool = False,
    token_type: str | None = None,
) -> Callable[[RenderFunc | type], type]:
    """Decorator to create directive handlers with minimal boilerplate.

    Works with both functions (simple directives) and classes (complex directives).

    Args:
        *names: Directive names (e.g., "note", "warning", "tip")
        options: Options class for typed option parsing
        contract: Optional nesting validation contract
        preserves_raw_content: If True, parser preserves raw content string
        token_type: Token type identifier (defaults to first name)

    Example (function):
        @directive("note", options=NoteOptions)
        def render_note(node: Directive[NoteOptions], children: str, sb: StringBuilder) -> None:
            sb.append(f'<div class="note">{children}</div>')

    Example (class):
        @directive("gallery", options=GalleryOptions, preserves_raw_content=True)
        class GalleryDirective:
            def render(self, node, children: str, sb: StringBuilder) -> None:
                images = self._parse_images(node.raw_content)
                    ...

    """
    from patitas.directives.options import DirectiveOptions
    from patitas.nodes import Directive

    if not names:
        msg = "At least one directive name must be provided"
        raise ValueError(msg)

    effective_token_type = token_type or names[0]
    effective_options = options or DirectiveOptions

    def decorator(func_or_class: RenderFunc | type) -> type:
        if isinstance(func_or_class, type):
            # Class decorator — add attributes via setattr to satisfy type checker
            func_or_class.names = names
            func_or_class.token_type = effective_token_type
            func_or_class.contract = contract
            func_or_class.options_class = effective_options
            func_or_class.preserves_raw_content = preserves_raw_content
            return func_or_class
        else:
            # Function decorator — wrap in class
            render_func = func_or_class
            # Capture closure variables with different names to avoid shadowing
            _names = names
            _token_type = effective_token_type
            _contract = contract
            _options_class = effective_options
            _preserves_raw = preserves_raw_content

            class GeneratedDirective:
                names = _names
                token_type = _token_type
                contract = _contract
                options_class = _options_class
                preserves_raw_content = _preserves_raw

                def parse(
                    self,
                    name: str,
                    title: str | None,
                    opts: DirectiveOptions,
                    content: str,
                    children: Sequence[Block],
                    location: SourceLocation,
                ) -> Directive[Any]:
                    return Directive(
                        location=location,
                        name=name,
                        title=title,
                        options=opts,
                        children=tuple(children),
                        raw_content=content if _preserves_raw else None,
                    )

                def render(
                    self,
                    node: Directive[Any],
                    rendered_children: str,
                    sb: StringBuilder,
                ) -> None:
                    return render_func(node, rendered_children, sb)

            func_name = getattr(render_func, "__name__", "anonymous")
            func_qualname = getattr(render_func, "__qualname__", "anonymous")
            GeneratedDirective.__name__ = f"{func_name}_directive"
            GeneratedDirective.__qualname__ = f"{func_qualname}_directive"
            return GeneratedDirective

    return decorator
