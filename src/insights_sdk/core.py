"""
core.py
-------
Main orchestrator for the insights SDK (Layer 3).
Takes the feature store and generates all domain-specific insights.
"""

from datetime import datetime, timezone

from .utils import sanitize, parse_timestamp
from .banking import generate_banking_insights
from .investment import generate_investment_insights
from .insurance import generate_insurance_insights
from .shopping import generate_shopping_insights
from .lending import generate_lending_insights
from .persona import generate_persona_insights
from .promotional import generate_promotional_insights


def generate_insights(feature_store: list[dict]) -> dict:
    """Generate all domain insights from the feature store.

    Parameters
    ----------
    feature_store : list[dict]
        List of parsed SMS dicts (output of Layer 2 parsers via .to_dict()).

    Returns
    -------
    dict
        Complete insights response with all domains, fully JSON-serializable.
    """
    # Group by category
    grouped: dict[str, list[dict]] = {}
    for d in feature_store:
        cat = d.get("sms_category", "Other")
        grouped.setdefault(cat, []).append(d)

    # Generate per-domain insights
    banking = generate_banking_insights(feature_store)
    investment = generate_investment_insights(feature_store)
    insurance = generate_insurance_insights(feature_store)
    shopping = generate_shopping_insights(feature_store)
    lending = generate_lending_insights(feature_store)
    promotional = generate_promotional_insights(feature_store)

    # Persona needs other insights
    persona = None
    if investment and insurance and shopping:
        persona = generate_persona_insights(shopping, insurance, investment, feature_store)

    # Collect all domain results for meta tracking
    domain_results = {
        "banking": banking,
        "investment": investment,
        "insurance": insurance,
        "shopping": shopping,
        "lending": lending,
        "promotional": promotional,
        "unified_persona": persona,
    }

    meta = _build_meta(feature_store, grouped, domain_results)

    return sanitize({
        "meta": meta,
        "promotional_insights": promotional,
        "banking_insights": banking,
        "investment_insights": investment,
        "insurance_insights": insurance,
        "shopping_insights": shopping,
        "loan_insights": lending,
        "unified_persona": persona,
        "parsed_count_by_category": {k: len(v) for k, v in grouped.items()},
    })


def _build_meta(
    feature_store: list[dict],
    grouped: dict[str, list[dict]],
    domain_results: dict,
) -> dict:
    """Build the meta block for the insights response."""
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Date range from feature store timestamps
    dates = []
    for d in feature_store:
        dt = parse_timestamp(d.get("timestamp"))
        if dt is not None:
            dates.append(dt)
    date_range = (
        {"from": min(dates).strftime("%Y-%m-%d"), "to": max(dates).strftime("%Y-%m-%d")}
        if dates else None
    )

    # Domain status — split into analyzed vs skipped with reason
    domains_analyzed = []
    domains_skipped = []
    for name, result in domain_results.items():
        if result is not None:
            domains_analyzed.append(name)
        else:
            domains_skipped.append({"module": name, "reason": "no_data"})

    # Category counts
    category_counts = {k: len(v) for k, v in grouped.items()}

    # Unique senders
    senders = {d.get("sender_address") for d in feature_store if d.get("sender_address")}

    return {
        "processed_at": processed_at,
        "date_range": date_range,
        "sms_counts": {
            "total_received": len(feature_store),
            **category_counts,
        },
        "unique_senders": len(senders),
        "domains_analyzed": domains_analyzed,
        "domains_skipped": domains_skipped,
    }
