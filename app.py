import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import plotly.graph_objects as go
import requests

# Path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from api import analyze, SMSRequest
except ImportError as e:
    st.error("System Error: Required components are missing. Please ensure all necessary files are configured.")
    st.stop()

# ── COLOUR PALETTE (White & Blue Theme) ────────────────────────────────────
BG_MAIN   = "#FFFFFF"
BG_CARD   = "#F8FAFC"
BORDER    = "#E2E8F0"
ACCENT    = "#2563EB"
TEXT_PRI  = "#0F172A"
TEXT_SEC  = "#475569"
VAL_COL   = "#1D4ED8"
BTN_COL   = "#3B82F6"
BTN_HOV   = "#2563EB"

GLOBAL_CSS = f"""
<style>
/* HIDE STREAMLIT HEADER AND FOOTER */
#MainMenu {{visibility: hidden;}}
header {{visibility: hidden;}}
footer {{visibility: hidden;}}

.stApp {{
    background-color: {BG_MAIN};
    color: {TEXT_PRI};
}}
div[data-testid="metric-container"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    padding: 1.1rem !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
}}
[data-testid="stMetricLabel"] * {{
    color: {TEXT_SEC} !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}}
[data-testid="stMetricValue"] * {{
    color: {VAL_COL} !important;
    font-weight: 800 !important;
    font-size: 1.65rem !important;
}}
.section-header {{
    border-bottom: 2px solid {BORDER};
    padding-bottom: 8px;
    margin-top: 2rem;
    margin-bottom: 20px;
    color: {ACCENT};
    font-weight: 800;
    font-size: 1.4rem;
}}
.sub-header {{
    color: {TEXT_SEC};
    font-weight: 700;
    font-size: 1.15rem;
    margin-bottom: 1rem;
    margin-top: 1rem;
}}

/* BUTTON STYLING */
.stButton>button[kind="primary"] {{
    font-weight: 700 !important;
    font-size: 1.15rem !important;
    border-radius: 8px !important;
    padding: 0.75rem 1.5rem !important;
    width: 100%;
    transition: all 0.2s ease-in-out;
}}
.stButton>button[kind="primary"]:hover {{
    transform: translateY(-2px);
}}

/* DRAG AND DROP STYLING */
[data-testid="stFileUploadDropzone"] {{
    background-color: {BG_CARD} !important;
    border: 2px dashed {ACCENT} !important;
    border-radius: 12px !important;
    padding: 2.5rem !important;
    margin-bottom: 1.5rem !important;
    transition: all 0.2s ease-in-out;
}}
[data-testid="stFileUploadDropzone"]:hover {{
    background-color: #EFF6FF !important;
    border-color: {BTN_HOV} !important;
}}
[data-testid="stFileUploader"] {{
    background-color: transparent !important;
    border: none !important;
}}

/* TAB BOX STYLING */
button[data-baseweb="tab"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    margin-right: 8px !important;
    margin-bottom: 8px !important;
    transition: all 0.2s ease-in-out !important;
}}
button[data-baseweb="tab"]:hover {{
    background-color: #EFF6FF !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    border-color: {BTN_HOV} !important;
    color: {TEXT_PRI} !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    background-color: {BTN_COL} !important;
}}
button[data-baseweb="tab"][aria-selected="true"] * {{
    color: white !important;
}}

/* REDUCE TOP PADDING */
.block-container {{
    padding-top: 0rem !important;
}}
</style>
"""

# Helper to safely format currency
def fmt_currency(val):
    if val is None or pd.isna(val):
        return "N/A"
    return f"₹ {float(val):,.2f}"

def make_donut(labels, values, title, colors=None):
    if not colors:
        colors = ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo='percent+label',
        insidetextorientation="radial",
        textfont=dict(size=13, color=TEXT_PRI, weight="bold")
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT_PRI, size=18, weight="bold"), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(color=TEXT_SEC), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=10, l=10, r=10), height=350,
    )
    return fig

def make_bar_chart(x, y, title, xlabel="", ylabel="", color="#3B82F6", orientation="v"):
    if orientation == "h":
        fig = go.Figure(go.Bar(
            y=x, x=y, orientation='h', marker_color=color,
            text=[f"{v:,.0f}" if isinstance(v, (int, float)) else str(v) for v in y],
            textposition="outside",
            textfont=dict(color=TEXT_PRI, size=13, weight="bold"),
        ))
        safe_y = [v for v in y if isinstance(v, (int, float))]
        y_max = max(safe_y) if safe_y else 0
        fig.update_layout(
            title=dict(text=title, font=dict(color=TEXT_PRI, size=18, weight="bold"), x=0.5),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title=xlabel, tickfont=dict(color=TEXT_SEC, size=12), gridcolor=BORDER, range=[0, y_max*1.15 if y_max > 0 else 1]),
            yaxis=dict(title=ylabel, tickfont=dict(color=TEXT_SEC, size=12), gridcolor=BORDER),
            margin=dict(t=50, b=40, l=40, r=10), height=350,
        )
    else:
        fig = go.Figure(go.Bar(
            x=x, y=y, marker_color=color,
            text=[f"{v:,.0f}" if isinstance(v, (int, float)) else str(v) for v in y],
            textposition="outside",
            textfont=dict(color=TEXT_PRI, size=13, weight="bold"),
        ))
        safe_y = [v for v in y if isinstance(v, (int, float))]
        y_max = max(safe_y) if safe_y else 0
        fig.update_layout(
            title=dict(text=title, font=dict(color=TEXT_PRI, size=18, weight="bold"), x=0.5),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title=xlabel, tickfont=dict(color=TEXT_SEC, size=12), gridcolor=BORDER),
            yaxis=dict(title=ylabel, tickfont=dict(color=TEXT_SEC, size=12), gridcolor=BORDER, range=[0, y_max*1.15 if y_max > 0 else 1]),
            margin=dict(t=50, b=40, l=40, r=10), height=350,
        )
    return fig


def render_dashboard(data: dict):
    tab_overview, tab_banking, tab_lifestyle, tab_wealth, tab_loans, tab_promos, tab_json = st.tabs([
        "📊 Overview & Persona",
        "🏦 Banking & Cash Flow",
        "🛍️ Shopping",
        "📈 Wealth & Insurance",
        "💳 Loans",
        "📢 Promos",
        "🧑‍💻 Data Details"
    ])

    meta = data.get("meta") or {}
    persona = data.get("unified_persona") or {}
    banking = data.get("banking_insights") or {}
    invest = data.get("investment_insights") or {}
    insur = data.get("insurance_insights") or {}
    shop = data.get("shopping_insights") or {}
    loan = data.get("loan_insights") or {}
    promo = data.get("promotional_insights") or {}

    # ──────────────────────────────────────────────────────────────────
    # OVERVIEW TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_overview:
        st.markdown("<div class='section-header'>📊 Data Overview</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        sms_counts = meta.get('sms_counts', {})
        c1.metric("Total SMS Processed", f"{sms_counts.get('total_received', 0):,}")
        c2.metric("Unique Senders", f"{meta.get('unique_senders', 0):,}")
        date_range = meta.get("date_range") or {}
        c3.metric("From Date", date_range.get("from", "N/A"))
        c4.metric("To Date", date_range.get("to", "N/A"))

        st.markdown("<hr style='border:1px solid #E2E8F0'>", unsafe_allow_html=True)
        col_bar, col_persona = st.columns(2)

        with col_bar:
            # SMS Categorization Breakdown
            labels, vals = [], []
            for k, v in sms_counts.items():
                if k != "total_received" and v > 0:
                    labels.append(k.replace("_", " ").title())
                    vals.append(v)
            if vals:
                fig_sc = make_bar_chart(labels, vals, "SMS Recognition Categories", color="#3B82F6", orientation="h")
                st.plotly_chart(fig_sc, width='content')

        with col_persona:
            # Persona View
            if persona:
                st.markdown("<div class='section-header' style='margin-top:0;'>👤 Unified Psychographic Persona</div>", unsafe_allow_html=True)
                pc1, pc2 = st.columns(2)
                pc1.metric("User Segment", persona.get("segment", "N/A"))
                pc2.metric("Disposable Income Health", persona.get("disposable_income_health", "N/A"))
                scores = persona.get("scores") or {}
                pc1.metric("Future-Proof Score", f"{scores.get('future_proof_score', 0):.2f}")
                pc2.metric("Burn-to-Build Multiple", f"{scores.get('burn_to_build_multiple', 0):.2f}")

    # ──────────────────────────────────────────────────────────────────
    # BANKING TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_banking:
        st.markdown("<div class='section-header'>🏦 Cash Flow Overview</div>", unsafe_allow_html=True)
        cash_flow = banking.get("cash_flow") or {}
        overall_cf = cash_flow.get("overall") or {}
        lm_cf = cash_flow.get("last_month") or {}

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Spend", fmt_currency(overall_cf.get("spend", {}).get("total")))
        c2.metric("Overall Earned", fmt_currency(overall_cf.get("earn", {}).get("total")))
        c3.metric("Last Month Spend", fmt_currency(lm_cf.get("spend", {}).get("total")))
        c4.metric("Last Month Earned", fmt_currency(lm_cf.get("earn", {}).get("total")))

        st.markdown("<hr style='border:1px solid #E2E8F0'>", unsafe_allow_html=True)
        ch_col1, ch_col2 = st.columns(2)
        with ch_col1:
            spend_val = overall_cf.get("spend", {}).get("total", 0)
            earn_val = overall_cf.get("earn", {}).get("total", 0)
            if spend_val or earn_val:
                fig = make_donut(["Total Spend", "Total Earned"], [spend_val, earn_val], "Overall Spend vs Earn", colors=["#EF4444", "#10B981"])
                st.plotly_chart(fig, width='content')
            
        with ch_col2:
            channels = (banking.get("channel_breakdown") or {}).get("overall") or {}
            if channels:
                upi_spend = channels.get("upi", {}).get("spend_total", 0)
                cc_spend = channels.get("credit_card", {}).get("spend_total", 0)
                other_spend = max(spend_val - (upi_spend + cc_spend), 0)
                fig2 = make_bar_chart(
                    x=["UPI", "Credit Card", "Other"],
                    y=[upi_spend, cc_spend, other_spend],
                    title="Channel Spend Breakdown",
                    ylabel="Amount (₹)"
                )
                st.plotly_chart(fig2, width='content')

        st.markdown("<div class='section-header'>💳 Accounts & Cards</div>", unsafe_allow_html=True)
        accounts = banking.get("accounts") or {}
        bank_accs = accounts.get("bank_accounts") or {}
        cc_accs = accounts.get("credit_cards") or {}

        a1, a2 = st.columns(2)
        with a1:
            st.markdown(f"**Bank Accounts:** {bank_accs.get('total', 0)}")
            for b in bank_accs.get("details", []):
                st.info(f"🏦 **Savings Account ending in {b.get('account_number')}** | Bal: {fmt_currency(b.get('balance', {}).get('value'))}")

        with a2:
            st.markdown(f"**Credit Cards:** {cc_accs.get('total', 0)}")
            for c in cc_accs.get("details", []):
                bal = c.get('balance', {}).get('value')
                limit = c.get('credit_limit', {}).get('value')
                bill = c.get('last_bill', {}).get('value')
                util = c.get('utilisation_pct')
                
                util_str = f" | Utilisation: **{util*100:.1f}%**" if util is not None else ""
                
                st.success(
                    f"💳 **Credit Card ending in {c.get('credit_card_number')}**\n\n"
                    f"**Available Balance:** {fmt_currency(bal)}\n\n"
                    f"**Credit Limit:** {fmt_currency(limit)}\n\n"
                    f"**Last Bill Amount:** {fmt_currency(bill)}{util_str}"
                )


    # ──────────────────────────────────────────────────────────────────
    # LIFESTYLE TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_lifestyle:
        st.markdown("<div class='section-header'>🛍️ Shopping Behavior</div>", unsafe_allow_html=True)
        if shop:
            merch = shop.get("merchants") or {}
            beh = shop.get("behavior") or {}
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Dominant Merchant", merch.get("dominant", "N/A"))
            c2.metric("Merchant Switches", merch.get("merchants_switch_count", 0))
            c3.metric("Impulse Purchase Index", f"{beh.get('impulse_purchase_index_pct', 0)}%")
            c4.metric("Refund Rate", f"{beh.get('refund_rate_pct', 0)}%")

            st.markdown("<hr style='border:1px solid #E2E8F0'>", unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            
            with sc1:
                tk = shop.get("avg_ticket_by_instrument") or {}
                if tk:
                    bank_upi = tk.get("bank_upi", 0)
                    cc = tk.get("credit_card", 0)
                    fig_tk = make_bar_chart(["Bank/UPI", "Credit Card"], [bank_upi, cc], "Avg Ticket Size", ylabel="₹")
                    st.plotly_chart(fig_tk, width='content')

            with sc2:
                mb = shop.get("monthly_burn_l3m") or {}
                if mb:
                    months = list(mb.keys())
                    burns = list(mb.values())
                    fig_mb = make_bar_chart(months, burns, "Monthly Burn (L3M)", ylabel="₹", color="#8B5CF6")
                    st.plotly_chart(fig_mb, width='content')

    # ──────────────────────────────────────────────────────────────────
    # WEALTH & INSURANCE TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_wealth:
        i1, i2 = st.columns(2)
        with i1:
            st.markdown("<div class='section-header'>📈 Investments</div>", unsafe_allow_html=True)
            if invest:
                pf = invest.get("portfolio") or {}
                act = invest.get("activity") or {}
                rel = invest.get("reliability") or {}
                st.metric("Total Invested", fmt_currency(pf.get("total_invested")))
                st.metric("Dominant Asset", pf.get("dominant_asset", "N/A"))
                st.metric("Stability Score", act.get("stability_score", "N/A"))
                
                wallet = pf.get("wallet_share") or {}
                if wallet:
                    labels = [k.replace("_pct", "").replace("_", " ").title() for k in wallet.keys()]
                    vals = list(wallet.values())
                    fig_w = make_donut(labels, vals, "Wallet Share")
                    st.plotly_chart(fig_w, width='content')


        with i2:
            st.markdown("<div class='section-header'>🛡️ Insurance</div>", unsafe_allow_html=True)
            if insur:
                cov = insur.get("coverage") or {}
                hh = insur.get("household") or {}
                st.metric("Total Premium Liability", fmt_currency(cov.get("total_premium_liability")))
                st.metric("Identified HH Size", hh.get("size", "N/A"))
                st.metric("Avg Cost Per Member", fmt_currency(hh.get("avg_cost_per_member")))

    # ──────────────────────────────────────────────────────────────────
    # LOANS & CREDIT TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_loans:
        st.markdown("<div class='section-header'>💳 Loan & Credit Activity</div>", unsafe_allow_html=True)
        if loan:
            delinq = loan.get("delinquency") or {}
            c1, c2, c3 = st.columns(3)
            c1.metric("Delinquent (30d)", delinq.get("cnt_delinquent_c30", 0))
            c2.metric("Delinquent (60d)", delinq.get("cnt_delinquent_c60", 0))
            c3.metric("Primary Loan EMI", fmt_currency(loan.get("primary_loan_emi")))

            cred = loan.get("credit") or {}
            if cred.get("flag"):
                st.markdown("<div class='sub-header'>Credit Limits Detected</div>", unsafe_allow_html=True)
                st.write(f"**Limit Decrease Notifications:** {cred.get('limit_decrease')}")
                st.write(f"**Limit Increase Notifications:** {cred.get('limit_increase')}")
                st.write("**Identified Accounts:**")
                for acc in cred.get("accounts", []):
                    st.info(f"**Account ID:** {acc.get('account_id')} | EMI: {fmt_currency(acc.get('emi'))} | Due: {acc.get('emi_latest_duedate')}")

    # ──────────────────────────────────────────────────────────────────
    # PROMOTIONS TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_promos:
        st.markdown("<div class='section-header'>📢 Promotional Insights</div>", unsafe_allow_html=True)
        if promo:
            st.metric("Total Promo Messages", promo.get("total_messages", 0))
            brk = promo.get("breakdown") or {}
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Credit Card", brk.get("credit_card", 0))
            c2.metric("Offer/Discount", brk.get("offer_or_discount", 0))
            c3.metric("Lending App", brk.get("lending_app", 0))
            c4.metric("Other", brk.get("other", 0))
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                if brk:
                    fig_p = make_donut(
                        ["Credit Card", "Offers", "Lending Apps", "Other"],
                        [brk.get("credit_card",0), brk.get("offer_or_discount",0), brk.get("lending_app",0), brk.get("other",0)],
                        "Promo Breakdown"
                    )
                    st.plotly_chart(fig_p, width='content')
                    
            with p_col2:
                lim = promo.get("avg_limit_offers") or {}
                st.markdown("<div class='sub-header'>Avg Limits Offered</div>", unsafe_allow_html=True)
                st.info(f"**Avg CC Limit Offered:** {fmt_currency(lim.get('credit_card_last5'))}")
                st.info(f"**Avg Lending Limit Offered:** {fmt_currency(lim.get('lending_app_last5'))}")

    # ──────────────────────────────────────────────────────────────────
    # RAW JSON TAB
    # ──────────────────────────────────────────────────────────────────
    with tab_json:
        st.markdown("<div class='section-header'>🧑‍💻 Processed Records</div>", unsafe_allow_html=True)
        st.json(data)


def main():
    st.set_page_config(
        page_title="Behavioral Intelligence | Sign3",
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="collapsed",
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 6])
    with col1:
        logo_path = os.path.join(current_dir, "sign3_logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=120)
    with col2:
        st.markdown(f"<h1 style='color:{ACCENT};margin-bottom:0px;'>Behavioral & Financial Intelligence Dashboard</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:{TEXT_SEC};font-size:1.1rem;font-weight:500;margin-top:0px;'>"
            "AI-Powered parsing of SMS data to generate a 360° psychographic persona.</p>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:1px solid #E2E8F0'>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload SMS Data File (.csv)", type=["csv"], label_visibility="collapsed", help="Only accept CSV files containing parsed SMS messages.")

    if uploaded_file is None:
        return

    if st.button("Analyze Data", type="primary", width='content'):
        with st.spinner("Processing records securely..."):
            try:
                # Read CSV
                df_raw = pd.read_csv(uploaded_file, low_memory=False)
                df_raw = df_raw.replace({np.nan: None})
                sms_data = df_raw.to_dict(orient="records")
                # print(df_raw.shape)
                result = None
                
                # 1. Background Engine processing 
                try:
                    response = requests.post("http://localhost:5004/analyze", json={"sms_data": sms_data}, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        st.toast("Data successfully processed!", icon="✅")
                    else:
                        pass # Silently fallback to native
                except requests.exceptions.RequestException:
                    pass # Silently fallback to native
                
                # 2. Native Processing Fallback
                if not result:
                    request_obj = SMSRequest(sms_data=sms_data)
                    result = analyze(request_obj)

                if result:
                    render_dashboard(result)
                else:
                    st.error("Engine failed to return results from the current dataset.")
            except Exception as e:
                st.error("Processing issue detected. Please check file formatting.")
                st.exception(e) 

if __name__ == "__main__":
    main()