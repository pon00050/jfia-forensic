"""Tests for downloader module and JFIACatalog.by_signal()."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from jfia_forensic.catalog import JFIACatalog
from jfia_forensic.downloader import download, _pdf_filename
from jfia_forensic.models import JFIAArticle


# --- Helpers ---

def _make_article(index: int = 1, title: str = "Test Article") -> JFIAArticle:
    return JFIAArticle(
        index=index,
        title=title,
        authors=["Author A"],
        abstract="Abstract text.",
        keywords=[],
        pdf_url=f"https://s3.amazonaws.com/example.com/JFIA-2020-1_{index}.pdf",
    )


# --- _pdf_filename ---

def test_pdf_filename_extracts_from_url():
    url = "https://s3.amazonaws.com/web.nacva.com/JFIA/Issues/JFIA-2009-1_4.pdf"
    assert _pdf_filename(url) == "JFIA-2009-1_4.pdf"


def test_pdf_filename_appends_extension_if_missing():
    url = "https://example.com/somefile"
    assert _pdf_filename(url).endswith(".pdf")


# --- download() ---

def test_download_empty_list_returns_empty_dict(tmp_path):
    result = download([], output_dir=tmp_path)
    assert result == {"downloaded": [], "skipped": [], "failed": []}


def test_download_creates_output_dir(tmp_path):
    dest = tmp_path / "nested" / "dir"
    with patch("urllib.request.urlretrieve", side_effect=lambda u, d: Path(d).write_bytes(b"")):
        download([_make_article()], output_dir=dest, delay=0)
    assert dest.exists()


def test_download_fetches_new_file(tmp_path):
    article = _make_article()
    filename = _pdf_filename(article.pdf_url)

    def fake_retrieve(url, dest):
        Path(dest).write_bytes(b"%PDF fake content")

    with patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
        result = download([article], output_dir=tmp_path, delay=0)

    assert filename in result["downloaded"]
    assert result["skipped"] == []
    assert result["failed"] == []
    assert (tmp_path / filename).exists()


def test_download_skips_existing_file(tmp_path):
    article = _make_article()
    filename = _pdf_filename(article.pdf_url)
    (tmp_path / filename).write_bytes(b"%PDF already here")

    with patch("urllib.request.urlretrieve") as mock_retrieve:
        result = download([article], output_dir=tmp_path, delay=0)

    mock_retrieve.assert_not_called()
    assert filename in result["skipped"]
    assert result["downloaded"] == []


def test_download_handles_url_error(tmp_path):
    import urllib.error
    article = _make_article()

    with patch(
        "urllib.request.urlretrieve",
        side_effect=urllib.error.URLError("404 Not Found"),
    ):
        result = download([article], output_dir=tmp_path, delay=0)

    assert result["downloaded"] == []
    assert len(result["failed"]) == 1
    assert result["failed"][0][0] == _pdf_filename(article.pdf_url)


def test_download_returns_correct_summary(tmp_path):
    articles = [_make_article(i) for i in range(3)]
    # Pre-create file for article 0 — should be skipped
    (tmp_path / _pdf_filename(articles[0].pdf_url)).write_bytes(b"%PDF")

    def fake_retrieve(url, dest):
        if "2" in str(dest):
            raise __import__("urllib.error", fromlist=["URLError"]).URLError("fail")
        Path(dest).write_bytes(b"%PDF")

    import urllib.error

    def selective_retrieve(url, dest):
        if _pdf_filename(url) == _pdf_filename(articles[2].pdf_url):
            raise urllib.error.URLError("fail")
        Path(dest).write_bytes(b"%PDF")

    with patch("urllib.request.urlretrieve", side_effect=selective_retrieve):
        result = download(articles, output_dir=tmp_path, delay=0)

    assert len(result["skipped"]) == 1
    assert len(result["downloaded"]) == 1
    assert len(result["failed"]) == 1


def test_download_respects_delay(tmp_path):
    articles = [_make_article(i) for i in range(2)]

    with patch("urllib.request.urlretrieve", side_effect=lambda u, d: Path(d).write_bytes(b"")):
        with patch("time.sleep") as mock_sleep:
            download(articles, output_dir=tmp_path, delay=1.0)

    mock_sleep.assert_called_once_with(1.0)


def test_download_no_delay_between_last_items(tmp_path):
    """No sleep after the final article."""
    articles = [_make_article(1)]

    with patch("urllib.request.urlretrieve", side_effect=lambda u, d: Path(d).write_bytes(b"")):
        with patch("time.sleep") as mock_sleep:
            download(articles, output_dir=tmp_path, delay=1.0)

    mock_sleep.assert_not_called()


# --- JFIACatalog.by_signal() ---

@pytest.fixture
def enriched_catalog(tmp_path) -> Path:
    catalog_data = {
        "scraped_at": "2025-01-01",
        "total_articles": 3,
        "issues": [{
            "volume": 1, "issue": 1, "period": "2009", "contentid": "x",
            "url": "https://example.com", "is_special_issue": False,
            "articles": [
                {"index": 1, "title": "Beneish Study", "authors": [], "abstract": "text",
                 "keywords": [], "pdf_url": "https://example.com/1.pdf"},
                {"index": 2, "title": "CB Fraud Patterns", "authors": [], "abstract": "text",
                 "keywords": [], "pdf_url": "https://example.com/2.pdf"},
                {"index": 3, "title": "No Abstract", "authors": [], "abstract": "",
                 "keywords": [], "pdf_url": "https://example.com/3.pdf"},
            ],
        }],
    }
    enriched_data = [
        {"article": {"index": 1, "title": "Beneish Study", "authors": [], "abstract": "text",
                     "keywords": [], "pdf_url": "https://example.com/1.pdf", "volume": 1,
                     "issue": 1, "period": "2009"},
         "scheme_type": "earnings_manipulation", "signals": ["Beneish M-Score", "DSRI"],
         "data_fields": [], "korean_applicability": "HIGH", "fss_violation_category": "revenue_fabrication"},
        {"article": {"index": 2, "title": "CB Fraud Patterns", "authors": [], "abstract": "text",
                     "keywords": [], "pdf_url": "https://example.com/2.pdf", "volume": 1,
                     "issue": 1, "period": "2009"},
         "scheme_type": "cb_bw_manipulation", "signals": ["insider trading"],
         "data_fields": [], "korean_applicability": "HIGH", "fss_violation_category": "disclosure_fraud"},
        {"article": {"index": 3, "title": "No Abstract", "authors": [], "abstract": "",
                     "keywords": [], "pdf_url": "https://example.com/3.pdf", "volume": 1,
                     "issue": 1, "period": "2009"},
         "scheme_type": None, "signals": [],
         "data_fields": [], "korean_applicability": "UNKNOWN", "fss_violation_category": None},
    ]
    cat_path = tmp_path / "catalog.json"
    enr_path = tmp_path / "enriched.json"
    cat_path.write_text(json.dumps(catalog_data), encoding="utf-8")
    enr_path.write_text(json.dumps(enriched_data), encoding="utf-8")
    return cat_path, enr_path


def test_by_signal_returns_matching_articles(enriched_catalog):
    cat_path, enr_path = enriched_catalog
    catalog = JFIACatalog.load(cat_path, enriched_path=enr_path)
    results = catalog.by_signal("Beneish M-Score")
    assert len(results) == 1
    assert results[0].title == "Beneish Study"


def test_by_signal_no_match_returns_empty(enriched_catalog):
    cat_path, enr_path = enriched_catalog
    catalog = JFIACatalog.load(cat_path, enriched_path=enr_path)
    assert catalog.by_signal("Zmijewski X-Score") == []


def test_by_signal_without_enriched_returns_empty(enriched_catalog):
    cat_path, _ = enriched_catalog
    catalog = JFIACatalog.load(cat_path)  # no enriched_path
    assert catalog.by_signal("Beneish M-Score") == []


def test_by_signal_multiple_matches(enriched_catalog):
    cat_path, enr_path = enriched_catalog
    catalog = JFIACatalog.load(cat_path, enriched_path=enr_path)
    # DSRI appears in article 1
    results = catalog.by_signal("DSRI")
    assert len(results) == 1
    assert results[0].title == "Beneish Study"
