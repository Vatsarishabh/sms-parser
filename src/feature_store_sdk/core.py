"""
core.py
-------
Main entry point for the feature_store_sdk.

Takes classified SMS messages (output of classifier_sdk) and extracts
structured features per SMS — one dict per SMS with all parsed fields.

Flow:
    classified SMS → dispatcher routes by category → category parser → typed dataclass → .to_dict()
"""

from .models import SMSBase
from .parsers import (
    parse_transaction_model,
    parse_insurance_model,
    parse_investment_model,
    parse_promotion_model,
    parse_lending_model,
    parse_epfo_model,
    parse_utility_model,
    parse_order_model,
    parse_security_model,
    parse_otp_model,
)

# ---------------------------------------------------------------------------
# Category → parser dispatch map
# ---------------------------------------------------------------------------
_CATEGORY_PARSERS = {
    "transactions": parse_transaction_model,
    "insurance": parse_insurance_model,
    "investments": parse_investment_model,
    "promotions": parse_promotion_model,
    "lending": parse_lending_model,
    "epfo": parse_epfo_model,
    "utility_bills": parse_utility_model,
    "orders": parse_order_model,
    "security_alert": parse_security_model,
    "otp": parse_otp_model,
}


def extract_features(classified_messages: list[dict]) -> list[dict]:
    """
    Extract structured features from classified SMS messages.

    Input: list of dicts from classifier_sdk (must have: body, address, category, timestamp,
           entity_name, header_code, traffic_type, occurrence_tag, alphabetical_tag, tag_count)
    Output: list of dicts — one per SMS with all extracted fields from the appropriate dataclass model.
    """
    results = []

    for msg in classified_messages:
        body = msg.get("body", "")
        address = msg.get("address", "")
        category = msg.get("category", "Other")

        # Build base_fields from classifier output
        base_fields = {
            "entity_name": msg.get("entity_name", "unknown"),
            "header_code": msg.get("header_code"),
            "traffic_type": msg.get("traffic_type", "general"),
            "sms_category": category,
            "occurrence_tag": msg.get("occurrence_tag", ""),
            "alphabetical_tag": msg.get("alphabetical_tag", ""),
            "tag_count": msg.get("tag_count", 0),
            "timestamp": msg.get("timestamp"),
        }

        # Dispatch to category-specific parser
        parser_fn = _CATEGORY_PARSERS.get(category)
        if parser_fn:
            model = parser_fn(body, address, base_fields)
        else:
            # Fallback: return SMSBase for unknown categories
            model = SMSBase(raw_body=body, sender_address=address, **base_fields)

        results.append(model.to_dict())

    return results
