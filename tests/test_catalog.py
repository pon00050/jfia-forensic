"""Tests for JFIACatalog — written before implementation (TDD)."""

import json
from pathlib import Path

import pytest

from jfia_forensic.catalog import JFIACatalog


# 3-article mini-catalog fixture
MINI_CATALOG = {
    "scraped_at": "2025-01-01",
    "total_articles": 3,
    "issues": [
        {
            "volume": 1,
            "issue": 1,
            "period": "2009 Q1",
            "contentid": "abc",
            "url": "https://example.com",
            "is_special_issue": False,
            "articles": [
                {
                    "index": 1,
                    "title": "Beneish M-Score and Earnings Manipulation",
                    "authors": ["Smith A"],
                    "abstract": "This study examines the Beneish M-Score as a tool for detecting earnings management in public companies.",
                    "keywords": ["M-SCORE", "earnings management", "fraud detection"],
                    "pdf_url": "https://example.com/1.pdf",
                },
                {
                    "index": 2,
                    "title": "Convertible Bond Repricing Manipulation",
                    "authors": ["Kim B"],
                    "abstract": "We analyze convertible bond repricing events and their association with stock price manipulation.",
                    "keywords": ["convertible bond", "repricing", "stock manipulation"],
                    "pdf_url": "https://example.com/2.pdf",
                },
                {
                    "index": 3,
                    "title": "Disclosure Timing and Insider Trading",
                    "authors": ["Lee C"],
                    "abstract": "",
                    "keywords": [],
                    "pdf_url": "https://example.com/3.pdf",
                },
            ],
        }
    ],
}

MINI_ENRICHED = [
    {
        "article": {
            "index": 1,
            "title": "Beneish M-Score and Earnings Manipulation",
            "authors": ["Smith A"],
            "abstract": "...",
            "keywords": ["M-SCORE"],
            "pdf_url": "https://example.com/1.pdf",
            "volume": 1,
            "issue": 1,
            "period": "2009 Q1",
        },
        "scheme_type": "earnings_manipulation",
        "signals": ["DSRI", "TATA"],
        "data_fields": ["receivables", "revenue"],
        "korean_applicability": "HIGH",
        "fss_violation_category": "revenue_fabrication",
    }
]


@pytest.fixture
def catalog_file(tmp_path: Path) -> Path:
    p = tmp_path / "jfia_catalog.json"
    p.write_text(json.dumps(MINI_CATALOG), encoding="utf-8")
    return p


@pytest.fixture
def enriched_file(tmp_path: Path) -> Path:
    p = tmp_path / "jfia_enriched.json"
    p.write_text(json.dumps(MINI_ENRICHED), encoding="utf-8")
    return p


def test_catalog_loads_json(catalog_file):
    """total_articles count matches loaded articles."""
    catalog = JFIACatalog.load(catalog_file)
    assert catalog.total_articles == 3


def test_catalog_article_has_issue_fields(catalog_file):
    """Loaded articles include volume, issue, period from parent issue."""
    catalog = JFIACatalog.load(catalog_file)
    article = catalog._articles[0]
    assert article.volume == 1
    assert article.issue == 1
    assert article.period == "2009 Q1"


def test_catalog_search_title_match(catalog_file):
    """Query 'Beneish' matches article with that word in title."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.search("Beneish")
    assert len(results) >= 1
    assert any("Beneish" in r.title for r in results)


def test_catalog_search_keyword_match(catalog_file):
    """Query 'earnings management' finds keyword match."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.search("earnings management")
    assert len(results) >= 1
    assert any("earnings management" in [k.lower() for k in r.keywords] for r in results)


def test_catalog_search_limit_respected(catalog_file):
    """limit parameter caps number of results."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.search("manipulation", limit=1)
    assert len(results) <= 1


def test_catalog_search_empty_query_raises(catalog_file):
    """Empty query string raises ValueError."""
    catalog = JFIACatalog.load(catalog_file)
    with pytest.raises(ValueError, match="non-empty"):
        catalog.search("")


def test_catalog_search_whitespace_query_raises(catalog_file):
    """Whitespace-only query raises ValueError."""
    catalog = JFIACatalog.load(catalog_file)
    with pytest.raises(ValueError):
        catalog.search("   ")


def test_catalog_handles_missing_abstract(catalog_file):
    """Article with empty abstract (index 3) loads cleanly."""
    catalog = JFIACatalog.load(catalog_file)
    article = next(a for a in catalog._articles if a.index == 3)
    assert article.abstract == ""


def test_catalog_by_scheme_requires_enriched(catalog_file):
    """by_scheme() returns empty list if enriched JSON not loaded."""
    catalog = JFIACatalog.load(catalog_file)  # no enriched_path
    results = catalog.by_scheme("earnings_manipulation")
    assert results == []


def test_catalog_by_scheme_returns_subset(catalog_file, enriched_file):
    """by_scheme() returns enriched articles of that scheme."""
    catalog = JFIACatalog.load(catalog_file, enriched_path=enriched_file)
    results = catalog.by_scheme("earnings_manipulation")
    assert len(results) == 1
    assert results[0].index == 1


def test_catalog_search_no_match_returns_empty(catalog_file):
    """Query with no matches returns empty list."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.search("xyzzy_nonexistent_term_12345")
    assert results == []


def test_catalog_by_keyword_case_insensitive(catalog_file):
    """by_keyword() matches case-insensitively."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.by_keyword("m-score")
    assert len(results) >= 1
    assert any("M-SCORE" in a.keywords for a in results)


def test_catalog_by_keyword_partial_match(catalog_file):
    """by_keyword() matches partial keyword strings."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.by_keyword("earnings")
    assert len(results) >= 1


def test_catalog_by_keyword_no_match(catalog_file):
    """by_keyword() returns empty list for non-matching keyword."""
    catalog = JFIACatalog.load(catalog_file)
    results = catalog.by_keyword("xyzzy_nonexistent_keyword")
    assert results == []


def test_catalog_by_keyword_empty_keywords_skipped(catalog_file):
    """Articles with empty keyword list are skipped by by_keyword()."""
    catalog = JFIACatalog.load(catalog_file)
    # Article 3 has keywords=[] — should not appear for any query
    results = catalog.by_keyword("Disclosure")
    assert all(a.index != 3 for a in results)
