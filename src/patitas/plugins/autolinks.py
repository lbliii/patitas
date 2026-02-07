"""Autolinks plugin for Patitas.

Adds support for automatic URL and email detection.

Usage:
    >>> md = create_markdown(plugins=["autolinks"])
    >>> md("Visit https://example.com for more info.")
    '<p>Visit <a href="https://example.com">https://example.com</a> for more info.</p>'

Syntax:
URLs are automatically linked:
- http://example.com
- https://example.com
- www.example.com

Emails are automatically linked:
- user@example.com

Explicit autolinks (CommonMark):
- <https://example.com>
- <user@example.com>

Notes:
- URLs in code spans are not autolinked
- URLs in explicit links are not double-linked
- Trailing punctuation is handled smartly

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("autolinks")
class AutolinksPlugin:
    """Plugin for automatic URL and email linking.

    Extends inline parsing to detect URLs and emails without
    explicit markdown link syntax.

    Enable via Markdown(plugins=["autolinks"]).

    Note: The actual parsing is controlled by ParseConfig.autolinks_enabled,
    which is set by the Markdown class based on the plugins list.

    """

    @property
    def name(self) -> str:
        return "autolinks"


# Autolink detection is integrated into inline parsing.
# See:
# - parser.py: _parse_autolink() in inline content handling
# - Uses Link node with auto-generated children
