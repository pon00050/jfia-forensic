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
- **Cost & token usage** — model, submission mode, total input/output tokens, per-article
  averages, and total cost broken down by input/output at the applicable rate (see pricing
  table below). Always record the service tier (`batch` vs standard) and batch ID if applicable.
- **Data quality findings** — tables comparing this run to prior runs across all
  five enriched fields
- **What worked** — changes that achieved their target, with evidence
- **Remaining issues** — problems not yet resolved, with root cause analysis and
  concrete remediation options ranked by priority
- **Pipeline health** — crashes, fallbacks, API errors, operational observations

---

## Model Pricing Reference

Rates as of 2026-03-15. Update this table if pricing changes.

| Model | Input (standard) | Output (standard) | Input (batch) | Output (batch) |
|-------|-----------------|-------------------|---------------|----------------|
| `claude-haiku-4-5` | $0.80/MTok | $4.00/MTok | $0.40/MTok | $2.00/MTok |
| `claude-sonnet-4-5` | $3.00/MTok | $15.00/MTok | $1.50/MTok | $7.50/MTok |
| `claude-opus-4-5` | $15.00/MTok | $75.00/MTok | $7.50/MTok | $37.50/MTok |

Batch API = 50% discount on all tiers. This project uses Haiku only (see `CLAUDE.md`).

---

## Run Index

| Run | Prep | Lessons | Key change | Total cost | Outcome |
|-----|------|---------|------------|------------|---------|
| 1 | — | `first_run_lessons.md` | Initial run (JSON prompt) | — | scheme_type: 129 freeform; signals: 1,978 unique |
| 2 | — | `second_run_lessons.md` | Forced tool use + enum constraints | — | scheme_type: 7 valid ✓; signals: 632 unique (89% singletons) |
| 3 | `third_run_prep.md` | `third_run_lessons.md` | Closed signals vocabulary + applicability redefinition | ~$0.55 | signals: 110 unique, 7.8% OOV; HIGH: 3→17 |
| 4 | `fourth_run_prep.md` | `fourth_run_lessons.md` | Seed expansion + underscore fix + explicit anti-leak list | ~$0.55 | OOV regressed 7.8%→13.9%; seed expansion backfired |
| 5 | `fifth_run_prep.md` | `fifth_run_lessons.md` | Option B (signals enum) + Batch API + normalise.py | $0.4847 (batch) | OOV 12.3%→2.51%; unique signals 208→81; HIGH 17→21 |

---

## Run Protocol

Follow this sequence for every run:

1. **Write `{n}_run_prep.md`** documenting all prompt/code changes and expected outcomes
2. **Smoke test:** `python -m jfia_forensic.enrichment ... --limit 20`
3. **Inspect smoke output** — check OOV signals, applicability distribution, leaking
4. **Patch seed if needed** — add any OOV terms that are legitimate; re-smoke if changes were substantial
5. **Full run:** `python -m jfia_forensic.enrichment ... --batch` (preferred) or sequential
6. **Normalise:** `python -m jfia_forensic.normalise data/curated/jfia_enriched.json`
7. **Analyse output** — run the standard inspection queries (see below)
8. **Write `{n}_run_lessons.md`** — post-mortem including cost/token table
9. **Commit:** `data/curated/jfia_enriched.json` + both report files

---

## Standard Inspection Queries

Run these after every full run to populate the lessons document:

```python
import json
from collections import Counter
from jfia_forensic.constants import SIGNAL_SEED_VOCABULARY, SIGNAL_FORBIDDEN_LABELS

data = json.load(open('data/curated/jfia_enriched.json', encoding='utf-8'))

# Field distributions
schemes  = Counter(a['scheme_type'] for a in data if a['scheme_type'])
fss      = Counter(a['fss_violation_category'] for a in data if a['fss_violation_category'])
ka       = Counter(a['korean_applicability'] for a in data)

# Signals analysis
all_signals = [s for a in data for s in (a.get('signals') or [])]
signal_counter = Counter(all_signals)
oov = [s for s in all_signals if s not in SIGNAL_SEED_VOCABULARY]

# HIGH articles
highs = [a for a in data if a['korean_applicability'] == 'HIGH']
```

### Cost query (batch run — run after retrieval, before writing output)

```python
from collections import Counter

total_input = total_output = 0
for item in client.messages.batches.results(BATCH_ID):
    if item.result.type == 'succeeded':
        u = item.result.message.usage
        total_input  += u.input_tokens
        total_output += u.output_tokens

input_cost  = total_input  / 1_000_000 * 0.40   # batch rate
output_cost = total_output / 1_000_000 * 2.00   # batch rate
print(f'Input:  {total_input:,} tokens  ${input_cost:.4f}')
print(f'Output: {total_output:,} tokens  ${output_cost:.4f}')
print(f'Total:  ${input_cost + output_cost:.4f}')
```
