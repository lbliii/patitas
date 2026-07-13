# Contributing to Patitas

Patitas protects Markdown correctness, immutable typed AST contracts, adversarial
input behavior, and Python 3.14 free-threading. Keep changes focused and leave an
executable proof near the behavior they affect.

## Setup and checks

```bash
uv sync --group dev
make test-fast
make lint
make ty
```

Run the complete pre-release gate before broad or release-facing changes:

```bash
make release-gate
```

That gate runs lint and format checks, `ty`, the non-slow suite in parallel,
the timing/performance-marked suite serially, and the non-slow suite with
coverage. Grammar changes also need `make commonmark`; performance changes need
the relevant benchmark and threshold checker.

Hosted CI runs the fast suite on both standard Python 3.14 with the GIL enabled
and free-threaded Python 3.14t with `PYTHON_GIL=0`. A change is not ready if it
works in only one interpreter lane.

## Coverage ratchet

The enforced floor is 80%. The 0.4.x non-slow suite currently measures 88%, so
the floor leaves cross-platform headroom without tolerating a large regression.
Never lower the floor to merge a change. Add focused tests or explicitly explain
why generated/unreachable code should be excluded.

Planned minimum floors are:

| Release line | Minimum floor |
| --- | ---: |
| 0.4.x | 80% |
| 0.5.x | 82% |
| 0.6.x | 85% |
| 1.0 | 90% |

Raise early when the measured suite supports it; do not wait for the target
release.

## Type-check ratchet

Correctness-class `ty` diagnostics are errors. A small set of non-correctness
rules remains warning/ignored in `pyproject.toml` while the codebase is narrowed.
Do not add new downgraded rules or broaden file exclusions. Promote one rule at
a time after its current findings are fixed, and keep optional imports guarded
with the exact current diagnostic code rather than a blanket suppression.

## Pull requests

- Add a focused regression test for behavior changes.
- Run the nearest scoped checks plus `make release-gate` for broad changes.
- Update README, docs, site, examples, and `CHANGELOG.md` when public behavior or
  claims change.
- Include benchmark context for performance claims and adversarial cases for
  security/parser hardening.
- Call out public API drift, dependency changes, CommonMark/GFM deltas, and any
  deferred risk in the PR description.
