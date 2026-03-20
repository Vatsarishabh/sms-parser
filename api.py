from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from src.classifier_sdk import classify_sms, set_classifier
from src.feature_store_sdk import extract_features
from src.insights_sdk import generate_insights

app = FastAPI(title="SMS Financial Parser API")

# "rules" | "sklearn" | "ensemble"
set_classifier("sklearn")


class SMSRequest(BaseModel):
    sms_data: List[Dict[str, Any]]


@app.post("/classify")
def classify(request: SMSRequest):
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")
    try:
        return classify_sms(request.sms_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/features")
def features(request: SMSRequest):
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")
    try:
        classified = classify_sms(request.sms_data)
        return extract_features(classified)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insights")
def insights(request: SMSRequest):
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
    return insights(request)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=5004, reload=True)