"""Shared fixtures for jfia-forensic tests."""

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_catalog_json(tmp_path: Path) -> Path:
    """3-article catalog JSON in tmp_path."""
    catalog = {
        "scraped_at": "2025-01-01",
        "total_articles": 3,
        "issues": [
            {
                "volume": 1, "issue": 1, "period": "2009 Q1",
                "contentid": "abc", "url": "https://example.com",
                "is_special_issue": False,
                "articles": [
                    {
                        "index": 1,
                        "title": "Beneish M-Score Detection",
                        "authors": ["Smith A"],
                        "abstract": "Earnings management detection via M-Score.",
                        "keywords": ["M-SCORE", "earnings management"],
                        "pdf_url": "https://example.com/1.pdf",
                    },
                    {
                        "index": 2,
                        "title": "Convertible Bond Fraud Patterns",
                        "authors": ["Kim B"],
                        "abstract": "CB repricing and stock manipulation.",
                        "keywords": ["convertible bond", "manipulation"],
                        "pdf_url": "https://example.com/2.pdf",
                    },
                    {
                        "index": 3,
                        "title": "Disclosure Timing Anomalies",
                        "authors": ["Lee C"],
                        "abstract": "",
                        "keywords": [],
                        "pdf_url": "https://example.com/3.pdf",
                    },
                ],
            }
        ],
    }
    p = tmp_path / "jfia_catalog.json"
    p.write_text(json.dumps(catalog), encoding="utf-8")
    return p


@pytest.fixture
def sample_detectlet_yaml(tmp_path: Path) -> Path:
    """Single valid detectlet YAML in tmp_path."""
    content = textwrap.dedent("""\
        name: "Sample Beneish"
        version: "1.0.0"
        scheme: "earnings_manipulation"
        fss_violation_categories:
          - "revenue_fabrication"
        jfia_citations:
          - volume: 1
            issue: 1
            index: 4
            title: "Test Paper"
            authors: ["Author A"]
            pdf_url: "https://example.com/paper.pdf"
        signals:
          - name: "DSRI"
            description: "Days Sales Receivable Index"
            threshold: 1.465
            direction: "above"
        required_fields:
          - receivables
          - revenue
        threshold: -1.78
        korean_threshold: -2.45
        output_fields:
          - m_score
          - flag
        interpretation: "M-Score above -1.78 indicates possible manipulation"
    """)
    p = tmp_path / "sample.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def two_article_catalog(tmp_path: Path) -> Path:
    """2-article catalog JSON in tmp_path (one with abstract, one without)."""
    catalog = {
        "scraped_at": "2025-01-01",
        "total_articles": 2,
        "issues": [
            {
                "volume": 1, "issue": 1, "period": "2009 Q1",
                "contentid": "abc", "url": "https://example.com",
                "is_special_issue": False,
                "articles": [
                    {
                        "index": 1,
                        "title": "Earnings Management and Fraud Detection",
                        "authors": ["Smith A"],
                        "abstract": "This study examines earnings manipulation using accruals.",
                        "keywords": ["earnings management", "accruals"],
                        "pdf_url": "https://example.com/1.pdf",
                    },
                    {
                        "index": 2,
                        "title": "Audit Quality and Fraud Risk",
                        "authors": ["Lee B"],
                        "abstract": "",
                        "keywords": [],
                        "pdf_url": "https://example.com/2.pdf",
                    },
                ],
            }
        ],
    }
    p = tmp_path / "two_article_catalog.json"
    p.write_text(json.dumps(catalog), encoding="utf-8")
    return p


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Monkeypatched Anthropic client returning a valid tool-use block."""
    tool_input = {
        "scheme_type": "earnings_manipulation",
        "signals": ["DSRI"],
        "data_fields": ["receivables"],
        "korean_applicability": "HIGH",
        "fss_violation_category": "revenue_fabrication",
    }
    client = MagicMock()
    tool_block = MagicMock()
    tool_block.input = tool_input
    client.messages.create.return_value = MagicMock(content=[tool_block])
    return client
