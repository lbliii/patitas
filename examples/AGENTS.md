# Examples Steward

Examples are runnable contracts showing real use of the public API for basic parsing, AST work, directives, plugins, notebooks, incremental parsing, diffing, parallelism, serialization, and LLM-safe output.

Related docs:
- root `AGENTS.md`
- `examples/README.md`
- `README.md`
- `site/content/docs/get-started/examples.md`

## Point Of View
Represent users copying code into their projects and maintainers checking that advertised workflows still work.

## Protect
- Examples should run from the repo root with `uv run python ...` and use public imports.
- Each example should demonstrate one workflow clearly without hidden services or undeclared dependencies.
- Notebook examples stay stdlib-only unless an optional dependency is explicitly documented.
- LLM-safety examples must sanitize before rendering untrusted content.
- Parallel examples must not imply unsafe cache or mutable state sharing.

## Contract Checklist
- Touched examples run from repo root with documented commands and public imports.
- README/site/docs links and feature tables point to existing example paths with matching behavior.
- Optional extras, environment requirements, notebook inputs, syntax highlighting, and filesystem assumptions are stated near examples that need them.
- Output expectations stay aligned with renderer, sanitizer, directive, plugin, role, notebook/frontmatter, incremental, differ, serialization, and visitor behavior.
- Tests or lightweight execution cover examples that advertise new public APIs or migration paths.
- Changelog/release notes mention new or materially changed examples when they support a released feature.

## Advocate
- Add or update an example when adding public API, extension behavior, or a migration path.
- Keep examples small enough to read but complete enough to run.
- Mirror examples in docs/site only when the code stays synchronized.

## Serve Peers
- Public API, directive, plugin, renderer, and docs stewards get runnable proof that their guidance works.
- Tests can import or execute examples for drift detection when practical.

## Do Not
- Use private modules in user-facing examples unless the file is explicitly advanced/internal.
- Add examples that require optional extras without documenting installation.
- Print benchmark-like claims from examples; keep performance evidence in benchmarks.
- Let README tables list examples that do not exist or no longer run.

## Own
- Files: `examples/README.md` and all `examples/**`.
- Checks: run touched examples with `uv run python`; update docs/site references when paths or outputs change.
