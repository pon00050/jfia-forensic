"""Tests for enrichment pipeline — written before implementation (TDD)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

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


VALID_TOOL_INPUT = {
    "scheme_type": "earnings_manipulation",
    "signals": ["DSRI", "TATA"],
    "data_fields": ["receivables", "revenue"],
    "korean_applicability": "HIGH",
    "fss_violation_category": "revenue_fabrication",
}


def _mock_tool_client(tool_input: dict) -> MagicMock:
    client = MagicMock()
    tool_block = MagicMock()
    tool_block.input = tool_input
    client.messages.create.return_value = MagicMock(content=[tool_block])
    return client


# --- Tests ---

def test_enrichment_calls_haiku_model():
    """_enrich_one must use HAIKU_MODEL, pass tools and tool_choice."""
    article = _make_article()
    client = _mock_tool_client(VALID_TOOL_INPUT)
    _enrich_one(client, article)
    call_kwargs = client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == HAIKU_MODEL
    assert "tools" in call_kwargs.kwargs
    assert call_kwargs.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "extract_article_metadata",
    }


def test_enrichment_skips_empty_abstract():
    """Article with empty abstract returns UNKNOWN applicability without calling API."""
    article = _make_article(abstract="")
    client = _mock_tool_client(VALID_TOOL_INPUT)
    result = _enrich_one(client, article)
    client.messages.create.assert_not_called()
    assert result.korean_applicability == "UNKNOWN"
    assert result.scheme_type is None


def test_enrichment_parses_valid_tool_response():
    """Valid tool response produces EnrichedArticle with all fields."""
    article = _make_article()
    client = _mock_tool_client(VALID_TOOL_INPUT)
    result = _enrich_one(client, article)
    assert result.scheme_type == "earnings_manipulation"
    assert "DSRI" in result.signals
    assert result.korean_applicability == "HIGH"
    assert result.fss_violation_category == "revenue_fabrication"


def test_enrichment_handles_malformed_response():
    """AttributeError from unexpected response structure returns fallback EnrichedArticle."""
    article = _make_article()
    client = MagicMock()
    # content[0].input raises AttributeError
    bad_block = MagicMock(spec=[])  # no .input attribute
    client.messages.create.return_value = MagicMock(content=[bad_block])
    result = _enrich_one(client, article)
    assert result.korean_applicability == "UNKNOWN"
    assert result.scheme_type is None
    assert result.signals == []


def test_enrichment_handles_api_exception():
    """API/auth exceptions propagate — they are NOT silently swallowed."""
    article = _make_article()
    client = MagicMock()
    client.messages.create.side_effect = Exception("API error")
    with pytest.raises(Exception, match="API error"):
        _enrich_one(client, article)


def test_enrichment_output_schema(tmp_path):
    """enrich_catalog output length == input length; all EnrichedArticle instances."""
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
    p.write_text(json.dumps(catalog_data), encoding="utf-8")
    catalog = JFIACatalog.load(p)

    client = _mock_tool_client(VALID_TOOL_INPUT)
    results = enrich_catalog(catalog, client)

    assert len(results) == 2
    assert all(isinstance(r, EnrichedArticle) for r in results)


def test_enrichment_limit_parameter(tmp_path):
    """limit=1 processes only 1 article."""
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
    p.write_text(json.dumps(catalog_data), encoding="utf-8")
    catalog = JFIACatalog.load(p)

    client = _mock_tool_client(VALID_TOOL_INPUT)
    results = enrich_catalog(catalog, client, limit=1)
    assert len(results) == 1


def test_enriched_article_invalid_scheme_type_coerces_to_none():
    """scheme_type not in SCHEME_TYPES is coerced to None."""
    article = _make_article()
    enriched = EnrichedArticle(
        article=article,
        scheme_type="Ponzi scheme",
        signals=[],
        data_fields=[],
        korean_applicability="UNKNOWN",
        fss_violation_category=None,
    )
    assert enriched.scheme_type is None


def test_enriched_article_valid_scheme_type_accepted():
    """Valid scheme_type passes through unchanged."""
    article = _make_article()
    enriched = EnrichedArticle(
        article=article,
        scheme_type="earnings_manipulation",
        signals=[],
        data_fields=[],
        korean_applicability="UNKNOWN",
        fss_violation_category=None,
    )
    assert enriched.scheme_type == "earnings_manipulation"


def test_enriched_article_invalid_fss_category_coerces_to_none():
    """fss_violation_category not in FSS_VIOLATION_CATEGORIES is coerced to None."""
    article = _make_article()
    enriched = EnrichedArticle(
        article=article,
        scheme_type=None,
        signals=[],
        data_fields=[],
        korean_applicability="UNKNOWN",
        fss_violation_category="channel_stuffing",
    )
    assert enriched.fss_violation_category is None


def test_by_scheme_end_to_end(tmp_path):
    """by_scheme returns articles matching the requested scheme_type."""
    catalog_data = {
        "scraped_at": "2025-01-01",
        "total_articles": 1,
        "issues": [
            {
                "volume": 1, "issue": 1, "period": "2009", "contentid": "x",
                "url": "https://example.com", "is_special_issue": False,
                "articles": [
                    {
                        "index": 1,
                        "title": "Beneish Detection Study",
                        "authors": ["Smith A"],
                        "abstract": "Earnings management via M-Score.",
                        "keywords": [],
                        "pdf_url": "https://example.com/1.pdf",
                    }
                ],
            }
        ],
    }
    enriched_data = [
        {
            "article": {
                "index": 1,
                "title": "Beneish Detection Study",
                "authors": ["Smith A"],
                "abstract": "Earnings management via M-Score.",
                "keywords": [],
                "pdf_url": "https://example.com/1.pdf",
                "volume": 1,
                "issue": 1,
                "period": "2009",
            },
            "scheme_type": "earnings_manipulation",
            "signals": ["DSRI"],
            "data_fields": [],
            "korean_applicability": "HIGH",
            "fss_violation_category": "revenue_fabrication",
        }
    ]
    catalog_path = tmp_path / "catalog.json"
    enriched_path = tmp_path / "enriched.json"
    catalog_path.write_text(json.dumps(catalog_data), encoding="utf-8")
    enriched_path.write_text(json.dumps(enriched_data), encoding="utf-8")

    catalog = JFIACatalog.load(catalog_path, enriched_path=enriched_path)
    results = catalog.by_scheme("earnings_manipulation")
    assert len(results) == 1
    assert results[0].title == "Beneish Detection Study"
