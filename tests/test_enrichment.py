"""Tests for enrichment pipeline — written before implementation (TDD)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jfia_forensic.constants import HAIKU_MODEL
from jfia_forensic.enrichment import enrich_catalog, _enrich_one, _build_fallback
from jfia_forensic.models import EnrichedArticle, JFIAArticle
from jfia_forensic.catalog import JFIACatalog


# --- Fixtures ---

def _make_article(index: int = 1, abstract: str = "Sample abstract text") -> JFIAArticle:
    return JFIAArticle(
        index=index,
        title=f"Article {index}",
        authors=["Author A"],
        abstract=abstract,
        keywords=["test"],
        pdf_url=f"https://example.com/{index}.pdf",
    )


VALID_HAIKU_RESPONSE = json.dumps({
    "scheme_type": "earnings_manipulation",
    "signals": ["DSRI", "TATA"],
    "data_fields": ["receivables", "revenue"],
    "korean_applicability": "HIGH",
    "fss_violation_category": "revenue_fabrication",
})


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


# --- Tests ---

def test_enrichment_calls_haiku_model():
    """_enrich_one must use HAIKU_MODEL, not sonnet/opus."""
    article = _make_article()
    client = _mock_client(VALID_HAIKU_RESPONSE)
    _enrich_one(client, article)
    call_kwargs = client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == HAIKU_MODEL


def test_enrichment_skips_empty_abstract():
    """Article with empty abstract returns UNKNOWN applicability without calling API."""
    article = _make_article(abstract="")
    client = _mock_client(VALID_HAIKU_RESPONSE)
    result = _enrich_one(client, article)
    client.messages.create.assert_not_called()
    assert result.korean_applicability == "UNKNOWN"
    assert result.scheme_type is None


def test_enrichment_parses_valid_json_response():
    """Valid Haiku JSON response produces EnrichedArticle with all fields."""
    article = _make_article()
    client = _mock_client(VALID_HAIKU_RESPONSE)
    result = _enrich_one(client, article)
    assert result.scheme_type == "earnings_manipulation"
    assert "DSRI" in result.signals
    assert result.korean_applicability == "HIGH"
    assert result.fss_violation_category == "revenue_fabrication"


def test_enrichment_handles_malformed_response():
    """JSON parse failure returns fallback EnrichedArticle with UNKNOWN."""
    article = _make_article()
    client = _mock_client("not valid json {{{")
    result = _enrich_one(client, article)
    assert result.korean_applicability == "UNKNOWN"
    assert result.scheme_type is None
    assert result.signals == []


def test_enrichment_handles_api_exception():
    """API exception returns fallback EnrichedArticle."""
    article = _make_article()
    client = MagicMock()
    client.messages.create.side_effect = Exception("API error")
    result = _enrich_one(client, article)
    assert result.korean_applicability == "UNKNOWN"


def test_enrichment_output_schema(tmp_path):
    """enrich_catalog output length == input length; all EnrichedArticle instances."""
    import json as _json
    catalog_data = {
        "scraped_at": "2025-01-01",
        "total_articles": 2,
        "issues": [
            {
                "volume": 1, "issue": 1, "period": "2009", "contentid": "x",
                "url": "https://example.com", "is_special_issue": False,
                "articles": [
                    {"index": 1, "title": "A", "authors": [], "abstract": "text", "keywords": [], "pdf_url": "https://x.com/1.pdf"},
                    {"index": 2, "title": "B", "authors": [], "abstract": "", "keywords": [], "pdf_url": "https://x.com/2.pdf"},
                ],
            }
        ],
    }
    p = tmp_path / "catalog.json"
    p.write_text(_json.dumps(catalog_data), encoding="utf-8")
    catalog = JFIACatalog.load(p)

    client = _mock_client(VALID_HAIKU_RESPONSE)
    results = enrich_catalog(catalog, client)

    assert len(results) == 2
    assert all(isinstance(r, EnrichedArticle) for r in results)


def test_enrichment_limit_parameter(tmp_path):
    """limit=1 processes only 1 article."""
    import json as _json
    catalog_data = {
        "scraped_at": "2025-01-01",
        "total_articles": 3,
        "issues": [
            {
                "volume": 1, "issue": 1, "period": "2009", "contentid": "x",
                "url": "https://example.com", "is_special_issue": False,
                "articles": [
                    {"index": i, "title": f"Article {i}", "authors": [], "abstract": "text", "keywords": [], "pdf_url": f"https://x.com/{i}.pdf"}
                    for i in range(1, 4)
                ],
            }
        ],
    }
    p = tmp_path / "catalog.json"
    p.write_text(_json.dumps(catalog_data), encoding="utf-8")
    catalog = JFIACatalog.load(p)

    client = _mock_client(VALID_HAIKU_RESPONSE)
    results = enrich_catalog(catalog, client, limit=1)
    assert len(results) == 1
