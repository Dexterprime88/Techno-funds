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
    parse_filename_dates
)

st.set_page_config(page_title="Net Gamma Exposure", layout="wide")

st.title("Net Gamma Exposure (GEX) Analysis")
st.markdown("""
This tool calculates the Net Gamma Exposure profile for Nifty options to identify the **Zero Gamma Level (Flip Point)**.
**Upload multiple CSV files** (e.g., different expiries) to generate the aggregate Gamma Profile.
""")

# --- Sidebar Inputs ---
st.sidebar.header("Configuration")

# File Uploader - Allow Multiple
uploaded_files = st.sidebar.file_uploader("Upload Option Chain CSVs", type=["csv"], accept_multiple_files=True)

# Contract Size
contract_size = st.sidebar.number_input("Contract Size", value=50, min_value=1)

# --- Logic ---

options_df = None
current_spot = 22000.0 # Default fallback
inferred_spot_list = []

if uploaded_files:
    all_data_frames = []

    st.info(f"Processing {len(uploaded_files)} file(s)...")

    for uploaded_file in uploaded_files:
        try:
            # Read file
            df_raw = pd.read_csv(uploaded_file)

            # Check format
            is_user_format = 'Call OI' in df_raw.columns and 'Put OI' in df_raw.columns

            if is_user_format:
                # Parse Dates from Filename
                expiry_date, snapshot_date = parse_filename_dates(uploaded_file.name)

                # If parsed, use them. If not, we might need user input or fallback?
                # For batch processing, individual user input is tedious.
                # We'll rely on parsing or current timestamp.

                expiry_dt = expiry_date if expiry_date else pd.Timestamp.now() + pd.Timedelta(days=7) # Fallback
                snapshot_dt = snapshot_date if snapshot_date else pd.Timestamp.now()

                # Process
                df_processed, spot_val = process_user_format_df(df_raw, expiry_dt, snapshot_dt)

                if spot_val:
                    inferred_spot_list.append(spot_val)

                all_data_frames.append(df_processed)

            else:
                # Standard format
                df_std, _ = load_data_from_standard_csv(uploaded_file)
                all_data_frames.append(df_std)

        except Exception as e:
            st.warning(f"Skipped file {uploaded_file.name} due to error: {e}")

    if all_data_frames:
        options_df = pd.concat(all_data_frames, ignore_index=True)
        st.success(f"Successfully loaded {len(options_df)} option contracts from {len(uploaded_files)} files.")

        # Spot Price Logic: Use the most common inferred spot or average?
        # Usually spot is same across files (if same snapshot time).
        if inferred_spot_list:
            # Take the one from the nearest expiry? Or just average?
            # Let's take the median to avoid outliers.
            current_spot = float(np.median(inferred_spot_list))

    else:
        st.error("No valid data found in uploaded files.")

else:
    st.info("No files uploaded. Using Mock Data for demonstration.")
    options_df = generate_mock_nifty_data(current_spot)

# --- Main Spot Input ---
st.sidebar.subheader("Market Data")
spot_price_input = st.sidebar.number_input("Spot Price", value=float(current_spot), format="%.2f")

# --- Analysis ---
if options_df is not None and not options_df.empty:

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Spot Price", f"{spot_price_input:,.2f}")
    col2.metric("Contract Size", contract_size)

    # Calculate Profile
    with st.spinner("Calculating Aggregate Gamma Profile..."):
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
