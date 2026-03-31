"""_paths.py — Canonical data directory paths for jfia-forensic.

All file I/O in this package should resolve paths through these constants
rather than constructing paths ad-hoc.
"""

from pathlib import Path

# Repository root (two levels up from this file: src/jfia_forensic/_paths.py)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_RAW_DIR: Path = DATA_DIR / "raw"
DATA_CURATED_DIR: Path = DATA_DIR / "curated"

# Input: jfia_catalog.json — sourced from jfia-catalog repo (gitignored here)
CATALOG_PATH: Path = DATA_RAW_DIR / "jfia_catalog.json"

# Output: Haiku-enriched catalog after running enrichment.py
ENRICHED_PATH: Path = DATA_CURATED_DIR / "jfia_enriched.json"

# Detectlet YAML definitions — committed domain expertise
DETECTLETS_DIR: Path = DATA_CURATED_DIR / "detectlets"

# Downloaded article PDFs
ARTICLES_DIR: Path = PROJECT_ROOT / "articles"
