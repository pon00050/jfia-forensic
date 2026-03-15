"""
normalise.py — Post-processing signal cleanup for jfia_enriched.json.

Usage:
    python -m jfia_forensic.normalise data/curated/jfia_enriched.json [--strict] [--output PATH]
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from .constants import SIGNAL_FORBIDDEN_LABELS, SIGNAL_SEED_VOCABULARY


def normalise_signals(records: list[dict], strict: bool = False) -> list[dict]:
    """
    Clean OOV signals from enriched article records.

    strict=False (default): removes signals in SIGNAL_FORBIDDEN_LABELS only.
    strict=True: keeps only signals in SIGNAL_SEED_VOCABULARY.

    Returns a new list (does not mutate input).
    """
    result = copy.deepcopy(records)
    for record in result:
        signals = record.get("signals") or []
        if strict:
            record["signals"] = [s for s in signals if s in SIGNAL_SEED_VOCABULARY]
        else:
            record["signals"] = [s for s in signals if s not in SIGNAL_FORBIDDEN_LABELS]
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Normalise signals in jfia_enriched.json")
    parser.add_argument("input_path", help="Path to jfia_enriched.json")
    parser.add_argument("--strict", action="store_true", help="Keep only seed vocabulary signals")
    parser.add_argument("--output", default=None, help="Output path (default: overwrite input)")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    with open(input_path, encoding="utf-8") as f:
        records = json.load(f)

    before_count = sum(len(r.get("signals") or []) for r in records)
    normalised = normalise_signals(records, strict=args.strict)
    after_count = sum(len(r.get("signals") or []) for r in normalised)

    output_path = Path(args.output) if args.output else input_path
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalised, f, ensure_ascii=False, indent=2)

    mode = "strict" if args.strict else "non-strict"
    print(f"Removed {before_count - after_count} signal occurrences ({mode} mode)", file=sys.stderr)


if __name__ == "__main__":
    main()
