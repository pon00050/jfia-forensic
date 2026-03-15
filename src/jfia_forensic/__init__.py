"""
jfia-forensic — Forensic accounting detectlet schema and JFIA literature catalog tools.

Public API:
    from jfia_forensic import Detectlet, DetectletRegistry, JFIACatalog
"""

from .models import (
    Detectlet,
    DetectletMatch,
    EnrichedArticle,
    JFIAArticle,
    JFIACitation,
    Signal,
)
from .registry import DetectletRegistry
from .catalog import JFIACatalog
from .downloader import download

__all__ = [
    "Detectlet",
    "DetectletMatch",
    "DetectletRegistry",
    "EnrichedArticle",
    "JFIAArticle",
    "JFIACatalog",
    "JFIACitation",
    "Signal",
    "download",
]
