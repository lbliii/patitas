"""Task list plugin for Patitas.

Adds support for checkbox task lists.

Usage:
    >>> md = create_markdown(plugins=["task_lists"])
    >>> md("- [ ] Unchecked\n- [x] Checked")
    '<ul><li class="task-list-item"><input type="checkbox" disabled> Unchecked</li>...'

Syntax:
- [ ] Unchecked task
- [x] Checked task
- [X] Also checked (uppercase)

Works with ordered lists too:
1. [ ] First task
2. [x] Second task

Notes:
- Checkboxes are rendered disabled by default
- The ListItem node has a `checked` field (True/False/None)
- Task list support is enabled by default in core parser

Thread Safety:
This plugin is stateless and thread-safe.

"""

from patitas.plugins import register_plugin


@register_plugin("task_lists")
class TaskListPlugin:
    """Plugin for task list checkbox support.

    Task lists are built into the core parser via the ListItem.checked field.
    Enable via Markdown(plugins=["task_lists"]).

    Note: The actual parsing is controlled by ParseConfig.task_lists_enabled,
    which is set by the Markdown class based on the plugins list.

    """

    @property
    def name(self) -> str:
        return "task_lists"


# Task list parsing is integrated into list handling.
# See:
# - parser.py: _parse_list_item() checks for [ ] / [x] / [X]
# - nodes.py: ListItem has checked: bool | None field
# - html.py: _render_list_item() renders checkbox
