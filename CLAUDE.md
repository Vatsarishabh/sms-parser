# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SMS financial parser that classifies Indian SMS messages (banking, insurance, investments, lending, EPFO, shopping, etc.) into structured data models and generates domain-specific financial insights + a unified psychographic persona.

## Commands

```bash
# Activate venv (Python 3.14)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Also requires: pip install pyahocorasick plotly

# Run FastAPI server
python api.py                        # serves on port 5004

# Run Streamlit dashboard
streamlit run app.py                 # connects to API on localhost:5004, falls back to native

# Run uvicorn directly
uvicorn api:app --host 0.0.0.0 --port 5004 --reload
```

No test suite exists yet. No linter/formatter is configured.

## Architecture

### 3-Layer Pipeline

```
raw SMS → classifier (strategy pattern) → parser (dispatch) → typed dataclass → domain insights
```

**Full flow in `api.py:run_pipeline()`:**
1. `promotion.analyze_promotions()` — separates promos (sender `-P` suffix + hidden promos)
2. `tagger.process_sms_df()` — Aho-Corasick keyword tagging on remaining SMS
3. `parser.parse_sms()` — classifies + dispatches each SMS to category-specific parser → returns typed dataclass
4. Domain insight generators consume `list[dict]` (from `.to_dict()`) grouped by category
5. `format_response()` reshapes raw insights into the final API response shape

### Classification (Strategy Pattern — Dependency Inversion)

`src/classifier.py` defines `SMSClassifier` ABC with three implementations:
- **RuleBasedClassifier** — Aho-Corasick + priority scoring + TRAI sender hint bonus (currently active)
- **FastTextClassifier** — stub, needs trained `.bin` model + 5K+ labeled SMS
- **EnsembleClassifier** — ML above confidence threshold, else rules fallback

`parser.py` depends only on the `SMSClassifier` abstraction. Switch at runtime:
```python
from src.parser import set_classifier
set_classifier("fasttext", model_path="model.bin")
```

### Data Models (`src/models.py`)

10 dataclasses inheriting `SMSBase`, all expose `.to_dict()`. The `CATEGORY_MODEL_MAP` dict maps category string → dataclass type. Categories: Transactions, Lending, Insurance, Investments, EPFO, Utility Bills, Promotions, Orders, Security Alert, OTP.

### Sender Identification

`src/data/sender_map.json` — 23K+ TRAI header-code → entity-name mappings. Sender address format: `XX-YYYY-Z` (Z = T/P/S/G traffic type) or `XX-YYYY`. `identify_sender()` + `decode_sender_meta()` in `tagger.py` handle lookup. `infer_sender_category()` derives category hints from entity name keywords.

### Entry Points

- **`api.py`** — FastAPI with `POST /analyze` (accepts `{sms_data: list[dict]}`) and `GET /health`. Contains `run_pipeline()` orchestration + all response formatters (`fmt_banking`, `fmt_investment`, etc.)
- **`app.py`** — Streamlit dashboard. Tries API at localhost:5004 first, falls back to calling `analyze()` natively. Plotly charts.

## Key Conventions

- Follow SOLID principles strictly — especially Dependency Inversion (classifiers) and Single Responsibility
- Insight generators accept `list[dict]` (model `.to_dict()` output), not raw DataFrames
- `banking_summary.py` is the exception: expects DataFrame with "Transaction Type", "Amount" column names from `analyze_transactions()`
- All date/timestamp parsing goes through `src/utils.parse_timestamp()` — handles epoch ms/ns/s and string formats
- Pandas is used only where it adds genuine value (groupby/aggregation): `banking_summary.py`, `shopping.py`, `investment.py`, `insurance.py`, `promotion.py`, `transaction.py`, `tagger.py`. Removed from `loan.py` and `persona.py` (plain Python suffices)
- `api.py` `sanitize()` recursively converts NaN/Inf/Timestamps/numpy scalars to JSON-safe types before response