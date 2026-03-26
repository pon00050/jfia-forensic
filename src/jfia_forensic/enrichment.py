"""
enrich_catalog() — Haiku enrichment of JFIA articles (sequential or batch).

Usage:
    python -m jfia_forensic.enrichment data/raw/jfia_catalog.json \
           data/curated/jfia_enriched.json [--limit N] [--batch]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .catalog import JFIACatalog
from .constants import (
    HAIKU_MODEL,
    ENRICHMENT_SYSTEM_PROMPT,
    SCHEME_TYPES,
    FSS_VIOLATION_CATEGORIES,
    SIGNAL_SEED_VOCABULARY,
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
            "signals": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(SIGNAL_SEED_VOCABULARY)},
            },
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


def _build_batch_request(position: int, article: JFIAArticle) -> dict:
    """Build a single batch request dict for the Anthropic Batch API."""
    return {
        "custom_id": str(position),
        "params": {
            "model": HAIKU_MODEL,
            "max_tokens": 512,
            "system": ENRICHMENT_SYSTEM_PROMPT,
            "tools": [ENRICHMENT_TOOL],
            "tool_choice": {"type": "tool", "name": "extract_article_metadata"},
            "messages": [
                {
                    "role": "user",
                    "content": f"Title: {article.title}\n\nAbstract: {article.abstract}",
                }
            ],
        },
    }


def _parse_batch_result(result, article: JFIAArticle) -> EnrichedArticle:
    """Parse a batch result object into an EnrichedArticle. Falls back on error."""
    try:
        if result.type != "succeeded":
            return _build_fallback(article)
        parsed = result.message.content[0].input
        return EnrichedArticle(
            article=article,
            scheme_type=parsed.get("scheme_type"),
            signals=parsed.get("signals") or [],
            data_fields=parsed.get("data_fields") or [],
            korean_applicability=parsed.get("korean_applicability") or "UNKNOWN",
            fss_violation_category=parsed.get("fss_violation_category"),
        )
    except (AttributeError, KeyError, ValueError, IndexError):
        return _build_fallback(article)


def enrich_catalog(
    catalog: JFIACatalog,
    client,
    limit: int | None = None,
    batch: bool = False,
    poll_interval: int = 30,
) -> list[EnrichedArticle]:
    """
    Enrich articles in catalog using Haiku.

    batch=False (default): sequential, one API call per article.
    batch=True: submits all abstract-bearing articles as a single Batch API request.

    limit applies to both modes — truncates the article list before processing.
    Returns list of EnrichedArticle, same length as the (possibly limited) article list.
    """
    articles = catalog.articles
    if limit is not None:
        articles = articles[:limit]

    if not batch:
        results = []
        for i, article in enumerate(articles, 1):
            enriched = _enrich_one(client, article)
            results.append(enriched)
            if i % 50 == 0:
                print(f"  Enriched {i}/{len(articles)}...", file=sys.stderr)
        return results

    # --- Batch path ---
    with_abstract = [(i, a) for i, a in enumerate(articles) if a.abstract]
    print(
        f"Submitting {len(with_abstract)}/{len(articles)} articles to Batch API...",
        file=sys.stderr,
    )

    requests = [_build_batch_request(i, a) for i, a in with_abstract]
    batch_job = client.messages.batches.create(requests=requests)
    print(f"Batch {batch_job.id} submitted. Polling every {poll_interval}s...", file=sys.stderr)

    while batch_job.processing_status != "ended":
        time.sleep(poll_interval)
        batch_job = client.messages.batches.retrieve(batch_job.id)
        print(f"  Status: {batch_job.processing_status}", file=sys.stderr)

    result_map: dict[int, EnrichedArticle] = {}
    for item in client.messages.batches.results(batch_job.id):
        pos = int(item.custom_id)
        result_map[pos] = _parse_batch_result(item.result, articles[pos])

    return [result_map.get(i, _build_fallback(a)) for i, a in enumerate(articles)]


def main() -> None:
    import argparse
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Enrich JFIA catalog via Haiku")
    parser.add_argument("catalog_path", help="Path to jfia_catalog.json")
    parser.add_argument("output_path", help="Path to write jfia_enriched.json")
    parser.add_argument("--limit", type=int, default=None, help="Max articles to enrich")
    parser.add_argument("--batch", action="store_true", help="Use Anthropic Batch API")
    args = parser.parse_args()

    print(f"Loading catalog from {args.catalog_path}...", file=sys.stderr)
    catalog = JFIACatalog.load(args.catalog_path)
    print(f"  {catalog.total_articles} articles loaded", file=sys.stderr)

    client = anthropic.Anthropic()
    print(f"Enriching via {HAIKU_MODEL} ({'batch' if args.batch else 'sequential'})...", file=sys.stderr)
    enriched = enrich_catalog(catalog, client, limit=args.limit, batch=args.batch)

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
