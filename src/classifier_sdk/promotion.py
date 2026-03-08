import re

# -----------------------------
# Offer/Marketing guard
# -----------------------------
_OFFER_PATTERNS = [
    r"\bpre[-\s]?qualified\b",
    r"\bpre[-\s]?approved\b",
    r"\bapproved\s+for\b",
    r"\byou('?re| are)\s+eligible\b",
    r"\bapply\s+now\b",
    r"\binstant\s+approval\b",
    r"\bclick\s+(now|here)\b",
    r"\boffer\b",
    r"\boffer\s+valid\b",
    r"\bvalid\s+till\b",
    r"\bzero\s+joining\s+fee\b",
    r"\bjoining\s+fee\b",
    r"\bannual\s+fee\b",
    r"\bannual\s+cashback\b",
    r"\bcashback\b",
    r"\bcredit\s+limit\b",
    r"\blimit\s+of\s+up\s+to\b",
    r"\bcard\b.*\b(offer|eligible|pre[-\s]?approved|pre[-\s]?qualified|apply)\b",
]

# If these appear, it becomes *very likely* it's NOT a transaction
_NON_TXN_STRONG_CTA = [
    r"\bhttp\b", r"\bwww\b", r"\bclick\b", r"\bapply\b", r"\bavail\b", r"\boffer\s+valid\b"
]


def is_offer_or_marketing(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.lower()

    # must NOT be an actual txn indicator
    txn_verbs = re.search(r"\b(credited|debited|spent|paid|purchase|withdrawn|received|transferred)\b", t)
    if txn_verbs:
        # if txn verbs exist, only block if BOTH strong offer cues AND strong CTA are present
        strong_offer = any(re.search(p, t) for p in _OFFER_PATTERNS)
        strong_cta   = any(re.search(p, t) for p in _NON_TXN_STRONG_CTA)
        return bool(strong_offer and strong_cta)

    # no txn verbs -> if any offer marker appears, classify as offer
    return any(re.search(p, t) for p in _OFFER_PATTERNS)
