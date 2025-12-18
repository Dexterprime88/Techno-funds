import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

from gamma_utils import calculate_net_gamma_profile, find_zero_gamma_level, plot_gamma_profile
from data_utils import (
    process_user_format_df,
    load_data_from_standard_csv,
    generate_mock_nifty_data,
    parse_filename_dates,
    infer_spot_price
)

st.set_page_config(page_title="Net Gamma Exposure", layout="wide")

st.title("Net Gamma Exposure (GEX) Analysis")
st.markdown("""
This tool calculates the Net Gamma Exposure profile for Nifty options to identify the **Zero Gamma Level (Flip Point)**.
Upload your Option Chain CSV file to get started.
""")

# --- Sidebar Inputs ---
st.sidebar.header("Configuration")

# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload Option Chain CSV", type=["csv"])

# Contract Size
contract_size = st.sidebar.number_input("Contract Size", value=50, min_value=1)

# --- Logic ---

options_df = None
current_spot = 22000.0 # Default
inferred_expiry = None
inferred_snapshot = None

if uploaded_file is not None:
    try:
        # Read the file
        df_raw = pd.read_csv(uploaded_file)

        # Check format
        # User format has 'Call OI', 'Put OI', 'IV' (percent)
        is_user_format = 'Call OI' in df_raw.columns and 'Put OI' in df_raw.columns

        if is_user_format:
            st.success("Detected Nifty Option Chain Format.")

            # Try parsing dates from filename
            expiry_date, snapshot_date = parse_filename_dates(uploaded_file.name)

            if expiry_date:
                inferred_expiry = expiry_date
            if snapshot_date:
                inferred_snapshot = snapshot_date

            # Process Data
            # We process initially to get spot inference, but we need final user inputs for dates
            # So we might need a two-pass or just default to today if not parsed

            # 1. Ask for Dates if not parsed or allow override
            st.sidebar.subheader("Date Settings")

            default_expiry = inferred_expiry if inferred_expiry else datetime.now()
            expiry_input = st.sidebar.date_input("Expiry Date", value=default_expiry)

            # For snapshot, we usually assume "now" if live, or file time if historical.
            # Let's ask user for snapshot time? Or just use file time if available.
            # Simplification: Use file timestamp if available, else now.

            # Since data_utils needs datetime objects:
            expiry_dt = pd.to_datetime(expiry_input)
            snapshot_dt = inferred_snapshot if inferred_snapshot else pd.Timestamp.now()

            # Process
            options_df, inferred_spot_val = process_user_format_df(df_raw, expiry_dt, snapshot_dt)

            if inferred_spot_val:
                current_spot = inferred_spot_val

        else:
            st.info("Detected Standard Format (Strike, OptionType, IV, OpenInterest, ExpirationDate).")
            # Standard loader
            # We need to save to temp or read from buffer. pd.read_csv accepts buffer.
            # Re-read to reset buffer position or just use df_raw
            # Standard loader expects specific columns.
            options_df, _ = load_data_from_standard_csv(uploaded_file)
            # No spot inference in standard loader usually

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("No file uploaded. Using Mock Data for demonstration.")
    options_df = generate_mock_nifty_data(current_spot)

# --- Main Spot Input ---
# Place this after file loading so we can populate with inferred value
st.sidebar.subheader("Market Data")
spot_price_input = st.sidebar.number_input("Spot Price", value=float(current_spot), format="%.2f")

# --- Analysis ---
if options_df is not None:

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Spot Price", f"{spot_price_input:,.2f}")
    col2.metric("Contract Size", contract_size)

    # Calculate Profile
    with st.spinner("Calculating Gamma Profile..."):
        try:
            profile_df = calculate_net_gamma_profile(options_df, spot_price_input, contract_size=contract_size)
            zeros = find_zero_gamma_level(profile_df)

            if zeros:
                zero_level = zeros[0]
                col3.metric("Zero Gamma Level", f"{zero_level:,.2f}", delta=f"{zero_level - spot_price_input:,.2f}")
            else:
                col3.metric("Zero Gamma Level", "Not Found")

            # Plot
            fig = plot_gamma_profile(profile_df, spot_price_input, zeros)
            st.plotly_chart(fig, use_container_width=True)

            # Data Preview
            with st.expander("Show Profile Data"):
                st.dataframe(profile_df)

        except Exception as e:
            st.error(f"Calculation Error: {e}")

st.markdown("---")
st.caption("Powered by Techno-funds")
