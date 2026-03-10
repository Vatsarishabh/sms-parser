"""
core.py
-------
Main entry point for the classifier SDK (Layer 1).

Takes raw SMS messages and returns classified messages with category,
confidence, tags, and sender metadata.
"""

import re

from .classifier import get_classifier, SMSClassifier, ClassificationResult
from .tagger import decode_sender_meta
from .promotion import is_offer_or_marketing

_SNAKE_SEP_RE = re.compile(r'[/\-\s]+')
_SNAKE_CAMEL_RE = re.compile(r'([a-z0-9])([A-Z])')


def _to_snake(value: str) -> str:
    """Convert a space/hyphen-delimited string to snake_case."""
    s = value.strip()
    s = _SNAKE_SEP_RE.sub('_', s)
    s = _SNAKE_CAMEL_RE.sub(r'\1_\2', s)
    return s.lower()


# ---------------------------------------------------------------------------
# Module-level classifier instance (swappable via set_classifier)
# ---------------------------------------------------------------------------
_classifier: SMSClassifier = get_classifier("rules")


def set_classifier(strategy: str = "rules", **kwargs) -> None:
    """Swap the classifier strategy at runtime.

    Parameters
    ----------
    strategy : "rules" | "fasttext" | "ensemble"
    kwargs   : model_path (for fasttext), confidence_threshold (for ensemble)
    """
    global _classifier
    _classifier = get_classifier(strategy, **kwargs)


def classify_sms(messages: list[dict]) -> list[dict]:
    """Classify a list of raw SMS messages.

    Parameters
    ----------
    messages : list of dicts, each with keys ``body``, ``address``, ``timestamp``
               (``address`` and ``timestamp`` are optional).

    Returns
    -------
    list of dicts — each input dict augmented with classification and sender
    metadata fields:
        category, confidence, occurrence_tag, alphabetical_tag, tag_count,
        unique_tags (list), entity_name, header_code, traffic_type,
        sender_category_hint
    """
    results: list[dict] = []

    for msg in messages:
        body = msg.get("body", "")
        address = msg.get("address", "")
        timestamp = msg.get("timestamp", None)

        # --- Classification ---
        clf_result: ClassificationResult = _classifier.classify(body, address)

        # --- Sender metadata ---
        meta = decode_sender_meta(address)

        # --- Promotion override ---
        # If traffic type is PROMOTIONAL or content looks like marketing,
        # override category to "Promotions"
        category = clf_result.category
        if meta["traffic_type"] == "PROMOTIONAL" or is_offer_or_marketing(body):
            category = "Promotions"  # will be snake_cased in output

        # --- Build output dict (strip None-valued keys, snake_case enums) ---
        out = {
            "body": body,
            "address": address,
            "timestamp": timestamp,
            "category": _to_snake(category),
            "confidence": clf_result.confidence,
            "occurrence_tag": clf_result.occurrence_tag,
            "alphabetical_tag": clf_result.alphabetical_tag,
            "tag_count": clf_result.tag_count,
            "unique_tags": sorted(clf_result.unique_tags),  # frozenset → sorted list
            "entity_name": meta["entity_name"],
            "header_code": meta["header_code"],
            "traffic_type": _to_snake(meta["traffic_type"]),
            "sender_category_hint": _to_snake(meta["sender_category_hint"]) if meta["sender_category_hint"] else None,
        }
        results.append({k: v for k, v in out.items() if v is not None})

    return results


# Alias
classify_sms_batch = classify_sms
