# Architecture

## Pipeline

```
                    POST /classify        POST /features         POST /insights
                         |                     |                      |
                         v                     v                      v
  raw SMS ──> [ classifier_sdk ] ──> [ feature_store_sdk ] ──> [ insights_sdk ]
                  Layer 1                  Layer 2                  Layer 3
              category + tags       1 dict per SMS with       aggregated domain
              sender metadata       all parsed fields         insights + meta
```

Each layer is an independent SDK package under `src/`. The API (`api.py`) is a thin orchestrator that chains them. Each endpoint returns a self-contained response — no post-formatting.

---

## Layer 1 — `src/classifier_sdk/`

Classifies raw SMS into one of 10 categories.

```
SMS body + sender address
  -> Aho-Corasick keyword scan (tagger.py)
  -> priority-scored category assignment (classifier.py)
  -> promotional override if sender is -P traffic or content matches marketing patterns
  -> output: category, confidence, tags, sender metadata
```

**Classifier is swappable at runtime:**

```python
from src.classifier_sdk import set_classifier
set_classifier("rules")                                # default — Aho-Corasick + scoring
set_classifier("fasttext", model_path="model.bin")     # ML-based (stub)
set_classifier("ensemble", confidence_threshold=0.7)   # ML + rules fallback (stub)
```

All strategies implement `SMSClassifier` ABC and return `ClassificationResult`.

**Sender identification** uses `data/sender_map.json` (23K+ TRAI header codes). Address format: `XX-YYYY-Z` where Z = T(ransactional) / P(romotional) / S(ervice) / G(overnment).

**Categories:** `transactions`, `insurance`, `lending`, `investments`, `epfo`, `utility_bills`, `promotions`, `orders`, `security_alert`, `otp`

---

## Layer 2 — `src/feature_store_sdk/`

Extracts structured features from each classified SMS.

```
classified SMS
  -> dispatch by category to specific parser
  -> parser returns typed dataclass (TransactionParsed, InsuranceParsed, etc.)
  -> .to_dict() strips null keys + standardizes enum values to snake_case
```

**10 dataclass models** inherit from `SMSBase`. Each category has a dedicated parser in `parsers/`.

**Transaction parser** extracts: txn_type, amount, balance, account/card number, channel (upi/neft/imps/card), payee, reference, mandate flags, salary detection, credit card limits.

---

## Layer 3 — `src/insights_sdk/`

Consumes the feature store and produces aggregated domain insights.

| Module | Input Filter | Output |
|--------|-------------|--------|
| `banking.py` | `sms_category == "transactions"` | accounts, cash flow, channel breakdown |
| `investment.py` | `sms_category == "investments"` | portfolio, activity, velocity, reliability |
| `insurance.py` | `sms_category == "insurance"` | coverage, household, engagement |
| `shopping.py` | all SMS (scans for merchant names) | monthly burn, merchant behavior, impulse index |
| `lending.py` | `sms_category == "lending"` | delinquency, approvals, per-account details |
| `promotional.py` | `sms_category == "promotions"` | breakdown, limit offers |
| `persona.py` | requires shopping + insurance + investment | cross-domain persona segment + scores |

Each module returns `None` when no relevant data exists. The meta block tracks which modules produced output and which were skipped:

```json
{
  "domains_analyzed": ["banking", "investment", "shopping"],
  "domains_skipped": [
    {"module": "insurance", "reason": "no_data"},
    {"module": "lending", "reason": "no_data"},
    {"module": "unified_persona", "reason": "no_data"}
  ]
}
```

---

## API — `api.py`

```
POST /classify   -> L1
POST /features   -> L1 -> L2
POST /insights   -> L1 -> L2 -> L3
POST /analyze    -> alias for /insights
GET  /health
```

Request body: `{"sms_data": [{"body": "...", "address": "...", "timestamp": "..."}]}`

---

## Output Contract

**Null handling:** Keys with `None` values are stripped at each layer — L1 via dict comprehension, L2 via `_clean_dict()` in `to_dict()`, L3 via `sanitize()`.

**Value format:** All enum-like fields use `snake_case` (`bank_account`, `upi_transfer`, `credit_card_transaction`). Free-text values (bank names, payee names, fund names) are preserved as-is.

**Standardized fields:** `sms_category`, `traffic_type`, `txn_type`, `txn_subtype`, `financial_product`, `txn_channel`, `context`, `event_type`, `insurance_type`, `asset_type`, `bill_type`, `promo_type`, `offered_product`, `alert_type`, `action_taken`, `otp_for`

---

## Other Components

**`src/bank_parsers/`** — 90+ bank-specific parsers with base class hierarchy, extracted from pwai branch.

**`app.py`** — Streamlit dashboard. Calls `/analyze` via HTTP (falls back to direct function call). Theme config in `.streamlit/config.toml`.

**Dependencies:** `fastapi`, `uvicorn`, `pandas`, `numpy`, `pyahocorasick`, `streamlit`, `plotly`, `requests` (pinned in `requirements.txt`).
