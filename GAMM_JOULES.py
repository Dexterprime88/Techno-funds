import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import norm
from datetime import datetime
import re

# Page config
st.set_page_config(page_title="GAMM_JOULES", layout="wide")

st.title("GAMM_JOULES: Gamma Exposure & Flip Point")

# Sidebar inputs
st.sidebar.header("Configuration")
spot_price_input = st.sidebar.number_input("Current Spot Price", min_value=0.0, value=19000.0, step=10.0)
risk_free_rate = st.sidebar.number_input("Risk Free Rate (%)", min_value=0.0, value=10.0, step=0.1) / 100.0
days_to_expiry_fallback = st.sidebar.number_input("Days to Expiry (Fallback)", min_value=0.1, value=1.0, step=1.0)

uploaded_file = st.sidebar.file_uploader("Upload Option Chain CSV", type=["csv", "xlsx"])

# Helper functions
def calculate_gamma(S, K, T, r, sigma):
    """
    Calculate Gamma for an option using Black-Scholes.
    S: Spot Price
    K: Strike Price
    T: Time to Expiry (years)
    r: Risk-free rate
    sigma: Implied Volatility (decimal)
    """
    if T <= 0 or sigma <= 0:
        return 0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return gamma

def parse_expiry_from_instrument(instrument_str):
    """
    Attempt to parse expiry date from Instrument string.
    Expected format examples: 'BANKNIFTY25OCT43000CE', 'NIFTY 25 Oct 19000 CE'
    """
    # Try generic pattern: SYMBOL + DD + MMM + STRIKE + TYPE
    # Example: NIFTY26OCT19000CE
    match = re.search(r'([0-9]{2})([A-Z]{3})', str(instrument_str), re.IGNORECASE)
    if match:
        day_str = match.group(1)
        month_str = match.group(2)
        current_year = datetime.now().year
        # Construct date string
        date_str = f"{day_str} {month_str} {current_year}"
        try:
            expiry_date = datetime.strptime(date_str, "%d %b %Y")
            # Handle year rollover if needed (e.g. Dec to Jan) - simplified for now
            return expiry_date
        except:
            pass
    return None

def estimate_time_to_expiry(row, fallback_days):
    """
    Estimate T (years) from row data or fallback.
    """
    # Strategy 1: Parse Instrument
    if 'Instrument' in row and pd.notna(row['Instrument']):
        expiry = parse_expiry_from_instrument(row['Instrument'])
        if expiry:
            delta = expiry - datetime.now()
            days = delta.days + (delta.seconds / 86400.0)
            if days > 0:
                return days / 365.0

    # Strategy 2: Use Time Value?
    # Time Value = Option Price - Intrinsic Value.
    # Not directly T.

    # Fallback
    return fallback_days / 365.0

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Clean columns (strip spaces)
        df.columns = [c.strip() for c in df.columns]

        # Verify headers
        required_cols = ['Call Gamma', 'Call OI', 'Put Gamma', 'Put OI', 'Strike', 'IV']
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(f"Missing columns: {missing}")
            st.write("Available columns:", df.columns.tolist())
        else:
            # Data Processing
            df = df.replace('-', np.nan)
            cols_to_numeric = ['Call Gamma', 'Call OI', 'Put Gamma', 'Put OI', 'Strike', 'IV', 'Put Time Value', 'Call Time Value']
            for col in cols_to_numeric:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # 1. Net GEX per Strike
            # Assumption: Gamma in CSV is per share. OI is in shares.
            # Net GEX = (Call OI * Call Gamma) - (Put OI * Put Gamma)
            # Usually GEX is reported as notional exposure: Gamma * OI * Spot * 100
            # But "Net GEX each strike" bar chart usually just shows the raw exposure difference.
            # We will use: CallGEX - PutGEX

            df['Call GEX'] = df['Call Gamma'] * df['Call OI']
            df['Put GEX'] = df['Put Gamma'] * df['Put OI']
            df['Net GEX'] = df['Call GEX'] - df['Put GEX']

            # Display Spot Price Info
            st.info(f"Analyzing for Spot Price: {spot_price_input}")

            # Bar Chart: Net GEX by Strike
            st.subheader("Net Gamma Exposure (GEX) by Strike")

            # Filter reasonably close strikes to avoid clutter
            # e.g. +/- 10% of spot
            min_strike = spot_price_input * 0.9
            max_strike = spot_price_input * 1.1
            filtered_df = df[(df['Strike'] >= min_strike) & (df['Strike'] <= max_strike)].copy()

            fig_bar = px.bar(
                filtered_df,
                x='Strike',
                y='Net GEX',
                title=f"Net GEX by Strike (Spot: {spot_price_input})",
                color='Net GEX',
                color_continuous_scale=['red', 'green']
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # 2. Gamma Flipping Point
            st.subheader("Gamma Flipping Point Analysis")

            # Generate range of spot prices
            spots = np.linspace(spot_price_input * 0.85, spot_price_input * 1.15, 50)
            total_gex_values = []

            # We need T (Time to Expiry) for calculations
            # We take the first valid T from the dataframe or fallback
            # Assuming all options in CSV have same expiry
            sample_t = estimate_time_to_expiry(df.iloc[0], days_to_expiry_fallback)

            st.write(f"Estimated Time to Expiry (Years): {sample_t:.4f}")

            for s in spots:
                # Calculate Net GEX for the entire chain at this hypothetical spot price 's'
                # Formula: Sum( (Call OI - Put OI) * Gamma_new )
                # Note: BS Gamma is same for Call and Put

                # Vectorized calculation
                # K = df['Strike']
                # IV = df['IV'] / 100.0 (Assuming IV is in %)
                # OI_Imbalance = df['Call OI'] - df['Put OI']

                # Filter out valid rows
                calc_df = df[df['Strike'] > 0].copy()

                K_vals = calc_df['Strike'].values
                IV_vals = calc_df['IV'].values / 100.0
                OI_net = (calc_df['Call OI'] - calc_df['Put OI']).values

                # Check for zero IVs
                IV_vals = np.where(IV_vals <= 0, 0.2, IV_vals) # Default to 20% if missing

                d1 = (np.log(s / K_vals) + (risk_free_rate + 0.5 * IV_vals ** 2) * sample_t) / (IV_vals * np.sqrt(sample_t))
                gamma_vals = norm.pdf(d1) / (s * IV_vals * np.sqrt(sample_t))

                # GEX at this spot (using derived Gamma)
                # We multiply by Spot 's' to get dollar gamma? Or just sum of gammas?
                # "Gamma Exposure" is usually: Gamma * OI * Spot * 100 (contract size)
                # But here we stick to relative units.
                # Common GEX = Gamma * OI * Spot * 100 (if contracts).
                # Since we don't know if OI is contracts or shares, we'll assume shares.
                # And we'll multiply by 's' to get exposure in currency units approx.
                # Or just keep it as Gamma * OI.

                # The "Flipping Point" is the Zero crossing.
                # Multiplicative constants don't change the zero crossing.
                # So Sum(Gamma * (Call OI - Put OI)) is sufficient to find the root.

                net_gamma_total = np.sum(gamma_vals * OI_net)
                total_gex_values.append(net_gamma_total)

            # Find flip point (zero crossing)
            flip_point_idx = np.where(np.diff(np.sign(total_gex_values)))[0]
            flip_points = []
            for idx in flip_point_idx:
                # Linear interpolation for better precision
                y1 = total_gex_values[idx]
                y2 = total_gex_values[idx+1]
                x1 = spots[idx]
                x2 = spots[idx+1]
                if y1 != y2:
                    zero_x = x1 + (0 - y1) * (x2 - x1) / (y2 - y1)
                    flip_points.append(zero_x)

            # Plot Line Chart
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=spots, y=total_gex_values, mode='lines', name='Total Net GEX'))

            # Add Zero Line
            fig_line.add_hline(y=0, line_dash="dash", line_color="gray")

            # Mark Spot
            fig_line.add_vline(x=spot_price_input, line_dash="dot", line_color="blue", annotation_text="Current Spot")

            # Mark Flip Points
            for fp in flip_points:
                fig_line.add_vline(x=fp, line_color="red", annotation_text=f"Flip: {fp:.2f}")

            fig_line.update_layout(title="Gamma Flipping Point Analysis", xaxis_title="Spot Price", yaxis_title="Total Net GEX")
            st.plotly_chart(fig_line, use_container_width=True)

            if flip_points:
                st.success(f"Gamma Flip Point(s) detected at: {[round(fp, 2) for fp in flip_points]}")
            else:
                st.warning("No Gamma Flip Point detected in range.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.exception(e)

else:
    st.info("Please upload a CSV file to proceed.")
