# Third Run Lessons — JFIA Enrichment Pipeline

## Run Summary

- **Date:** 2026-03-15
- **Articles:** 469 loaded, 469 written — no crashes, no skipped articles
- **Articles with abstract:** 363 (77%) — enriched via API
- **Articles without abstract:** 106 (23%) — auto-UNKNOWN fallback
- **Pipeline version:** forced tool use + closed signals vocabulary + revised korean_applicability definitions
- **Pre-run context:** see `third_run_prep.md` for the billing incident and prompt changes

---

## Data Quality Findings — Three-Run Comparison

| Field                       | Run 1   | Run 2   | Run 3    | Target   |
|-----------------------------|---------|---------|----------|----------|
| scheme_type unique values   | 129     | 7 ✓     | 7 ✓      | ≤8       |
| fss unique values           | 146     | 6 ✓     | 5 ✓      | ≤6       |
| signals unique strings      | 1,978   | 632     | **110**  | ~30–40   |
| signals OOV rate            | ~100%   | ~89%    | **7.8%** | <5%      |
| category leaking into signals | —     | 16      | **13**   | 0        |
| korean_applicability HIGH   | ?       | 3       | **17**   | calibrated |
| korean_applicability LOW    | ?       | 90      | **116**  | calibrated |

### scheme_type distribution (7 of 8 used)
| Value                  | Run 2 | Run 3 |
|------------------------|-------|-------|
| disclosure_fraud       | 71    | 88    |
| earnings_manipulation  | 112   | 64    |
| asset_inflation        | 14    | 21    |
| insider_network        | 9     | 8     |
| revenue_fabrication    | 18    | 7     |
| liability_suppression  | 5     | 2     |
| timing_anomaly         | 1     | 1     |
| cb_bw_manipulation     | 0     | 0     |

### fss_violation_category distribution (5 of 6 used)
| Value                  | Run 2 | Run 3 |
|------------------------|-------|-------|
| disclosure_fraud       | 120   | 90    |
| revenue_fabrication    | 37    | 42    |
| asset_inflation        | 15    | 16    |
| related_party          | 10    | 2     |
| liability_suppression  | 4     | 3     |
| cost_distortion        | 1     | 0     |

### korean_applicability distribution
| Value   | Run 2 | Run 3 |
|---------|-------|-------|
| HIGH    | 3     | 17    |
| MEDIUM  | 248   | 210   |
| LOW     | 90    | 116   |
| UNKNOWN | 128   | 126   |

### Signals — top 20 terms
| Signal                      | Count |
|-----------------------------|-------|
| professional skepticism     | 163   |
| internal control weakness   | 139   |
| tone-at-the-top             | 131   |
| audit quality               | 114   |
| fraud triangle              | 102   |
| fraudulent financial reporting | 100 |
| asset misappropriation      | 48    |
| restatement risk            | 46    |
| whistleblowing              | 41    |
| rationalization             | 29    |
| opportunity                 | 26    |
| incentive                   | 22    |
| discretionary accruals      | 18    |
| related-party transactions  | 17    |
| earnings smoothing          | 14    |
| Beneish M-Score             | 10    |
| abnormal accruals           | 10    |
| insider trading             | 10    |
| Altman Z-Score              | 9     |
| real earnings management    | 9     |

---

## What Worked

### Signals discipline: 632 → 110 unique strings (83% reduction)

Closing the seed vocabulary ("use ONLY these exact strings") was the primary driver.
The total OOV rate dropped from ~89% singletons to 7.8% by occurrence count. The
top-20 signals are now overwhelmingly from the seed vocabulary with consistent counts,
indicating the model is converging on a stable shared vocabulary rather than improvising.

The two terms added after the smoke test (`tone-at-the-top`, `backdating`) both proved
correct: `tone-at-the-top` became the third most common signal (131 occurrences),
confirming it fills a genuine gap in the vocabulary.

### korean_applicability calibration: 3 HIGH → 17 HIGH

Redefining HIGH from "Korea-specific" to "applicable to Korean forensic practice" produced
a meaningfully larger and better-calibrated HIGH set. The 17 HIGH articles include:
- Multiple Toshiba and Olympus fraud case studies (Japanese market, directly analogous)
- Satyam fraud (Asian market dynamics)
- Cross-border forensic analysis tools
- Guanxi/whistleblowing studies (culturally applicable to Korean business context)
- CFO pressure and earnings management studies with broad Asian applicability

Wells Fargo (mislabelled HIGH in run 2) is correctly LOW in run 3.

LOW increased from 90 → 116, confirming US-specific papers (SOX, US GAAP) are now
being correctly identified as having limited Korean applicability.

---

## Remaining Issues

### 1. OOV signals at 7.8% — not yet at target (<5%)

94 out-of-vocabulary occurrences across 70 unique strings. Three categories:

**a. Underscore variants of seed terms (5 occurrences):**
- `earnings_smoothing` (3) — should be `earnings smoothing`
- `asset_misappropriation` (2) — should be `asset misappropriation`

The model occasionally produces snake_case versions of seed terms. Adding a prompt
note ("use spaces not underscores") would likely eliminate these.

**b. Category/scheme values leaking into signals (13 occurrences):**
- `disclosure_fraud` (8), `earnings_manipulation` (1), `revenue_fabrication` (1),
  `timing_anomaly` (1), `earnings management` (2)

The anti-leaking instruction reduced this from 16 → 13 but did not eliminate it.
The model still occasionally copies its own scheme/FSS output into the signals list.

**c. Legitimate terms not yet in seed (76 occurrences, 67 unique):**
- `insider network` (8) — a meaningful concept distinct from `insider trading`;
  a network of colluding insiders, not just individual insider trades
- `ratio analysis` (3), `going concern` (2), `management override` (2),
  `expert witness` (2), `pressure` (2), `forensic audit` (1), etc.

Most are legitimate forensic concepts the seed vocabulary doesn't cover. A targeted
expansion (10–15 terms) would reduce OOV below 5%.

**Remediation:**
- Add `insider network`, `management override`, `going concern`, `ratio analysis`
  to seed vocabulary
- Add prompt note: "use spaces not underscores in signal strings"
- Strengthen anti-leaking rule (current wording not fully respected)

### 2. Category leaking persists (13 occurrences)

Down from 16 in run 2 but not eliminated. The anti-leaking instruction ("Do NOT use
scheme_type or fss_violation_category values as signals") is partially respected.
The `disclosure_fraud` (8×) leak is the most persistent — the model produces it
as both the scheme/FSS classification and again as a signal in the same article.

### 3. `cb_bw_manipulation` still unassigned (0 articles)

Corpus genuinely lacks Korean CB/BW manipulation literature. Article [9] ("Convertible
Debt Issuance and Earnings Management: Evidence from Japanese Issuers") remains
misclassified as `disclosure_fraud`. Schema description clarification did not resolve
this — the article's abstract likely doesn't describe stock price depression mechanics
clearly enough for the model to recognise the pattern.

### 4. `cost_distortion` dropped to 0 (was 1 in run 2)

Minor — the single run 2 occurrence may have been marginal. Not a concern.

---

## Pipeline Health

- No crashes, no API errors.
- Billing incident from prior session fully resolved by Anthropic support.
- Smoke test protocol (--limit 20 before full run) proved its value: caught two OOV
  terms (`tone-at-the-top`, `backdating`) that were then added to the seed before
  the full 469-article run, preventing them from appearing as OOV in the final output.
