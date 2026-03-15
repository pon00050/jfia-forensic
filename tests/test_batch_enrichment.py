"""Tests for batch API enrichment path (enrich_catalog with batch=True)."""

import json
from unittest.mock import MagicMock

import pytest

from jfia_forensic.catalog import JFIACatalog
from jfia_forensic.constants import HAIKU_MODEL
from jfia_forensic.enrichment import (
    _build_batch_request,
    _parse_batch_result,
    enrich_catalog,
)
from jfia_forensic.models import EnrichedArticle, JFIAArticle


VALID_TOOL_INPUT = {
    "scheme_type": "earnings_manipulation",
    "signals": ["DSRI", "TATA"],
    "data_fields": ["receivables"],
    "korean_applicability": "HIGH",
    "fss_violation_category": "revenue_fabrication",
}


def _make_article(index: int = 1, abstract: str = "Sample abstract") -> JFIAArticle:
    return JFIAArticle(
        index=index,
        title=f"Article {index}",
        authors=["Author A"],
        abstract=abstract,
        keywords=[],
        pdf_url=f"https://example.com/{index}.pdf",
    )


def _make_batch_result_item(custom_id: str, tool_input: dict) -> MagicMock:
    item = MagicMock()
    item.custom_id = custom_id
    item.result.type = "succeeded"
    item.result.message.content = [MagicMock(input=tool_input)]
    return item


def _make_error_result_item(custom_id: str) -> MagicMock:
    item = MagicMock()
    item.custom_id = custom_id
    item.result.type = "errored"
    return item


def _make_batch_client(result_items: list) -> MagicMock:
    """Client whose batch job is immediately 'ended' on create."""
    client = MagicMock()
    batch_job = MagicMock()
    batch_job.id = "batch_test_001"
    batch_job.processing_status = "ended"
    client.messages.batches.create.return_value = batch_job
    client.messages.batches.retrieve.return_value = batch_job
    client.messages.batches.results.return_value = iter(result_items)
    return client


# --- _build_batch_request ---

def test_build_batch_request_uses_haiku_model():
    req = _build_batch_request(0, _make_article())
    assert req["params"]["model"] == HAIKU_MODEL


def test_build_batch_request_tool_choice():
    req = _build_batch_request(0, _make_article())
    assert req["params"]["tool_choice"] == {"type": "tool", "name": "extract_article_metadata"}


def test_build_batch_request_custom_id_is_string_position():
    req = _build_batch_request(42, _make_article())
    assert req["custom_id"] == "42"


def test_build_batch_request_prompt_contains_abstract():
    article = _make_article(abstract="Unique abstract content XYZ")
    req = _build_batch_request(0, article)
    content = req["params"]["messages"][0]["content"]
    assert "Unique abstract content XYZ" in content


# --- _parse_batch_result ---

def test_parse_batch_result_valid_response():
    result = MagicMock()
    result.type = "succeeded"
    result.message.content = [MagicMock(input=VALID_TOOL_INPUT)]
    enriched = _parse_batch_result(result, _make_article())
    assert enriched.scheme_type == "earnings_manipulation"
    assert "DSRI" in enriched.signals
    assert enriched.korean_applicability == "HIGH"


def test_parse_batch_result_error_response():
    result = MagicMock()
    result.type = "errored"
    enriched = _parse_batch_result(result, _make_article())
    assert enriched.korean_applicability == "UNKNOWN"
    assert enriched.scheme_type is None
    assert enriched.signals == []


# --- enrich_catalog with batch=True ---

def test_batch_output_length_equals_catalog_length(two_article_catalog):
    catalog = JFIACatalog.load(two_article_catalog)
    result_items = [_make_batch_result_item("0", VALID_TOOL_INPUT)]
    client = _make_batch_client(result_items)

    results = enrich_catalog(catalog, client, batch=True, poll_interval=0)
    assert len(results) == len(catalog._articles)


def test_no_abstract_articles_excluded_from_batch(two_article_catalog):
    """Only the 1 article with an abstract is submitted; no-abstract article gets fallback."""
    catalog = JFIACatalog.load(two_article_catalog)
    result_items = [_make_batch_result_item("0", VALID_TOOL_INPUT)]
    client = _make_batch_client(result_items)

    results = enrich_catalog(catalog, client, batch=True, poll_interval=0)

    create_call = client.messages.batches.create.call_args
    submitted = create_call.kwargs.get("requests") or create_call.args[0]
    assert len(submitted) == 1
    assert results[1].korean_applicability == "UNKNOWN"


def test_batch_results_mapped_by_custom_id(sample_catalog_json):
    """Results returned in reverse order are still placed at the correct output positions."""
    catalog = JFIACatalog.load(sample_catalog_json)
    # sample_catalog_json: positions 0 and 1 have abstracts, position 2 does not
    input_a = dict(VALID_TOOL_INPUT, signals=["DSRI"])     # for position 0
    input_b = dict(VALID_TOOL_INPUT, signals=["AQI"])      # for position 1
    # Return in reverse order (1 before 0)
    result_items = [
        _make_batch_result_item("1", input_b),
        _make_batch_result_item("0", input_a),
    ]
    client = _make_batch_client(result_items)

    results = enrich_catalog(catalog, client, batch=True, poll_interval=0)

    assert results[0].signals == ["DSRI"]
    assert results[1].signals == ["AQI"]
    assert results[2].korean_applicability == "UNKNOWN"  # no abstract → fallback


def test_errored_result_falls_back(two_article_catalog):
    """An error result for one article returns fallback, not a crash."""
    catalog = JFIACatalog.load(two_article_catalog)
    result_items = [_make_error_result_item("0")]
    client = _make_batch_client(result_items)

    results = enrich_catalog(catalog, client, batch=True, poll_interval=0)

    assert results[0].korean_applicability == "UNKNOWN"
    assert results[0].scheme_type is None


def test_batch_with_limit(sample_catalog_json):
    """limit applies before batch submission — only limited articles are processed."""
    catalog = JFIACatalog.load(sample_catalog_json)
    result_items = [_make_batch_result_item("0", VALID_TOOL_INPUT)]
    client = _make_batch_client(result_items)

    results = enrich_catalog(catalog, client, limit=1, batch=True, poll_interval=0)

    assert len(results) == 1
    create_call = client.messages.batches.create.call_args
    submitted = create_call.kwargs.get("requests") or create_call.args[0]
    assert len(submitted) == 1


def test_sequential_path_unchanged(two_article_catalog):
    """batch=False (default) still works via _enrich_one."""
    catalog = JFIACatalog.load(two_article_catalog)
    tool_block = MagicMock()
    tool_block.input = VALID_TOOL_INPUT
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[tool_block])

    results = enrich_catalog(catalog, client)

    assert len(results) == 2
    assert results[0].scheme_type == "earnings_manipulation"
    assert results[1].korean_applicability == "UNKNOWN"  # no abstract
    client.messages.batches.create.assert_not_called()
