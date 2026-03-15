"""
downloader.py — Download JFIA article PDFs.

Usage (one-liner after catalog is loaded):

    from jfia_forensic import JFIACatalog, download

    c = JFIACatalog.load(
        "data/raw/jfia_catalog.json",
        enriched_path="data/curated/jfia_enriched.json",
    )

    download(c.by_signal("Beneish M-Score"))
    download(c.by_scheme("earnings_manipulation"))
    download(c.search("Beneish", limit=20))

PDFs are saved to <project_root>/articles/ by default.
Pass output_dir to override.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .models import JFIAArticle

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "articles"


def _pdf_filename(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def download(
    articles: list[JFIAArticle],
    output_dir: Path | str | None = None,
    delay: float = 0.5,
) -> dict:
    """
    Preview found articles then download their PDFs.

    Prints a summary of what was found (count + titles + new/exists status),
    then fetches any files not already present in output_dir.

    Args:
        articles:   List of JFIAArticle objects — the result of any catalog query.
        output_dir: Destination directory. Defaults to <project_root>/articles/.
        delay:      Seconds to wait between requests (polite crawling). Default 0.5.

    Returns:
        {"downloaded": [filenames], "skipped": [filenames], "failed": [(filename, error)]}
    """
    output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Preview ---
    print(f"Found {len(articles)} article(s):", file=sys.stderr)
    for a in articles:
        dest = output_dir / _pdf_filename(a.pdf_url)
        status = "exists" if dest.exists() else "new"
        print(f"  [{status}]  {a.title}", file=sys.stderr)

    if not articles:
        return {"downloaded": [], "skipped": [], "failed": []}

    new_count = sum(
        1 for a in articles
        if not (output_dir / _pdf_filename(a.pdf_url)).exists()
    )
    print(
        f"\n{new_count} to download, "
        f"{len(articles) - new_count} already present. "
        f"Output: {output_dir}",
        file=sys.stderr,
    )
    if new_count == 0:
        return {"downloaded": [], "skipped": [_pdf_filename(a.pdf_url) for a in articles], "failed": []}

    print(file=sys.stderr)

    # --- Download ---
    downloaded: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for i, article in enumerate(articles):
        filename = _pdf_filename(article.pdf_url)
        dest = output_dir / filename

        if dest.exists():
            skipped.append(filename)
            continue

        try:
            urllib.request.urlretrieve(article.pdf_url, dest)
            size = dest.stat().st_size
            downloaded.append(filename)
            print(f"  ok    {filename}  ({size:,} bytes)", file=sys.stderr)
        except urllib.error.URLError as e:
            failed.append((filename, str(e)))
            print(f"  fail  {filename}  — {e}", file=sys.stderr)

        if delay and i < len(articles) - 1:
            time.sleep(delay)

    print(
        f"\nDone: {len(downloaded)} downloaded, "
        f"{len(skipped)} already present, "
        f"{len(failed)} failed.",
        file=sys.stderr,
    )
    return {"downloaded": downloaded, "skipped": skipped, "failed": failed}
