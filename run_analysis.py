import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from gamma_utils import calculate_net_gamma_profile, find_zero_gamma_level, plot_gamma_profile

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

def load_data_from_standard_csv(filepath):
    """
    Loads option data from a standard CSV file (simple format).
    Expected columns: 'StrikePrice', 'OptionType', 'IV', 'OpenInterest', 'ExpirationDate'
    """
    df = pd.read_csv(filepath)
    df['OptionType'] = df['OptionType'].str.lower()
    return df, None # No spot inference for standard CSV

def parse_filename_dates(filepath):
    """
    Parses the filename to extract Expiry Date and Snapshot Date.
    Format: NIFTY_YYYY-MM-DD_option_chain_YYYY-MM-DD-HH-MM-SS
    """
    filename = os.path.basename(filepath)
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
        # Find rows with positive intrinsic value
        itm_calls = df[df[target_col] > 0]
        if not itm_calls.empty:
            # Take the deep ITM ones or average a few to reduce noise?
            # Usually strict formula: Intrinsic = Spot - Strike => Spot = Intrinsic + Strike
            # Let's take the one with highest Intrinsic (Deep ITM) to avoid near-zero noise
            row = itm_calls.iloc[0]
            try:
                spot = float(row['Strike']) + float(row[target_col])
                return spot
            except:
                pass
    return None

def load_user_format_csv(filepath):
    """
    Loads data from the specific user CSV format.
    Returns: DataFrame, Inferred Spot Price (or None)
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip() # Clean headers

    # 1. Parse Dates from Filename
    expiry_date, snapshot_date = parse_filename_dates(filepath)
    if expiry_date is None or snapshot_date is None:
        raise ValueError("Could not parse dates from filename. Ensure format: NIFTY_YYYY-MM-DD_option_chain_YYYY-MM-DD-HH-MM-SS.csv")

    print(f"Parsed from filename -> Expiry: {expiry_date}, Snapshot: {snapshot_date}")

    # Calculate Time to Expiry
    # Assuming 15:30 expiry time on the expiry date
    expiry_datetime = expiry_date + pd.Timedelta(hours=15, minutes=30)
    time_diff = expiry_datetime - snapshot_date
    time_till_expiry_years = time_diff.total_seconds() / (365.0 * 24 * 3600)

    if time_till_expiry_years < 0:
        time_till_expiry_years = 0.0001

    # 2. Infer Spot Price
    inferred_spot = infer_spot_price(df)
    if inferred_spot:
        print(f"Inferred Spot Price from Data: {inferred_spot}")
    else:
        print("Could not infer Spot Price from data columns.")

    processed_data = []

    # 3. Iterate and Transform
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
                'ExpirationDate': expiry_date,
                'TimeTillExpiry': time_till_expiry_years
            })

            # Add Put Row
            processed_data.append({
                'StrikePrice': strike,
                'OptionType': 'put',
                'IV': iv,
                'OpenInterest': put_oi,
                'ExpirationDate': expiry_date,
                'TimeTillExpiry': time_till_expiry_years
            })

        except ValueError:
            continue

    return pd.DataFrame(processed_data), inferred_spot

def main():
    # --- CONFIGURATION ---
    contract_size = 50      # Nifty contract size is 50
    default_spot = 24500    # Fallback spot

    # Look for matching user files
    user_files = [f for f in os.listdir('.') if f.startswith('NIFTY_') and 'option_chain' in f and f.endswith('.csv')]

    options_df = None
    current_spot = default_spot

    if user_files:
        target_file = user_files[0]
        print(f"Found user file: {target_file}")
        try:
            options_df, inferred_spot = load_user_format_csv(target_file)
            if inferred_spot:
                current_spot = inferred_spot
            print("Successfully loaded user data.")
        except Exception as e:
            print(f"Error loading user file: {e}")

    if options_df is None:
        print("No valid user file found. Checking for sample_nifty_data.csv...")
        if os.path.exists('sample_nifty_data.csv'):
            options_df, _ = load_data_from_standard_csv('sample_nifty_data.csv')
        else:
            print("No data files found. Generating Mock Data.")
            options_df = generate_mock_nifty_data(current_spot)

    print(f"--- Net Gamma Exposure Analysis ---")
    print(f"Spot Price: {current_spot:.2f}")
    print(f"Contract Size: {contract_size}")

    # 1. Calculate Profile
    print(f"Calculating Net Gamma Profile...")
    profile_df = calculate_net_gamma_profile(options_df, current_spot, contract_size=contract_size)

    # 2. Find Zero Gamma Levels
    print("Finding Zero Gamma Levels...")
    zeros = find_zero_gamma_level(profile_df)
    if zeros:
        print(f"Zero Gamma Level (Flip Point): {zeros[0]:.2f}")
    else:
        print("No Zero Gamma Level found within the range.")

    # 3. Plot
    print("Generating Plot...")
    fig = plot_gamma_profile(profile_df, current_spot, zeros)

    # Save output
    output_filename = "gamma_profile.html"
    fig.write_html(output_filename)
    print(f"Analysis Complete. Plot saved to {output_filename}")

if __name__ == "__main__":
    main()
