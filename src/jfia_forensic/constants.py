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
HAIKU_MODEL = "claude-haiku-4-5"

ENRICHMENT_SYSTEM_PROMPT = """\
You are a forensic accounting classifier. Call the extract_article_metadata tool \
with structured classification results for the given article.

## Signals Seed Vocabulary
Prefer these terms where applicable (exact spelling):
Beneish ratios: DSRI, AQI, GMI, DSI, SGAI, DEPI, LVGI, TATA
Common forensic terms: abnormal accruals, discretionary accruals, restatement risk,
audit quality, related-party transactions, insider trading, earnings smoothing,
big bath accounting, channel stuffing, round-trip transactions

Only add a new signal term if no seed term fits.

## Examples

Title: Detection of Earnings Management Using the Beneish M-Score
Abstract: Applies Beneish (1999) M-Score to Korean listed companies. DSRI and TATA
are the strongest predictors of SEC enforcement actions.
→ scheme_type: "earnings_manipulation", signals: ["DSRI", "TATA"],
  fss_violation_category: "revenue_fabrication", korean_applicability: "HIGH"

Title: Convertible Bond Repricing and Stock Price Manipulation
Abstract: Examines whether CB repricing events are preceded by deliberate stock price
depression. Evidence of coordinated insider selling prior to repricing.
→ scheme_type: "cb_bw_manipulation", signals: ["insider trading"],
  fss_violation_category: "disclosure_fraud", korean_applicability: "HIGH"
"""
