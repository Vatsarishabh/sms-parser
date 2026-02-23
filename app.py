import streamlit as st
import pandas as pd
import os
import sys
import re
import plotly.graph_objects as go
import plotly.express as px

# Path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from src.promotion_analysis import analyze_promotions
    from src.tagger import process_sms_df
    from src.transaction import analyze_transactions
    from src.transaction_summary import monthly_and_overall_insights
    from src.investment import parse_investment_sms, generate_investment_insights
    from src.insurance import parse_insurance_sms, generate_insurance_insights
    from src.shopping_spend import parse_shopping_sms, generate_shopping_insights
    from src.in_in_sh import generate_unified_persona
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.stop()

# ── COLOUR PALETTE ──────────────────────────────────────────────────────────
BG_MAIN   = "#1A4B84"   # mid-blue (app background)
BG_CARD   = "#11335f"   # darker blue (metric cards / tables)
BG_CARD2  = "#0d2a50"   # even darker for alternate rows
BORDER    = "#2e6db4"
ACCENT    = "#60a5fa"   # light-blue accent
TEXT_PRI  = "#ffffff"   # primary text
TEXT_SEC  = "#cce0ff"   # secondary / label text
VAL_COL   = "#7dd3fc"   # metric value colour (sky-blue – readable on dark bg)
BTN_COL   = "#3b82f6"
BTN_HOV   = "#2563eb"

# ── HELPERS ─────────────────────────────────────────────────────────────────
def safe_val(data, keys, default="N/A"):
    try:
        for key in keys:
            data = data[key]
        return data if pd.notna(data) else default
    except (KeyError, TypeError, IndexError):
        return default


def parse_promo_text(promo_text):
    metrics = {
        "Total Messages": "0", "CC Messages": "0", "Offers/Discounts": "0",
        "NBFC/Lending": "0", "Other Promos": "0",
        "Avg CC Limit": "N/A", "Avg Lending Limit": "N/A"
    }
    if not isinstance(promo_text, str):
        return metrics

    patterns = {
        "Total Messages":    r"Total Promotional Messages:\s*([\d.]+)",
        "CC Messages":       r"Credit Card Promotional Messages:\s*([\d.]+)",
        "Offers/Discounts":  r"Offer or Discount Messages:\s*([\d.]+)",
        "NBFC/Lending":      r"NBFC / Lending Apps Promotional Messages:\s*([\d.]+)",
        "Other Promos":      r"Other Promotional Messages:\s*([\d.]+)",
        "Avg CC Limit":      r"Average of last 5 Credit Card Limit offers:\s*([\d.]+)",
        "Avg Lending Limit": r"Average of last 5 Lending App Limit offers:\s*([\d.]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, promo_text)
        if m:
            val = m.group(1)
            if key in ("Avg CC Limit", "Avg Lending Limit"):
                metrics[key] = f"₹ {float(val):,.2f}"
            else:
                metrics[key] = val
    return metrics


def make_donut(labels, values, title, colors=None):
    """Small donut chart for quick composition views."""
    if colors is None:
        colors = [ACCENT, "#818cf8", "#34d399", "#fb923c", "#f472b6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors[:len(labels)], line=dict(color=BG_CARD, width=2)),
        textfont=dict(color=TEXT_PRI, size=12),
        insidetextorientation="radial",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT_PRI, size=14), x=0.5),
        paper_bgcolor=BG_CARD, plot_bgcolor=BG_CARD,
        legend=dict(font=dict(color=TEXT_SEC), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=10, l=10, r=10), height=280,
    )
    return fig


def make_bar(x, y, title, xlabel="", ylabel="", color=ACCENT):
    fig = go.Figure(go.Bar(
        x=x, y=y, marker_color=color,
        text=[f"{v:,.0f}" for v in y],
        textposition="outside",
        textfont=dict(color=TEXT_PRI, size=11),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT_PRI, size=14), x=0.5),
        paper_bgcolor=BG_CARD, plot_bgcolor=BG_CARD,
        xaxis=dict(title=xlabel, tickfont=dict(color=TEXT_SEC), gridcolor=BORDER),
        yaxis=dict(title=ylabel, tickfont=dict(color=TEXT_SEC), gridcolor=BORDER),
        margin=dict(t=50, b=30, l=30, r=10), height=280,
    )
    return fig


# ── CSS ─────────────────────────────────────────────────────────────────────
GLOBAL_CSS = f"""
<style>
/* ── Base ── */
.stApp {{ background-color: {BG_MAIN} !important; color: {TEXT_PRI} !important; }}
html, body {{ color: {TEXT_PRI} !important; }}

/* ── File uploader ── */
.stFileUploader, [data-testid="stFileUploader"] {{
    background-color: {BG_CARD} !important;
}}
[data-testid="stFileUploadDropzone"] {{
    background-color: {BG_CARD} !important;
    border: 2px dashed {ACCENT} !important;
    border-radius: 10px !important;
}}
[data-testid="stFileUploadDropzone"] *, .stFileUploader label {{
    color: {TEXT_PRI} !important;
}}
[data-testid="stFileUploadDropzone"] button {{
    background-color: {BTN_COL} !important;
    color: {TEXT_PRI} !important;
    border: 1px solid {ACCENT} !important;
    font-weight: 800 !important;
    border-radius: 6px !important;
}}
[data-testid="stFileUploadDropzone"] button:hover {{
    background-color: {BTN_HOV} !important;
}}

/* ── Metric cards ── */
div[data-testid="metric-container"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    padding: 1.1rem !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.25) !important;
}}
[data-testid="stMetricLabel"] *, [data-testid="stMetricLabel"] {{
    color: {TEXT_SEC} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}}
[data-testid="stMetricValue"] *, [data-testid="stMetricValue"] {{
    color: {VAL_COL} !important;
    font-weight: 900 !important;
    font-size: 1.65rem !important;
}}
[data-testid="stMetricDelta"] * {{ color: #34d399 !important; }}

/* ── Typography ── */
h1, h2, h3, h4 {{ color: {TEXT_PRI} !important; font-family: 'Inter', sans-serif !important; }}
p, span, li, div {{ color: {TEXT_PRI} !important; }}
label {{ color: {TEXT_SEC} !important; }}

/* ── Section header ── */
.section-header {{
    border-bottom: 2px solid {BORDER} !important;
    padding-bottom: 8px !important;
    margin-bottom: 20px !important;
    color: {TEXT_PRI} !important;
    font-weight: 900 !important;
    font-size: 1.4rem !important;
}}

/* ── Placeholder card ── */
.placeholder-card {{
    background-color: {BG_CARD} !important;
    border: 1px dashed {BORDER} !important;
    border-radius: 10px !important;
    padding: 2rem 1rem !important;
    text-align: center !important;
    color: {TEXT_SEC} !important;
    font-size: 1.1rem !important;
    margin-bottom: 1rem !important;
}}

/* ── Button ── */
.stButton>button {{
    background-color: {BTN_COL} !important;
    color: {TEXT_PRI} !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 0.55rem 1.2rem !important;
    font-weight: 800 !important;
    width: 100% !important;
}}
.stButton>button:hover {{ background-color: {BTN_HOV} !important; }}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {{
    color: {TEXT_SEC} !important;
    font-weight: 700 !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT} !important;
}}

/* ── Dataframe / table ── */
.stDataFrame, [data-testid="stDataFrame"] {{
    background-color: {BG_CARD} !important;
    border-radius: 8px !important;
}}
.stDataFrame th {{
    background-color: {BG_CARD2} !important;
    color: {ACCENT} !important;
    font-weight: 800 !important;
}}
.stDataFrame td {{ color: {TEXT_PRI} !important; }}

/* ── Spinner / info / success ── */
[data-testid="stSpinner"] * {{ color: {ACCENT} !important; }}
[data-testid="stAlert"] {{ background-color: {BG_CARD} !important; border-color: {BORDER} !important; }}
</style>
"""


# ── PLACEHOLDER HELPER ───────────────────────────────────────────────────────
def placeholder_section(icon, title, fields):
    """Render a greyed-out placeholder section before data is loaded."""
    st.markdown(f"<h2 class='section-header'>{icon} {title}</h2>", unsafe_allow_html=True)
    cols = st.columns(len(fields))
    for col, (label, hint) in zip(cols, fields):
        col.metric(label, hint)
    st.markdown("<br>", unsafe_allow_html=True)


# ── PROMO RAW DATA DASHBOARD ─────────────────────────────────────────────────
def render_promo_raw_dashboard(df_promo: pd.DataFrame):
    """Full dashboard tab for Promotional & Lending Offers raw data."""
    if df_promo is None or df_promo.empty:
        st.info("No promotional data available to display.")
        return

    st.markdown("<h3 style='color:#7dd3fc;'>📋 Promotional & Lending Offers — Detailed View</h3>",
                unsafe_allow_html=True)

    # ── Filters row ──────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 2, 2])

    category_col = next((c for c in ["category", "Category", "promo_type", "type"] if c in df_promo.columns), None)
    sender_col   = next((c for c in ["sender", "Sender", "address", "from"] if c in df_promo.columns), None)
    date_col     = next((c for c in ["date", "Date", "timestamp"] if c in df_promo.columns), None)

    cat_options = ["All"]
    if category_col:
        cat_options += sorted(df_promo[category_col].dropna().unique().tolist())

    with f1:
        selected_cat = st.selectbox("Filter by Category", cat_options, key="promo_cat_filter")
    with f2:
        search_term = st.text_input("Search message text", placeholder="e.g. cashback, loan, offer…", key="promo_search")
    with f3:
        if date_col and pd.api.types.is_datetime64_any_dtype(df_promo[date_col]):
            date_min = df_promo[date_col].min().date()
            date_max = df_promo[date_col].max().date()
            date_range = st.date_input("Date range", value=(date_min, date_max), key="promo_date")
        else:
            date_range = None

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = df_promo.copy()
    if selected_cat != "All" and category_col:
        filtered = filtered[filtered[category_col] == selected_cat]
    if search_term:
        msg_col = next((c for c in ["body", "message", "text", "sms"] if c in filtered.columns), None)
        if msg_col:
            filtered = filtered[filtered[msg_col].str.contains(search_term, case=False, na=False)]
    if date_range and date_col and len(date_range) == 2:
        filtered = filtered[
            (filtered[date_col].dt.date >= date_range[0]) &
            (filtered[date_col].dt.date <= date_range[1])
        ]

    total_filtered = len(filtered)

    # ── Summary KPI row ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Records Shown", f"{total_filtered:,}")
    if category_col:
        k2.metric("Unique Categories", filtered[category_col].nunique())
    if sender_col:
        k3.metric("Unique Senders", filtered[sender_col].nunique())
    if date_col and pd.api.types.is_datetime64_any_dtype(filtered[date_col]) and not filtered.empty:
        k4.metric("Date Span", f"{filtered[date_col].min().strftime('%d %b %y')} → {filtered[date_col].max().strftime('%d %b %y')}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        if category_col and not filtered.empty:
            cat_counts = filtered[category_col].value_counts().head(8)
            fig = make_bar(
                cat_counts.index.tolist(),
                cat_counts.values.tolist(),
                "Messages by Category",
                ylabel="Count",
                color=ACCENT,
            )
            st.plotly_chart(fig, use_container_width=True)

    with ch2:
        if sender_col and not filtered.empty:
            sender_counts = filtered[sender_col].value_counts().head(8)
            fig = make_bar(
                sender_counts.index.tolist(),
                sender_counts.values.tolist(),
                "Top Senders",
                ylabel="Count",
                color="#818cf8",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Monthly volume trend ──────────────────────────────────────────────────
    if date_col and pd.api.types.is_datetime64_any_dtype(filtered[date_col]) and not filtered.empty:
        monthly = filtered.groupby(filtered[date_col].dt.to_period("M")).size().reset_index()
        monthly.columns = ["Month", "Count"]
        monthly["Month"] = monthly["Month"].astype(str)
        fig_trend = go.Figure(go.Scatter(
            x=monthly["Month"], y=monthly["Count"],
            mode="lines+markers",
            line=dict(color=ACCENT, width=2),
            marker=dict(color=VAL_COL, size=6),
        ))
        fig_trend.update_layout(
            title=dict(text="Monthly Promo Volume", font=dict(color=TEXT_PRI, size=14), x=0.5),
            paper_bgcolor=BG_CARD, plot_bgcolor=BG_CARD,
            xaxis=dict(tickfont=dict(color=TEXT_SEC), gridcolor=BORDER),
            yaxis=dict(tickfont=dict(color=TEXT_SEC), gridcolor=BORDER),
            margin=dict(t=50, b=30, l=30, r=10), height=240,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # ── Raw data table (no download) ──────────────────────────────────────────
    st.markdown("<h4 style='color:#7dd3fc;margin-top:1rem;'>Raw Records</h4>", unsafe_allow_html=True)
    display_cols = [c for c in filtered.columns if c not in ("id", "_id")]
    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=380,
    )


# ── MAIN DASHBOARD ───────────────────────────────────────────────────────────
def render_dashboard(promo_text, promo_df, banking, invest, insur, shop, unified):

    # ====== TAB STRUCTURE ======
    tab_main, tab_promo_raw = st.tabs([
        "📊 Financial Intelligence Dashboard",
        "📨 Promotional & Lending Offers"
    ])

    with tab_main:
        _render_main_dashboard(promo_text, banking, invest, insur, shop, unified)

    with tab_promo_raw:
        render_promo_raw_dashboard(promo_df)


def _render_main_dashboard(promo_text, banking, invest, insur, shop, unified):
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 1. UNIFIED PERSONA ───────────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>👤 Unified Psychographic Persona</h2>", unsafe_allow_html=True)
    if unified:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("User Segment",         safe_val(unified, ["Unified_Persona", "Segment"]))
        c2.metric("Future-Proof Score",   f"{safe_val(unified, ['Cross_Domain_Metrics','Future_Proof_Score'], 0):.1f}/100")
        c3.metric("Burn-to-Build Multiple", safe_val(unified, ["Cross_Domain_Metrics","Burn_to_Build_Multiple"], 0))
        c4.metric("Value Hunter Level",   safe_val(unified, ["Cross_Domain_Metrics","Value_Hunting_Intensity"], "—"))
    else:
        cols = st.columns(4)
        for col, label in zip(cols, ["User Segment", "Future-Proof Score", "Burn-to-Build Multiple", "Value Hunter Level"]):
            col.metric(label, "—")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 2. BANKING & CASH FLOW ───────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>🏦 Banking & Cash Flow</h2>", unsafe_allow_html=True)
    if banking:
        tab1, tab2 = st.tabs(["Global Overview", "Last Month"])
        for tab, key in zip([tab1, tab2], ["overall", "last_month"]):
            with tab:
                data = banking.get(key, {})
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Spend",    f"₹ {safe_val(data, ['spend_total'], 0):,.2f}")
                c2.metric("Total Earned",   f"₹ {safe_val(data, ['earn_total'], 0):,.2f}")
                c3.metric("Bank Accounts",  int(safe_val(data, ['num_bank_accounts'], 0)))
                c4.metric("Credit Cards",   int(safe_val(data, ['num_credit_cards'], 0)))

                st.markdown(f"<div style='margin-top:12px;color:{ACCENT};font-weight:800;'>Channel Intelligence</div>",
                            unsafe_allow_html=True)
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("UPI Spend",       f"₹ {safe_val(data, ['upi_spend_total'], 0):,.2f}")
                cc2.metric("CC Spend",        f"₹ {safe_val(data, ['cc_spend_total'], 0):,.2f}")
                cc3.metric("Primary Channel", safe_val(data, ['top_channel']))

                # ── Spend vs Earn donut ──
                spend = safe_val(data, ['spend_total'], 0)
                earn  = safe_val(data, ['earn_total'], 0)
                if spend or earn:
                    d1, d2 = st.columns(2)
                    with d1:
                        st.plotly_chart(
                            make_donut(["Spend", "Earn"], [spend, earn], "Spend vs Earn"),
                            use_container_width=True
                        )
                    with d2:
                        upi = safe_val(data, ['upi_spend_total'], 0)
                        cc  = safe_val(data, ['cc_spend_total'], 0)
                        other = max(spend - upi - cc, 0)
                        st.plotly_chart(
                            make_donut(["UPI", "Credit Card", "Other"], [upi, cc, other], "Channel Mix"),
                            use_container_width=True
                        )
    else:
        cols = st.columns(4)
        for col, label in zip(cols, ["Total Spend", "Total Earned", "Bank Accounts", "Credit Cards"]):
            col.metric(label, "—")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. PROMOTIONS SUMMARY ────────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>📢 Promotional Message Analysis</h2>", unsafe_allow_html=True)
    if promo_text:
        p = parse_promo_text(promo_text)
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Total Promos",        p["Total Messages"])
        p2.metric("Credit Card Promos",  p["CC Messages"])
        p3.metric("NBFC / Lending App",  p["NBFC/Lending"])
        p4.metric("Offers / Discounts",  p["Offers/Discounts"])
        p5.metric("Other Promos",        p["Other Promos"])

        c1, c2 = st.columns(2)
        c1.metric("Avg Limit (Last 5 CC Offers)",      p["Avg CC Limit"])
        c2.metric("Avg Limit (Last 5 Lending Apps)",   p["Avg Lending Limit"])

        # Donut of promo composition
        try:
            vals = [int(p["CC Messages"]), int(p["NBFC/Lending"]), int(p["Offers/Discounts"]), int(p["Other Promos"])]
            labels = ["Credit Card", "NBFC/Lending", "Offers/Discounts", "Other"]
            vals_nonzero = [(l, v) for l, v in zip(labels, vals) if v > 0]
            if vals_nonzero:
                lbl, val = zip(*vals_nonzero)
                _, dc = st.columns([2, 1])
                with dc:
                    st.plotly_chart(make_donut(list(lbl), list(val), "Promo Composition"), use_container_width=True)
        except Exception:
            pass
    else:
        cols = st.columns(5)
        for col, label in zip(cols, ["Total Promos", "Credit Card Promos", "NBFC / Lending App", "Offers / Discounts", "Other Promos"]):
            col.metric(label, "—")
        c1, c2 = st.columns(2)
        c1.metric("Avg Limit (Last 5 CC Offers)", "—")
        c2.metric("Avg Limit (Last 5 Lending Apps)", "—")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 4. INVESTMENT & WEALTH ───────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>📈 Investment & Wealth</h2>", unsafe_allow_html=True)
    if invest:
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Invested Value", f"₹ {safe_val(invest, ['Portfolio_Health','Total_Invested_Value'], 0):,.2f}")
        c2.metric("Dominant Asset",     safe_val(invest, ['Portfolio_Health','Dominant_Asset']))
        c3.metric("Stability Score",    safe_val(invest, ['Habit_Signal','Stability_Score']))
    else:
        cols = st.columns(3)
        for col, label in zip(cols, ["Net Invested Value", "Dominant Asset", "Stability Score"]):
            col.metric(label, "—")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 5. INSURANCE & RISK ──────────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>🛡️ Insurance & Risk</h2>", unsafe_allow_html=True)
    if insur:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Premium Liability", f"₹ {safe_val(insur, ['Total_Premium_Liability'], 0):,.2f}")
        c2.metric("Household Size",          f"{safe_val(insur, ['Identified_Household_Size'], 0)} Members")
        c3.metric("Wellness Index",          f"{safe_val(insur, ['Wellness_Engagement_Index'], 0)}%")
    else:
        cols = st.columns(3)
        for col, label in zip(cols, ["Total Premium Liability", "Household Size", "Wellness Index"]):
            col.metric(label, "—")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 6. LIFESTYLE & SHOPPING ──────────────────────────────────────────────
    st.markdown("<h2 class='section-header'>🛍️ Lifestyle & Shopping</h2>", unsafe_allow_html=True)
    if shop:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dominant Merchant",   safe_val(shop, ['Dominant_Merchant']))
        c2.metric("Weekend Spend Ratio", safe_val(shop, ['Weekend_Spend_Ratio'], 0))
        c3.metric("30d Order Velocity",  safe_val(shop, ['Latest_30d_Velocity'], 0))
        c4.metric("Brand Switch Index",  safe_val(shop, ['Aggregator_Conflict_Index','Switch_Consistency_Ratio'], 0))
    else:
        cols = st.columns(4)
        for col, label in zip(cols, ["Dominant Merchant", "Weekend Spend Ratio", "30d Order Velocity", "Brand Switch Index"]):
            col.metric(label, "—")
    st.markdown("<br>", unsafe_allow_html=True)


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Behavioral Intelligence | Sign3",
        layout="wide",
        page_icon="📊",
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 5])
    with col1:
        logo_path = os.path.join(current_dir, "sign3_logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=140)
    with col2:
        st.title("Behavioral & Financial Intelligence Dashboard")
        st.markdown(
            f"<p style='color:{TEXT_SEC};font-size:1.05rem;font-weight:600;'>"
            "AI-Powered parsing of SMS data to generate a 360° psychographic persona.</p>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── File uploader ─────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader("Upload Raw SMS CSV", type=["csv"])

    # ── Placeholder dashboard (shown before any file is processed) ────────────
    if uploaded_file is None:
        st.markdown(
            f"<div class='placeholder-card'>⬆️  Upload a CSV file above and click <b>Initialize Analysis Engine</b> to populate the dashboard.</div>",
            unsafe_allow_html=True,
        )
        # Render placeholder sections so layout is visible
        render_dashboard(None, None, None, None, None, None, None)
        return

    # ── Analyze button ────────────────────────────────────────────────────────
    if st.button("Initialize Analysis Engine"):
        with st.spinner("Analyzing data streams…"):
            try:
                df_raw = pd.read_csv(uploaded_file, low_memory=False)

                df_promo, df_rest, promo_report = analyze_promotions(df_raw)
                df_tagged = process_sms_df(df_rest)

                df_tagged["date"] = pd.to_datetime(df_tagged["date"], unit="ms", errors="coerce")
                df_raw["date"]    = pd.to_datetime(df_raw["date"],    unit="ms", errors="coerce")
                if "date" in df_promo.columns:
                    df_promo["date"] = pd.to_datetime(df_promo["date"], unit="ms", errors="coerce")

                df_trans  = analyze_transactions(df_tagged)
                df_invest = parse_investment_sms(df_raw)
                df_insur  = parse_insurance_sms(df_raw)
                df_shop   = parse_shopping_sms(df_raw)

                banking_insights = monthly_and_overall_insights(df_trans) if not df_trans.empty else {}
                invest_insights  = generate_investment_insights(df_invest)
                insur_insights   = generate_insurance_insights(df_insur)
                shop_insights    = generate_shopping_insights(df_shop)

                unified_insights = None
                if invest_insights and insur_insights and shop_insights:
                    unified_insights = generate_unified_persona(
                        df_shop, shop_insights, insur_insights, invest_insights
                    )

                render_dashboard(
                    promo_report, df_promo,
                    banking_insights, invest_insights,
                    insur_insights, shop_insights,
                    unified_insights,
                )

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
                import traceback
                st.code(traceback.format_exc(), language="python")


if __name__ == "__main__":
    main()