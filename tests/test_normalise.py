"""Tests for normalise module — post-processing signal cleanup."""

import json
from unittest.mock import patch

import pytest

from jfia_forensic.constants import SIGNAL_FORBIDDEN_LABELS, SIGNAL_SEED_VOCABULARY
from jfia_forensic.normalise import main, normalise_signals


def _make_records(signals_list: list[list[str]]) -> list[dict]:
    return [
        {
            "article": {
                "index": i, "title": f"Article {i}", "authors": [],
                "abstract": "text", "keywords": [], "pdf_url": "https://x.com/",
            },
            "signals": signals,
            "scheme_type": "earnings_manipulation",
            "data_fields": [],
            "korean_applicability": "HIGH",
            "fss_violation_category": "revenue_fabrication",
        }
        for i, signals in enumerate(signals_list, 1)
    ]


def test_non_strict_removes_forbidden_labels_only():
    records = _make_records([["disclosure fraud", "fraud detection"]])
    result = normalise_signals(records, strict=False)
    assert "disclosure fraud" not in result[0]["signals"]
    assert "fraud detection" in result[0]["signals"]


def test_non_strict_removes_all_forbidden_surface_forms():
    forbidden = list(SIGNAL_FORBIDDEN_LABELS)[:3]
    records = _make_records([forbidden + ["DSRI"]])
    result = normalise_signals(records, strict=False)
    for f in forbidden:
        assert f not in result[0]["signals"]
    assert "DSRI" in result[0]["signals"]


def test_strict_keeps_only_seed_vocabulary():
    records = _make_records([["DSRI", "fraud detection"]])
    result = normalise_signals(records, strict=True)
    assert "DSRI" in result[0]["signals"]
    assert "fraud detection" not in result[0]["signals"]


def test_strict_keeps_all_seed_terms():
    seed_sample = list(SIGNAL_SEED_VOCABULARY)[:5]
    records = _make_records([seed_sample])
    result = normalise_signals(records, strict=True)
    assert set(result[0]["signals"]) == set(seed_sample)


def test_does_not_mutate_input():
    records = _make_records([["disclosure fraud", "DSRI"]])
    original_signals = list(records[0]["signals"])
    normalise_signals(records, strict=False)
    assert records[0]["signals"] == original_signals


def test_empty_and_null_signals_handled():
    records = [
        {
            "article": {"index": 1, "title": "A", "authors": [],
                        "abstract": "", "keywords": [], "pdf_url": "https://x.com/"},
            "signals": [],
            "scheme_type": None, "data_fields": [],
            "korean_applicability": "UNKNOWN", "fss_violation_category": None,
        },
        {
            "article": {"index": 2, "title": "B", "authors": [],
                        "abstract": "", "keywords": [], "pdf_url": "https://x.com/"},
            "signals": None,
            "scheme_type": None, "data_fields": [],
            "korean_applicability": "UNKNOWN", "fss_violation_category": None,
        },
    ]
    result = normalise_signals(records)
    assert result[0]["signals"] == []
    assert result[1]["signals"] == []


def test_non_signal_fields_preserved():
    records = _make_records([["DSRI"]])
    records[0]["scheme_type"] = "earnings_manipulation"
    records[0]["korean_applicability"] = "HIGH"
    result = normalise_signals(records)
    assert result[0]["scheme_type"] == "earnings_manipulation"
    assert result[0]["korean_applicability"] == "HIGH"


def test_main_cli_overwrites_input_by_default(tmp_path):
    records = _make_records([["disclosure fraud", "DSRI"]])
    input_path = tmp_path / "enriched.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")

    with patch("sys.argv", ["normalise", str(input_path)]):
        main()

    result = json.loads(input_path.read_text(encoding="utf-8"))
    assert "disclosure fraud" not in result[0]["signals"]
    assert "DSRI" in result[0]["signals"]


def test_main_cli_output_flag_writes_separate_file(tmp_path):
    records = _make_records([["DSRI"]])
    input_path = tmp_path / "enriched.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")

    with patch("sys.argv", ["normalise", str(input_path), "--output", str(output_path)]):
        main()

    assert output_path.exists()
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result[0]["signals"] == ["DSRI"]


def test_main_cli_strict_mode(tmp_path):
    records = _make_records([["DSRI", "fraud detection"]])
    input_path = tmp_path / "enriched.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")

    with patch("sys.argv", ["normalise", str(input_path), "--strict"]):
        main()

    result = json.loads(input_path.read_text(encoding="utf-8"))
    assert "DSRI" in result[0]["signals"]
    assert "fraud detection" not in result[0]["signals"]
