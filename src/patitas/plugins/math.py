"""Math plugin for Patitas.

Adds support for LaTeX-style math expressions.

Usage:
    >>> md = create_markdown(plugins=["math"])
    >>> md("Inline: $E = mc^2$")
    '<p>Inline: <span class="math">E = mc^2</span></p>'
    >>> md("$$\nE = mc^2\n$$")
    '<div class="math-block">E = mc^2</div>'

Syntax:
Inline math: $expression$
Block math: $$expression$$ (on separate lines)

Escaping:
- ``\\$`` for literal dollar sign
- Inside code spans, $ is literal

Notes:
- This plugin outputs semantic HTML classes
- Actual math rendering (MathJax, KaTeX) is done client-side
- Block math with display mode is on separate lines

Thread Safety:
This plugin is stateless and thread-safe.

"""

from __future__ import annotations

from patitas.plugins import register_plugin


@register_plugin("math")
class MathPlugin:
    """Plugin adding $math$ and $$math$$ support.

    Inline math uses $...$ syntax.
    Block math uses $$...$$ on separate lines.

    Enable via Markdown(plugins=["math"]).

    Note: The actual parsing is controlled by ParseConfig.math_enabled,
    which is set by the Markdown class based on the plugins list.

    """

    @property
    def name(self) -> str:
        return "math"


# Math parsing is integrated into lexer and parser.
# See:
# - lexer.py: _scan_math_block()
# - parser.py: _parse_inline_math(), _parse_math_block()
# - nodes.py: Math, MathBlock
