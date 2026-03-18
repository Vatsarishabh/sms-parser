"""
Strategy pattern for SMS classification.

Usage:
    clf = get_classifier("rules")     # Aho-Corasick (default)
    clf = get_classifier("sklearn")   # trained ML model
    clf = get_classifier("ensemble")  # ML + rules fallback
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import json
import numpy as np


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    occurrence_tag: str = ""
    alphabetical_tag: str = ""
    tag_count: int = 0
    unique_tags: frozenset = frozenset()


class SMSClassifier(ABC):

    @abstractmethod
    def classify(self, body: str, address: str = "") -> ClassificationResult: ...

    def classify_batch(self, bodies: list[str], addresses: list[str] = None) -> list[ClassificationResult]:
        addresses = addresses or [""] * len(bodies)
        return [self.classify(b, a) for b, a in zip(bodies, addresses)]


class RuleBasedClassifier(SMSClassifier):

    def __init__(self):
        from .tagger import _build_automaton, CATEGORY_RULES
        self._automaton = _build_automaton()
        self._rules = CATEGORY_RULES

    def _tag(self, text: str) -> dict:
        text = str(text).lower().strip()
        if not text:
            return {"occurrence_tag": "", "alphabetical_tag": "", "unique_tags": set(), "tag_count": 0}

        matches = list(self._automaton.iter(text))
        sorted_matches = sorted(matches, key=lambda x: x[0] - len(x[1][1]) + 1)

        occurrence_tags = [m[1][0] for m in sorted_matches]
        cleaned = []
        for i, tag in enumerate(occurrence_tags):
            if i == 0 or tag != occurrence_tags[i - 1]:
                cleaned.append(tag)

        unique = set(cleaned)
        return {
            "occurrence_tag": "*".join(cleaned),
            "alphabetical_tag": "*".join(sorted(unique)),
            "unique_tags": unique,
            "tag_count": len(cleaned),
        }

    def _score(self, unique_tags: set, sender_category_hint: str = None) -> tuple[str, float]:
        if not unique_tags:
            return "Other", 0.0

        best_category = "Other"
        best_score = 0
        total_score = 0

        # Banking hint maps to the actual category name
        _hint = sender_category_hint
        if _hint == "Banking":
            _hint = "Transactions"

        for category, rule in self._rules.items():
            required_hits = unique_tags & rule["required"]
            boost_hits = unique_tags & rule["boost"]
            weak_hits = unique_tags & rule.get("weak", set())

            if not required_hits:
                if len(weak_hits) < 2:
                    continue
                required_hits = weak_hits

            exclude = rule.get("exclude", set())
            if exclude and (unique_tags & exclude):
                continue
            score = len(required_hits) * rule["priority"] + len(boost_hits) + len(weak_hits)
            if _hint and category == _hint:
                score += 3
            total_score += score
            if score > best_score:
                best_score = score
                best_category = category

        confidence = (best_score / total_score) if total_score > 0 else 0.0
        return best_category, round(min(confidence, 1.0), 4)

    def classify(self, body: str, address: str = "") -> ClassificationResult:
        tags = self._tag(body)

        from .tagger import decode_sender_meta
        meta = decode_sender_meta(address)
        sender_hint = meta.get("sender_category_hint")

        category, confidence = self._score(tags["unique_tags"], sender_category_hint=sender_hint)

        return ClassificationResult(
            category=category,
            confidence=confidence,
            occurrence_tag=tags["occurrence_tag"],
            alphabetical_tag=tags["alphabetical_tag"],
            tag_count=tags["tag_count"],
            unique_tags=frozenset(tags["unique_tags"]),
        )


_DATA_DIR = Path(__file__).parent / "data"
_sklearn_cache: tuple | None = None


def _get_sklearn_artifacts():
    global _sklearn_cache
    if _sklearn_cache is None:
        import joblib
        pipeline = joblib.load(_DATA_DIR / "sms_classifier.pkl")
        mlb = joblib.load(_DATA_DIR / "label_binarizer.pkl")
        with open(_DATA_DIR / "thresholds.json") as f:
            thresholds = json.load(f)
        threshold_array = np.array([thresholds[cls] for cls in mlb.classes_])
        _sklearn_cache = (pipeline, mlb, threshold_array)
    return _sklearn_cache


class SklearnClassifier(SMSClassifier):

    def __init__(self):
        from .text_cleaning import clean_text
        self._clean_text = clean_text
        self._pipeline, self._mlb, self._thresholds = _get_sklearn_artifacts()
        self._rule_tagger = RuleBasedClassifier()

    def _build_input(self, body: str, header_code: str, traffic_type: str) -> str:
        """Must match training/text_cleaning.py build_input exactly."""
        cleaned = self._clean_text(body)
        parts = []
        if header_code and header_code != "nan":
            parts.append(f"_hdr_{header_code.lower()}_")
        if traffic_type and traffic_type.lower() != "general":
            parts.append(f"_traf_{traffic_type.lower()}_")
        return " ".join(parts + [cleaned])

    def _predict(self, texts: list[str]):
        proba = self._pipeline.predict_proba(texts)
        binary = (proba >= self._thresholds).astype(int)

        # Argmax fallback — always predict at least one label
        no_label = binary.sum(axis=1) == 0 if len(texts) > 1 else [binary.sum() == 0]
        for row in np.where(no_label)[0]:
            binary[row, proba[row].argmax()] = 1

        return proba, binary

    def _to_result(self, proba_row, binary_row, body: str, address: str) -> ClassificationResult:
        cats = [cls for cls, b in zip(self._mlb.classes_, binary_row) if b]
        conf = float(max(proba_row[binary_row == 1]))
        rule_result = self._rule_tagger.classify(body, address)

        return ClassificationResult(
            category=",".join(sorted(cats)),
            confidence=round(conf, 4),
            occurrence_tag=rule_result.occurrence_tag,
            alphabetical_tag=rule_result.alphabetical_tag,
            tag_count=rule_result.tag_count,
            unique_tags=rule_result.unique_tags,
        )

    def classify(self, body: str, address: str = "") -> ClassificationResult:
        from .tagger import decode_sender_meta
        meta = decode_sender_meta(address)
        text = self._build_input(body, meta["header_code"], meta["traffic_type"])

        proba, binary = self._predict([text])
        return self._to_result(proba[0], binary[0], body, address)

    def classify_batch(self, bodies: list[str], addresses: list[str] = None) -> list[ClassificationResult]:
        from .tagger import decode_sender_meta
        addresses = addresses or [""] * len(bodies)
        metas = [decode_sender_meta(addr) for addr in addresses]

        texts = [
            self._build_input(body, meta["header_code"], meta["traffic_type"])
            for body, meta in zip(bodies, metas)
        ]

        proba, binary = self._predict(texts)
        return [
            self._to_result(proba[i], binary[i], body, addr)
            for i, (body, addr) in enumerate(zip(bodies, addresses))
        ]


class EnsembleClassifier(SMSClassifier):
    """ML when confident, rules when not. Always keeps rule-based tags for downstream parsing."""

    def __init__(self, confidence_threshold: float = 0.7):
        self._ml = SklearnClassifier()
        self._rules = RuleBasedClassifier()
        self._threshold = confidence_threshold

    def classify(self, body: str, address: str = "") -> ClassificationResult:
        ml_result = self._ml.classify(body, address)
        rule_result = self._rules.classify(body, address)

        if ml_result.confidence >= self._threshold:
            return ClassificationResult(
                category=ml_result.category,
                confidence=ml_result.confidence,
                occurrence_tag=rule_result.occurrence_tag,
                alphabetical_tag=rule_result.alphabetical_tag,
                tag_count=rule_result.tag_count,
                unique_tags=rule_result.unique_tags,
            )

        return rule_result


_CLASSIFIER_INSTANCE: Optional[SMSClassifier] = None


def get_classifier(strategy: str = "rules", **kwargs) -> SMSClassifier:
    global _CLASSIFIER_INSTANCE

    if strategy == "rules":
        if _CLASSIFIER_INSTANCE is None or not isinstance(_CLASSIFIER_INSTANCE, RuleBasedClassifier):
            _CLASSIFIER_INSTANCE = RuleBasedClassifier()
        return _CLASSIFIER_INSTANCE

    if strategy == "sklearn":
        if _CLASSIFIER_INSTANCE is None or not isinstance(_CLASSIFIER_INSTANCE, SklearnClassifier):
            _CLASSIFIER_INSTANCE = SklearnClassifier()
        return _CLASSIFIER_INSTANCE

    if strategy == "ensemble":
        threshold = kwargs.get("confidence_threshold", 0.7)
        if _CLASSIFIER_INSTANCE is None or not isinstance(_CLASSIFIER_INSTANCE, EnsembleClassifier):
            _CLASSIFIER_INSTANCE = EnsembleClassifier(confidence_threshold=threshold)
        return _CLASSIFIER_INSTANCE

    raise ValueError(f"Unknown strategy: {strategy}. Use 'rules', 'sklearn', or 'ensemble'.")