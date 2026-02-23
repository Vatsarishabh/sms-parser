import argparse
import os
import sys
import pandas as pd

# Add the parent directory to sys.path to allow importing from the Parser package
parser_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(parser_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

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
    print(f"Import Error: {e}")
    sys.exit(1)

def format_integrated_report(promo_stats, insights, inv_insights, ins_insights, shop_insights, unified_insights):
    """Generates a professional, simple, and detailed master report covering all financial domains."""
    report = []
    
    def safe_f(val):
        """Helper to return 0.0 for nan/None and format correctly."""
        try:
            if pd.isna(val) or val is None: return 0.0
            return float(val)
        except:
            return 0.0

    report.append("=" * 70)
    report.append("  MASTER FINANCIAL INTELLIGENCE REPORT: 360-DEGREE VIEW")
    report.append("=" * 70)

    # 1. PROMOTIONAL INSIGHTS
    report.append("\n1. PROMOTIONAL AND LENDING OFFERS")
    report.append("-" * 70)
    report.append(promo_stats if promo_stats else "No promotional data analyzed.")

    # 2. BANKING AND CASH FLOW
    report.append("\n2. BANKING AND CASH FLOW INTELLIGENCE")
    report.append("-" * 70)
    periods = {"overall": "GLOBAL OVERVIEW", "last_month": "LAST MONTH"}
    
    for key, title in periods.items():
        data = insights.get(key, {})
        cc_count = int(safe_f(data.get('num_credit_cards', 0)))
        
        report.append(f"\n[ {title} ]")
        report.append(f"  - Accounts Hooked     : {int(safe_f(data.get('num_bank_accounts', 0)))} Bank A/Cs | {cc_count} Credit Cards")
        report.append(f"  - Data Scope         : {insights.get(f'{key}_rows', 0)} raw transactions analyzed")
        
        report.append(f"  CASH FLOW SUMMARY")
        report.append(f"    - Total Spend      : Rs. {safe_f(data.get('spend_total', 0)):>13,.2f} ({int(safe_f(data.get('spend_txn_count', 0)))} txns)")
        report.append(f"    - Average Spend    : Rs. {safe_f(data.get('avg_spend_per_txn', 0)):>13,.2f}")
        report.append(f"    - Total Earn       : Rs. {safe_f(data.get('earn_total', 0)):>13,.2f} ({int(safe_f(data.get('earn_txn_count', 0)))} txns)")
        report.append(f"    - Average Earn     : Rs. {safe_f(data.get('avg_earn_per_txn', 0)):>13,.2f}")
        
        report.append(f"  CHANNEL PERFORMANCE")
        report.append(f"    - UPI Impact       : Rs. {safe_f(data.get('upi_spend_total', 0)):>13,.2f} ({int(safe_f(data.get('upi_spend_txn_count', 0)))} txns)")
        report.append(f"    - UPI Ticket Size  : Rs. {safe_f(data.get('upi_ticket_size', 0)):>13,.2f}")
        
        report.append(f"    - CC Utilization   : Rs. {safe_f(data.get('cc_spend_total', 0)):>13,.2f} ({int(safe_f(data.get('cc_spend_txn_count', 0)))} txns)")
        report.append(f"    - CC Ticket Size   : Rs. {safe_f(data.get('cc_ticket_size', 0)):>13,.2f}")
        report.append(f"    - Primary Channel  : {data.get('top_channel', 'N/A')}")

    # 3. INVESTMENT AND WEALTH
    if inv_insights:
        report.append("\n3. INVESTMENT AND WEALTH INTELLIGENCE")
        report.append("-" * 70)
        ph = inv_insights.get("Portfolio_Health", {})
        rs = inv_insights.get("Recency_Signal", {})
        hs = inv_insights.get("Habit_Signal", {})
        vm = inv_insights.get("Velocity_Metrics", {})
        rel = inv_insights.get("Reliability_Signals", {})

        report.append(f"  PORTFOLIO HEALTH")
        report.append(f"    - Net Invested Value: Rs. {ph.get('Total_Invested_Value', 0):>13,.2f}")
        report.append(f"    - Dominant Asset    : {ph.get('Dominant_Asset', 'N/A')}")
        share = ph.get('Asset_Wallet_Share', {})
        if share:
            report.append(f"    - Wallet Share      : {' | '.join([f'{k}: {v:.1f}%' for k, v in share.items()])}")
        
        report.append(f"  BEHAVIORAL SIGNALS")
        report.append(f"    - Last Activity    : {rs.get('Last_Activity_Date', 'N/A')} ({rs.get('Status', 'N/A')})")
        report.append(f"    - Investment Tenure: {hs.get('Total_Investment_Tenure', 'N/A')}")
        report.append(f"    - Stability Score  : {hs.get('Stability_Score', 'N/A')} (Avg Gap: {hs.get('Average_Gap_Between_Actions', 'N/A')})")
        
        report.append(f"  MANDATE AND RELIABILITY")
        report.append(f"    - Realization Rate : {rel.get('Mandate_Realization_Rate', '0%')}")
        report.append(f"    - Predicted SIP Day: {rel.get('Predicted_SIP_Date', 'N/A')}")
        report.append(f"    - Engagement Points: {rel.get('Total_Engagement_Points', 0)} verified signals")

    # 4. INSURANCE AND RISK
    if ins_insights:
        report.append("\n4. INSURANCE AND RISK COVERAGE")
        report.append("-" * 70)
        report.append(f"  POLICY HOLDINGS")
        report.append(f"    - Total Premium Liab: Rs. {ins_insights.get('Total_Premium_Liability', 0):>13,.2f}")
        report.append(f"    - Household Size    : {ins_insights.get('Identified_Household_Size', 0)} Members")
        report.append(f"    - Peak Liability Qtr: {ins_insights.get('Peak_Liability_Quarter', 'N/A')}")
        
        report.append(f"  STRATEGIC INDEX")
        report.append(f"    - Wellness Index    : {ins_insights.get('Wellness_Engagement_Index', 0):.1f}%")
        report.append(f"    - Health/Life Ratio : {ins_insights.get('Health_to_Life_Engagement_Ratio', 0):.1f}")

    # 5. LIFESTYLE AND SHOPPING
    if shop_insights:
        report.append("\n5. LIFESTYLE AND SHOPPING BEHAVIOR")
        report.append("-" * 70)
        burn = shop_insights.get("Total_Monthly_Burn_L3M", {})
        if burn:
            report.append(f"  MONTHLY BURN (L3M)")
            for m, val in burn.items():
                report.append(f"    - {m:<18}: {val}")
        
        report.append(f"  CONSUMPTION PATTERNS")
        report.append(f"    - Dominant Merchant : {shop_insights.get('Dominant_Merchant', 'N/A')}")
        report.append(f"    - Weekend Spend Rat : {shop_insights.get('Weekend_Spend_Ratio', 0):.2f}")
        report.append(f"    - Late Night Orders : {shop_insights.get('Late_Night_Order_Count', 0)} (Impulse Signal)")
        
        ac = shop_insights.get("Aggregator_Conflict_Index", {})
        report.append(f"  BEHAVIORAL SIGNALS")
        report.append(f"    - Brand Switch Index: {ac.get('Switch_Consistency_Ratio', 0):.2f}")
        report.append(f"    - Payday Velocity   : {shop_insights.get('Payday_Splurge_Velocity', 0):.2f} (Spend Stress)")
        report.append(f"    - 30d Order Velocity: {shop_insights.get('Latest_30d_Velocity', 0)} orders")

    # 6. UNIFIED PSYCHOGRAPHIC PERSONA
    if unified_insights:
        report.append("\n6. UNIFIED PSYCHOGRAPHIC PERSONA")
        report.append("-" * 70)
        up = unified_insights.get("Unified_Persona", {})
        cdm = unified_insights.get("Cross_Domain_Metrics", {})
        report.append(f"  - User Segment       : {up.get('Segment', 'N/A')}")
        report.append(f"  - Disposable Health  : {up.get('Disposable_Income_Health', 'N/A')}")
        report.append(f"  - Future-Proof Score : {cdm.get('Future_Proof_Score', 0):.1f}/100")
        report.append(f"  - Burn-to-Build Mult : {cdm.get('Burn_to_Build_Multiple', 0):.2f}")
        report.append(f"  - Value Hunter Level : {cdm.get('Value_Hunting_Intensity', '0%')}")

    report.append("\n" + "=" * 70)
    report.append("           PROCESS COMPLETED: ALL DOMAINS ANALYZED")
    report.append("=" * 70)
    
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Integrated SMS Parsing System")
    parser.add_argument("--input", type=str, required=True, help="Input SMS CSV file path")
    parser.add_argument("--output_dir", type=str, default=os.path.join(parser_dir, 'output'), help="Output directory")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        sys.exit(1)

    print(f"🚀 Initializing Analysis Engine on {os.path.basename(input_path)}...")
    df_raw = pd.read_csv(input_path, low_memory=False)

    # 1. Promotion Analysis (In-Memory Filtering)
    print("▸ Analyzing Promotions...")
    df_promo, df_rest, promo_report = analyze_promotions(df_raw)

    # 2. Categorization & Tagging
    print("▸ Tagging & Categorizing...")
    df_tagged = process_sms_df(df_rest)
    
    # 3. Domain Analysis Branching
    print("▸ Running Domain Extractors...")
    # Standardize dates for all extractors
    df_tagged['date'] = pd.to_datetime(df_tagged['date'], unit='ms', errors='coerce')
    df_raw['date'] = pd.to_datetime(df_raw['date'], unit='ms', errors='coerce')

    # Parallel Execution Data Prep
    df_trans = analyze_transactions(df_tagged)
    df_invest = parse_investment_sms(df_raw)
    df_insur = parse_insurance_sms(df_raw)
    df_shop = parse_shopping_sms(df_raw)

    # 4. Insight Generation
    print("▸ Generating Intelligence Ratios...")
    banking_insights = monthly_and_overall_insights(df_trans) if not df_trans.empty else {}
    invest_insights = generate_investment_insights(df_invest)
    insur_insights = generate_insurance_insights(df_insur)
    shop_insights = generate_shopping_insights(df_shop)

    # 5. Unified Persona
    unified_insights = None
    if invest_insights and insur_insights and shop_insights:
        print("▸ Synthesizing Unified Persona...")
        unified_insights = generate_unified_persona(df_shop, shop_insights, insur_insights, invest_insights)

    # 6. Final Report Generation
    print("▸ Finalizing Master Report...")
    final_report = format_integrated_report(
        promo_report, banking_insights, invest_insights, insur_insights, shop_insights, unified_insights
    )

    # Output Management: Single Report File
    report_path = os.path.join(output_dir, 'master_financial_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(final_report)

    # OPTIONAL: Save one master analysis CSV for traceback if needed (optimized version usually skips this, but keep for usability)
    # The user said "optimized", so we strictly skip saving intermediate multi-CSVs but saving the report is required.
    
    print(final_report)
    print(f"\n✨ System Success! Complete report saved to: {report_path}")

if __name__ == "__main__":
    main()
