import re

from .classifier import get_classifier, SMSClassifier, ClassificationResult
from .tagger import decode_sender_meta
from .promotion import is_offer_or_marketing

_SNAKE_SEP_RE = re.compile(r'[/\-\s]+')
_SNAKE_CAMEL_RE = re.compile(r'([a-z0-9])([A-Z])')


def _to_snake(value: str) -> str:
    s = value.strip()
    s = _SNAKE_SEP_RE.sub('_', s)
    s = _SNAKE_CAMEL_RE.sub(r'\1_\2', s)
    return s.lower()


_classifier: SMSClassifier = get_classifier("rules")


def set_classifier(strategy: str = "rules", **kwargs) -> None:
    global _classifier
    _classifier = get_classifier(strategy, **kwargs)


def classify_sms(messages: list[dict]) -> list[dict]:
    results: list[dict] = []

    for msg in messages:
        body = msg.get("body", "")
        address = msg.get("address", "")
        timestamp = msg.get("timestamp", None)

        clf_result: ClassificationResult = _classifier.classify(body, address)
        meta = decode_sender_meta(address)

        # Override to promotions only if ML didn't already catch it
        category = clf_result.category
        is_promo = meta["traffic_type"] == "PROMOTIONAL" or is_offer_or_marketing(body)
        if is_promo and "promotions" not in category.lower():
            category = "Promotions"

        out = {
            "body": body,
            "address": address,
            "timestamp": timestamp,
            "category": _to_snake(category),
            "confidence": clf_result.confidence,
            "occurrence_tag": clf_result.occurrence_tag,
            "alphabetical_tag": clf_result.alphabetical_tag,
            "tag_count": clf_result.tag_count,
            "unique_tags": sorted(clf_result.unique_tags),
            "entity_name": meta["entity_name"],
            "header_code": meta["header_code"],
            "traffic_type": _to_snake(meta["traffic_type"]),
            "sender_category_hint": _to_snake(meta["sender_category_hint"]) if meta["sender_category_hint"] else None,
        }
        results.append({k: v for k, v in out.items() if v is not None})

    return results


classify_sms_batch = classify_sms