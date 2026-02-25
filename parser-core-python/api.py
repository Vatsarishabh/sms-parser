from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import importlib.util
from decimal import Decimal
import uvicorn

# ── Bootstrap ─────────────────────────────────────────────────────────────────
# The folder is named "parser-core-python" (hyphen → invalid Python identifier).
# We load it manually via importlib and register it in sys.modules under the
# alias "parser_core_python" so that all internal relative imports work.
_THIS_DIR   = os.path.dirname(os.path.realpath(__file__))   # …/parser-core-python
_PKG_ALIAS  = "parser_core_python"

if _PKG_ALIAS not in sys.modules:
    # Register the top-level package
    spec = importlib.util.spec_from_file_location(
        _PKG_ALIAS,
        os.path.join(_THIS_DIR, "__init__.py"),
        submodule_search_locations=[_THIS_DIR],
    )
    pkg = importlib.util.module_from_spec(spec)
    pkg.__path__ = [_THIS_DIR]
    pkg.__package__ = _PKG_ALIAS
    sys.modules[_PKG_ALIAS] = pkg
    spec.loader.exec_module(pkg)

from parser_core_python.bank.bank_parser_factory import BankParserFactory
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SMS Parser API",
    description="API for parsing banking SMS messages into structured transaction data.",
    version="1.0.0"
)

class SMSRequest(BaseModel):
    _id: Optional[int] = None
    date: int
    address: str
    body: str
    type: Optional[str] = None

class ParseResponse(BaseModel):
    _id: Optional[int] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    merchant: Optional[str] = None
    reference: Optional[str] = None
    account_last4: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    bank_name: Optional[str] = None
    is_from_card: bool = False
    currency: str = "INR"
    from_account: Optional[str] = None
    to_account: Optional[str] = None
    transaction_id: Optional[str] = None
    status: str = "parsed"

def format_parsed_txn(parsed_txn):
    if not parsed_txn:
        return None
    
    return {
        "amount": float(parsed_txn.amount) if parsed_txn.amount is not None else None,
        "type": parsed_txn.type.value if hasattr(parsed_txn.type, 'value') else str(parsed_txn.type),
        "merchant": parsed_txn.merchant,
        "reference": parsed_txn.reference,
        "account_last4": parsed_txn.account_last4,
        "balance": float(parsed_txn.balance) if parsed_txn.balance is not None else None,
        "credit_limit": float(parsed_txn.credit_limit) if parsed_txn.credit_limit is not None else None,
        "bank_name": parsed_txn.bank_name,
        "is_from_card": parsed_txn.is_from_card,
        "currency": parsed_txn.currency,
        "from_account": parsed_txn.from_account,
        "to_account": parsed_txn.to_account,
        "transaction_id": parsed_txn.generate_transaction_id()
    }

@app.post("/parse", response_model=ParseResponse)
async def parse_sms(request: SMSRequest):
    """
    Parse a single SMS message with the custom JSON format.
    """
    parser = BankParserFactory.get_parser(request.address)
    if not parser:
        raise HTTPException(status_code=404, detail=f"No parser found for sender: {request.address}")
    
    parsed_txn = parser.parse(request.body, request.address, request.date)
    if not parsed_txn:
        raise HTTPException(status_code=422, detail="Could not extract transaction data from the SMS body.")
    
    result = format_parsed_txn(parsed_txn)
    result["_id"] = request._id
    result["status"] = "success"
    return result

@app.post("/parse-batch", response_model=List[dict])
async def parse_sms_batch(requests: List[SMSRequest]):
    """
    Parse multiple SMS messages in one request using the custom JSON format.
    """
    results = []
    for request in requests:
        parser = BankParserFactory.get_parser(request.address)
        if not parser:
            results.append({
                "_id": request._id,
                "status": "error", 
                "message": f"No parser found for sender: {request.address}"
            })
            continue
            
        parsed_txn = parser.parse(request.body, request.address, request.date)
        if not parsed_txn:
            results.append({
                "_id": request._id,
                "status": "unparsed", 
                "message": "Could not extract transaction data."
            })
            continue
            
        formatted = format_parsed_txn(parsed_txn)
        formatted["_id"] = request._id
        formatted["status"] = "success"
        results.append(formatted)
        
    return results

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
