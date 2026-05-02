# Test Steward

The test tree is the executable specification for CommonMark compliance, security invariants, extension behavior, public API stability, and regression confidence.

Related docs:
- root `AGENTS.md`
- `README.md`
- `benchmarks/README.md`
- `docs/security.md`

## Point Of View
Represent future contributors and downstream users who need failures to be precise, reproducible, and tied to real contracts.

## Protect
- `tests/fixtures/commonmark_spec_0_31_2.json` remains the CommonMark compliance source.
- Tests should encode behavior, edge cases, and contracts rather than current implementation accidents.
- Thread-safety tests must exercise real concurrency risks around ContextVar config, plugins, caches, and render contexts.
- Public API and docs examples should fail when imports or behavior drift.
- Keep tests deterministic and avoid environment-specific timing assertions unless explicitly benchmark-oriented.

## Advocate
- Reproduction tests for every bug fix before implementation changes when practical.
- Focused tests near the failure mode plus one integration test when boundaries are involved.
- Property/adversarial cases for parser, lexer, sanitizer, and plugin behavior.
- Better fixture names and comments for non-obvious CommonMark or security cases.

## Serve Peers
- Each code steward gets targeted tests that identify the owning domain.
- Docs/examples get import and behavior checks where possible.
- Benchmarks get correctness assertions separate from timing measurements.

## Do Not
- Update expected output just to make tests pass without explaining the behavior change.
- Hide flaky sleeps or timing thresholds in normal unit tests.
- Add broad snapshot assertions that obscure the specific contract being protected.
- Depend on private internals unless the test is explicitly for an internal invariant.

## Own
- Tests: all `tests/` files and fixtures.
- Checks: `make test`, `make test-fast`, `make commonmark`, `make test-cov` when coverage or shared behavior changes.
- Maintenance: remove stale `__pycache__`/local artifacts from commits, keep markers and fixture versions explicit.
