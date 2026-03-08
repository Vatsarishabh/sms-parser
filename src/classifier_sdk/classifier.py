"""
classifier.py
-------------
Strategy pattern for SMS classification.

Defines the abstract interface and concrete implementations.
parser.py depends on this abstraction, not on any specific classifier.

Usage:
    from src.classifier_sdk.classifier import get_classifier

    clf = get_classifier()                          # default: rule-based
    clf = get_classifier("fasttext", model_path="model.bin")  # future: fastText

    category, confidence, tags = clf.classify(body, address)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    """Output of any classifier — uniform contract."""
    category: str
    confidence: float           # 0.0 – 1.0
    occurrence_tag: str = ""
    alphabetical_tag: str = ""
    tag_count: int = 0
    unique_tags: frozenset = frozenset()


class SMSClassifier(ABC):
    """Abstract base — every classifier must implement classify()."""

    @abstractmethod
    def classify(self, body: str, address: str = "") -> ClassificationResult:
        """
        Classify a single SMS.

        Parameters
        ----------
        body    : SMS text
        address : sender address (optional, some classifiers use sender metadata)

        Returns
        -------
        ClassificationResult with category, confidence, and optional tag metadata.
        """
        ...

    def classify_batch(self, bodies: list[str], addresses: list[str] = None) -> list[ClassificationResult]:
        """Default batch: loop over singles. Subclasses can override for vectorised ops."""
        addresses = addresses or [""] * len(bodies)
        return [self.classify(b, a) for b, a in zip(bodies, addresses)]


# ---------------------------------------------------------------------------
# Concrete: Rule-based (current Aho-Corasick + priority scoring)
# ---------------------------------------------------------------------------
class RuleBasedClassifier(SMSClassifier):
    """
    Deterministic classifier using Aho-Corasick keyword tagging + priority-scored rules.
    Zero training data required. Fully interpretable.
    """

    def __init__(self):
        from .tagger import _build_automaton, CATEGORY_RULES
        self._automaton = _build_automaton()
        self._rules = CATEGORY_RULES

    def _tag(self, text: str) -> dict:
        """Run Aho-Corasick and return tag metadata."""
        text = str(text).lower().strip()
        if not text:
            return {"occurrence_tag": "", "alphabetical_tag": "", "unique_tags": set(), "tag_count": 0}

        matches = list(self._automaton.iter(text))
        sorted_matches = sorted(matches, key=lambda x: x[0] - len(x[1][1]) + 1)

        occurrence_tags = [m[1][0] for m in sorted_matches]
        # clean consecutive duplicates
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
        """Score categories and return (best_category, confidence).

        If ``sender_category_hint`` is provided (e.g. from the TRAI sender map),
        it adds a bonus to the matching category's score.
        """
        if not unique_tags:
            return "Other", 0.0

        best_category = "Other"
        best_score = 0
        total_score = 0

        # Map Banking hint → Transactions (the actual category name)
        _hint = sender_category_hint
        if _hint == "Banking":
            _hint = "Transactions"

        for category, rule in self._rules.items():
            required_hits = unique_tags & rule["required"]
            boost_hits = unique_tags & rule["boost"]
            weak_hits = unique_tags & rule.get("weak", set())

            # Need at least one strong required tag, OR 2+ weak tags
            if not required_hits:
                if len(weak_hits) < 2:
                    continue
                required_hits = weak_hits

            exclude = rule.get("exclude", set())
            if exclude and (unique_tags & exclude):
                continue
            score = len(required_hits) * rule["priority"] + len(boost_hits) + len(weak_hits)
            # Sender-hint bonus: +3 if the entity name suggests this category
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

        # Derive sender category hint from TRAI header map
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


# ---------------------------------------------------------------------------
# Concrete: FastText (stub — ready for when you have a trained model)
# ---------------------------------------------------------------------------
class FastTextClassifier(SMSClassifier):
    """
    fastText-based classifier. Requires a trained .bin model.

    Training workflow (future):
        1. Export labeled data: category + cleaned SMS text
        2. Format as fastText input: "__label__Transactions INR 2000 debited..."
        3. Train: fasttext.train_supervised("train.txt", epoch=25, lr=0.5, wordNgrams=2)
        4. Save model: model.save_model("sms_classifier.bin")
        5. Pass path here: FastTextClassifier("sms_classifier.bin")
    """

    def __init__(self, model_path: str):
        try:
            import fasttext
            self._model = fasttext.load_model(model_path)
        except ImportError:
            raise ImportError("fasttext not installed. Run: pip install fasttext")
        except Exception as e:
            raise FileNotFoundError(f"Could not load fastText model at {model_path}: {e}")

        # Optional: keep rule-based tagger for structural tags (occurrence/alphabetical)
        # even when using fastText for classification
        self._rule_tagger = RuleBasedClassifier()

    def _clean_for_prediction(self, text: str) -> str:
        """Minimal text cleaning for fastText input."""
        import re
        text = str(text).lower().strip()
        text = re.sub(r'https?://\S+', ' ', text)
        text = re.sub(r'[^\w\s./]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def classify(self, body: str, address: str = "") -> ClassificationResult:
        cleaned = self._clean_for_prediction(body)
        labels, probs = self._model.predict(cleaned, k=1)

        # fastText labels are "__label__CategoryName"
        category = labels[0].replace("__label__", "") if labels else "Other"
        confidence = float(probs[0]) if probs else 0.0

        # Get structural tags from rule-based tagger (useful for parsing even with ML classification)
        rule_result = self._rule_tagger.classify(body, address)

        return ClassificationResult(
            category=category,
            confidence=round(confidence, 4),
            occurrence_tag=rule_result.occurrence_tag,
            alphabetical_tag=rule_result.alphabetical_tag,
            tag_count=rule_result.tag_count,
            unique_tags=rule_result.unique_tags,
        )

    def classify_batch(self, bodies: list[str], addresses: list[str] = None) -> list[ClassificationResult]:
        """Vectorised prediction — faster than looping for large batches."""
        cleaned = [self._clean_for_prediction(b) for b in bodies]
        all_labels, all_probs = self._model.predict(cleaned, k=1)

        addresses = addresses or [""] * len(bodies)
        results = []
        for i, (body, addr) in enumerate(zip(bodies, addresses)):
            category = all_labels[i][0].replace("__label__", "") if all_labels[i] else "Other"
            confidence = float(all_probs[i][0]) if all_probs[i] else 0.0

            rule_result = self._rule_tagger.classify(body, addr)

            results.append(ClassificationResult(
                category=category,
                confidence=round(confidence, 4),
                occurrence_tag=rule_result.occurrence_tag,
                alphabetical_tag=rule_result.alphabetical_tag,
                tag_count=rule_result.tag_count,
                unique_tags=rule_result.unique_tags,
            ))
        return results


# ---------------------------------------------------------------------------
# Concrete: Ensemble (future — combines both for production)
# ---------------------------------------------------------------------------
class EnsembleClassifier(SMSClassifier):
    """
    Combines rule-based and ML classifiers.

    Strategy:
      - If ML confidence >= threshold → use ML prediction
      - Otherwise → fall back to rule-based
      - If both disagree and ML confidence is borderline → flag for review
    """

    def __init__(self, ml_classifier: SMSClassifier, confidence_threshold: float = 0.7):
        self._ml = ml_classifier
        self._rules = RuleBasedClassifier()
        self._threshold = confidence_threshold

    def classify(self, body: str, address: str = "") -> ClassificationResult:
        ml_result = self._ml.classify(body, address)
        rule_result = self._rules.classify(body, address)

        if ml_result.confidence >= self._threshold:
            # Use ML prediction but keep rule-based tags
            return ClassificationResult(
                category=ml_result.category,
                confidence=ml_result.confidence,
                occurrence_tag=rule_result.occurrence_tag,
                alphabetical_tag=rule_result.alphabetical_tag,
                tag_count=rule_result.tag_count,
                unique_tags=rule_result.unique_tags,
            )

        # Low ML confidence — defer to rules
        return rule_result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_CLASSIFIER_INSTANCE: Optional[SMSClassifier] = None


def get_classifier(strategy: str = "rules", **kwargs) -> SMSClassifier:
    """
    Factory function. Returns a classifier instance.

    Parameters
    ----------
    strategy : "rules" | "fasttext" | "ensemble"
    kwargs   : model_path (for fasttext), confidence_threshold (for ensemble)
    """
    global _CLASSIFIER_INSTANCE

    if strategy == "rules":
        if _CLASSIFIER_INSTANCE is None or not isinstance(_CLASSIFIER_INSTANCE, RuleBasedClassifier):
            _CLASSIFIER_INSTANCE = RuleBasedClassifier()
        return _CLASSIFIER_INSTANCE

    if strategy == "fasttext":
        model_path = kwargs.get("model_path")
        if not model_path:
            raise ValueError("model_path required for fasttext strategy")
        return FastTextClassifier(model_path)

    if strategy == "ensemble":
        model_path = kwargs.get("model_path")
        if not model_path:
            raise ValueError("model_path required for ensemble strategy")
        ml = FastTextClassifier(model_path)
        threshold = kwargs.get("confidence_threshold", 0.7)
        return EnsembleClassifier(ml, threshold)

    raise ValueError(f"Unknown strategy: {strategy}. Use 'rules', 'fasttext', or 'ensemble'.")
