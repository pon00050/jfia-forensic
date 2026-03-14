"""
JFIACatalog — loads and searches the JFIA article catalog JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import JFIAArticle, EnrichedArticle


class JFIACatalog:
    def __init__(
        self,
        articles: list[JFIAArticle],
        enriched: list[EnrichedArticle] | None = None,
    ) -> None:
        self._articles = articles
        # Map index → enriched for fast lookup
        self._enriched: dict[int, EnrichedArticle] = (
            {e.article.index: e for e in enriched} if enriched else {}
        )

    @classmethod
    def load(
        cls,
        catalog_path: str | Path,
        enriched_path: str | Path | None = None,
    ) -> "JFIACatalog":
        """
        Load catalog from jfia_catalog.json (nested issues → articles).
        Optionally load enriched JSON for scheme-based search.
        """
        catalog_path = Path(catalog_path)
        with open(catalog_path, encoding="utf-8") as f:
            raw = json.load(f)

        articles: list[JFIAArticle] = []
        for issue in raw.get("issues", []):
            vol = issue.get("volume")
            iss = issue.get("issue")
            period = issue.get("period")
            for a in issue.get("articles", []):
                articles.append(
                    JFIAArticle(
                        index=a["index"],
                        title=a.get("title", ""),
                        authors=a.get("authors", []),
                        abstract=a.get("abstract") or "",
                        keywords=a.get("keywords") or [],
                        pdf_url=a.get("pdf_url", ""),
                        volume=vol,
                        issue=iss,
                        period=period,
                    )
                )

        enriched: list[EnrichedArticle] | None = None
        if enriched_path is not None:
            ep = Path(enriched_path)
            if ep.exists():
                with open(ep, encoding="utf-8") as f:
                    enriched_raw = json.load(f)
                from .models import EnrichedArticle as EA
                enriched = [EA.model_validate(e) for e in enriched_raw]

        return cls(articles, enriched)

    @property
    def total_articles(self) -> int:
        return len(self._articles)

    def search(self, query: str, limit: int = 10) -> list[JFIAArticle]:
        """
        Keyword search over title, keywords, and abstract.
        Falls back to title-only if query matches nothing in keywords.
        Raises ValueError on empty query.
        """
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        terms = query.lower().split()

        def score(article: JFIAArticle) -> int:
            s = 0
            title_lower = article.title.lower()
            abstract_lower = article.abstract.lower()
            kw_lower = " ".join(article.keywords).lower()
            for term in terms:
                if term in title_lower:
                    s += 3
                if term in kw_lower:
                    s += 2
                if term in abstract_lower:
                    s += 1
            return s

        scored = [(score(a), a) for a in self._articles]
        scored = [(s, a) for s, a in scored if s > 0]
        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored[:limit]]

    def by_scheme(self, scheme: str) -> list[JFIAArticle]:
        """
        Return articles classified under a scheme_type.
        Requires enriched JSON; returns empty list if not loaded.
        """
        matching = [
            e.article
            for e in self._enriched.values()
            if e.scheme_type == scheme
        ]
        return matching

    def by_keyword(self, keyword: str) -> list[JFIAArticle]:
        """Return articles whose keyword list contains keyword (case-insensitive)."""
        kw_lower = keyword.lower()
        return [
            a for a in self._articles
            if any(kw_lower in k.lower() for k in a.keywords)
        ]
