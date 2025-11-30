import pandas as pd
import numpy as np

def analyze_option_chain(csv_path, spot_price=None):
    """
    Analyzes the NIFTY/BANKNIFTY End-of-Day Option Chain data.
    """
    df = pd.read_csv(csv_path)
    df = df.sort_values(by='Strike').reset_index(drop=True)

    # --- Auto-detect Spot Price ---
    if spot_price is None:
        spot_price = df.loc[(df['Call OI'] + df['Put OI']).idxmax()]['Strike']

    # --- Module 1: Basic Summary Dashboard ---
    total_put_oi = df['Put OI'].sum()
    total_call_oi = df['Call OI'].sum()
    pcr_oi = total_put_oi / total_call_oi if total_call_oi else 0
    pcr_volume = df['Put Volume'].sum() / df['Call Volume'].sum() if df['Call Volume'].sum() else 0
    net_oi_change = df['Call OI Change'].sum() - df['Put OI Change'].sum()
    highest_oi_call_strike = df.loc[df['Call OI'].idxmax()]['Strike']
    highest_oi_put_strike = df.loc[df['Put OI'].idxmax()]['Strike']
    highest_volume_call_strike = df.loc[df['Call Volume'].idxmax()]['Strike']
    highest_volume_put_strike = df.loc[df['Put Volume'].idxmax()]['Strike']

    summary_data = {
        'Metric': ['Current Spot', 'Total Put OI', 'Total Call OI', 'PCR (OI)', 'PCR (Volume)',
                   'Net OI Change', 'Highest OI Call Strike', 'Highest OI Put Strike',
                   'Highest Volume Call Strike', 'Highest Volume Put Strike'],
        'Value': [spot_price, total_put_oi, total_call_oi, pcr_oi, pcr_volume,
                  net_oi_change, highest_oi_call_strike, highest_oi_put_strike,
                  highest_volume_call_strike, highest_volume_put_strike]
    }
    summary_df = pd.DataFrame(summary_data)

    # --- Module 2: Maximum Gamma Pain Strike (MGP) ---
    df['MGP Score'] = abs(df['Call Gamma'] * 100) * abs(df['Put Gamma'] * 100) * \
                      abs(df['Call Gamma'] * 100 - df['Put Gamma'] * 100) * \
                      (df['Call OI Change'] + df['Put OI Change'])
    mgp_strike = df.loc[df['MGP Score'].idxmax()]['Strike']

    # --- Module 3: Call-Writer Pain Strike (CWP) & Put-Writer Pain Strike (PWP) ---
    df['CWP Score'] = (df['Call Gamma'] * 100) * abs(df['Call Delta'].diff().fillna(0)) * df['Call OI Change']
    df['PWP Score'] = (df['Put Gamma'] * 100) * abs(df['Put Delta'].diff().fillna(0)) * df['Put OI Change']
    cwp_strike = df.loc[df['CWP Score'].idxmax()]['Strike']
    pwp_strike = df.loc[df['PWP Score'].idxmax()]['Strike']

    # --- Module 4: Dealer Theta-Box & Comfort Zone ---
    upper_wall = cwp_strike
    lower_wall = pwp_strike
    cwp_gamma = df.loc[df['Strike'] == cwp_strike, 'Call Gamma']
    pwp_gamma = df.loc[df['Strike'] == pwp_strike, 'Put Gamma']
    total_gamma = df['Call Gamma'].sum() + df['Put Gamma'].sum()
    box_strength = (cwp_gamma.iloc[0] + pwp_gamma.iloc[0]) / total_gamma if total_gamma and not cwp_gamma.empty and not pwp_gamma.empty else 0
    cwp_score = df.loc[df['Strike'] == cwp_strike, 'CWP Score'].iloc[0]
    pwp_score = df.loc[df['Strike'] == pwp_strike, 'PWP Score'].iloc[0]
    pain_ratio = cwp_score / pwp_score if pwp_score else np.inf

    # --- Module 5: One-Sided Explosion Predictor ---
    verdict = ""
    verdict_color = "black"
    if box_strength > 0.45 and 0.6 <= pain_ratio <= 1.7:
        verdict = "SIDEWAYS THETA EXPIRY INSIDE BOX"
        verdict_color = "blue"
    elif pain_ratio > 2.0:
        verdict = "UPSIDE ONE-SIDED GAMMA SQUEEZE IMMINENT"
        verdict_color = "lime"
    elif pain_ratio < 0.5:
        verdict = "DOWNSIDE ONE-SIDED GAMMA SQUEEZE IMMINENT"
        verdict_color = "red"
    else:
        verdict = "DIRECTIONAL BIAS – BOX UNDER PRESSURE"

    # --- Module 6: Delta Area Zones ---
    upper_delta_area = (df.loc[(df['Strike'] > spot_price + 100) & (df['Strike'] <= spot_price + 600), 'Call Gamma'] * 100 -
                        df.loc[(df['Strike'] > spot_price + 100) & (df['Strike'] <= spot_price + 600), 'Put Gamma'] * 100).sum()
    lower_delta_area = (df.loc[(df['Strike'] >= spot_price - 600) & (df['Strike'] < spot_price - 100), 'Put Gamma'] * 100 -
                        df.loc[(df['Strike'] >= spot_price - 600) & (df['Strike'] < spot_price - 100), 'Call Gamma'] * 100).sum()
    upper_delta_color = "green" if upper_delta_area > 8_000_000 else "black"
    lower_delta_color = "red" if lower_delta_area > 8_000_000 else "black"

    # --- Module 7: Dynamic Delta Skew Bands ---
    near_call_gamma = df.loc[(df['Strike'] >= spot_price - 200) & (df['Strike'] <= spot_price + 200), 'Call Gamma'].sum()
    near_put_gamma = df.loc[(df['Strike'] >= spot_price - 200) & (df['Strike'] <= spot_price + 200), 'Put Gamma'].sum()
    mid_call_gamma = df.loc[(df['Strike'] > spot_price + 200) & (df['Strike'] <= spot_price + 500), 'Call Gamma'].sum()
    mid_put_gamma = df.loc[(df['Strike'] > spot_price + 200) & (df['Strike'] <= spot_price + 500), 'Put Gamma'].sum()
    far_call_gamma = df.loc[(df['Strike'] > spot_price + 500) & (df['Strike'] <= spot_price + 1000), 'Call Gamma'].sum()
    far_put_gamma = df.loc[(df['Strike'] > spot_price + 500) & (df['Strike'] <= spot_price + 1000), 'Put Gamma'].sum()
    near_gamma_ratio = near_call_gamma / near_put_gamma if near_put_gamma else np.inf
    mid_gamma_ratio = mid_call_gamma / mid_put_gamma if mid_put_gamma else np.inf
    far_gamma_ratio = far_call_gamma / far_put_gamma if far_put_gamma else np.inf
    far_gamma_color = "darkgreen" if far_gamma_ratio > 2.0 else "black"

    # --- Module 8: Gamma Slope & Acceleration ---
    gamma_diff = (df['Call Gamma'] * 100 - df['Put Gamma'] * 100)
    strikes = df['Strike']
    gamma_slope = np.polyfit(strikes, gamma_diff, 1)[0]
    gamma_slope_color = "lime" if gamma_slope > 30000 else "black"

    # --- Module 9: Top 5 Gamma Walls Table ---
    top_5_call_gamma = df.nlargest(5, 'Call Gamma')[['Strike', 'Call Gamma', 'Call OI', 'Call OI Change']]
    top_5_put_gamma = df.nlargest(5, 'Put Gamma')[['Strike', 'Put Gamma', 'Put OI', 'Put OI Change']]

    # --- Module 10: Final Institutional Verdict Panel ---
    final_verdict = f"""
    DEALER COMFORT BOX: {lower_wall} – {upper_wall} | BOX STRENGTH: {'STRONG' if box_strength > 0.45 else 'WEAK'}
    CALL WRITERS TRAPPED ABOVE {cwp_strike} | PAIN RATIO {pain_ratio:.2f} → {verdict}
    MGP NUCLEAR TRIGGER: {mgp_strike} | UPPER DELTA AREA: +{upper_delta_area/1_000_000:.1f}M ({'EXTREME CALL OVERLOAD' if upper_delta_area > 8_000_000 else 'NORMAL'})
    FINAL CALL: AGGRESSIVELY {'LONG' if pain_ratio > 2.0 else 'SHORT' if pain_ratio < 0.5 else 'NEUTRAL'} ABOVE {cwp_strike if pain_ratio > 2.0 else pwp_strike}
    """

    # --- What Each Module Means ---
    explanations = {
        "Basic Summary Dashboard": "Overall market sentiment and key levels.",
        "Maximum Gamma Pain Strike (MGP)": "The strike where the most pain is felt by option sellers, a potential turning point.",
        "Call-Writer Pain Strike (CWP) & Put-Writer Pain Strike (PWP)": "Strikes where call or put writers are most vulnerable.",
        "Dealer Theta-Box & Comfort Zone": "The range where market makers are comfortable, and theta decay is maximized.",
        "One-Sided Explosion Predictor": "Predicts the likelihood of a strong directional move.",
        "Delta Area Zones": "Measures the amount of trapped capital on either side of the market.",
        "Dynamic Delta Skew Bands": "Shows the skew of bullish vs. bearish bets at different distances from the spot price.",
        "Gamma Slope & Acceleration": "Measures the rate of change of directional risk.",
        "Top 5 Gamma Walls Table": "The most significant levels of support and resistance based on gamma.",
        "Final Institutional Verdict Panel": "A summary of the most critical insights for immediate trading decisions."
    }

    # --- HTML Output ---
    html = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .module {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }}
                .header {{ font-weight: bold; font-size: 1.2em; }}
                .verdict-panel {{ border: 2px solid black; padding: 15px; font-size: 1.1em; font-weight: bold; background-color: #f0f0f0; }}
            </style>
        </head>
        <body>
            <h1>NIFTY/BANKNIFTY End-of-Day Option Chain Analysis</h1>

            <div class="module">
                <div class="header">What Each Module Means</div>
                <ul>
                    {"".join(f"<li><b>{module}</b>: {desc}</li>" for module, desc in explanations.items())}
                </ul>
            </div>

            <div class="verdict-panel">
                <div class="header">Final Institutional Verdict Panel</div>
                <pre>{final_verdict}</pre>
            </div>

            <div class="module">
                <div class="header">Basic Summary Dashboard</div>
                {summary_df.to_html(index=False)}
            </div>

            <div class="module">
                <div class="header">Maximum Gamma Pain Strike (MGP)</div>
                <p><b>MGP Nuclear Trigger:</b> {mgp_strike}</p>
            </div>

            <div class="module">
                <div class="header">Call-Writer Pain Strike (CWP) & Put-Writer Pain Strike (PWP)</div>
                <p><b>CWP Strike:</b> {cwp_strike}</p>
                <p><b>PWP Strike:</b> {pwp_strike}</p>
            </div>

            <div class="module">
                <div class="header">Dealer Theta-Box & Comfort Zone</div>
                <p><b>Upper Wall:</b> {upper_wall}, <b>Lower Wall:</b> {lower_wall}</p>
                <p><b>Box Strength:</b> {box_strength:.2%}</p>
                <p><b>Pain Ratio:</b> {pain_ratio:.2f}</p>
            </div>

            <div class="module">
                <div class="header">One-Sided Explosion Predictor</div>
                <p style="color:{verdict_color};">{verdict}</p>
            </div>

            <div class="module">
                <div class="header">Delta Area Zones</div>
                <p style="color:{upper_delta_color};"><b>Upper Delta Area:</b> {upper_delta_area:,.0f}</p>
                <p style="color:{lower_delta_color};"><b>Lower Delta Area:</b> {lower_delta_area:,.0f}</p>
            </div>

            <div class="module">
                <div class="header">Dynamic Delta Skew Bands</div>
                <p><b>Near (±200):</b> {near_gamma_ratio:.2f}</p>
                <p><b>Mid (+200 to +500):</b> {mid_gamma_ratio:.2f}</p>
                <p style="color:{far_gamma_color};"><b>Far (+500 to +1000):</b> {far_gamma_ratio:.2f}</p>
            </div>

            <div class="module">
                <div class="header">Gamma Slope & Acceleration</div>
                <p style="color:{gamma_slope_color};"><b>Gamma Slope:</b> {gamma_slope:,.0f}</p>
            </div>

            <div class="module">
                <div class="header">Top 5 Gamma Walls</div>
                <h4>Call Gamma Walls</h4>
                {top_5_call_gamma.to_html(index=False)}
                <h4>Put Gamma Walls</h4>
                {top_5_put_gamma.to_html(index=False)}
            </div>
        </body>
    </html>
    """
    with open("option_chain_analysis.html", "w") as f:
        f.write(html)

    # --- Console Output ---
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
        print("--- What Each Module Means ---")
        for module, desc in explanations.items():
            print(f"- **{module}**: {desc}")

        print("\n--- Final Institutional Verdict Panel ---")
        print(final_verdict)

        print("\n--- Basic Summary Dashboard ---")
        print(summary_df.to_string(index=False))

        print(f"\n--- Maximum Gamma Pain Strike (MGP): {mgp_strike} ---")

        print(f"\n--- Call-Writer Pain Strike (CWP): {cwp_strike} & Put-Writer Pain Strike (PWP): {pwp_strike} ---")

        print("\n--- Dealer Theta-Box & Comfort Zone ---")
        print(f"Upper Wall: {upper_wall}, Lower Wall: {lower_wall}, Box Strength: {box_strength:.2%}, Pain Ratio: {pain_ratio:.2f}")

        print("\n--- One-Sided Explosion Predictor ---")
        print(verdict)

        print("\n--- Delta Area Zones ---")
        print(f"Upper Delta Area: {upper_delta_area:,.0f}, Lower Delta Area: {lower_delta_area:,.0f}")

        print("\n--- Dynamic Delta Skew Bands ---")
        print(f"Near: {near_gamma_ratio:.2f}, Mid: {mid_gamma_ratio:.2f}, Far: {far_gamma_ratio:.2f}")

        print("\n--- Gamma Slope & Acceleration ---")
        print(f"Gamma Slope: {gamma_slope:,.0f}")

        print("\n--- Top 5 Gamma Walls (Call) ---")
        print(top_5_call_gamma.to_string(index=False))

        print("\n--- Top 5 Gamma Walls (Put) ---")
        print(top_5_put_gamma.to_string(index=False))

if __name__ == '__main__':
    analyze_option_chain('NIFTY_2025-12-02_option_chain_.csv')
