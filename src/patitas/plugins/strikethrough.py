"""Strikethrough plugin for Patitas.

Adds support for ~~deleted~~ syntax.

Usage:
    >>> md = create_markdown(plugins=["strikethrough"])
    >>> md("~~deleted text~~")
    '<p><del>deleted text</del></p>'

Syntax:
~~text~~ → <del>text</del>

Strikethrough can contain other inline elements:
~~**bold deleted**~~ → <del><strong>bold deleted</strong></del>

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("strikethrough")
class StrikethroughPlugin:
    """Plugin adding ~~strikethrough~~ support.

    Extends inline parsing to recognize ~~ delimiters.

    Enable via Markdown(plugins=["strikethrough"]).

    Note: The actual parsing is controlled by ParseConfig.strikethrough_enabled,
    which is set by the Markdown class based on the plugins list.

    """

    @property
    def name(self) -> str:
        return "strikethrough"


# The actual parsing is integrated into the parser's inline handling.
# See parser.py _parse_inline_content() for the ~~ handling.
# The Strikethrough node is defined in nodes.py.
