import re

_OFFER_RE = re.compile(
    r"\bpre[-\s]?qualified\b"
    r"|\bpre[-\s]?approved\b"
    r"|\bapproved\s+for\b"
    r"|\byou('?re| are)\s+eligible\b"
    r"|\bapply\s+now\b"
    r"|\binstant\s+approval\b"
    r"|\bclick\s+(now|here)\b"
    r"|\boffer\b"
    r"|\boffer\s+valid\b"
    r"|\bvalid\s+till\b"
    r"|\bzero\s+joining\s+fee\b"
    r"|\bjoining\s+fee\b"
    r"|\bannual\s+fee\b"
    r"|\bannual\s+cashback\b"
    r"|\bcashback\b"
    r"|\bcredit\s+limit\b"
    r"|\blimit\s+of\s+up\s+to\b"
    r"|\bcard\b.*\b(offer|eligible|pre[-\s]?approved|pre[-\s]?qualified|apply)\b"
)

_NON_TXN_CTA_RE = re.compile(
    r"\bhttp\b|\bwww\b|\bclick\b|\bapply\b|\bavail\b|\boffer\s+valid\b"
)

_TXN_VERBS_RE = re.compile(
    r"\b(credited|debited|spent|paid|purchase|withdrawn|received|transferred)\b"
)


def is_offer_or_marketing(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.lower()

    if _TXN_VERBS_RE.search(t):
        # Txn verbs present — need both offer cues AND CTA to avoid false positives on real transactions
        return bool(_OFFER_RE.search(t) and _NON_TXN_CTA_RE.search(t))

    return bool(_OFFER_RE.search(t))