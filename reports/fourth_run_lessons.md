# Fourth Run Lessons — JFIA Enrichment Pipeline

## Run Summary

- **Date:** 2026-03-15
- **Articles:** 469 loaded, 469 written — no crashes
- **Articles with abstract:** 363 (77%) — enriched via API
- **Articles without abstract:** 106 (23%) — auto-UNKNOWN fallback
- **Pipeline version:** forced tool use + expanded closed seed (~50 terms) +
  underscore prohibition + explicit anti-leaking value list
- **Pre-run context:** see `fourth_run_prep.md` — two smoke tests conducted,
  governance terms and audit terms added before full run

---

## Data Quality Findings — Four-Run Comparison

| Field                       | Run 1   | Run 2   | Run 3    | Run 4     |
|-----------------------------|---------|---------|----------|-----------|
| scheme_type unique values   | 129     | 7 ✓     | 7 ✓      | 6 ✓       |
| fss unique values           | 146     | 6 ✓     | 5 ✓      | 6 ✓       |
| signals unique strings      | 1,978   | 632     | 110      | **214**   |
| signals total               | —       | —       | 1,207    | **1,526** |
| signals per abstract article| —       | —       | 3.3      | **4.2**   |
| OOV rate (by occurrence)    | ~100%   | ~89%    | 7.8%     | **13.9%** |
| category leaking            | —       | 16      | 13       | **27**    |
| `korean_applicability` HIGH | ?       | 3       | 17       | 17        |
| `korean_applicability` LOW  | ?       | 90      | 116      | 108       |

### scheme_type distribution
| Value                  | Run 3 | Run 4 |
|------------------------|-------|-------|
| disclosure_fraud       | 88    | 75    |
| earnings_manipulation  | 64    | 64    |
| asset_inflation        | 21    | 19    |
| insider_network        | 8     | 9     |
| revenue_fabrication    | 7     | 11    |
| liability_suppression  | 2     | 0     |
| timing_anomaly         | 1     | 2     |
| cb_bw_manipulation     | 0     | 0     |

### korean_applicability distribution
| Value   | Run 3 | Run 4 |
|---------|-------|-------|
| HIGH    | 17    | 17    |
| MEDIUM  | 210   | 220   |
| LOW     | 116   | 108   |
| UNKNOWN | 126   | 124   |

### Top OOV signals
| Signal                  | Count | Category |
|-------------------------|-------|----------|
| disclosure fraud        | 19    | Leaking (forbidden, persists) |
| fraud detection         | 6     | Generic field descriptor |
| Sarbanes-Oxley          | 4     | Forbidden, persists |
| corporate governance    | 3     | Legitimate — not in seed |
| analytical procedures   | 3     | Legitimate — not in seed |
| auditor independence    | 3     | Legitimate — not in seed |
| governance              | 3     | Too generic |
| segregation of duties   | 3     | Legitimate — not in seed |

165 unique OOV strings; most are singletons.

---

## What Worked

**Controlled-vocabulary fields remain clean.**
- `scheme_type`: 6 unique, all valid — no regression
- `fss_violation_category`: 6 unique, all valid — fss actually recovered
  `cost_distortion` (0 in run 3, 1 in run 4)
- `korean_applicability`: HIGH stable at 17, same articles as run 3 — the
  applicability definition from run 3 is holding

**Underscore prohibition worked.**
Zero occurrences of `earnings_smoothing`, `asset_misappropriation`, or any other
underscore variant of a seed term. The single-sentence prompt fix was fully effective.

**New seed terms are used correctly.**
`management override` (113×), `forensic audit` (82×), `control environment` (66×),
`ratio analysis` (36×), `board composition` (14×), `tests of controls` (14×) all
appeared prominently in the top-25, confirming they filled genuine gaps.

---

## Regression: OOV Rate 7.8% → 13.9%

This is the central finding of run 4. Despite a larger, more carefully constructed
seed vocabulary and stronger anti-leaking rules, OOV worsened.

### Root cause: seed expansion backfired

The model generates more signals per article when given a larger vocabulary to draw
from (3.3 signals/article in run 3 → 4.2 in run 4). A longer seed list appears to
signal "this is a rich domain with many signals" rather than "use only these terms."
The closed-list instruction ("use ONLY these exact strings") is honored for the most
common patterns but treated as advisory for edge cases.

This reveals a fundamental limit of prompt-based vocabulary enforcement for free-form
string arrays: the model cannot be reliably constrained to a closed list via instruction
alone when the output field is `{"type": "array", "items": {"type": "string"}}`.

### category leaking worsened: 13 → 27 occurrences

`disclosure fraud` (19×) is the primary driver — it more than doubled from run 3's
8× despite being explicitly listed in the forbidden values. `Sarbanes-Oxley` (4×)
also persisted despite explicit prohibition. The explicit enumeration approach reduced
generic leaking (no `earnings management` this time, `revenue_fabrication` down to 1×)
but could not suppress the model's tendency to mirror its own classification labels.

### The whack-a-mole dynamic

Each seed expansion catches known OOV terms but unlocks new ones. Run 3 caught
`tone-at-the-top`, `backdating`. Run 4 caught governance terms, audit procedures.
Run 5 would likely catch `segregation of duties`, `auditor independence`,
`analytical procedures` — and reveal another layer beneath. This approach has no
natural convergence point.

---

## Remediation Options

The prompt-based approach has reached its practical ceiling. Three paths forward:

### Option A: Accept current state (recommended for now)
The core use case — `by_scheme()` lookups, scheme/FSS aggregation,
`korean_applicability` filtering — does not depend on signals being a closed
vocabulary. Signals are supplementary metadata. The 165 unique OOV strings are mostly
legitimate forensic terms that add descriptive value even if inconsistently named.
The OOV rate of 13.9% by occurrence is a quality concern but not a functional blocker.

### Option B: Enforce signals as an enum in the tool schema
Replace `{"type": "array", "items": {"type": "string"}}` with an enum-constrained
array. This would enforce the closed list at the token-generation level (same mechanism
that fixed scheme_type and fss in run 2). Trade-off: requires finalising the full
vocabulary before running; any missed legitimate term becomes permanently inaccessible
without a schema change and re-run.

### Option C: Post-process signals after enrichment
Map OOV signal strings to nearest seed term via exact-match normalisation (e.g.,
`disclosure fraud` → null or excluded) and fuzzy matching for legitimate variants
(e.g., `auditor independence` → `audit quality`). Does not require another API run;
can be applied to existing `jfia_enriched.json` at any time.

**Recommendation:** Pursue Option C before any future re-run. A normalisation pass
on the existing data is cheap and would bring effective OOV to near-zero without
spending API credits. If Option B is pursued in future, finalise the complete
~60-term vocabulary first using the OOV data from run 4 as the reference list.

---

## Pipeline Health

- No crashes, no API errors.
- 469/469 articles processed cleanly.
- Background task pattern (with `TaskOutput` for monitoring) confirmed as the
  correct approach on Windows — no monitoring failures this run.
