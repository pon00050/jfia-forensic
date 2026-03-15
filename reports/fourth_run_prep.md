# Fourth Run Preparation — JFIA Enrichment Pipeline

*Follows from: `third_run_lessons.md`*

---

## Issues to Address

Three issues carried forward from run 3, ranked by impact:

### 1. Signals OOV at 7.8% — target <5%

Run 3 left 94 OOV signal occurrences across 70 unique strings. Broken into three
sub-categories:

**a. Underscore variants of seed terms (5 occurrences)**
`earnings_smoothing` (3×), `asset_misappropriation` (2×) — model occasionally produces
snake_case where the seed uses spaces.

**b. Category/scheme leaking into signals (13 occurrences)**
`disclosure_fraud` (8×), `earnings_manipulation` (1×), `revenue_fabrication` (1×),
`timing_anomaly` (1×), `earnings management` (2×). Anti-leaking instruction exists but
is not fully respected.

**c. Legitimate terms not yet in seed (76 occurrences, 67 unique)**
`insider network` (8×), `ratio analysis` (3×), `going concern` (2×),
`management override` (2×), `expert witness` (2×), `pressure` (2×).

---

## Pipeline Changes

### 1. Expand seed vocabulary (addresses issue 1c)

Add to the seed list under appropriate categories:

- **Accruals/transactions:** `insider network`
- **Audit/reporting:** `going concern`, `management override`, `forensic audit`
- **Forensic models:** `ratio analysis`

Do not add `expert witness` or `pressure` — these are too generic to be useful
forensic signals.

### 2. Add underscore prohibition (addresses issue 1a)

Add one sentence to the signals vocabulary section:
> "Use spaces not underscores — write `earnings smoothing`, not `earnings_smoothing`."

### 3. Strengthen anti-leaking rule with explicit value list (addresses issues 1b and 2)

Replace the current generic instruction with an explicit enumeration:
> "Do NOT use any of the following as signals — these are classification labels,
> not indicators: earnings_manipulation, revenue_fabrication, asset_inflation,
> liability_suppression, disclosure_fraud, insider_network, cb_bw_manipulation,
> timing_anomaly, cost_distortion, related_party, earnings manipulation,
> earnings management, disclosure fraud."

Listing the actual values is more effective than a general rule, as run 3 showed the
generic instruction was only partially respected.

---

## Expected Outcomes

| Metric | Run 3 | Run 4 Target |
|--------|-------|--------------|
| Signals unique strings | 110 | ~50–70 |
| OOV rate (by occurrence) | 7.8% | <5% |
| Category leaking | 13 | 0–3 |
| Underscore variants | 5 | 0 |
| `korean_applicability` HIGH | 17 | ~15–20 (stable) |
| `korean_applicability` LOW | 116 | ~110–125 (stable) |
| `scheme_type` unique | 7 | 7–8 (no regression) |
| `fss` unique | 5 | 5–6 (no regression) |

`cb_bw_manipulation` is expected to remain at 0. The corpus does not contain Korean
CB/BW manipulation literature; this is a data gap, not a pipeline failure.

---

## Smoke Test Checklist

Before launching the full run, verify on `--limit 20` output:
- [ ] Zero underscore-variant signals
- [ ] Zero scheme/category labels appearing as signals
- [ ] OOV list contains only legitimate new forensic terms (if any)
- [ ] `korean_applicability` distribution roughly matches run 3 proportions
- [ ] Any new OOV terms: evaluate and add to seed before full run
