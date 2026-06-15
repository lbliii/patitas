# Linting

Patitas ships a small content linter — a ruff-for-Markdown — that walks the
typed AST and scans the raw source, emitting structured `Diagnostic`s. Rules are
stateless and the runner is created fresh per call, so the linter is safe to use
under free-threaded Python.

## Quick start

```python
from patitas import lint

source = "# Title\n\n### Skipped a level   "

for diag in lint(source):
    print(diag)
# 3:20: [trailing-whitespace] Trailing whitespace (3 character(s))
# 3:1: [heading-increment] Heading level skipped: expected h2 or lower after h1, found h3
```

`lint()` returns a materialized `list[Diagnostic]`, sorted by document position
`(offset, line, col, rule_id)` so output is stable for snapshots and CLIs.

Each `Diagnostic` carries:

- `rule_id` — the kebab-case rule that produced it (e.g. `heading-increment`).
- `message` — a single-line, human-readable description.
- `location` — a `SourceLocation` (`str(diag)` renders `file:line:col: [rule-id] message`).
- `severity` — a `Severity` (`ERROR` / `WARNING` / `INFO`); `severity.to_lsp()`
  gives the LSP `DiagnosticSeverity` integer.

## Built-in rules

| id | severity | description | source |
| --- | --- | --- | --- |
| `heading-increment` | WARNING | A heading whose level is more than one greater than the previous heading (e.g. `h1` → `h3`). The first heading may start at any level. | AST |
| `no-empty-link` | WARNING | A link with no visible text (no children, or only whitespace). Image-only and code-span links are not flagged. | AST |
| `trailing-whitespace` | INFO | A source line ending in spaces/tabs, excluding lines inside fenced/indented code blocks. | source |

## Pre-parsed documents

If you already have a `Document`, pass it directly and supply the raw source via
`text=` so source-driven rules (like `trailing-whitespace`) still run:

```python
from patitas import lint, parse

source = "# Title\n\ntrailing here   "
doc = parse(source, source_file="page.md")

diags = lint(doc, text=source, source_file="page.md")
```

If you omit `text=`, AST rules still run but source-driven rules have no input.
For the trivial path, prefer `lint(source_string)` — it captures the source for
you and runs every rule.

## Writing a custom rule

A rule implements the `LintRule` protocol: two class variables and one method.
Rules must be stateless (all per-run state lives in `check`).

```python
from dataclasses import dataclass
from typing import ClassVar

from patitas import Diagnostic, Severity, lint
from patitas.location import SourceLocation


@dataclass(frozen=True, slots=True)
class NoTabsRule:
    rule_id: ClassVar[str] = "no-tabs"
    default_severity: ClassVar[Severity] = Severity.WARNING

    def check(self, ctx):
        for i, line in enumerate(ctx.lines, start=1):
            col = line.find("\t")
            if col != -1:
                yield Diagnostic(
                    rule_id=self.rule_id,
                    message="Line contains a tab character",
                    location=SourceLocation(
                        lineno=i, col_offset=col + 1, source_file=ctx.source_file
                    ),
                )


diags = lint("ok\n\tindented", rules=[NoTabsRule()])
```

The `ctx` argument is a `LintContext` carrying `ctx.document`, `ctx.source`,
`ctx.source_file`, `ctx.lines`, and the document-order accessors
`ctx.headings()` / `ctx.nodes_of_type(SomeNode)`. The runner stamps `rule_id`
and `severity` onto each diagnostic from the emitting rule, so they can never
drift from the producing rule.

To compose rules into a reusable set, build a registry:

```python
from patitas.linting import LintRuleRegistryBuilder, Linter, create_default_lint_registry

registry = (
    LintRuleRegistryBuilder()
    .register_all(create_default_lint_registry().rules)
    .register(NoTabsRule())
    .build()
)
linter = Linter(registry)  # immutable; safe to share across threads
diags = linter.lint("# Title\n\n\tindented")
```

## Thread safety

Rules are stateless frozen dataclasses, the `LintRuleRegistry`/`Linter` are
immutable, and each `lint()` call builds its own context and accumulator. A
single `Linter` (or registry) is safe to share across threads; the only
per-call mutable state is created fresh inside each call.

## Position precision (known limitations)

Diagnostics reuse the offending node's `SourceLocation`. Two limitations follow
from how the parser populates locations and are out of scope for the initial
linter:

- **Inline diagnostics are block-granular.** All inline children of a block
  share the enclosing block's single location, so `no-empty-link` is reported at
  the start of the enclosing block, not the exact link column. The link URL is
  included in the message to disambiguate multiple empty links in one block.
- **Nested-block positions can be approximate.** A heading or code block nested
  inside a block quote or list item may carry an inner-buffer-relative line
  number. Top-level positions are exact; deeply nested ones are best-effort. For
  the same reason, `trailing-whitespace` excludes only *top-level* code blocks.

## Dogfooding

You can lint the repo's own Markdown — diagnostics are data, not exceptions:

```python
from pathlib import Path

from patitas import lint, parse

for path in sorted(Path("docs").glob("*.md")):
    source = path.read_text(encoding="utf-8")
    doc = parse(source, source_file=str(path))
    for diag in lint(doc, text=source, source_file=str(path)):
        print(diag)
```
