import pandas as pd
import numpy as np
import os
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

def load_data_from_csv(filepath):
    """
    Loads option data from a CSV file.
    Expected CSV columns: 'StrikePrice', 'OptionType' ('call'/'put'), 'IV', 'OpenInterest', 'ExpirationDate'
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    df = pd.read_csv(filepath)

    # Standardize column names (optional, map your CSV headers here)
    # df = df.rename(columns={'strike': 'StrikePrice', 'type': 'OptionType', ...})

    # Ensure required columns exist
    required_cols = ['StrikePrice', 'OptionType', 'IV', 'OpenInterest', 'ExpirationDate']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # Ensure OptionType is lowercase
    df['OptionType'] = df['OptionType'].str.lower()

    return df

def main():
    # --- CONFIGURATION ---
    current_spot = 22000    # Set the current spot price of Nifty
    contract_size = 50      # Nifty contract size is 50
    csv_file_path = 'sample_nifty_data.csv' # Path to your data file
    use_mock_data = False    # Set to False to use the CSV file
    # ---------------------

    print(f"--- Net Gamma Exposure Analysis ---")
    print(f"Spot Price: {current_spot}")
    print(f"Contract Size: {contract_size}")

    if use_mock_data:
        print("Mode: Using Mock Data")
        options_df = generate_mock_nifty_data(current_spot)
    else:
        print(f"Mode: Loading data from {csv_file_path}")
        if os.path.exists(csv_file_path):
            options_df = load_data_from_csv(csv_file_path)
        else:
            print(f"Warning: {csv_file_path} not found. Falling back to mock data.")
            options_df = generate_mock_nifty_data(current_spot)

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

    # Show or Save
    # fig.show() # Uncomment to show in browser if running locally
    # fig.write_html("gamma_profile.html") # Uncomment to save as HTML
    print("Analysis Complete.")
    print("NOTE: To see the chart, uncomment 'fig.show()' or 'fig.write_html(...)' in the script.")

if __name__ == "__main__":
    main()
