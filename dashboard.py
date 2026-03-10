"""
dashboard.py
------------
Internal pipeline explorer for the SMS parser.
Shows all 3 SDK layers side-by-side for debugging and parser validation.

Run:  streamlit run dashboard.py
API:  must be running on localhost:5004 (or uses direct imports as fallback)
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import json
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.classifier_sdk import classify_sms
from src.feature_store_sdk import extract_features
from src.insights_sdk import generate_insights

# ── Theme ────────────────────────────────────────────────────────────────────
BG_CARD = "#F8FAFC"
BORDER = "#E2E8F0"
ACCENT = "#2563EB"
TEXT_PRI = "#0F172A"
TEXT_SEC = "#475569"

CSS = f"""
<style>
#MainMenu {{visibility: hidden;}}
header {{visibility: hidden;}}
footer {{visibility: hidden;}}
.stApp {{ background-color: #FFFFFF; color: {TEXT_PRI}; }}
.block-container {{ padding-top: 1rem !important; }}
.layer-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.8rem;
    margin-bottom: 8px;
}}
.l1 {{ background: #DBEAFE; color: #1E40AF; }}
.l2 {{ background: #D1FAE5; color: #065F46; }}
.l3 {{ background: #FEE2E2; color: #991B1B; }}
.sms-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 0.85rem;
    line-height: 1.5;
}}
.field-name {{ color: {TEXT_SEC}; font-weight: 600; }}
.field-val {{ color: {TEXT_PRI}; }}
.cat-tag {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 4px;
}}
</style>
"""

CAT_COLORS = {
    "transactions": ("#DBEAFE", "#1E40AF"),
    "insurance": ("#FCE7F3", "#9D174D"),
    "investments": ("#D1FAE5", "#065F46"),
    "lending": ("#FEF3C7", "#92400E"),
    "promotions": ("#FEE2E2", "#991B1B"),
    "epfo": ("#E0E7FF", "#3730A3"),
    "utility_bills": ("#F3E8FF", "#6B21A8"),
    "orders": ("#FFEDD5", "#9A3412"),
    "security_alert": ("#FEE2E2", "#991B1B"),
    "otp": ("#F1F5F9", "#475569"),
    "other": ("#F1F5F9", "#475569"),
}


def cat_badge(category):
    bg, fg = CAT_COLORS.get(category, ("#F1F5F9", "#475569"))
    return f"<span class='cat-tag' style='background:{bg};color:{fg};'>{category}</span>"


def fmt_currency(val):
    if val is None:
        return "N/A"
    try:
        return f"{float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val)


def truncate(text, n=120):
    if not text:
        return ""
    return text[:n] + "..." if len(text) > n else text


# ── Pipeline execution ───────────────────────────────────────────────────────

def run_pipeline(sms_data):
    """Run all 3 layers and return intermediate results."""
    classified = classify_sms(sms_data)
    features = extract_features(classified)
    insights = generate_insights(features)
    return classified, features, insights


# ── Renderers ────────────────────────────────────────────────────────────────

def render_l1(classified):
    """Layer 1: Classification results."""
    st.markdown("<span class='layer-badge l1'>Layer 1 — Classifier</span>", unsafe_allow_html=True)
    st.caption(f"{len(classified)} SMS classified")

    # Summary bar
    cat_counts = {}
    for c in classified:
        cat = c.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    badges = " ".join(
        f"{cat_badge(cat)} <b>{count}</b>" for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])
    )
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("---")

    # Filters
    col_cat, col_conf, col_search = st.columns([2, 2, 3])
    with col_cat:
        all_cats = sorted(set(c.get("category", "other") for c in classified))
        selected_cats = st.multiselect("Filter by category", all_cats, default=all_cats, key="l1_cat")
    with col_conf:
        min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05, key="l1_conf")
    with col_search:
        search = st.text_input("Search body text", "", key="l1_search").lower()

    filtered = [
        c for c in classified
        if c.get("category") in selected_cats
        and c.get("confidence", 0) >= min_conf
        and (not search or search in c.get("body", "").lower())
    ]

    st.caption(f"Showing {len(filtered)} of {len(classified)}")

    # Table view
    if filtered:
        rows = []
        for c in filtered:
            rows.append({
                "category": c.get("category"),
                "confidence": c.get("confidence"),
                "entity_name": c.get("entity_name", ""),
                "traffic_type": c.get("traffic_type", ""),
                "tags": c.get("occurrence_tag", ""),
                "body": truncate(c.get("body", ""), 100),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)

    # Expandable detail per SMS
    with st.expander("Detailed view (per SMS)"):
        for i, c in enumerate(filtered[:50]):
            body_preview = truncate(c.get("body", ""), 80)
            cat = c.get("category", "other")
            conf = c.get("confidence", 0)
            html = (
                f"<div class='sms-card'>"
                f"{cat_badge(cat)} <b>{conf:.0%}</b> "
                f"<span class='field-name'>sender:</span> {c.get('entity_name', '')} "
                f"<span class='field-name'>traffic:</span> {c.get('traffic_type', '')} "
                f"<span class='field-name'>hint:</span> {c.get('sender_category_hint', '')} "
                f"<br><span style='color:#64748B;font-size:0.8rem;'>{body_preview}</span>"
                f"<br><span class='field-name'>tags:</span> <code>{c.get('occurrence_tag', '')}</code>"
                f"</div>"
            )
            st.markdown(html, unsafe_allow_html=True)
        if len(filtered) > 50:
            st.caption(f"Showing first 50 of {len(filtered)}")


def render_l2(features):
    """Layer 2: Feature store."""
    st.markdown("<span class='layer-badge l2'>Layer 2 — Feature Store</span>", unsafe_allow_html=True)
    st.caption(f"{len(features)} feature dicts extracted")

    # Filters
    col_cat, col_search = st.columns([3, 4])
    with col_cat:
        all_cats = sorted(set(f.get("sms_category", "other") for f in features))
        selected_cats = st.multiselect("Filter by category", all_cats, default=all_cats, key="l2_cat")
    with col_search:
        search = st.text_input("Search fields/values", "", key="l2_search").lower()

    filtered = [
        f for f in features
        if f.get("sms_category") in selected_cats
        and (not search or search in json.dumps(f, default=str).lower())
    ]

    st.caption(f"Showing {len(filtered)} of {len(features)}")

    # Category tabs
    cats_present = sorted(set(f.get("sms_category", "other") for f in filtered))
    if cats_present:
        tabs = st.tabs(cats_present)
        for tab, cat in zip(tabs, cats_present):
            with tab:
                cat_features = [f for f in filtered if f.get("sms_category") == cat]

                # Show as table — exclude raw_body for readability
                exclude_keys = {"raw_body", "occurrence_tag", "alphabetical_tag"}
                rows = []
                for f in cat_features:
                    rows.append({k: v for k, v in f.items() if k not in exclude_keys})
                df = pd.DataFrame(rows)
                st.dataframe(df, width="stretch", hide_index=True)

                # Field completeness
                all_keys = set()
                for f in cat_features:
                    all_keys.update(f.keys())
                all_keys -= exclude_keys
                filled_counts = {}
                for k in sorted(all_keys):
                    filled_counts[k] = sum(1 for f in cat_features if k in f)

                with st.expander(f"Field coverage ({cat})"):
                    coverage_df = pd.DataFrame([
                        {"field": k, "filled": v, "total": len(cat_features), "pct": f"{v/len(cat_features)*100:.0f}%"}
                        for k, v in filled_counts.items()
                    ])
                    st.dataframe(coverage_df, width="stretch", hide_index=True)


def render_l3(insights):
    """Layer 3: Insights."""
    st.markdown("<span class='layer-badge l3'>Layer 3 — Insights</span>", unsafe_allow_html=True)

    meta = insights.get("meta", {})

    # Meta summary
    col1, col2, col3, col4 = st.columns(4)
    sms_counts = meta.get("sms_counts", {})
    col1.metric("Total SMS", sms_counts.get("total_received", 0))
    col2.metric("Unique Senders", meta.get("unique_senders", 0))
    date_range = meta.get("date_range") or {}
    col3.metric("Date Range", f"{date_range.get('from', '?')} to {date_range.get('to', '?')}" if date_range else "N/A")
    analyzed = meta.get("domains_analyzed", [])
    col4.metric("Domains Active", f"{len(analyzed)} of 7")

    # Skipped modules
    skipped = meta.get("domains_skipped", [])
    if skipped:
        skip_str = ", ".join(f"**{s['module']}** ({s['reason']})" for s in skipped)
        st.info(f"Skipped: {skip_str}")

    st.markdown("---")

    # Domain tabs
    domain_keys = [
        ("banking_insights", "Banking"),
        ("investment_insights", "Investment"),
        ("insurance_insights", "Insurance"),
        ("shopping_insights", "Shopping"),
        ("loan_insights", "Lending"),
        ("promotional_insights", "Promotional"),
        ("unified_persona", "Persona"),
    ]

    available = [(k, label) for k, label in domain_keys if insights.get(k)]
    if not available:
        st.warning("No domain insights generated.")
        return

    tabs = st.tabs([label for _, label in available])
    for tab, (key, label) in zip(tabs, available):
        with tab:
            data = insights[key]
            # Render as structured JSON with collapsible sections
            if isinstance(data, dict):
                for section_name, section_data in data.items():
                    with st.expander(section_name, expanded=True):
                        if isinstance(section_data, (dict, list)):
                            st.json(section_data)
                        else:
                            st.write(section_data)
            else:
                st.json(data)

    # Full JSON
    with st.expander("Raw JSON response"):
        st.json(insights)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="SMS Parser — Pipeline Explorer",
        layout="wide",
        page_icon="🔍",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        f"<h2 style='color:{ACCENT};margin-bottom:0;'>SMS Parser — Pipeline Explorer</h2>"
        f"<p style='color:{TEXT_SEC};margin-top:0;'>Internal tool for inspecting all 3 SDK layers</p>",
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("Upload SMS CSV", type=["csv"], label_visibility="collapsed")
    if not uploaded:
        st.info("Upload a CSV file with columns: `body`, `address`, `timestamp`")
        return

    if st.button("Run Pipeline", type="primary"):
        with st.spinner("Running classify -> features -> insights ..."):
            try:
                df_raw = pd.read_csv(uploaded, low_memory=False)
                df_raw = df_raw.replace({np.nan: None})
                sms_data = df_raw.to_dict(orient="records")

                classified, features, insights = run_pipeline(sms_data)

                st.session_state["pipeline_result"] = (classified, features, insights)
                st.session_state["sms_count"] = len(sms_data)

            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                st.exception(e)
                return

    if "pipeline_result" not in st.session_state:
        return

    classified, features, insights = st.session_state["pipeline_result"]

    # Pipeline summary
    st.markdown(
        f"<div style='background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:12px 20px;"
        f"display:flex;gap:40px;align-items:center;margin-bottom:16px;'>"
        f"<span><b>{st.session_state['sms_count']}</b> SMS input</span>"
        f"<span style='color:#94A3B8;'>→</span>"
        f"<span class='layer-badge l1'>L1</span> <b>{len(classified)}</b> classified"
        f"<span style='color:#94A3B8;'>→</span>"
        f"<span class='layer-badge l2'>L2</span> <b>{len(features)}</b> features"
        f"<span style='color:#94A3B8;'>→</span>"
        f"<span class='layer-badge l3'>L3</span> <b>{len(insights.get('meta', {}).get('domains_analyzed', []))}</b> domains"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Layer tabs
    tab_l1, tab_l2, tab_l3 = st.tabs(["L1 — Classify", "L2 — Features", "L3 — Insights"])

    with tab_l1:
        render_l1(classified)
    with tab_l2:
        render_l2(features)
    with tab_l3:
        render_l3(insights)


if __name__ == "__main__":
    main()