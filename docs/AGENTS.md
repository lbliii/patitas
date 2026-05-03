# Reference Docs Steward

The `docs/` tree owns focused reference guidance that supports security, performance interpretation, and migration from other Markdown parsers.

Related docs:
- root `AGENTS.md`
- `README.md`
- `site/content/docs/`
- `benchmarks/README.md`

## Point Of View
Represent adopters evaluating risk: security reviewers, migration owners, and performance-sensitive operators.

## Protect
- `docs/security.md` must stay aligned with actual lexer, renderer, sanitizer, and URL behavior.
- `docs/performance-investigation.md` must distinguish architectural tradeoffs from regressions and cite benchmark context.
- `docs/migrate-from-mistune.md` must use working public APIs and accurate syntax differences.
- Security reporting guidance should not encourage public disclosure of sensitive issues.

## Contract Checklist
- Security claims against lexer progress, regex avoidance, sanitizer policies, HTML escaping, URL behavior, and LLM-safety tests.
- Performance claims against current benchmark scripts, command lines, environment caveats, and README/site numbers.
- Migration examples against top-level public imports, plugin names, directive APIs, frontmatter/notebook helpers, and current dependency/extras behavior.
- Cross-links from README and site docs to `docs/**`, including stale filenames, headings, and release-specific claims.
- Changelog/release notes when documentation updates describe changed public behavior, dependency surface, security posture, or performance evidence.
- Focused snippet or test execution when examples are non-trivial and use public APIs.

## Advocate
- Updating docs in the same change as security, migration, plugin, renderer, or benchmark behavior changes.
- Short runnable examples over broad claims.
- Explicit caveats where behavior depends on plugin flags, optional extras, Python version, or downstream sanitization.

## Serve Peers
- Lexer/renderers get precise security language.
- Benchmarks get documented interpretation of results.
- Site docs can link to stable deep-dive references rather than duplicating all details.

## Do Not
- Claim ReDoS, escaping, or sanitizer properties that are not covered by tests.
- Let migration examples use deprecated or imaginary APIs.
- State performance wins without a current benchmark command and context.

## Own
- Files: `docs/security.md`, `docs/performance-investigation.md`, `docs/migrate-from-mistune.md`.
- Checks: run examples mentally and, when changed materially, with `uv run python` or focused tests; run relevant security/performance tests for behavior claims.
