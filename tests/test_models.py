"""Tests for Pydantic models — written before implementation (TDD)."""

import pytest
from pydantic import ValidationError

from jfia_forensic.models import (
    Detectlet,
    DetectletMatch,
    EnrichedArticle,
    JFIAArticle,
    JFIACitation,
    Signal,
)


# --- Helpers ---

def _make_citation() -> JFIACitation:
    return JFIACitation(
        volume=1, issue=1, index=4,
        title="Test Paper",
        authors=["Author A"],
        pdf_url="https://example.com/paper.pdf",
    )


def _make_detectlet(scheme: str = "earnings_manipulation") -> Detectlet:
    return Detectlet(
        name="Test Detectlet",
        version="1.0.0",
        scheme=scheme,
        fss_violation_categories=["revenue_fabrication"],
        jfia_citations=[_make_citation()],
        signals=[Signal(name="DSRI", description="Days Sales Receivable Index")],
        required_fields=["receivables", "revenue"],
        threshold=-1.78,
        korean_threshold=-2.45,
        output_fields=["m_score", "flag"],
        interpretation="Test interpretation",
    )


def _make_article() -> JFIAArticle:
    return JFIAArticle(
        index=1,
        title="Test Article",
        authors=["Author A"],
        abstract="Some abstract text",
        keywords=["earnings management"],
        pdf_url="https://example.com/article.pdf",
    )


# --- Tests ---

def test_detectlet_requires_valid_scheme():
    """Invalid scheme string raises ValidationError."""
    with pytest.raises(ValidationError, match="scheme"):
        Detectlet(
            name="Bad",
            version="1.0.0",
            scheme="invalid_scheme_xyz",
            fss_violation_categories=[],
            jfia_citations=[],
            signals=[],
            required_fields=[],
            output_fields=[],
            interpretation="x",
        )


def test_detectlet_valid_scheme_accepted():
    """All SCHEME_TYPES values are accepted."""
    from jfia_forensic.constants import SCHEME_TYPES
    for scheme in SCHEME_TYPES:
        d = _make_detectlet(scheme=scheme)
        assert d.scheme == scheme


def test_detectlet_serializes_to_dict():
    """model_dump() roundtrip preserves all fields."""
    d = _make_detectlet()
    dumped = d.model_dump()
    assert dumped["name"] == "Test Detectlet"
    assert dumped["scheme"] == "earnings_manipulation"
    assert dumped["threshold"] == -1.78
    assert dumped["korean_threshold"] == -2.45
    assert len(dumped["signals"]) == 1
    assert dumped["signals"][0]["name"] == "DSRI"


def test_detectlet_optional_thresholds_default_none():
    """threshold and korean_threshold default to None."""
    d = Detectlet(
        name="No Threshold",
        version="1.0.0",
        scheme="earnings_manipulation",
        fss_violation_categories=[],
        jfia_citations=[],
        signals=[],
        required_fields=[],
        output_fields=[],
        interpretation="x",
    )
    assert d.threshold is None
    assert d.korean_threshold is None


def test_enriched_article_applicability_values():
    """Only HIGH/MEDIUM/LOW/UNKNOWN accepted for korean_applicability."""
    for valid in ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        ea = EnrichedArticle(article=_make_article(), korean_applicability=valid)
        assert ea.korean_applicability == valid

    with pytest.raises(ValidationError):
        EnrichedArticle(article=_make_article(), korean_applicability="INVALID")


def test_jfia_article_empty_abstract_allowed():
    """Empty abstract is valid — 106 articles have none."""
    a = JFIAArticle(
        index=99,
        title="No Abstract Paper",
        authors=["Author B"],
        abstract="",
        keywords=[],
        pdf_url="https://example.com/noabs.pdf",
    )
    assert a.abstract == ""


def test_jfia_article_abstract_defaults_to_empty():
    """abstract has default of empty string."""
    a = JFIAArticle(
        index=1,
        title="T",
        authors=[],
        pdf_url="https://example.com/x.pdf",
    )
    assert a.abstract == ""


def test_detectlet_match_relevance_range():
    """DetectletMatch accepts any relevance_score; validate range in usage."""
    dm = DetectletMatch(
        detectlet=_make_detectlet(),
        matching_articles=[_make_article()],
        relevance_score=0.75,
    )
    assert 0.0 <= dm.relevance_score <= 1.0


def test_signal_optional_fields_default_none():
    """Signal threshold and direction default to None."""
    s = Signal(name="X", description="Y")
    assert s.threshold is None
    assert s.direction is None
