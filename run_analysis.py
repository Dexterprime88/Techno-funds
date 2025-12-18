import pandas as pd
import numpy as np
from gamma_utils import calculate_net_gamma_profile, find_zero_gamma_level, plot_gamma_profile

def generate_mock_nifty_data(current_spot=22000):
    """
    Generates mock Nifty option chain data.
    """
    strikes = np.arange(current_spot - 2000, current_spot + 2000, 50)
    data = []

    for K in strikes:
        # Volatility Smile
        iv = 0.15 + 0.00001 * (K - current_spot)**2 / current_spot

        # Open Interest Distribution
        oi_call = int(100000 * np.exp(-((K - (current_spot + 500))**2) / (2 * 1000**2)))
        oi_put = int(100000 * np.exp(-((K - (current_spot - 500))**2) / (2 * 1000**2)))

        data.append({
            'StrikePrice': K,
            'OptionType': 'call',
            'IV': iv,
            'OpenInterest': oi_call,
            'ExpirationDate': pd.Timestamp.now() + pd.Timedelta(days=7)
        })

        data.append({
            'StrikePrice': K,
            'OptionType': 'put',
            'IV': iv,
            'OpenInterest': oi_put,
            'ExpirationDate': pd.Timestamp.now() + pd.Timedelta(days=7)
        })

    return pd.DataFrame(data)

def main():
    current_spot = 22000
    contract_size = 50 # Nifty specific
    print(f"Generating mock data for Spot: {current_spot}")
    options_df = generate_mock_nifty_data(current_spot)

    print(f"Calculating Net Gamma Profile (Contract Size: {contract_size})...")
    profile_df = calculate_net_gamma_profile(options_df, current_spot, contract_size=contract_size)

    print("Finding Zero Gamma Levels...")
    zeros = find_zero_gamma_level(profile_df)
    print(f"Zero Gamma Levels: {zeros}")

    print("Generating Plot...")
    fig = plot_gamma_profile(profile_df, current_spot, zeros)

    # Do not save file to disk in this script to avoid artifact creation in the repo.
    # In a real environment, user would display it.
    print("Plot object created successfully.")

if __name__ == "__main__":
    main()
