import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

def generate_mock_nifty_data(current_spot=22000):
    """
    Generates mock Nifty option chain data.
    Useful for testing when no real data is available.
    """
    strikes = np.arange(current_spot - 2000, current_spot + 2000, 50)
    data = []

    for K in strikes:
        # Volatility Smile approximation
        iv = 0.15 + 0.00001 * (K - current_spot)**2 / current_spot

        # Open Interest Distribution approximation
        oi_call = int(100000 * np.exp(-((K - (current_spot + 500))**2) / (2 * 1000**2)))
        oi_put = int(100000 * np.exp(-((K - (current_spot - 500))**2) / (2 * 1000**2)))

        # Add Call
        data.append({
            'StrikePrice': K,
            'OptionType': 'call',
            'IV': iv,
            'OpenInterest': oi_call,
            'ExpirationDate': pd.Timestamp.now() + pd.Timedelta(days=7)
        })

        # Add Put
        data.append({
            'StrikePrice': K,
            'OptionType': 'put',
            'IV': iv,
            'OpenInterest': oi_put,
            'ExpirationDate': pd.Timestamp.now() + pd.Timedelta(days=7)
        })

    return pd.DataFrame(data)

def load_data_from_standard_csv(file_or_path):
    """
    Loads option data from a standard CSV file (simple format).
    Expected columns: 'StrikePrice', 'OptionType', 'IV', 'OpenInterest', 'ExpirationDate'
    """
    df = pd.read_csv(file_or_path)
    df.columns = df.columns.str.strip()
    if 'OptionType' in df.columns:
        df['OptionType'] = df['OptionType'].str.lower()
    return df, None # No spot inference for standard CSV

def parse_filename_dates(filename):
    """
    Parses the filename to extract Expiry Date and Snapshot Date.
    Format: NIFTY_YYYY-MM-DD_option_chain_YYYY-MM-DD-HH-MM-SS
    """
    # Ensure we just have the filename, not full path
    filename = os.path.basename(filename)
    match = re.search(r'_(\d{4}-\d{2}-\d{2})_option_chain_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})', filename)

    if match:
        expiry_str = match.group(1)
        snapshot_str = match.group(2)
        expiry_date = pd.to_datetime(expiry_str)
        snapshot_date = pd.to_datetime(snapshot_str, format='%Y-%m-%d-%H-%M-%S')
        return expiry_date, snapshot_date
    else:
        return None, None

def infer_spot_price(df):
    """
    Infers spot price from 'Call Intrinsic Value(Spot)' column if available.
    Spot = Strike + Call Intrinsic Value
    """
    # Check for likely column names
    col_candidates = ['Call Intrinsic Value(Spot)', 'Call Intrinsic Value', 'Call Intrinsic']
    target_col = next((c for c in col_candidates if c in df.columns), None)

    if target_col:
        # Ensure numeric
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        df['Strike'] = pd.to_numeric(df['Strike'], errors='coerce')

        # Find rows with positive intrinsic value
        itm_calls = df[df[target_col] > 0]
        if not itm_calls.empty:
            # Take the one with highest Intrinsic (Deep ITM) to avoid near-zero noise
            # Sort by intrinsic desc
            itm_calls = itm_calls.sort_values(by=target_col, ascending=False)
            row = itm_calls.iloc[0]
            try:
                spot = float(row['Strike']) + float(row[target_col])
                return spot
            except:
                pass
    return None

def process_user_format_df(df, expiry_date, snapshot_date):
    """
    Processes the raw DataFrame from the user format into the standard analysis format.
    """
    df.columns = df.columns.str.strip() # Clean headers

    # Calculate Time to Expiry
    if expiry_date and snapshot_date:
        # Assuming 15:30 expiry time on the expiry date
        expiry_datetime = expiry_date + pd.Timedelta(hours=15, minutes=30)
        time_diff = expiry_datetime - snapshot_date
        time_till_expiry_years = time_diff.total_seconds() / (365.0 * 24 * 3600)
    else:
        # Default fallback if dates missing
        time_till_expiry_years = 7 / 365.0

    if time_till_expiry_years < 0:
        time_till_expiry_years = 0.0001

    # Infer Spot Price
    inferred_spot = infer_spot_price(df)

    processed_data = []

    # Iterate and Transform
    for _, row in df.iterrows():
        try:
            strike = float(row['Strike'])
            iv_percent = float(row['IV'])
            iv = iv_percent / 100.0

            call_oi = float(row['Call OI']) if pd.notnull(row['Call OI']) else 0
            put_oi = float(row['Put OI']) if pd.notnull(row['Put OI']) else 0

            # Add Call Row
            processed_data.append({
                'StrikePrice': strike,
                'OptionType': 'call',
                'IV': iv,
                'OpenInterest': call_oi,
                'ExpirationDate': expiry_date if expiry_date else pd.Timestamp.now(),
                'TimeTillExpiry': time_till_expiry_years
            })

            # Add Put Row
            processed_data.append({
                'StrikePrice': strike,
                'OptionType': 'put',
                'IV': iv,
                'OpenInterest': put_oi,
                'ExpirationDate': expiry_date if expiry_date else pd.Timestamp.now(),
                'TimeTillExpiry': time_till_expiry_years
            })

        except (ValueError, KeyError):
            continue

    return pd.DataFrame(processed_data), inferred_spot

def load_user_format_csv(filepath):
    """
    Loads data from the specific user CSV format file path.
    Wrapper around process_user_format_df for file paths.
    """
    df = pd.read_csv(filepath)

    # Parse Dates from Filename
    expiry_date, snapshot_date = parse_filename_dates(filepath)

    if expiry_date is None or snapshot_date is None:
        # Try to parse from first row if filename fails? Or just warn.
        # For CLI usage, we raise error if filename is strictly expected.
        # But for robust usage, we might allow manual input later.
        # Here we just pass None and let the processor handle or caller handle.
        pass

    return process_user_format_df(df, expiry_date, snapshot_date)
