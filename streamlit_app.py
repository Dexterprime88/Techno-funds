import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
import plotly.graph_objects as go

from gamma_utils import calculate_net_gamma_profile, find_zero_gamma_level, plot_gamma_profile
from data_utils import (
    process_user_format_df,
    load_data_from_standard_csv,
    generate_mock_nifty_data,
    parse_filename_dates
)

st.set_page_config(page_title="Net Gamma Exposure", layout="wide")

st.title("Net Gamma Exposure (GEX) Dashboard")
st.markdown("""
**Instructions:**
1. Upload one or more Option Chain CSV files.
2. Adjust the Analysis Date and Spot Price in the sidebar if needed.
3. View the interactive Gamma Profile and Zero Gamma Level.
""")

# --- Sidebar Inputs ---
st.sidebar.header("1. Upload Data")

# File Uploader - Allow Multiple
uploaded_files = st.sidebar.file_uploader("Upload Option Chain CSVs", type=["csv"], accept_multiple_files=True)

st.sidebar.header("2. Configuration")

# Contract Size
contract_size = st.sidebar.number_input("Contract Size", value=50, min_value=1)

# Dates
# We need a reference "Analysis Date" (Snapshot Time).
# Default to "Now" or infer from the first file later.
# We'll initialize with today, but update it if a file is loaded?
# Streamlit re-runs on interaction, so we can set a default.
default_analysis_date = datetime.now().date()
analysis_date_input = st.sidebar.date_input("Analysis / Snapshot Date", value=default_analysis_date)
# Optional: Time input? For now, assume market close (15:30) or current time?
# Let's assume 15:30 for consistency if user picks a past date, or now if today.
analysis_time_input = st.sidebar.time_input("Snapshot Time", value=time(15, 30))

analysis_dt = datetime.combine(analysis_date_input, analysis_time_input)

# Fallback Expiry
default_expiry_input = st.sidebar.date_input("Fallback Expiry Date (if parsing fails)", value=datetime.now().date() + pd.Timedelta(days=7))


# --- Logic ---

options_df = None
current_spot = 22000.0 # Default fallback
inferred_spot_list = []

# To update 'current_spot' input based on data, we use session state or a placeholder.
# But simpler: just process data, get inferred spot, and if the USER hasn't manually changed the input, update it?
# Streamlit input widgets are tricky to update programmatically without session state.
# We'll calculate the 'suggested' spot and show it, or set the default of the input if it's the first run.

if "spot_price" not in st.session_state:
    st.session_state.spot_price = 22000.0

if uploaded_files:
    all_data_frames = []

    status_text = st.empty()
    status_text.info(f"Processing {len(uploaded_files)} file(s)...")

    # First pass: Parse dates and infer spot to maybe update defaults
    # (Actually we process everything in one pass for efficiency)

    for uploaded_file in uploaded_files:
        try:
            # Read file
            # Reset buffer?
            uploaded_file.seek(0)
            df_raw = pd.read_csv(uploaded_file)

            # Check format
            is_user_format = 'Call OI' in df_raw.columns and 'Put OI' in df_raw.columns

            if is_user_format:
                # Parse Dates from Filename
                parsed_expiry, parsed_snapshot = parse_filename_dates(uploaded_file.name)

                # Determine Effective Expiry
                if parsed_expiry:
                    effective_expiry = parsed_expiry
                else:
                    effective_expiry = pd.to_datetime(default_expiry_input)

                # Determine Effective Snapshot (for this file's TTE calculation?)
                # Ideally TTE is (Expiry - Global_Analysis_Date).
                # So we use 'analysis_dt' set by user as the anchor.

                # Process
                # Note: process_user_format_df uses snapshot_date to calc TTE.
                # We pass our global 'analysis_dt' to ensure all options are evaluated at the same 'now'.
                df_processed, spot_val = process_user_format_df(df_raw, effective_expiry, analysis_dt)

                if spot_val:
                    inferred_spot_list.append(spot_val)

                all_data_frames.append(df_processed)

            else:
                # Standard format
                uploaded_file.seek(0)
                df_std, _ = load_data_from_standard_csv(uploaded_file)
                # Recalculate TTE based on global analysis date if needed?
                # Standard CSV usually has 'TimeTillExpiry' or 'ExpirationDate'.
                # Let's ensure ExpirationDate is datetime
                if 'ExpirationDate' in df_std.columns:
                     df_std['ExpirationDate'] = pd.to_datetime(df_std['ExpirationDate'])
                     # Update TTE
                     time_diff = df_std['ExpirationDate'] + pd.Timedelta(hours=15, minutes=30) - analysis_dt
                     df_std['TimeTillExpiry'] = time_diff.dt.total_seconds() / (365.0 * 24 * 3600)
                     df_std['TimeTillExpiry'] = df_std['TimeTillExpiry'].clip(lower=0.0001)

                all_data_frames.append(df_std)

        except Exception as e:
            st.warning(f"Skipped file {uploaded_file.name} due to error: {e}")

    if all_data_frames:
        options_df = pd.concat(all_data_frames, ignore_index=True)
        status_text.success(f"Successfully loaded {len(options_df)} option contracts from {len(uploaded_files)} files.")

        # Spot Price Inference
        if inferred_spot_list:
            median_spot = float(np.median(inferred_spot_list))
            # Only update session state if it looks like default
            if st.session_state.spot_price == 22000.0 and median_spot > 0:
                 st.session_state.spot_price = median_spot
                 st.rerun() # Rerun to update the input widget

    else:
        status_text.error("No valid data found in uploaded files.")

else:
    st.info("No files uploaded. Using Mock Data for demonstration.")
    options_df = generate_mock_nifty_data(st.session_state.spot_price)


# --- Main Spot Input ---
st.sidebar.subheader("3. Market Parameters")
# We use session_state for the value to allow programmatic updates
spot_price_input = st.sidebar.number_input("Spot Price", key="spot_price", format="%.2f")

# --- Analysis ---
if options_df is not None and not options_df.empty:

    st.divider()

    # Calculate Profile
    with st.spinner("Calculating Aggregate Gamma Profile..."):
        try:
            profile_df = calculate_net_gamma_profile(options_df, spot_price_input, contract_size=contract_size)
            zeros = find_zero_gamma_level(profile_df)

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spot Price", f"{spot_price_input:,.2f}")
            col2.metric("Contracts", f"{len(options_df):,}")

            if zeros:
                zero_level = zeros[0]
                dist_pts = zero_level - spot_price_input
                dist_pct = (dist_pts / spot_price_input) * 100
                col3.metric("Zero Gamma Level", f"{zero_level:,.2f}")
                col4.metric("Distance", f"{dist_pts:,.2f} ({dist_pct:.2f}%)")
            else:
                col3.metric("Zero Gamma Level", "Not Found")
                col4.metric("Distance", "-")

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
