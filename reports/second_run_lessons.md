# Second Run Lessons — JFIA Enrichment Pipeline

## Run Summary

- **Date:** 2026-03-14
- **Articles:** 469 loaded, 469 written (no crashes, no skipped articles)
- **Articles with abstract:** 363 (77%) — enriched via API
- **Articles without abstract:** 106 (23%) — auto-UNKNOWN fallback
- **Pipeline version:** forced tool use with JSON Schema enum constraints

---

## Data Quality Findings (Second Run vs First Run)

| Field                  | Run 1 fill | Run 1 unique | Run 2 fill | Run 2 unique | Allowed |
|------------------------|------------|--------------|------------|--------------|---------|
| scheme_type            | 40%        | 129          | **49%**    | **7** ✓      | 8       |
| fss_violation_category | 35%        | 146          | **40%**    | **6** ✓      | 6       |
| signals (total strings)| —          | 1,978        | —          | **632**      | (seed)  |
| korean_applicability   | 100%       | 4 ✓          | 100%       | 4 ✓          | 4       |

### scheme_type distribution (7 of 8 used)
| Value                  | Count |
|------------------------|-------|
| earnings_manipulation  | 112   |
| disclosure_fraud       | 71    |
| revenue_fabrication    | 18    |
| asset_inflation        | 14    |
| insider_network        | 9     |
| liability_suppression  | 5     |
| timing_anomaly         | 1     |
| **cb_bw_manipulation** | **0** |

### fss_violation_category distribution (6 of 6 used — perfect vocabulary)
| Value                  | Count |
|------------------------|-------|
| disclosure_fraud       | 120   |
| revenue_fabrication    | 37    |
| asset_inflation        | 15    |
| related_party          | 10    |
| liability_suppression  | 4     |
| cost_distortion        | 1     |

### korean_applicability distribution
| Value   | Count |
|---------|-------|
| MEDIUM  | 248   |
| UNKNOWN | 128   |
| LOW     | 90    |
| HIGH    | 3     |

### signals — top 20 terms
| Signal                    | Count |
|---------------------------|-------|
| audit quality             | 98    |
| restatement risk          | 84    |
| abnormal accruals         | 57    |
| related-party transactions| 46    |
| discretionary accruals    | 39    |
| earnings smoothing        | 36    |
| insider trading           | 20    |
| insider network           | 16    |
| big bath accounting       | 11    |
| fraud triangle            | 9     |
| fraud detection           | 9     |
| disclosure_fraud          | 8     |
| disclosure fraud          | 8     |
| whistleblowing            | 8     |
| channel stuffing          | 8     |
| round-trip transactions   | 7     |
| earnings management       | 7     |
| professional skepticism   | 6     |
| embezzlement              | 6     |
| opportunity               | 5     |

---

## What Worked

**Forced tool use completely fixed the controlled-vocabulary fields.**
- `scheme_type`: 129 freeform values → 7 valid enum values. Zero invalid strings.
- `fss_violation_category`: 146 freeform values → 6 valid enum values. Every allowed
  value is represented; zero invalid strings.
- `korean_applicability`: already correct in run 1; remains correct.
- Fill rates improved slightly (40% → 49% for scheme_type; 35% → 40% for FSS),
  suggesting the structured tool format helps the model commit to a classification
  rather than defaulting to null.

---

## Remaining Issues

### 1. `signals` still highly fragmented (632 unique, target ~20–30)

The seed vocabulary pulled the top terms into alignment (audit quality, restatement risk,
abnormal accruals, discretionary accruals all highly concentrated), but 632 unique strings
remain because the model continues appending novel terms. The seed alone is insufficient;
the model treats it as a starting point, not a closed list.

**Root cause:** `signals` is a free-form array in the tool schema (`"items": {"type": "string"}`),
so there is no enum constraint. The system prompt says "Only add a new signal term if no seed
term fits" — but this is advisory, not enforced.

**Remediation options (in increasing strictness):**
- A: Expand seed vocabulary and add stronger wording ("use ONLY the seed terms below, never
  invent new ones")
- B: Split into two fields: `seed_signals` (enum-constrained array) and `other_signals`
  (free-form) — allows both discipline and extensibility
- C: Post-process: map novel strings to nearest seed term via fuzzy match or embedding
  similarity

### 2. Category values leaking into `signals`

`"disclosure_fraud"` appears 8 times as a signal string, and `"disclosure fraud"` (space
variant) appears 8 more times. These are `fss_violation_category` values, not signals —
the model is copying the category name into the signal list. Similarly `"earnings management"`
(7 occurrences) overlaps with scheme-level vocabulary.

**Root cause:** The few-shot examples in the prompt show signals and categories side by side,
and the model does not maintain a clear conceptual boundary. The snake_case vs space form
duplication (`disclosure_fraud` / `disclosure fraud`) suggests the model is independently
producing the same concept in two surface forms.

**Remediation:** Add an explicit system prompt constraint: "Signals must be measurable
indicators or ratios, not scheme or category names. Do not repeat scheme_type or
fss_violation_category values as signals."

### 3. `korean_applicability` is nearly always MEDIUM — only 3 HIGH

Only 3 of 363 enriched articles received HIGH applicability. This is plausibly correct
(the JFIA corpus is an international journal; Korean-specific content would be a minority),
but it is also plausible the model is being systematically conservative. The few-shot
examples both show HIGH, which may have anchored the model incorrectly toward MEDIUM as
a "safe" answer for non-obvious cases.

**Remediation:** Review the 3 HIGH articles manually to calibrate. Consider adding a
MEDIUM and LOW example to the few-shot set to balance the anchor effect.

### 4. `cb_bw_manipulation` was never assigned (0 articles)

Convertible bond/bond warrant manipulation is a distinctly Korean market phenomenon.
Its absence may be correct (the corpus may genuinely lack such articles), or the model
may not recognise it without a clearer description. The label itself is opaque —
`"cb_bw_manipulation"` is not self-explanatory in English.

**Remediation:** Verify by searching the catalog for "convertible bond" articles and
checking if they were assigned to another scheme or left null. If they exist and were
misclassified, add a third few-shot example covering this scheme.

---

## Operational Incidents

### 1. Background task launched; output unreadable due to Windows path quoting

The enrichment was started as a background shell task. Immediately after launch, an attempt
was made to read the live output file using `tail`/`cat` via bash. Both commands failed
silently because the bash shell on Windows did not handle the long Windows path correctly
(backslash-separated segments were interpreted as a single malformed argument). The task
was running and writing output the entire time; the monitoring step was the failure, not
the pipeline.

**Lesson:** On Windows, background task output files should be read via the `TaskOutput`
tool, not via bash file commands. The path format the system provides is a Windows path;
bash does not quote it correctly when passed to native commands.

### 2. Redundant synchronous run launched; hit billing wall

Because the background task's output appeared unreadable, a second synchronous run was
launched to verify the pipeline was working. That run immediately failed with:

```
anthropic.BadRequestError: 400 — credit balance is too low
```

At this point it was unclear whether the background task was still running, had already
succeeded, or had also failed. The background task completed successfully shortly after
and posted its completion notification — confirming that it had consumed the remaining
credit during its run, leaving none for the synchronous re-run.

**The successful run was the original background task (b30ckg4fa), not a new run.**
The enriched JSON was written by that task; the analysis and this post-mortem are based
on its output.

**Lesson:** Do not launch a second run while a background task is still in progress.
Wait for the `TaskOutput` notification before concluding a run has failed.

### 3. Auth-propagation fix confirmed correct

The billing wall error was raised immediately and propagated cleanly — it was not swallowed
by the fallback handler. Had the run 1 bug (broad `except` around the API call) still been
present, the synchronous run would have silently written 469 UNKNOWN fallback records and
exited 0. Instead it raised `BadRequestError` and exited 1. The fix works as intended.

---

## Pipeline Health

- No crashes, no fallback triggered by API errors.
- Coercing validators confirmed working: zero invalid strings in scheme_type or
  fss_violation_category despite the model having theoretically been able to produce them
  via content[0].input before Pydantic validation.
