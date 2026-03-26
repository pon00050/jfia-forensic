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

ENRICHMENT_SYSTEM_PROMPT = """\
You are a forensic accounting classifier. Call the extract_article_metadata tool \
with structured classification results for the given article.

## Signals Vocabulary (CLOSED LIST — use ONLY these exact strings)
Beneish M-Score components: DSRI, AQI, GMI, DSI, SGAI, DEPI, LVGI, TATA
Forensic models: Beneish M-Score, Benford's Law, Altman Z-Score, F-Score, Jones Model,
  Modified Jones Model, Dechow-Dichev Model, Zmijewski X-Score
Accruals: abnormal accruals, discretionary accruals, real earnings management,
  earnings smoothing, big bath accounting
Transactions: channel stuffing, round-trip transactions, related-party transactions,
  insider trading, asset misappropriation, profit shifting, transfer price manipulation
Audit/reporting: audit quality, internal control weakness, fraudulent financial reporting,
  restatement risk, professional skepticism, whistleblowing, tone-at-the-top, backdating,
  going concern, management override, forensic audit, control environment, tests of controls
Fraud theory: fraud triangle, opportunity, rationalization, incentive
Governance: board composition, CEO duality, audit committee composition
Other: insider network, ratio analysis, stock option compensation

Use spaces not underscores — write "earnings smoothing", not "earnings_smoothing".

Do NOT use any of the following as signals — these are classification labels, not
indicators: earnings_manipulation, revenue_fabrication, asset_inflation,
liability_suppression, disclosure_fraud, insider_network, cb_bw_manipulation,
timing_anomaly, cost_distortion, related_party, earnings manipulation,
earnings management, disclosure fraud, Sarbanes-Oxley.

## korean_applicability Levels
Rate how applicable the paper's methods, findings, or fraud patterns are to Korean
forensic accounting practice. Korea does not need to be mentioned explicitly.

HIGH: methods or fraud patterns transfer directly to Korean forensic practice —
  e.g., earnings management detection models (M-Score, accruals), CB/BW schemes,
  Asian or code-law market dynamics, audit quality in concentrated ownership structures.
MEDIUM: general forensic methods with broad applicability including Korea — accruals
  models, fraud triangle, audit standards — but not particularly tailored to Korean
  market conditions or fraud typologies.
LOW: findings tied to jurisdiction-specific rules or case contexts that do not transfer
  well — e.g., US SOX mandates, EU GDPR, US GAAP-specific treatments, or case studies
  so institutionally bound that the methodology does not generalise.
UNKNOWN: no abstract available.

## Examples

Title: Detection of Earnings Management Using the Beneish M-Score in Japanese Markets
Abstract: Applies Beneish (1999) M-Score to Japanese listed companies. DSRI and TATA
are the strongest predictors of enforcement actions. Results robust across Asian markets.
→ scheme_type: "earnings_manipulation", signals: ["Beneish M-Score", "DSRI", "TATA"],
  fss_violation_category: "revenue_fabrication", korean_applicability: "HIGH"

Title: Convertible Bond Repricing and Stock Price Manipulation
Abstract: Examines whether CB repricing events are preceded by deliberate stock price
depression. Evidence of coordinated insider selling prior to repricing.
→ scheme_type: "cb_bw_manipulation", signals: ["insider trading"],
  fss_violation_category: "disclosure_fraud", korean_applicability: "HIGH"

Title: Discretionary Accruals and Big 4 Audit Quality: Evidence from OECD Countries
Abstract: Examines whether Big 4 auditors constrain discretionary accruals across 15
OECD countries. Results support a monitoring hypothesis globally.
→ scheme_type: "earnings_manipulation", signals: ["discretionary accruals", "audit quality"],
  fss_violation_category: "revenue_fabrication", korean_applicability: "MEDIUM"

Title: Sarbanes-Oxley Section 404 and Internal Control Reporting in US Firms
Abstract: Investigates SOX 404 internal control mandates among US accelerated filers.
Material weakness disclosures are associated with higher post-SOX restatement rates.
→ scheme_type: "disclosure_fraud", signals: ["internal control weakness", "restatement risk"],
  fss_violation_category: "disclosure_fraud", korean_applicability: "LOW"
"""

SIGNAL_SEED_VOCABULARY: frozenset[str] = frozenset({
    # Beneish M-Score components
    "DSRI", "AQI", "GMI", "SGI", "DSI", "SGAI", "DEPI", "LVGI", "TATA",
    # Forensic models
    "Beneish M-Score", "Benford's Law", "Altman Z-Score", "F-Score",
    "Jones Model", "Modified Jones Model", "Dechow-Dichev Model", "Zmijewski X-Score",
    # Accruals
    "abnormal accruals", "discretionary accruals", "real earnings management",
    "earnings smoothing", "big bath accounting",
    # Transactions
    "channel stuffing", "round-trip transactions", "related-party transactions",
    "insider trading", "asset misappropriation", "profit shifting",
    "transfer price manipulation",
    # Audit/reporting
    "audit quality", "internal control weakness", "fraudulent financial reporting",
    "restatement risk", "professional skepticism", "whistleblowing", "tone-at-the-top",
    "backdating", "going concern", "management override", "forensic audit",
    "control environment", "tests of controls",
    # Fraud theory
    "fraud triangle", "opportunity", "rationalization", "incentive",
    # Governance
    "board composition", "CEO duality", "audit committee composition",
    # Other
    "insider network", "ratio analysis", "stock option compensation",
    # Underscore variants the model generates
    "disclosure_fraud", "earnings_smoothing", "timing_anomaly",
})


def _expand_to_surface_forms(terms: list[str]) -> set[str]:
    result = set()
    for t in terms:
        result.add(t)
        result.add(t.replace("_", " "))
    return result


SIGNAL_FORBIDDEN_LABELS: frozenset[str] = frozenset(
    (
        _expand_to_surface_forms(SCHEME_TYPES)
        | _expand_to_surface_forms(FSS_VIOLATION_CATEGORIES)
        | {"earnings management", "Sarbanes-Oxley"}
    )
    - SIGNAL_SEED_VOCABULARY  # never forbid a term that is explicitly in the seed
)
