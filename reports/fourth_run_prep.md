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

---

## Smoke Test 1 Results (--limit 20)

Run against the first 20 articles with the initial fourth-run prompt changes applied.

### Results summary
- Unique signals: 25 | Total: 66 | OOV occurrences: 5
- Underscore variants: **0** — prohibition working
- `korean_applicability`: UNKNOWN 6, MEDIUM 9, LOW 5, HIGH 0

### OOV findings — three distinct situations

**1. `disclosure_fraud` (1× — leaking, persistent)**
The model classified an article as `disclosure_fraud` and then immediately used it
again as a signal in the same article. This persisted despite the explicit forbidden
list. The model's tendency to mirror its own output appears deep enough that
prompt-level rules alone cannot fully suppress it. Expected to produce 3–6 occurrences
in the full run (down from 8× in run 3, but not zero).

**2. `board composition`, `CEO duality`, `audit committee composition` (1× each — legitimate OOV)**
A coherent cluster of corporate governance structure signals used as fraud predictors.
All three arrived in the same articles. These are legitimate forensic signals, not
classification labels. Given how frequently corporate governance appears in forensic
accounting literature, these likely occur 20–40× each in the full corpus.
**Decision: add all three to seed under a new "Governance" category.**

**3. `Sarbanes-Oxley` (1× — not a valid signal)**
A regulatory framework name, not a measurable indicator. Should not appear as a signal.
**Decision: add to the forbidden list.**

### Checklist outcome
- [x] Zero underscore-variant signals
- [ ] Zero scheme/category labels appearing as signals — `disclosure_fraud` (1×) persists
- [x] OOV contains only legitimate new terms (plus one forbidden label)
- [x] `korean_applicability` distribution consistent with run 3
- [ ] New OOV terms evaluated — governance cluster requires seed addition before full run

### Actions before full run
1. Add to seed (Governance category): `board composition`, `CEO duality`,
   `audit committee composition`
2. Add to forbidden list: `Sarbanes-Oxley`
3. Re-smoke to confirm zero OOV before launching full 469-article run

---

## Smoke Test 2 Results (--limit 20)

Run after adding governance terms and `Sarbanes-Oxley` to forbidden list.

### Results summary
- Unique signals: 28 | Total: 68 | OOV occurrences: 8 (7 unique)
- Underscore variants: **0**
- `korean_applicability`: UNKNOWN 7, MEDIUM 7, LOW 5, HIGH 1

### OOV findings

| Term | Count | Verdict |
|---|---|---|
| `disclosure fraud` | 1× | Persistent leaking — explicitly forbidden, still produced. Irreducible via prompt. |
| `fraud detection` | 2× | Field-level descriptor, not a specific signal. Do not add. |
| `compliance` | 1× | Too generic. Do not add. |
| `audit planning` | 1× | Audit process term, not a fraud indicator. Do not add. |
| `control environment` | 1× | Legitimate — COSO framework component, meaningful forensic signal. **Add.** |
| `tests of controls` | 1× | Legitimate — specific audit procedure. **Add.** |
| `stock option compensation` | 1× | Legitimate — directly tied to backdating schemes already in seed. **Add.** |

### Assessment: diminishing returns on smoke testing

Each smoke iteration is catching fewer issues of decreasing materiality. The remaining
OOV after this patch will be dominated by `disclosure fraud` leaking (irreducible via
prompting — model mirrors its own classification output regardless of explicit
prohibition) and rare one-off terms that will appear too infrequently in the full corpus
to affect aggregate signal quality.

### Actions before full run
1. Add to seed: `control environment`, `tests of controls`, `stock option compensation`
2. Proceed directly to full 469-article run — no third smoke needed
