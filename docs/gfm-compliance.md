# GFM Compliance Tracking

Patitas has measured CommonMark 0.31.2 compliance through
`tests/fixtures/commonmark_spec_0_31_2.json` and `make commonmark`.

GitHub Flavored Markdown compliance is not yet measured against the official GFM
spec fixture. Until that fixture and test target exist, treat Patitas as
CommonMark-compliant with several GFM-style plugin features, not as a fully
reported GFM-compliant parser.

## Current GFM-Style Coverage

| Feature | Patitas support | Current verification |
|---|---|---|
| Tables | `Markdown(plugins=["table"])` | Unit, integration, property, and docs tests |
| Task list items | `Markdown(plugins=["task_lists"])` | Unit and renderer edge-case tests |
| Strikethrough | `Markdown(plugins=["strikethrough"])` | Inline/parser/serialization tests |
| Autolinks | `Markdown(plugins=["autolinks"])` | Plugin integration and config tests |

Footnotes and math are supported plugin families, but they are tracked as
Patitas extensions here rather than counted toward a GFM pass rate.

## Tracking Plan

1. Vendor or generate the official GFM spec fixture in `tests/fixtures/` with a
   clear upstream version and license note.
2. Add a `gfm` pytest marker and a focused `tests/test_gfm_spec.py` target.
3. Report pass counts separately from CommonMark, for example `GFM: 128/130`.
4. Update README, site docs, and benchmarks only after the measured pass rate
   exists.
5. Keep GFM extensions opt-in through `ParseConfig` and `Markdown(plugins=[...])`
   unless there is an explicit public behavior decision.

## Not Yet Claimed

Patitas does not currently publish an official GFM pass count. Avoid wording
such as "full GFM compliance" or "strict GFM spec compliance" until the fixture,
test target, and public report are in place.
