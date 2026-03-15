# CLAUDE.md — jfia-forensic

Forensic accounting detectlet schema and JFIA literature catalog tools.

## Ecosystem

Part of the Korean forensic accounting toolkit.
- Hub: `../forensic-accounting-toolkit/` | [GitHub](https://github.com/pon00050/forensic-accounting-toolkit)
- Task board: https://github.com/users/pon00050/projects/1
- Role: Analysis library
- Depends on: jfia-catalog (reads jfia_catalog.json)
- Consumed by: kr-forensic-finance (MCP tool #11, detectlet registry)

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

# Run enrichment pipeline — sequential (~$0.55) or batch (~$0.28, 50% discount)
python -m jfia_forensic.enrichment data/raw/jfia_catalog.json \
       data/curated/jfia_enriched.json [--limit N] [--batch]

# Post-processing: remove forbidden/OOV signals (no API calls)
python -m jfia_forensic.normalise data/curated/jfia_enriched.json
python -m jfia_forensic.normalise data/curated/jfia_enriched.json --strict  # keep only seed vocab
```

## Architecture

```
src/jfia_forensic/
    __init__.py      — Public API: all models + DetectletRegistry, JFIACatalog (see __all__)
    constants.py     — SCHEME_TYPES, FSS_VIOLATION_CATEGORIES, HAIKU_MODEL,
                       SIGNAL_SEED_VOCABULARY, SIGNAL_FORBIDDEN_LABELS
    models.py        — Pydantic: Detectlet, Signal, JFIACitation, JFIAArticle, EnrichedArticle
    registry.py      — DetectletRegistry: from_yaml_dir(), get(), search(), all()
    catalog.py       — JFIACatalog: load(catalog_path, enriched_path=None), search(), by_scheme(), by_keyword()
                       by_scheme() returns empty list if enriched_path was not passed to load()
    enrichment.py    — enrich_catalog(): Haiku enrichment → EnrichedArticle list → JSON
                       batch=False (sequential) or batch=True (Batch API, 50% discount)
    normalise.py     — normalise_signals(): remove OOV/forbidden signals post-enrichment; CLI
    downloader.py    — download(): fetch article PDFs to articles/ by signal, scheme, or search

data/curated/
    detectlets/      — YAML detectlet definitions (tracked — domain expertise)
    jfia_enriched.json — Haiku-enriched catalog (tracked after one-time run)

data/raw/            — jfia_catalog.json (gitignored — source from career-development)
```

## Conventions

- All models use `BaseModel`, Python 3.11+ union syntax (`float | None`)
- `Detectlet.scheme` and `EnrichedArticle.korean_applicability` have `@field_validator` enforcing controlled vocabulary (`SCHEME_TYPES` and `KOREAN_APPLICABILITY_VALUES`); all other fields are unenforced
- `HAIKU_MODEL = "claude-haiku-4-5"` — never use opus in this project; always use the short model ID (no date suffix)
- Enrichment is idempotent: re-running with same input produces same output
- `catalog.search()` scores across title (3pts), keywords (2pts), abstract (1pt); no enriched-data dependency

## TDD Rules

Write tests before implementations. Every new behaviour needs a test that fails first.
