"""Must stay in sync with training/text_cleaning.py — any divergence silently degrades the model."""

import re

_RE_URL = re.compile(r'https?://\S+')
_RE_AMT = re.compile(r'\brs\.?\s?\d[\d,]*\.?\d*\b', re.I)
_RE_PHONE = re.compile(r'\b\d{10,}\b')
_RE_ACCT = re.compile(r'x{2,}\d{2,4}', re.I)
_RE_NUM = re.compile(r'\b\d+\b')
_RE_NONWORD = re.compile(r'[^\w\s]')
_RE_SPACES = re.compile(r'\s+')


def clean_text(text: str) -> str:
    text = str(text).lower().strip()
    text = _RE_URL.sub(' _url_ ', text)
    text = _RE_AMT.sub(' _amt_ ', text)
    text = _RE_PHONE.sub(' _phone_ ', text)
    text = _RE_ACCT.sub(' _acct_ ', text)
    text = _RE_NUM.sub(' _num_ ', text)
    text = _RE_NONWORD.sub(' ', text)
    text = _RE_SPACES.sub(' ', text).strip()
    return text