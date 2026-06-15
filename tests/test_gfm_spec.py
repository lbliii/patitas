"""GitHub Flavored Markdown (GFM) 0.29 Specification Compliance Tests.

This module runs the official GFM spec examples against Patitas with the GFM
feature plugins enabled (table, strikethrough, task_lists, autolinks). The
fixture (tests/fixtures/gfm_spec_0_29.json) is extracted from the upstream
spec.txt at version 0.29 (CC-BY-SA 4.0); see GFM_SPEC_LICENSE.txt.

Patitas does NOT target 100% of GFM 0.29. Two structural reasons account for
the bulk of the gap:

1. Spec version drift. GFM 0.29 is built on CommonMark 0.28, whereas Patitas
   targets CommonMark 0.31.2. Several emphasis examples have different expected
   nesting between those CommonMark versions; Patitas matches its 0.31.2 target
   (those exact examples PASS in test_commonmark_spec.py) but "fails" the older
   GFM 0.29 expectation.
2. Unimplemented extensions: GFM extended autolinks (bare ``www.``/URL/email)
   and the tagfilter (disallowed raw HTML) extension are not implemented.

So rather than asserting every example, we:
- Run every example and xfail the known-failing ones (KNOWN_FAIL) with reasons.
- Track the aggregate pass count via a ratchet test (test_gfm_pass_rate) that
  prints ``GFM: N/M`` and asserts N never drops below a measured baseline.

Usage:
    pytest tests/test_gfm_spec.py -m gfm
    pytest tests/test_gfm_spec.py -k "example_199" -m gfm
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Reuse the CommonMark normalizer so comparison rules stay identical.
from tests.test_commonmark_spec import normalize_for_comparison

SPEC_PATH = Path(__file__).parent / "fixtures" / "gfm_spec_0_29.json"

# GFM feature set under test.
GFM_PLUGINS = ["table", "strikethrough", "task_lists", "autolinks"]


def _load_spec() -> list[dict[str, Any]]:
    """Load GFM spec tests, returning empty list if fixture not found."""
    if not SPEC_PATH.exists():
        return []
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


SPEC_TESTS: list[dict[str, Any]] = _load_spec()

# Measured pass-count baseline (ratchet). Update upward only — never lower it to
# accommodate a regression. Measured against GFM 0.29 with GFM_PLUGINS enabled.
GFM_PASS_BASELINE = 654
GFM_TOTAL = 672

# Known-failing examples with honest reasons. Each is xfailed (strict=False) so
# the suite stays green while still surfacing any that start passing (XPASS).
KNOWN_FAIL: dict[int, str] = {
    # --- Tables (extension) ---
    199: (
        'Alignment rendered via inline style (style="text-align: ...") rather '
        'than GFM\'s align="..." attribute. Cosmetic rendering choice.'
    ),
    202: (
        "GFM lazily extends a table with a following paragraph-continuation row; "
        "Patitas does not append non-row continuation lines to a table."
    ),
    # --- Task list items (extension) ---
    279: (
        "Two intentional divergences from the GFM 0.29 fixture: (1) Patitas "
        "adds the 'contains-task-list' class on the <ul> and 'task-list-item' "
        "on each task <li>, which the fixture omits; (2) <input> attribute "
        "format/order differs (Patitas emits "
        "'<input type=\"checkbox\" disabled />', GFM emits "
        '\'<input disabled="" type="checkbox">\'). Both are semantically '
        "equivalent."
    ),
    280: (
        "Nested task list: same two intentional divergences as example 279 -- "
        "the added 'contains-task-list'/'task-list-item' classes (absent from "
        "the fixture) plus the <input> attribute format/order difference."
    ),
    # --- Emphasis and strong emphasis (CommonMark version drift) ---
    # GFM 0.29 is based on CommonMark 0.28; Patitas targets 0.31.2 and matches
    # the 0.31.2 expected output for these exact inputs (they pass in
    # test_commonmark_spec.py). The GFM 0.29 fixture encodes the older behavior.
    398: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    426: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    434: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    435: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    436: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    473: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    474: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    475: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    477: "CommonMark 0.28 vs 0.31.2 emphasis nesting drift (Patitas matches 0.31.2).",
    # --- Autolinks (core CommonMark section): these examples assume the GFM
    # extended-autolink extension is OFF. With the extension enabled (as GFM
    # intends, and as the `autolinks` plugin does here), Patitas links the bare
    # URL/email, so it diverges from these pre-extension examples. ---
    616: (
        "Core CommonMark 'Autolinks' example assuming the extended-autolink "
        "extension is off; with it enabled Patitas links the bare URL."
    ),
    619: (
        "Core CommonMark 'Autolinks' example assuming the extended-autolink "
        "extension is off; with it enabled Patitas links the bare URL."
    ),
    620: (
        "Core CommonMark 'Autolinks' example assuming the extended-autolink "
        "extension is off; with it enabled Patitas links the bare email."
    ),
    # --- Autolinks (extension): two remaining edge cases (621-627, 629-630
    # now PASS). ---
    628: (
        "GFM extended autolink: Patitas links the http(s) sub-cases but not the "
        "ftp:// one in this example (only http/https/www/mailto are linkified)."
    ),
    # --- Disallowed Raw HTML (extension) ---
    652: "GFM tagfilter (disallowed raw HTML) extension not implemented.",
}


def _render(markdown: str) -> str:
    """Render markdown with GFM plugins enabled, mirroring Markdown.parse()."""
    from patitas import Markdown

    md = Markdown(plugins=GFM_PLUGINS)
    return md(markdown)


def pytest_generate_tests(metafunc: Any) -> None:
    """Generate one test per GFM spec example."""
    if "gfm_example" in metafunc.fixturenames:
        if not SPEC_TESTS:
            metafunc.parametrize("gfm_example", [{}], ids=["no_spec_found"])
            return
        ids = [
            f"example_{ex['example']:03d}_{ex['section'].replace(' ', '_')}" for ex in SPEC_TESTS
        ]
        metafunc.parametrize("gfm_example", SPEC_TESTS, ids=ids)


@pytest.mark.gfm
class TestGfmSpec:
    """Official GFM 0.29 specification tests (GFM features enabled)."""

    def test_gfm_example(self, gfm_example: dict[str, Any]) -> None:
        """Test a single GFM spec example."""
        if not gfm_example:
            pytest.skip("GFM spec fixture not found")

        example_num = gfm_example["example"]
        if example_num in KNOWN_FAIL:
            pytest.xfail(KNOWN_FAIL[example_num])

        markdown = gfm_example["markdown"]
        expected_html = gfm_example["html"]
        section = gfm_example["section"]

        try:
            actual_html = _render(markdown)
        except Exception as e:  # pragma: no cover - defensive
            pytest.fail(f"Parser/renderer error: {e}")

        expected_norm, actual_norm = normalize_for_comparison(expected_html, actual_html)

        assert actual_norm == expected_norm, (
            f"\n\nGFM example {example_num} ({section}) failed:\n"
            f"\n--- Markdown ---\n{markdown!r}\n"
            f"\n--- Expected ---\n{expected_html!r}\n"
            f"\n--- Actual ---\n{actual_html!r}\n"
            f"\n--- Expected (normalized) ---\n{expected_norm!r}\n"
            f"\n--- Actual (normalized) ---\n{actual_norm!r}\n"
        )


@pytest.mark.gfm
class TestGfmBaseline:
    """Aggregate GFM compliance tracking."""

    def test_total_examples(self) -> None:
        """Verify the fixture has the expected number of examples."""
        if not SPEC_TESTS:
            pytest.skip("GFM spec fixture not found")
        assert len(SPEC_TESTS) == GFM_TOTAL, (
            f"Expected {GFM_TOTAL} GFM examples, got {len(SPEC_TESTS)}"
        )

    def test_example_structure(self) -> None:
        """Verify every example has the required keys."""
        if not SPEC_TESTS:
            pytest.skip("GFM spec fixture not found")
        for ex in SPEC_TESTS:
            assert {"markdown", "html", "example", "section"} <= ex.keys()

    def test_gfm_pass_rate(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ratchet: measured pass count must not drop below the baseline.

        Prints ``GFM: N/M`` for visibility. Raise GFM_PASS_BASELINE when the
        pass count improves; never lower it to mask a regression.
        """
        if not SPEC_TESTS:
            pytest.skip("GFM spec fixture not found")

        passed = 0
        for ex in SPEC_TESTS:
            try:
                actual = _render(ex["markdown"])
            except Exception:
                continue
            expected_norm, actual_norm = normalize_for_comparison(ex["html"], actual)
            if expected_norm == actual_norm:
                passed += 1

        total = len(SPEC_TESTS)
        with capsys.disabled():
            print(f"\nGFM: {passed}/{total} ({passed / total * 100:.1f}%)")

        assert passed >= GFM_PASS_BASELINE, (
            f"GFM pass count regressed: {passed}/{total} < baseline "
            f"{GFM_PASS_BASELINE}/{total}. If this is an intentional change, "
            f"investigate before adjusting GFM_PASS_BASELINE."
        )

    def test_known_fail_list_is_consistent(self) -> None:
        """Every KNOWN_FAIL example exists and currently fails (no stale entries).

        Guards against the xfail list drifting out of sync with reality: an
        example that has started passing should be removed from KNOWN_FAIL.
        """
        if not SPEC_TESTS:
            pytest.skip("GFM spec fixture not found")

        by_num = {ex["example"]: ex for ex in SPEC_TESTS}
        stale_unknown: list[int] = []
        now_passing: list[int] = []
        for num in KNOWN_FAIL:
            ex = by_num.get(num)
            if ex is None:
                stale_unknown.append(num)
                continue
            actual = _render(ex["markdown"])
            expected_norm, actual_norm = normalize_for_comparison(ex["html"], actual)
            if expected_norm == actual_norm:
                now_passing.append(num)

        assert not stale_unknown, f"KNOWN_FAIL references missing examples: {stale_unknown}"
        assert not now_passing, f"KNOWN_FAIL examples now PASS (remove them): {sorted(now_passing)}"
