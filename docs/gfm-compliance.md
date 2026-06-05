# GFM Compliance Tracking

Patitas measures CommonMark 0.31.2 compliance through
`tests/fixtures/commonmark_spec_0_31_2.json` (`pytest -m commonmark`) and now
also measures GitHub Flavored Markdown 0.29 compliance through
`tests/fixtures/gfm_spec_0_29.json` (`pytest -m gfm`).

## Measured GFM Compliance

With the GFM feature plugins enabled
(`Markdown(plugins=["table", "strikethrough", "task_lists", "autolinks"])`),
Patitas passes **647 of 672** GFM 0.29 spec examples (**96.3%**).

The pass count is tracked as a ratchet in `tests/test_gfm_spec.py`
(`TestGfmBaseline::test_gfm_pass_rate`), which prints `GFM: N/M` and asserts the
count never drops below the recorded baseline. The 25 known-failing examples are
individually `xfail`ed in `KNOWN_FAIL` with reasons.

The fixture is extracted from the upstream `spec.txt` at version 0.29
(CC-BY-SA 4.0); see `tests/fixtures/GFM_SPEC_LICENSE.txt`.

### Why the remaining 25 fail

| Count | Category | Reason |
|---|---|---|
| 11 | Autolinks (extension) | GFM extended autolinks (bare `www.`, bare URL, bare email) are not yet implemented. CommonMark angle-bracket autolinks `<https://...>` work without any plugin. |
| 9 | Emphasis | CommonMark version drift: GFM 0.29 is based on CommonMark 0.28, but Patitas targets 0.31.2. These exact emphasis inputs have different expected nesting between the two CommonMark versions; Patitas matches its 0.31.2 target (the same examples PASS in `test_commonmark_spec.py`). |
| 2 | Tables (extension) | One alignment example renders alignment via inline `style="text-align: ..."` instead of GFM's `align="..."` attribute (cosmetic); one relies on lazily extending a table with a following paragraph-continuation row, which Patitas does not do. |
| 2 | Task list items (extension) | `<input>` attribute format/order differs (`<input type="checkbox" disabled />` vs GFM's `<input disabled="" type="checkbox">`); semantically equivalent. |
| 1 | Disallowed Raw HTML (extension) | The GFM tagfilter extension is not implemented. |

## GFM-Style Coverage

| Feature | Patitas support | Notes |
|---|---|---|
| Tables | `Markdown(plugins=["table"])` | Tables without outer pipes, ragged-row pad/truncate, and paragraph interruption are now handled (verified against markdown-it-py and mistune). Lazy table-row continuation is not. |
| Task list items | `Markdown(plugins=["task_lists"])` | Now emits GitHub's `contains-task-list` (on the list) and `task-list-item` (on each task `<li>`) CSS classes. `<input>` attribute order still differs cosmetically from GitHub. |
| Strikethrough | `Markdown(plugins=["strikethrough"])` | Inline/parser/serialization tests pass. |
| Autolinks (bare URL/email/`www.`) | not yet implemented | The `autolinks` plugin sets a config flag, but GFM extended autolinks are not yet wired up (tracked separately). CommonMark angle-bracket autolinks `<https://...>` work without any plugin. |

Footnotes and math are supported plugin families, but they are tracked as
Patitas extensions here rather than counted toward the GFM pass rate.

## Updating the baseline

When a change improves GFM compliance, raise `GFM_PASS_BASELINE` in
`tests/test_gfm_spec.py` and remove the now-passing example(s) from `KNOWN_FAIL`
(the `test_known_fail_list_is_consistent` test enforces that `KNOWN_FAIL` has no
stale or now-passing entries). Never lower the baseline to mask a regression.
