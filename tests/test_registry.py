"""Tests for DetectletRegistry — written before implementation (TDD)."""

import textwrap
from pathlib import Path

import pytest

from jfia_forensic.registry import DetectletRegistry


VALID_YAML = textwrap.dedent("""\
    name: "Test Beneish"
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

VALID_YAML_2 = textwrap.dedent("""\
    name: "Test CB/BW"
    version: "1.0.0"
    scheme: "cb_bw_manipulation"
    fss_violation_categories:
      - "disclosure_fraud"
    jfia_citations: []
    signals:
      - name: "repricing_flag"
        description: "CB repriced below market"
    required_fields:
      - issue_amount
    output_fields:
      - flag_count
    interpretation: "CB/BW manipulation flag"
""")

INVALID_YAML = "not: valid: yaml: :"


def _write_yaml(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def test_registry_loads_yaml_dir(tmp_path):
    """Loads all .yaml files from a directory."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    _write_yaml(tmp_path, "b.yaml", VALID_YAML_2)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    assert len(registry.all()) == 2


def test_registry_get_by_name(tmp_path):
    """Exact name lookup returns Detectlet."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    d = registry.get("Test Beneish")
    assert d is not None
    assert d.name == "Test Beneish"
    assert d.scheme == "earnings_manipulation"


def test_registry_get_missing_returns_none(tmp_path):
    """Missing name returns None."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    assert registry.get("Nonexistent Detectlet") is None


def test_registry_search_by_scheme(tmp_path):
    """scheme='earnings_manipulation' returns only matching detectlets."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    _write_yaml(tmp_path, "b.yaml", VALID_YAML_2)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    results = registry.search(scheme="earnings_manipulation")
    assert len(results) == 1
    assert results[0].name == "Test Beneish"


def test_registry_search_no_filter_returns_all(tmp_path):
    """search() with no scheme returns all detectlets."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    _write_yaml(tmp_path, "b.yaml", VALID_YAML_2)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    assert len(registry.search()) == 2


def test_registry_all_returns_list(tmp_path):
    """.all() returns list of all loaded detectlets."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    result = registry.all()
    assert isinstance(result, list)
    assert len(result) == 1


def test_registry_empty_dir(tmp_path):
    """Empty directory returns empty registry."""
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    assert registry.all() == []


def test_registry_rejects_invalid_yaml(tmp_path):
    """Malformed YAML raises ValueError with filename."""
    _write_yaml(tmp_path, "bad.yaml", INVALID_YAML)
    with pytest.raises(ValueError, match="bad.yaml"):
        DetectletRegistry.from_yaml_dir(tmp_path)


def test_registry_rejects_invalid_scheme(tmp_path):
    """YAML with unknown scheme raises ValueError."""
    bad_scheme = VALID_YAML.replace(
        "scheme: \"earnings_manipulation\"",
        "scheme: \"fake_scheme\""
    )
    _write_yaml(tmp_path, "bad_scheme.yaml", bad_scheme)
    with pytest.raises(ValueError):
        DetectletRegistry.from_yaml_dir(tmp_path)


def test_registry_by_fss_violation_category(tmp_path):
    """by_fss_violation_category() returns matching detectlets."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    _write_yaml(tmp_path, "b.yaml", VALID_YAML_2)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    results = registry.by_fss_violation_category("revenue_fabrication")
    assert len(results) == 1
    assert results[0].name == "Test Beneish"


def test_registry_by_fss_violation_category_no_match(tmp_path):
    """by_fss_violation_category() returns empty for non-matching category."""
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    results = registry.by_fss_violation_category("asset_inflation")
    assert results == []


def test_registry_by_fss_violation_category_multiple_matches(tmp_path):
    """by_fss_violation_category() returns all detectlets with that category."""
    # Modify VALID_YAML_2 to also include revenue_fabrication
    yaml_with_same_cat = VALID_YAML_2.replace(
        '- "disclosure_fraud"',
        '- "disclosure_fraud"\n  - "revenue_fabrication"'
    )
    _write_yaml(tmp_path, "a.yaml", VALID_YAML)
    _write_yaml(tmp_path, "b.yaml", yaml_with_same_cat)
    registry = DetectletRegistry.from_yaml_dir(tmp_path)
    results = registry.by_fss_violation_category("revenue_fabrication")
    assert len(results) == 2
