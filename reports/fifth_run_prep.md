# Fifth Run Preparation — JFIA Enrichment Pipeline

*Follows from: `fourth_run_lessons.md`*

---

## Actions Completed Before This Run

### 1. Normalisation pass on run 4 data (Option C — free, no API calls)

`normalise.py` was written and applied to `data/curated/jfia_enriched.json`:

```bash
python -m jfia_forensic.normalise data/curated/jfia_enriched.json
# Removed 28 signal occurrences (non-strict mode)
```

**What was removed:**

| Signal                | Count | Reason |
|-----------------------|-------|--------|
| `disclosure fraud`    | 19    | Forbidden label — space form of `disclosure_fraud` |
| `Sarbanes-Oxley`      | 4     | Explicitly forbidden |
| `earnings management` | 2     | Explicitly forbidden |
| `revenue_fabrication` | 1     | Forbidden (snake_case scheme type) |
| `disclosure_fraud`    | 1     | Forbidden (snake_case scheme type) |
| `asset inflation`     | 1     | Forbidden — space form of `asset_inflation` |

**Post-normalisation state (run 4 data, now committed):**

| Metric | Run 4 (raw) | Run 4 (post-normalisation) |
|--------|-------------|----------------------------|
| Total signal occurrences | 1,526 | 1,498 |
| Unique signal strings | 214 | 208 |
| OOV rate (by occurrence) | 13.9% | 12.3% |
| Forbidden labels | 28 | 0 |

**Bug found and fixed during implementation:** `"insider network"` was incorrectly included in
`SIGNAL_FORBIDDEN_LABELS` because it is the space form of the `insider_network` scheme type. Since
`"insider network"` is also explicitly listed in `SIGNAL_SEED_VOCABULARY`, the constant now
subtracts `SIGNAL_SEED_VOCABULARY` from the forbidden set to prevent this class of error:

```python
SIGNAL_FORBIDDEN_LABELS = frozenset(
    (_expand_to_surface_forms(SCHEME_TYPES) | ...) - SIGNAL_SEED_VOCABULARY
)
```

### 2. Batch API path added to `enrich_catalog()`

`enrich_catalog()` now accepts `batch=True`. When set, all abstract-bearing articles are submitted
as a single Anthropic Batch API request (50% per-token discount, parallel processing):

```bash
python -m jfia_forensic.enrichment data/raw/jfia_catalog.json \
       data/curated/jfia_enriched.json --batch
```

`--limit` works with both modes. Estimated cost at 50% discount: ~$0.28 for the full 363-article
batch (vs ~$0.55 sequential).

---

## Outstanding Issue — The OOV Ceiling

After normalisation, 185 OOV occurrences remained (12.3%). These are all legitimate forensic terms
not in the seed vocabulary — not leaking category labels, but terms like `"auditor independence"`,
`"analytical procedures"`, `"segregation of duties"` that the model fills in when the prompt
vocabulary doesn't cover the article's content.

The prompt-based closed-list approach has no mechanism to prevent this. As run 4 demonstrated,
expanding the seed induces more signals-per-article at roughly the same OOV rate. The instruction
"use ONLY these exact strings" is treated as advisory, not binding.

---

## Decision: Option B — Signals as Enum

### Options considered (2026-03-15)

Three approaches were evaluated for the OOV problem:

**Option A — Accept the status quo.**
The 12% OOV signals are mostly legitimate forensic terms that add descriptive value even if
inconsistently named. `scheme_type`, `fss_violation_category`, and `korean_applicability` — the
fields used for filtering and aggregation — are all clean. OOV only affects signal-level lookups.
No API spend required.

**Option B — Enforce the vocabulary at token-generation time (chosen).**
Replace the free-string array in the tool schema with an enum-constrained array. The model is
physically unable to emit a value outside the approved list — the same mechanism that fixed
`scheme_type` (run 2: 129 freeform → 7 valid) and `fss_violation_category` (146 → 6 valid).
Trade-off: any legitimate term not in the seed at run time is silently dropped rather than
appearing as OOV. The seed must be considered final before running.

**Option C — Post-process after enrichment.**
Run `normalise.py` to strip forbidden labels after the fact. Applied to run 4 data (removed 28
occurrences). Can only *remove* bad terms — cannot *remap* `"auditor independence"` to
`"audit quality"` because the mapping is not known. The 185 remaining OOV signals cannot be fixed
this way; they are legitimate terms with no obvious canonical equivalent.

**Decision:** Option B. The reason: `signals` is only useful as a lookup field if it is
consistently named. With 159 unique OOV strings across 185 occurrences, signal-level queries
(`"find all articles using Beneish M-Score"`) are unreliable. Option B makes signals a proper
controlled vocabulary, consistent with how the other classification fields are already enforced.

### Implementation

Changed in `enrichment.py` (`ENRICHMENT_TOOL`):

```python
# Before (free-text, enforces nothing)
"signals": {"type": "array", "items": {"type": "string"}}

# After (enum-constrained to SIGNAL_SEED_VOCABULARY)
"signals": {
    "type": "array",
    "items": {"type": "string", "enum": sorted(SIGNAL_SEED_VOCABULARY)},
}
```

`SIGNAL_SEED_VOCABULARY` is defined in `constants.py` (51 terms). It is now the single source of
truth for both the prompt text and the tool schema — changes to the vocabulary must be made in
`constants.py` and will propagate to both automatically.

### Seed completeness assessment

Before locking the vocabulary, the top recurring OOV terms from run 4 were evaluated:

| Term | Count | Decision |
|------|-------|----------|
| `fraud detection`         | 6 | Omit — field-level descriptor, not a measurable indicator |
| `corporate governance`    | 4 | Omit — `board composition` covers the key causal mechanism |
| `analytical procedures`   | 3 | Omit — audit process step, not a fraud indicator |
| `auditor independence`    | 3 | Omit — captured adequately by `audit quality` |
| `segregation of duties`   | 3 | Omit — internal control term; `internal control weakness` covers it |
| `governance`              | 3 | Omit — too generic |
| `audit planning`          | 2 | Omit — process term |
| `continuous auditing`     | 2 | Omit — technique, not a fraud signal |
| `red flags`               | 2 | Omit — too generic |
| `financial statement analysis` | 2 | Omit — too broad |

All omitted. The existing 51-term seed is considered final for run 5. The rationale: these terms
describe audit *processes* or *contexts* rather than specific forensic *indicators*. The seed
already contains the indicator-level equivalents (`audit quality`, `internal control weakness`,
`board composition`, etc.).

---

## Smoke Test Checklist

Before launching the full run:

- [x] Option B implemented in `ENRICHMENT_TOOL`
- [x] Seed vocabulary finalised (no additions)
- [x] Smoke test: `python -m jfia_forensic.enrichment ... --limit 20` → 20 articles, 76 signals
- [x] OOV: 1 occurrence (`disclosure_fraud` snake_case — persistent leaker, caught by `normalise.py`)
      Enum constraint reduced OOV from 13.9% → 1.3%. Array-item enums are a strong hint, not a hard lock.
- [x] `korean_applicability`: HIGH 1, MEDIUM 10, LOW 3, UNKNOWN 6 — consistent with run 4 proportions
- [x] No `scheme_type` regression — all 4 unique values valid
- [x] Launch full batch run: `python -m jfia_forensic.enrichment data/raw/jfia_catalog.json data/curated/jfia_enriched.json --batch`
