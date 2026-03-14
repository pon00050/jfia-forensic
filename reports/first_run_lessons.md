# First Run Lessons — JFIA Enrichment Pipeline

## Pipeline Bugs Discovered and Fixed

1. **Wrong model ID** (`"claude-haiku-4-5-20251001"` → `"claude-haiku-4-5"`)
   The date-suffixed model ID was rejected by the API. `HAIKU_MODEL` in `constants.py`
   now uses the short form; `CLAUDE.md` documents this convention explicitly.

2. **Broad `except` swallowed auth errors silently**
   The original `try/except` wrapped the `client.messages.create()` call, meaning
   authentication failures and network errors returned a fallback `EnrichedArticle`
   with no indication of failure. The API call was moved outside the try block so
   auth/connection errors propagate. Only parse/validation failures are caught.

3. **Code fence stripping needed despite "Only JSON" instruction**
   The model occasionally wrapped its JSON response in ` ```json ... ``` ` despite
   the system prompt instructing otherwise. A stripping step was added post-hoc.
   (This issue is now eliminated entirely by forced tool use.)

---

## Data Quality Findings (First Run — 469 articles)

| Field                  | Fill rate | Unique values | Allowed values |
|------------------------|-----------|---------------|----------------|
| scheme_type            | 40%       | 129           | 8              |
| fss_violation_category | 35%       | 146           | 6              |
| signals                | 73%       | 1,978 strings | (seed vocab)   |
| korean_applicability   | 100%      | 4             | 4 ✓            |

- **Total articles:** 469
- **With abstract:** ~363 (77%) — enriched via API
- **Without abstract:** ~106 (23%) — auto-UNKNOWN fallback

`korean_applicability` worked correctly because the prompt explicitly enumerated its
4 allowed values. The other constrained fields listed `string_or_null` — no vocabulary —
so the model improvised freely.

---

## Root Cause

`ENRICHMENT_SYSTEM_PROMPT` enumerated valid values only for `korean_applicability`.
`scheme_type` and `fss_violation_category` were described as `string_or_null` with no
vocabulary constraint, leaving the model free to produce arbitrary strings.

---

## Remediation

1. **Forced tool use** — `tool_choice={"type": "tool", "name": "extract_article_metadata"}`
   with a JSON Schema `enum` constraint enforces allowed values at token-generation level.
   Response arrives as a Python dict (`response.content[0].input`); no JSON parsing needed,
   no code fence stripping needed.

2. **Seed vocabulary in system prompt** — Beneish ratios (DSRI, AQI, GMI, …) and common
   forensic terms listed explicitly, with two few-shot examples anchoring classification
   quality and reducing signal fragmentation.

3. **Belt-and-suspenders coercing validators in `EnrichedArticle`** — `scheme_type` and
   `fss_violation_category` now have `@field_validator(mode="before")` that coerces
   out-of-vocabulary strings to `None` (consistent with "not classifiable"), rather than
   raising. This handles any future prompt drift or SDK version change.
