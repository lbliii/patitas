"""Table plugin for Patitas (GFM-style pipe tables).

Adds support for GitHub-Flavored Markdown tables.

Usage:
    >>> md = create_markdown(plugins=["table"])
    >>> md("| A | B |\n|---|---|\n| 1 | 2 |")
    '<table><thead><tr><th>A</th><th>B</th></tr></thead>...'

Syntax:
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

Alignment:
| Left | Center | Right |
|:-----|:------:|------:|
| L    |   C    |     R |

Features:
- Column alignment via :--- :--: ---:
- Inline markdown in cells
- Pipes can be escaped with ``\\|``

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("table")
class TablePlugin:
    """Plugin adding GFM table support.

    Tables are detected at the block level when a line starts with |
    and is followed by a delimiter row (|---|---|).

    Enable via Markdown(plugins=["table"]).

    Note: The actual parsing is controlled by ParseConfig.tables_enabled,
    which is set by the Markdown class based on the plugins list.

    """

    @property
    def name(self) -> str:
        return "table"


# Table parsing is integrated into the lexer and parser.
# See:
# - lexer.py: _is_table_row(), _scan_table()
# - parser.py: _parse_table()
# - nodes.py: Table, TableRow, TableCell
