# CLAUDE.md — jfia-forensic

Forensic accounting detectlet schema and JFIA literature catalog tools.

## Common Commands

```bash
# Install
uv sync --extra dev

# Run tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_models.py::test_name -v

# Load registry (quick sanity check)
python -c "
from jfia_forensic import DetectletRegistry
r = DetectletRegistry.from_yaml_dir('data/curated/detectlets/')
print([d.name for d in r.all()])
"

# Search catalog
python -c "
from jfia_forensic import JFIACatalog
c = JFIACatalog.load('data/raw/jfia_catalog.json')
for a in c.search('Beneish', limit=3): print(a.title)
"

# Run enrichment pipeline (one-time, ~$0.50 with Haiku)
python -m jfia_forensic.enrichment data/raw/jfia_catalog.json \
       data/curated/jfia_enriched.json
```

## Architecture

```
src/jfia_forensic/
    __init__.py      — Public API: Detectlet, DetectletRegistry, JFIACatalog
    constants.py     — SCHEME_TYPES, FSS_VIOLATION_CATEGORIES, HAIKU_MODEL
    models.py        — Pydantic: Detectlet, Signal, JFIACitation, JFIAArticle, EnrichedArticle
    registry.py      — DetectletRegistry: from_yaml_dir(), get(), search(), all()
    catalog.py       — JFIACatalog: load(), search(), by_scheme(), by_keyword()
    enrichment.py    — enrich_catalog(): Haiku batch → EnrichedArticle list → JSON

data/curated/
    detectlets/      — YAML detectlet definitions (tracked — domain expertise)
    jfia_enriched.json — Haiku-enriched catalog (tracked after one-time run)

data/raw/            — jfia_catalog.json (gitignored — source from career-development)
```

## Conventions

- All models use `BaseModel`, Python 3.11+ union syntax (`float | None`)
- No runtime validators; models document contracts only
- `HAIKU_MODEL = "claude-haiku-4-5-20251001"` — never use opus in this project
- Enrichment is idempotent: re-running with same input produces same output
- `catalog.search()` uses keyword overlap on title + keywords + abstract; falls back
  to title-only if enriched JSON absent

## TDD Rules

Write tests before implementations. Every new behaviour needs a test that fails first.
