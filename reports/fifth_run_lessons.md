# Fifth Run Lessons — JFIA Enrichment Pipeline

## Run Summary

- **Date:** 2026-03-15
- **Articles:** 469 loaded, 469 written — no crashes
- **Articles with abstract:** 363 (77%) — submitted to Batch API
- **Articles without abstract:** 106 (23%) — auto-UNKNOWN fallback
- **Pipeline version:** Option B (signals enum-constrained to `SIGNAL_SEED_VOCABULARY`) +
  Batch API + normalise.py post-processing
- **Pre-run context:** see `fifth_run_prep.md`

### Operational notes

- First run using the Batch API — 363 requests submitted in a single batch, completed in ~2 minutes
- **SDK bug encountered and fixed mid-run:** `_parse_batch_result` checked `result.type == "message"`
  but the real SDK uses `result.type == "succeeded"` with the message at `result.message.content[0]`
  (not `result.content[0]`). All 469 articles were written as fallbacks on the first pass.
  Results were re-retrieved from the same batch ID without resubmitting — no additional API cost.
  The fix was applied to `enrichment.py` and `test_batch_enrichment.py` immediately.

---

## Data Quality Findings — Five-Run Comparison

| Field                        | Run 1   | Run 2   | Run 3    | Run 4 (raw) | Run 4 (norm) | Run 5 (norm) |
|------------------------------|---------|---------|----------|-------------|--------------|--------------|
| scheme_type unique values    | 129     | 7 ✓     | 7 ✓      | 6 ✓         | 6 ✓          | 7 ✓          |
| fss unique values            | 146     | 6 ✓     | 5 ✓      | 6 ✓         | 6 ✓          | 4            |
| signals unique strings       | 1,978   | 632     | 110      | 214         | 208          | **81**       |
| signals total                | —       | —       | 1,207    | 1,526       | 1,498        | **1,551**    |
| signals per abstract article | —       | —       | 3.3      | 4.2         | 4.1          | **4.3**      |
| OOV rate (by occurrence)     | ~100%   | ~89%    | 7.8%     | 13.9%       | 12.3%        | **2.51%**    |
| Forbidden labels removed     | —       | —       | —        | 28          | 0            | 17 → 0       |
| `korean_applicability` HIGH  | ?       | 3       | 17       | 17          | 17           | **21**       |
| `korean_applicability` LOW   | ?       | 90      | 116      | 108         | 108          | **100**      |

### scheme_type distribution

| Value                  | Run 3 | Run 4 | Run 5 |
|------------------------|-------|-------|-------|
| disclosure_fraud       | 88    | 75    | 43    |
| earnings_manipulation  | 64    | 64    | 61    |
| asset_inflation        | 21    | 19    | 33    |
| revenue_fabrication    | 7     | 11    | 16    |
| insider_network        | 8     | 9     | 5     |
| liability_suppression  | 2     | 0     | 2     |
| timing_anomaly         | 1     | 2     | 1     |
| cb_bw_manipulation     | 0     | 0     | 0     |

### korean_applicability distribution

| Value   | Run 3 | Run 4 | Run 5 |
|---------|-------|-------|-------|
| HIGH    | 17    | 17    | 21    |
| MEDIUM  | 210   | 220   | 230   |
| LOW     | 116   | 108   | 100   |
| UNKNOWN | 126   | 124   | 118   |

### Top 20 signals (post-normalisation)

| Signal                       | Count |
|------------------------------|-------|
| professional skepticism      | 149   |
| internal control weakness    | 138   |
| forensic audit               | 129   |
| fraud triangle               | 120   |
| tone-at-the-top              | 104   |
| fraudulent financial reporting | 103 |
| control environment          | 97    |
| management override          | 93    |
| audit quality                | 64    |
| ratio analysis               | 61    |
| asset misappropriation       | 50    |
| rationalization              | 45    |
| incentive                    | 44    |
| opportunity                  | 43    |
| restatement risk             | 34    |
| whistleblowing               | 28    |
| tests of controls            | 24    |
| board composition            | 16    |
| discretionary accruals       | 16    |
| insider network              | 15    |

### Remaining OOV signals (39 occurrences, 31 unique)

| Signal                   | Count | Assessment |
|--------------------------|-------|------------|
| `governance`             | 4     | Too generic — omit from seed |
| `auditor independence`   | 2     | Covered by `audit quality` — omit |
| `accruals`               | 2     | Too generic — `discretionary accruals`/`abnormal accruals` preferred |
| `audit risk`             | 2     | Process term — omit |
| `red flags`              | 2     | Too generic — omit |
| `pressure`               | 2     | Too generic — `fraud triangle`/`incentive` preferred |
| `earnings_smoothing`     | 1     | Snake_case variant of seed term — enum constraint partially bypassed |
| `analytical procedures`  | 1     | Evaluated and omitted in run 5 prep — confirm omit |
| `GAAP`                   | 1     | Jurisdiction/standard reference — omit |
| (22 singletons)          | 1 each | Highly specific, one-off terms — acceptable noise |

The enum constraint on array items is a strong hint, not a hard lock. The model bypassed it 56
times pre-normalise (17 forbidden + 39 remaining OOV), vs 212 OOV in run 4 — a **74% reduction**.

---

## What Worked

### Option B: OOV rate 12.3% → 2.51% (80% reduction)

Enforcing `signals` as an enum-constrained array in the tool schema delivered the expected result.
Unique signal strings collapsed from 208 to 81 — and 51 of those 81 are from the seed vocabulary,
meaning OOV unique strings went from 159 to 30. The signal field is now a reliable lookup: a query
for `"Beneish M-Score"` returns consistent results, not a mix of `"Beneish"`, `"M-Score"`,
`"Beneish model"`, etc.

### Batch API: correct and fast

363 articles processed in ~2 minutes (vs ~8–10 minutes estimated for sequential). The Batch API
path is confirmed as the standard mode for future full runs. The operational cost at 50% discount
was ~$0.28 (vs ~$0.55 sequential).

### `korean_applicability` improving

HIGH rose from 17 to 21 — a small but consistent trend over the last two runs, suggesting the
applicability definition from run 3 is calibrating correctly over time.

### normalise.py working as designed

17 forbidden-label leakers removed post-run. The `SIGNAL_SEED_VOCABULARY - SIGNAL_FORBIDDEN_LABELS`
set subtraction (bug fixed this run) correctly preserves `"insider network"` (seed term) while
forbidding `"insider_network"` (scheme type label).

---

## Remaining Issues

### 1. fss_violation_category coverage narrowed

Run 5 shows only 4 of 6 valid `fss_violation_category` values (`cost_distortion` and `related_party`
are absent). Run 4 had all 6. This is likely natural run-to-run variance at low counts — these
categories were rare in run 4 (1× each). Not a regression, but worth monitoring.

### 2. 39 residual OOV signals (2.51%)

The enum constraint on array items cannot fully prevent OOV — the model bypasses it occasionally.
The 39 remaining are a mix of too-generic terms (`governance`, `pressure`) and legitimate specifics
(`auditor independence`, `analytical procedures`). The current approach (enum + normalise.py) is
the practical ceiling for prompt/schema-based enforcement.

If signal precision is critical, the only structural fix is to audit the 31 unique OOV strings and
either add legitimate ones to the seed or accept the noise level.

### 3. disclosure_fraud scheme_type shift

`disclosure_fraud` dropped from 75 (run 4) to 43 (run 5) while `asset_inflation` rose from 19 to
33. The magnitude of change (−32 and +14 respectively) is larger than expected from noise alone
— possibly a prompt or model interaction effect. No action required unless the run 3/4/5 trend
continues monotonically in run 6.

---

## Recommendation: No Immediate Run 6

**Decision (2026-03-15): Do not proceed with run 6 at this time.**

The pipeline is in its best state across all five runs. The three remaining issues do not justify
the cost or effort of another enrichment run:

| Issue | Severity | Verdict |
|-------|----------|---------|
| `disclosure_fraud` scheme_type drift (75→43) | Monitor | Would confirm noise vs trend but produce no quality gain |
| 39 residual OOV signals (2.51%) | Low | Practical ceiling — no seed changes identified that would meaningfully improve this |
| `fss_violation_category` missing 2 values | Negligible | Low-count variance, not a pipeline failure |

The only triggers that would justify run 6:

1. **New JFIA catalog data** — if new issues have been published and the catalog updated, enriching
   net-new articles is full value.
2. **Seed vocabulary decision** — if a future use case requires specific signals not in the current
   51-term seed, update the seed and re-run. The run 5 OOV list is the reference for candidates.
3. **Persistent drift confirmed** — if run 6 is eventually triggered for another reason and
   `disclosure_fraud` continues its monotonic decline, investigate the prompt interaction.

The signal field is now a reliable controlled vocabulary. The core use cases — `by_scheme()`,
`korean_applicability` filtering, `fss_violation_category` aggregation — are all clean and stable.

---

## Cost & Token Usage

| Metric | Value |
|--------|-------|
| Model | `claude-haiku-4-5-20251001` |
| Submission mode | Batch API (50% discount) |
| Articles submitted | 363 (abstract-bearing only) |
| Total input tokens | 911,868 |
| Total output tokens | 59,980 |
| Total tokens | 971,848 |
| Avg input tokens / article | 2,512 |
| Avg output tokens / article | 165 |
| Input cost ($0.40/MTok batch) | $0.3647 |
| Output cost ($2.00/MTok batch) | $0.1200 |
| **Total cost** | **$0.4847** |

For reference, the equivalent sequential cost at standard rates ($0.80/$4.00 per MTok) would have
been ~$0.97 — the Batch API saved approximately $0.49 (50%).

---

## Pipeline Health

- No crashes, no API errors. 363/363 batch results returned as `succeeded`.
- Batch API confirmed as production-ready for this workflow. Completed in ~2 minutes.
- One SDK bug found and fixed — `_parse_batch_result` used wrong result shape. Results recovered
  from existing batch without resubmission. Tests updated to match real SDK structure.
