# jfia-forensic

Forensic accounting detectlet schema and JFIA literature catalog tools.

Provides:
- `Detectlet` / `DetectletRegistry` — structured YAML-based fraud detection module definitions
- `JFIACatalog` — searchable index of 469 JFIA peer-reviewed forensic accounting papers
- Haiku-powered enrichment pipeline for abstracting scheme/signal metadata from abstracts

## Install

```bash
pip install jfia-forensic
```

## Quick start

```python
from jfia_forensic import DetectletRegistry, JFIACatalog

# Load detectlet definitions
registry = DetectletRegistry.from_yaml_dir("data/curated/detectlets/")
beneish = registry.get("Beneish M-Score")

# Search JFIA literature
catalog = JFIACatalog.load("data/raw/jfia_catalog.json")
papers = catalog.search("earnings management", limit=5)
for p in papers:
    print(p.title)
```

## Data

The JFIA catalog (`data/raw/jfia_catalog.json`) is sourced from the
[jfia-catalog](https://github.com/pon00050/jfia-catalog) dataset repository.
469 articles, 2009–2025.

## License

MIT
