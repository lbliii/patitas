"""Autolinks plugin for Patitas.

.. warning::

    GFM **extended** autolinks (bare ``https://...``, ``www....``, and bare
    ``user@example.com``) are NOT yet implemented. Enabling this plugin sets
    ``ParseConfig.autolinks_enabled`` but no parsing code consumes that flag
    today, so bare URLs are currently left as plain text. Tracking issue:
    "implement GFM extended autolinks".

CommonMark **angle-bracket** autolinks work without this plugin:

    >>> from patitas import Markdown
    >>> Markdown()("Visit <https://example.com>")
    '<p>Visit <a href="https://example.com">https://example.com</a></p>\\n'

Planned syntax (once implemented):
- bare URLs:   http://example.com, https://example.com, www.example.com
- bare emails: user@example.com

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("autolinks")
class AutolinksPlugin:
    """Plugin stub for automatic (GFM extended) URL and email linking.

    Enabling via ``Markdown(plugins=["autolinks"])`` sets
    ``ParseConfig.autolinks_enabled``. The bare-URL/email parsing behavior is
    not yet wired up (see module docstring); CommonMark angle-bracket autolinks
    ``<https://...>`` already work without this plugin.
    """

    @property
    def name(self) -> str:
        return "autolinks"
