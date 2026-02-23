import numpy as np
import pandas as pd

def generate_unified_persona(shop_data, shop, ins, inv):

    def calculate_average_monthly_burn(shop_df):
        if shop_df.empty:
            return 0.0
            
        # Ensure date is datetime for period conversion
        if not pd.api.types.is_datetime64_any_dtype(shop_df['date']):
            # Assuming ms epoch if not datetime
            shop_df['date'] = pd.to_datetime(shop_df['date'], unit='ms', errors='coerce')
            
        shop_df['net_amt'] = shop_df.apply(
            lambda x: -x['shopping_amount'] if x['shopping_is_refund'] else x['shopping_amount'],
            axis=1
        )
        shop_df['month_year'] = shop_df['date'].dt.to_period('M')
        monthly_totals = shop_df.groupby('month_year')['net_amt'].sum()
        avg_burn = monthly_totals.mean()

        return round(avg_burn, 2)


    # --- 1. The Burn-to-Build Ratio ---
    # Total annual shopping burn (estimated from L3M) vs Total Portfolio
    avg_shop_burn = calculate_average_monthly_burn(shop_data)
    monthly_inv = inv['Velocity_Metrics']['Verified_Monthly_Commitment_L3M']

    # Ratio > 1 means you spend more on lifestyle than you save in new capital
    burn_build_ratio = avg_shop_burn / monthly_inv if monthly_inv > 0 else np.inf

    # --- 2. The Responsibility Score ---
    # High Wellness Index + High Mutual Fund Share - High Impulse Index
    # This measures how 'Future-Proof' the user is.
    responsibility_score = (ins['Wellness_Engagement_Index'] +
                            inv['Portfolio_Health']['Asset_Wallet_Share'].get('Mutual Fund', 0) -
                            shop['Impulse_Purchase_Index'])

    # --- 3. Liquidity Stress Forecast ---
    # Identifying if the Predicted SIP Date clashes with Payday Splurge
    is_clashing = "High" if shop['Payday_Splurge_Velocity'] > 0.8 else "Low"

    # --- 4. Brand Agnostic Value Hunter ---
    # High Switch Ratio + High Refund Rate (indicates someone who optimizes every penny)
    value_hunter_signal = (shop['Aggregator_Conflict_Index']['Switch_Consistency_Ratio'] * 100 +
                           shop['Refund_Rate_Percentage']) / 2

    # --- Final Unified Persona Report ---
    unified_report = {
        "Unified_Persona": {
            "Segment": "The Disciplined Modernist" if responsibility_score > 100 else "The Impulse-Heavy Professional",
            "Disposable_Income_Health": "Strained" if burn_build_ratio > 10 else "Balanced"
        },
        "Cross_Domain_Metrics": {
            "Burn_to_Build_Multiple": round(float(burn_build_ratio), 2),
            "Future_Proof_Score": round(float(responsibility_score), 2),
            "Value_Hunting_Intensity": f"{value_hunter_signal:.1f}%",
            "Liquidity_Conflict_Risk": is_clashing
        }
    }

    return unified_report