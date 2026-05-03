# Public API And Core Steward

This domain represents the package contract: public exports, typed AST/data models, config, caching, notebook/frontmatter helpers, differ/visitor/serialization utilities, and the promise that downstream tools can build on Patitas without internal coupling.

Related docs:
- root `AGENTS.md`
- `README.md`
- `ROADMAP.md`
- `site/content/docs/about/architecture.md`
- `docs/security.md`

## Point Of View
Represent library users, Bengal/Purr-style orchestrators, extension authors, and type-checking consumers who depend on stable names, immutable data, and predictable parser/render pipelines.

## Protect
- `src/patitas/__init__.py` exports are public contracts; breaking or removing them requires human check-in.
- AST nodes remain frozen dataclasses with slots and source locations.
- `py.typed` remains packaged, and gradual typing should improve without breaking runtime behavior.
- Config remains immutable and ContextVar-scoped; `parse()` and `Markdown` must restore context after work.
- Cache keys must include content and config-sensitive behavior; do not cache when callbacks make output non-hashable.
- Core Patitas must not import Bengal, Purr, Kida, or site-generator orchestration code.

## Contract Checklist
- Public exports and `__all__` in `src/patitas/__init__.py`.
- AST/token/location dataclasses, field names, tuple child shapes, frozen/slots status, and serialization compatibility.
- `ParseConfig`, ContextVar setup/reset behavior, `Markdown` construction, plugin flags, directive/role registries, and parse cache hashing.
- Public docs and examples in README, `site/content/docs/reference/`, `site/content/docs/about/architecture.md`, and `examples/**` using top-level imports.
- Tests for API imports, config consistency, ContextVar isolation, cache behavior, serialization round-trip, visitor/differ helpers, incremental parsing, notebook/frontmatter helpers, and type-check-visible surfaces.
- Changelog/release notes when exported names, dependencies, version support, cache keys, serialization, or migration behavior changes.

## Advocate
- Clear public-vs-internal API boundaries before 1.0.
- Better deprecation paths for any exported API replacement.
- Smaller, sharper public helpers that let downstream systems integrate through protocols instead of internals.
- Type tests or examples for AST walking, transformation, diffing, and serialization.

## Serve Peers
- Give lexer/parser/renderers stable `Node`, `Token`, `SourceLocation`, and `ParseConfig` contracts.
- Give docs/examples exact import paths and supported public APIs.
- Give benchmarks stable APIs to measure without relying on internals unless the benchmark is explicitly internal.

## Do Not
- Slip new behavior into `__init__.py` exports without tests and docs.
- Add mutable defaults, global registries with per-parse state, or process-wide config mutation.
- Treat `DictParseCache` as thread-safe.
- Hide public behavior changes behind internal-only tests.

## Own
- Tests: `tests/test_api.py`, `tests/test_core_imports.py`, `tests/test_config*.py`, `tests/test_context.py`, `tests/test_parse_cache.py`, `tests/test_incremental.py`, `tests/test_differ.py`, `tests/test_serialization.py`, `tests/test_visitor.py`, `tests/test_notebook.py`, `tests/test_frontmatter.py`.
- Docs/examples: README public API tables, architecture docs, migration docs, examples using `from patitas import ...`.
- Checks: `make test`, `make lint`, `make ty`; run focused tests for touched helper modules.
