# Enrichment Pipeline Run Records

Each enrichment run produces two documents, written in order:

---

## File Pattern

### `{n}_run_prep.md` — written before the run
Documents everything that happened between the previous post-mortem and the moment
the full run is launched. Contains:

- **Pipeline changes** — what was modified in the code/prompt and why, with a link
  back to the specific issue identified in the prior `lessons.md`
- **Expected outcomes** — what improvement we expect to see for each change, stated
  as measurable targets where possible (e.g. "OOV rate <5%")
- **Smoke test results** — findings from the `--limit 20` pre-run; any seed additions
  made as a result
- **Operational incidents** — anything that went wrong during the run itself
  (billing issues, crashes, monitoring failures, etc.)

### `{n}_run_lessons.md` — written after the run completes
Formal post-mortem of the completed run. Contains:

- **Run summary** — article counts, pipeline version
- **Data quality findings** — tables comparing this run to prior runs across all
  five enriched fields
- **What worked** — changes that achieved their target, with evidence
- **Remaining issues** — problems not yet resolved, with root cause analysis and
  concrete remediation options ranked by priority
- **Pipeline health** — crashes, fallbacks, API errors, operational observations

---

## Run Index

| Run | Prep | Lessons | Key change | Outcome |
|-----|------|---------|------------|---------|
| 1 | — | `first_run_lessons.md` | Initial run (JSON prompt) | scheme_type: 129 freeform values; signals: 1,978 unique |
| 2 | — | `second_run_lessons.md` | Forced tool use + enum constraints | scheme_type: 7 valid ✓; signals: 632 unique (89% singletons) |
| 3 | `third_run_prep.md` | `third_run_lessons.md` | Closed signals vocabulary + applicability redefinition | signals: 110 unique, 7.8% OOV; HIGH: 3→17 |
| 4 | `fourth_run_prep.md` | `fourth_run_lessons.md` | Seed expansion + underscore fix + explicit anti-leak list | OOV regressed 7.8%→13.9%; seed expansion backfired; leaking worsened |

---

## Run Protocol

Follow this sequence for every run:

1. **Write `{n}_run_prep.md`** documenting all prompt/code changes and expected outcomes
2. **Smoke test:** `python -m jfia_forensic.enrichment ... --limit 20`
3. **Inspect smoke output** — check OOV signals, applicability distribution, leaking
4. **Patch seed if needed** — add any OOV terms that are legitimate; re-smoke if changes were substantial
5. **Full run:** `python -m jfia_forensic.enrichment ...` (background task)
6. **Analyse output** — run the standard inspection queries (see below)
7. **Write `{n}_run_lessons.md`** — post-mortem with three-run comparison tables
8. **Commit:** `data/curated/jfia_enriched.json` + both report files

---

## Standard Inspection Queries

Run these after every full run to populate the lessons document:

```python
import json
from collections import Counter

data = json.load(open('data/curated/jfia_enriched.json', encoding='utf-8'))

# Field distributions
schemes  = Counter(a['scheme_type'] for a in data if a['scheme_type'])
fss      = Counter(a['fss_violation_category'] for a in data if a['fss_violation_category'])
ka       = Counter(a['korean_applicability'] for a in data)

# Signals analysis
all_signals = [s for a in data for s in a.get('signals', [])]
signal_counter = Counter(all_signals)
oov = [s for s in all_signals if s not in SEED]          # define SEED from constants
leaking = [s for s in all_signals if s in SCHEME_TYPES + FSS_VIOLATION_CATEGORIES]

# HIGH articles
highs = [a for a in data if a['korean_applicability'] == 'HIGH']
```
