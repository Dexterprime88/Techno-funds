import pandas as pd
import numpy as np
import os
from gamma_utils import calculate_net_gamma_profile, find_zero_gamma_level, plot_gamma_profile
from data_utils import (
    load_user_format_csv,
    load_data_from_standard_csv,
    generate_mock_nifty_data,
    parse_filename_dates
)

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
            # Parse dates just for logging
            expiry, snapshot = parse_filename_dates(target_file)
            if expiry and snapshot:
                 print(f"Parsed -> Expiry: {expiry}, Snapshot: {snapshot}")

            options_df, inferred_spot = load_user_format_csv(target_file)
            if inferred_spot:
                current_spot = inferred_spot
                print(f"Inferred Spot Price from Data: {inferred_spot}")
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
