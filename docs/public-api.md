# Public API & Stability Contract (1.0)

Patitas follows a clear boundary between its **supported public API** and its
**internal implementation**. The public API is everything exported from the
top-level `patitas` package (i.e. the names in `patitas.__all__`). These symbols
follow semantic-versioning stability guarantees for 1.0: they will not be
removed or changed incompatibly within a major version without a deprecation
period.

Everything else — submodules, helper functions, private attributes — is
**internal** and may change without notice between any two releases, including
patch releases.

## Supported public API

Import these from the top level, e.g. `from patitas import Markdown, parse`.

### Core

- `parse` — parse Markdown source into a `Document` AST.
- `render` — render a `Document` AST to HTML.
- `parse_notebook` — parse a Jupyter notebook into a `Document`.
- `Markdown` — high-level parse + render processor.

### Parse cache

- `ParseCache`, `DictParseCache`, `hash_config`, `hash_content`

### AST nodes

- Block nodes: `Block`, `BlockQuote`, `Document`, `FencedCode`, `FootnoteDef`,
  `Heading`, `HtmlBlock`, `IndentedCode`, `List`, `ListItem`, `MathBlock`,
  `Paragraph`, `Table`, `TableCell`, `TableRow`, `ThematicBreak`
- Inline nodes: `Inline`, `CodeSpan`, `Emphasis`, `FootnoteRef`, `HtmlInline`,
  `Image`, `LineBreak`, `Link`, `Math`, `Role`, `SoftBreak`, `Strikethrough`,
  `Strong`, `Text`

### Directive extensibility

- `Directive`, `DirectiveRegistry`, `DirectiveRegistryBuilder`,
  `create_default_registry`, `create_registry_with_defaults`, `directive`

### Roles (inline `{role}` `` `content` `` extensibility)

- `RoleHandler` — protocol to implement a custom inline role.
- `RoleRegistry` — immutable registry of role handlers.
- `RoleRegistryBuilder` — mutable builder for a `RoleRegistry`.
- `create_default_role_registry` — factory returning the built-in roles
  (`ref`, `doc`, `kbd`, `abbr`, `math`, `sub`, `sup`, `icon`).

  The built-in roles render out of the box: `` Markdown()("{kbd}`Ctrl`") ``
  produces `<kbd>Ctrl</kbd>`. Pass a custom `role_registry=` to `Markdown`,
  `render`, to override or extend them.

### Linting

- `lint` — lint Markdown (a string or a pre-parsed `Document`) and return a
  sorted `list[Diagnostic]`.
- `Diagnostic` — a single lint finding (rule id, message, `SourceLocation`,
  `Severity`). Reuses `SourceLocation`; `str(diag)` prints
  `file:line:col: [rule-id] message`.
- `LintRule` — `@runtime_checkable` protocol for custom rules (`rule_id` /
  `default_severity` class vars + a `check(ctx)` method).
- `Severity` — `ERROR` / `WARNING` / `INFO` enum, with `.to_lsp()` for the LSP
  `DiagnosticSeverity` integer.

  The rich surface — `Linter`, `LintContext`, `LintRuleRegistry`,
  `LintRuleRegistryBuilder`, `create_default_lint_registry`, and the built-in
  rule classes — lives in the `patitas.linting` submodule. See `docs/linting.md`.

### Renderers

- `HtmlRenderer`, `LlmRenderer`, `render_llm`, `ASTRenderer`

### Text & content helpers

- `extract_text`, `extract_excerpt`, `extract_meta_description`
- `sanitize`, `Policy`
- `parse_frontmatter`, `extract_body`
- `parse_incremental`
- `CONTENT_CONTEXT_MAP`, `context_paths_for`

### Visitor & transform

- `BaseVisitor`, `transform`

### Diffing

- `ASTChange`, `diff_documents`

### Profiling

- `ParseAccumulator`, `profiled_parse`, `get_parse_accumulator`

### Serialization

- `to_dict`, `from_dict`, `to_json`, `from_json`

### Configuration (ContextVar-based)

- `ParseConfig`, `get_parse_config`, `set_parse_config`, `reset_parse_config`,
  `parse_config_context`

### Low-level building blocks

- `Lexer`, `Parser`, `SourceLocation`, `Token`, `TokenType`

### Version

- `__version__`

## Internal modules — NOT part of the stability contract

The following are implementation details. **Do not import from them.** They may
be renamed, restructured, or removed at any time without a deprecation period:

- `patitas.lexer` (use the top-level `Lexer` if you need it)
- `patitas.parser` (use the top-level `Parser`)
- `patitas.parsing.*` (block and inline parsing internals)
- `patitas.renderers.*` internals (helpers, render context, string builder)
- `patitas.tokens` internals beyond `Token` / `TokenType`
- `patitas.nodes` internals beyond the exported node classes
- `patitas.directives.*` and `patitas.roles.*` submodules — use the top-level
  directive/role API instead
- `patitas.stringbuilder`, `patitas.cache` internals, `patitas.profiling`
  internals, and any module or attribute prefixed with `_`

If you find yourself needing something that is only available via an internal
module, please open an issue so it can be considered for promotion to the
public API.

> Note: this boundary is enforced by `tests/test_public_api.py`, which pins the
> exact contents of `patitas.__all__`. Adding or removing a public symbol will
> fail CI until the pin (and this document) are updated deliberately.
