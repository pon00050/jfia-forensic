"""
Shared constants for jfia-forensic.
No magic strings in pipeline or analysis code — import from here.
"""

SCHEME_TYPES = [
    "earnings_manipulation",
    "revenue_fabrication",
    "asset_inflation",
    "liability_suppression",
    "disclosure_fraud",
    "insider_network",
    "cb_bw_manipulation",
    "timing_anomaly",
]

FSS_VIOLATION_CATEGORIES = [
    "revenue_fabrication",
    "cost_distortion",
    "asset_inflation",
    "liability_suppression",
    "related_party",
    "disclosure_fraud",
]

KOREAN_APPLICABILITY_VALUES = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]

# Model routing — never use opus in this project
HAIKU_MODEL = "claude-haiku-4-5-20251001"

ENRICHMENT_SYSTEM_PROMPT = """You are a forensic accounting classifier. Given a journal article abstract, \
extract structured information. Respond ONLY with valid JSON matching this schema:
{"scheme_type": string_or_null, "signals": [string], "data_fields": [string], \
"korean_applicability": "HIGH"|"MEDIUM"|"LOW"|"UNKNOWN", "fss_violation_category": string_or_null}
No explanation. Only JSON."""
