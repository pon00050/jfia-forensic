"""
enrich_catalog() — Haiku batch enrichment of JFIA articles.

Usage:
    python -m jfia_forensic.enrichment data/raw/jfia_catalog.json \
           data/curated/jfia_enriched.json [--limit N]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .catalog import JFIACatalog
from .constants import (
    HAIKU_MODEL,
    ENRICHMENT_SYSTEM_PROMPT,
    SCHEME_TYPES,
    FSS_VIOLATION_CATEGORIES,
)
from .models import EnrichedArticle, JFIAArticle


ENRICHMENT_TOOL = {
    "name": "extract_article_metadata",
    "description": "Extract forensic accounting classification from a journal article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scheme_type": {
                "type": ["string", "null"],
                "enum": SCHEME_TYPES + [None],
                "description": (
                    "cb_bw_manipulation = convertible bond or bond warrant schemes "
                    "where issuers depress stock price before conversion/exercise "
                    "(common in Korean markets). Use null if no scheme clearly fits."
                ),
            },
            "signals": {"type": "array", "items": {"type": "string"}},
            "data_fields": {"type": "array", "items": {"type": "string"}},
            "korean_applicability": {
                "type": "string",
                "enum": ["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
            },
            "fss_violation_category": {
                "type": ["string", "null"],
                "enum": FSS_VIOLATION_CATEGORIES + [None],
            },
        },
        "required": [
            "scheme_type", "signals", "data_fields",
            "korean_applicability", "fss_violation_category",
        ],
    },
}


def _build_fallback(article: JFIAArticle) -> EnrichedArticle:
    return EnrichedArticle(
        article=article,
        scheme_type=None,
        signals=[],
        data_fields=[],
        korean_applicability="UNKNOWN",
        fss_violation_category=None,
    )


def _enrich_one(client, article: JFIAArticle) -> EnrichedArticle:
    """Call Haiku to enrich a single article. Returns fallback on failure."""
    if not article.abstract:
        return _build_fallback(article)

    prompt = f"Title: {article.title}\n\nAbstract: {article.abstract}"

    # Auth/connection errors propagate — not caught.
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=ENRICHMENT_SYSTEM_PROMPT,
        tools=[ENRICHMENT_TOOL],
        tool_choice={"type": "tool", "name": "extract_article_metadata"},
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        parsed = response.content[0].input  # dict; no JSON parsing needed
        return EnrichedArticle(
            article=article,
            scheme_type=parsed.get("scheme_type"),
            signals=parsed.get("signals") or [],
            data_fields=parsed.get("data_fields") or [],
            korean_applicability=parsed.get("korean_applicability") or "UNKNOWN",
            fss_violation_category=parsed.get("fss_violation_category"),
        )
    except (AttributeError, KeyError, ValueError):
        return _build_fallback(article)


def enrich_catalog(
    catalog: JFIACatalog,
    client,
    limit: int | None = None,
) -> list[EnrichedArticle]:
    """
    Enrich all (or up to limit) articles in catalog using Haiku.
    Returns list of EnrichedArticle, same length as input articles.
    """
    articles = catalog._articles
    if limit is not None:
        articles = articles[:limit]

    results = []
    for i, article in enumerate(articles, 1):
        enriched = _enrich_one(client, article)
        results.append(enriched)
        if i % 50 == 0:
            print(f"  Enriched {i}/{len(articles)}...", file=sys.stderr)

    return results


def main() -> None:
    import argparse
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Enrich JFIA catalog via Haiku")
    parser.add_argument("catalog_path", help="Path to jfia_catalog.json")
    parser.add_argument("output_path", help="Path to write jfia_enriched.json")
    parser.add_argument("--limit", type=int, default=None, help="Max articles to enrich")
    args = parser.parse_args()

    print(f"Loading catalog from {args.catalog_path}...", file=sys.stderr)
    catalog = JFIACatalog.load(args.catalog_path)
    print(f"  {catalog.total_articles} articles loaded", file=sys.stderr)

    client = anthropic.Anthropic()
    print(f"Enriching via {HAIKU_MODEL}...", file=sys.stderr)
    enriched = enrich_catalog(catalog, client, limit=args.limit)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [e.model_dump() for e in enriched],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Wrote {len(enriched)} enriched articles to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
