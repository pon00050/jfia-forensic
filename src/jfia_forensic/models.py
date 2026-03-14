"""
Pydantic models for jfia-forensic.
Models document dict-returning function contracts; not enforced at runtime.
Uses Python 3.11+ union syntax.
"""

from pydantic import BaseModel, field_validator

from .constants import (
    SCHEME_TYPES,
    FSS_VIOLATION_CATEGORIES,
    KOREAN_APPLICABILITY_VALUES,
)


class Signal(BaseModel):
    name: str
    description: str
    threshold: float | None = None
    direction: str | None = None  # "above" | "below" | "nonzero"


class JFIACitation(BaseModel):
    volume: int
    issue: int
    index: int
    title: str
    authors: list[str]
    pdf_url: str


class Detectlet(BaseModel):
    name: str
    version: str
    scheme: str
    fss_violation_categories: list[str]
    jfia_citations: list[JFIACitation]
    signals: list[Signal]
    required_fields: list[str]
    threshold: float | None = None
    korean_threshold: float | None = None
    output_fields: list[str]
    interpretation: str

    @field_validator("scheme")
    @classmethod
    def scheme_must_be_valid(cls, v: str) -> str:
        if v not in SCHEME_TYPES:
            raise ValueError(
                f"scheme '{v}' not in SCHEME_TYPES: {SCHEME_TYPES}"
            )
        return v


class JFIAArticle(BaseModel):
    index: int
    title: str
    authors: list[str]
    abstract: str = ""
    keywords: list[str] = []
    pdf_url: str
    # Issue-level fields, populated when loading from catalog
    volume: int | None = None
    issue: int | None = None
    period: str | None = None


class EnrichedArticle(BaseModel):
    article: JFIAArticle
    scheme_type: str | None = None
    signals: list[str] = []
    data_fields: list[str] = []
    korean_applicability: str = "UNKNOWN"
    fss_violation_category: str | None = None

    @field_validator("scheme_type", mode="before")
    @classmethod
    def coerce_scheme_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SCHEME_TYPES:
            return None
        return v

    @field_validator("fss_violation_category", mode="before")
    @classmethod
    def coerce_fss_category(cls, v: str | None) -> str | None:
        if v is not None and v not in FSS_VIOLATION_CATEGORIES:
            return None
        return v

    @field_validator("korean_applicability")
    @classmethod
    def applicability_must_be_valid(cls, v: str) -> str:
        if v not in KOREAN_APPLICABILITY_VALUES:
            raise ValueError(
                f"korean_applicability '{v}' not in {KOREAN_APPLICABILITY_VALUES}"
            )
        return v


class DetectletMatch(BaseModel):
    detectlet: Detectlet
    matching_articles: list[JFIAArticle]
    relevance_score: float
