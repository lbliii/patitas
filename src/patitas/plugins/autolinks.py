"""Autolinks plugin for Patitas.

Enables GFM **extended** autolinks: bare URLs, ``www.`` links, and bare email
addresses are turned into links inside ordinary inline text. This implements
the GFM "Autolinks (extension)" rules:
https://github.github.com/gfm/#autolinks-extension-

    >>> from patitas import Markdown
    >>> Markdown(plugins=["autolinks"])("Visit https://example.com now")
    '<p>Visit <a href="https://example.com">https://example.com</a> now</p>\\n'
    >>> Markdown(plugins=["autolinks"])("See www.example.com")
    '<p>See <a href="http://www.example.com">www.example.com</a></p>\\n'
    >>> Markdown(plugins=["autolinks"])("Mail foo@example.com")
    '<p>Mail <a href="mailto:foo@example.com">foo@example.com</a></p>\\n'

Recognized forms (only when this plugin is enabled):
- bare URLs:   ``http://example.com``, ``https://example.com``
- www links:   ``www.example.com`` (rendered href gets ``http://`` prepended;
               the link text keeps the original ``www.`` text)
- bare emails: ``user@example.com`` (href ``mailto:...``)

Rules applied (per the GFM extension):
- An autolink is recognized only at a *left boundary*: start-of-line/text,
  after whitespace, or after one of ``* _ ~ (``.
- Trailing punctuation (``? ! . , : * _ ~``) is excluded from the link. A
  trailing ``)`` is excluded when there are more ``)`` than ``(`` in the match.
  A trailing entity reference (``&...;``) is stripped.
- ``<`` immediately ends the autolink. The authority must contain at least one
  ``.`` and no spaces.

CommonMark **angle-bracket** autolinks work without this plugin:

    >>> Markdown()("Visit <https://example.com>")
    '<p>Visit <a href="https://example.com">https://example.com</a></p>\\n'

Known limitation: because emphasis delimiters ``_`` are tokenized before this
scan runs, an underscore inside a URL path/local-part can split the surrounding
text and truncate the autolink (e.g. a Wikipedia URL containing ``Foo_(bar)``).
Bare URLs without underscores, and all forms above, are handled.

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("autolinks")
class AutolinksPlugin:
    """Plugin enabling automatic (GFM extended) URL and email linking.

    Enabling via ``Markdown(plugins=["autolinks"])`` sets
    ``ParseConfig.autolinks_enabled``, which the inline tokenizer consults to
    scan plain-text runs for bare URLs, ``www.`` links, and emails. CommonMark
    angle-bracket autolinks ``<https://...>`` already work without this plugin.
    """

    @property
    def name(self) -> str:
        return "autolinks"
