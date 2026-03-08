"""
api.py
------
Thin FastAPI orchestrator for the 3-layer SMS parsing SDK.

Endpoints:
    POST /classify   → Layer 1: classify raw SMS
    POST /features   → Layer 1 + 2: classify → extract features
    POST /insights   → Layer 1 + 2 + 3: classify → features → insights
    POST /analyze    → Alias for /insights (backward compat)
    GET  /health     → Health check
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from src.classifier_sdk import classify_sms
from src.feature_store_sdk import extract_features
from src.insights_sdk import generate_insights

app = FastAPI(title="SMS Financial Parser API")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class SMSRequest(BaseModel):
    sms_data: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/classify")
def classify(request: SMSRequest):
    """Layer 1: Classify raw SMS messages."""
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")
    try:
        return classify_sms(request.sms_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/features")
def features(request: SMSRequest):
    """Layer 1 + 2: Classify → Extract features."""
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")
    try:
        classified = classify_sms(request.sms_data)
        return extract_features(classified)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insights")
def insights(request: SMSRequest):
    """Layer 1 + 2 + 3: Classify → Features → Insights."""
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")
    try:
        classified = classify_sms(request.sms_data)
        feature_store = extract_features(classified)
        return generate_insights(feature_store)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
def analyze(request: SMSRequest):
    """Full pipeline (alias for /insights)."""
    return insights(request)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=5004, reload=True)
