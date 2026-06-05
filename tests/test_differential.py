"""Differential fuzzing harness: patitas vs. a second reference parser.

This is a *second oracle*. Where ``tests/test_commonmark_spec.py`` checks
patitas against the spec's expected HTML, this module renders the same
CommonMark spec examples with both patitas and ``markdown-it-py``
(``MarkdownIt("commonmark")``) and compares normalized HTML.

The two parsers are not byte-identical everywhere (e.g. patitas emits a newline
inside empty ``<blockquote>`` elements where markdown-it-py does not), so this is
a **ratchet / informational** harness rather than a hard per-example gate:

* It asserts the number of agreeing examples is ``>=`` a measured baseline, so a
  regression that breaks previously-agreeing output fails CI.
* It collects every disagreement and reports a compact summary, so divergences
  are visible without flaking.

Marked ``slow`` so it stays out of the default fast loop (run with
``pytest -m slow``). A nightly job can run the slow suite.

Baseline (measured 2026-06, CommonMark 0.31.2, 652 examples):
    agree=649, disagree=3 (all the empty-blockquote whitespace cosmetic diff).
We set the floor a touch below the measured number to absorb harmless
reference-library churn while still catching real regressions.
"""

import json
from pathlib import Path

import pytest

from patitas import parse, render
from tests.test_commonmark_spec import normalize_for_comparison

pytestmark = pytest.mark.slow

markdown_it = pytest.importorskip("markdown_it")

SPEC_PATH = Path(__file__).parent / "fixtures" / "commonmark_spec_0_31_2.json"

# Floor: the number of spec examples whose normalized HTML must match the
# reference parser. Measured agreement is 649/652; we require >= 645 so a
# reference-library patch nudging a couple of cosmetic cases does not flake the
# build, while any real regression (which moves the number by far more) fails.
AGREEMENT_FLOOR = 645


def _load_examples() -> list[dict]:
    if not SPEC_PATH.exists():
        return []
    return json.loads(SPEC_PATH.read_text())


def _render_patitas(md: str) -> str:
    return render(parse(md), source=md)


def test_differential_agreement_meets_ratchet() -> None:
    """Patitas must agree with markdown-it-py on >= AGREEMENT_FLOOR examples."""
    examples = _load_examples()
    if not examples:
        pytest.skip("CommonMark spec fixture not found")

    mit = markdown_it.MarkdownIt("commonmark")

    agree = 0
    disagreements: list[tuple[int, str, str, str, str]] = []
    errors: list[tuple[int, str]] = []

    for ex in examples:
        md = ex["markdown"]
        try:
            ours = _render_patitas(md)
        except Exception as exc:
            errors.append((ex["example"], f"{type(exc).__name__}: {exc}"))
            continue
        theirs = mit.render(md)
        ref_norm, ours_norm = normalize_for_comparison(theirs, ours)
        if ref_norm == ours_norm:
            agree += 1
        else:
            disagreements.append((ex["example"], ex["section"], md, theirs, ours))

    total = len(examples)

    # Informational report (visible with -s / on failure).
    print(
        f"\n[differential] total={total} agree={agree} "
        f"disagree={len(disagreements)} errors={len(errors)} "
        f"floor={AGREEMENT_FLOOR}"
    )
    if disagreements:
        print("[differential] disagreeing examples:")
        for num, section, md, theirs, ours in disagreements[:25]:
            print(f"  #{num} ({section})")
            print(f"      md    : {md!r}")
            print(f"      ref   : {theirs!r}")
            print(f"      ours  : {ours!r}")
        if len(disagreements) > 25:
            print(f"  ... and {len(disagreements) - 25} more")

    # Patitas must never raise on a valid spec example.
    assert not errors, f"patitas raised on {len(errors)} spec example(s): {errors[:5]}"

    # Ratchet: agreement must not regress below the measured floor.
    assert agree >= AGREEMENT_FLOOR, (
        f"Differential agreement regressed: {agree}/{total} agree with "
        f"markdown-it-py, below floor {AGREEMENT_FLOOR}. "
        f"{len(disagreements)} disagreement(s); see report above."
    )


def test_both_parsers_produce_strings_and_never_crash() -> None:
    """Sanity: both oracles return strings for every spec example."""
    examples = _load_examples()
    if not examples:
        pytest.skip("CommonMark spec fixture not found")

    mit = markdown_it.MarkdownIt("commonmark")
    for ex in examples:
        md = ex["markdown"]
        ours = _render_patitas(md)
        theirs = mit.render(md)
        assert isinstance(ours, str)
        assert isinstance(theirs, str)
