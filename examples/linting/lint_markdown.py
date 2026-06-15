"""Content linting — flag Markdown issues over the typed AST + raw source.

Shows the headline ``lint(source)`` path, a custom rule via the ``LintRule``
protocol, and a reusable ``Linter`` bound to a registry.
"""

from dataclasses import dataclass
from typing import ClassVar

from patitas import Diagnostic, Severity, lint
from patitas.linting import Linter, LintRuleRegistryBuilder, create_default_lint_registry
from patitas.location import SourceLocation

source = """# Title

### Skipped a level

[](https://example.com)

trailing here
"""

# 1. The trivial path: pass a string, get a sorted list[Diagnostic].
print("Default rules:")
for diag in lint(source):
    print(f"  {diag}")


# 2. A custom rule is a stateless frozen dataclass implementing LintRule.
@dataclass(frozen=True, slots=True)
class NoTabsRule:
    """Flag any source line containing a tab character."""

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


print("\nCustom rule only:")
for diag in lint("ok\n\tindented", rules=[NoTabsRule()]):
    print(f"  {diag}")

# 3. Compose the built-ins + a custom rule into a reusable, thread-safe Linter.
registry = (
    LintRuleRegistryBuilder()
    .register_all(create_default_lint_registry().rules)
    .register(NoTabsRule())
    .build()
)
linter = Linter(registry)  # immutable; safe to share across threads

print("\nLinter with built-ins + custom rule:")
for diag in linter.lint("# Title\n\n\tindented"):
    print(f"  {diag}")
