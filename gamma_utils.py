import numpy as np
import pandas as pd
from scipy.stats import norm
import plotly.graph_objects as go

def black_scholes_gamma(S, K, T, r, sigma, option_type):
    """
    Calculates the Gamma of a European option using Black-Scholes formula.

    Parameters:
    S (float): Spot price of the underlying asset
    K (float): Strike price
    T (float): Time to expiration in years
    r (float): Risk-free interest rate
    sigma (float): Volatility of the underlying asset
    option_type (str): 'call' or 'put'

    Returns:
    float: Gamma of the option
    """
    # Avoid division by zero
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    # Gamma is the same for calls and puts
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

    return gamma

def calculate_gex(row, spot_price, contract_size=100):
    """
    Calculates the Gamma Exposure (GEX) for a single option row.

    Parameters:
    row (pd.Series): A row from the options DataFrame containing:
                     'StrikePrice', 'ExpirationDate', 'OptionType' ('call'/'put'),
                     'IV' (Implied Volatility), 'OpenInterest'.
                     'TimeTillExpiry' (in years) should be pre-calculated or calculated here.
    spot_price (float): The current spot price to evaluate Gamma at.
    contract_size (int): Contract size multiplier (e.g., 50 for Nifty, 100 for Generic).

    Returns:
    float: The GEX value (dollar gamma per 1% move).
    """

    S = spot_price
    K = row['StrikePrice']
    sigma = row['IV']
    T = row['TimeTillExpiry']
    r = 0.0 # Assuming 0 risk-free rate for simplicity, or pass it as a parameter
    option_type = row['OptionType'].lower()
    oi = row['OpenInterest']

    # Calculate Unit Gamma
    gamma = black_scholes_gamma(S, K, T, r, sigma, option_type)

    # Calculate GEX
    # Formula: Gamma * Open Interest * Contract Size * Spot * Spot * 0.01
    gex = gamma * oi * contract_size * S * S * 0.01

    if option_type == 'put':
        gex *= -1

    return gex

def calculate_net_gamma_profile(options_df, current_spot, spot_range_pct=0.2, steps=60, contract_size=100):
    """
    Calculates the Net Gamma Exposure profile across a range of spot prices.

    Parameters:
    options_df (pd.DataFrame): DataFrame with columns ['StrikePrice', 'OptionType', 'IV', 'OpenInterest', 'ExpirationDate']
    current_spot (float): Current underlying spot price.
    spot_range_pct (float): Percentage range to calculate (e.g., 0.2 for +/- 20%).
    steps (int): Number of steps in the profile.
    contract_size (int): Contract size multiplier (default 100).

    Returns:
    pd.DataFrame: DataFrame with 'SpotPrice' and 'TotalGEX'.
    """

    # Ensure TimeTillExpiry is present
    if 'TimeTillExpiry' not in options_df.columns:
         now = pd.Timestamp.now()
         options_df['TimeTillExpiry'] = (pd.to_datetime(options_df['ExpirationDate']) - now).dt.days / 365.0
         options_df['TimeTillExpiry'] = options_df['TimeTillExpiry'].clip(lower=0.001)

    from_strike = current_spot * (1 - spot_range_pct)
    to_strike = current_spot * (1 + spot_range_pct)
    spot_levels = np.linspace(from_strike, to_strike, steps)

    profile_data = []

    # Data for vectorization
    K = options_df['StrikePrice'].values
    T = options_df['TimeTillExpiry'].values
    sigma = options_df['IV'].values
    oi = options_df['OpenInterest'].values
    r = 0.0
    is_put = options_df['OptionType'].str.lower() == 'put'

    for spot in spot_levels:
        # Vectorized Black-Scholes Gamma
        # d1 = (ln(S/K) + (r + 0.5*sigma^2)*T) / (sigma * sqrt(T))

        # Note: 'spot' is scalar here, K is vector.
        d1 = (np.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

        # Gamma
        gamma_vec = norm.pdf(d1) / (spot * sigma * np.sqrt(T))
        gamma_vec = np.nan_to_num(gamma_vec)

        # GEX Calculation
        gex_vec = gamma_vec * oi * contract_size * spot * spot * 0.01

        # Apply sign for puts (Long Put -> Positive Gamma -> Dealer Short Put -> Negative GEX)
        # Note: Dealer is Short Put. Short Put Gamma is Negative.
        # Article: "Option's Gamma ... (-1 if puts)"
        gex_vec[is_put] *= -1

        total_gex = np.sum(gex_vec)

        profile_data.append({'SpotPrice': spot, 'TotalGEX': total_gex})

    return pd.DataFrame(profile_data)

def find_zero_gamma_level(profile_df):
    """
    Finds the zero gamma level (flipping point) by interpolation.
    """
    gex_values = profile_df['TotalGEX'].values
    spot_values = profile_df['SpotPrice'].values

    zero_crossings = np.where(np.diff(np.sign(gex_values)))[0]

    flipping_points = []

    for idx in zero_crossings:
        neg_gex = gex_values[idx]
        pos_gex = gex_values[idx+1]
        neg_spot = spot_values[idx]
        pos_spot = spot_values[idx+1]

        # Linear interpolation
        if (pos_gex - neg_gex) == 0:
            zero_spot = neg_spot
        else:
            zero_spot = pos_spot - ((pos_spot - neg_spot) * pos_gex / (pos_gex - neg_gex))

        flipping_points.append(zero_spot)

    return flipping_points

def plot_gamma_profile(profile_df, current_spot, zero_gamma_levels):
    """
    Plots the Gamma Exposure Profile using Plotly.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=profile_df['SpotPrice'], y=profile_df['TotalGEX'],
                             mode='lines', name='Total Gamma Exposure',
                             line=dict(color='blue')))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=current_spot, line_dash="dash", line_color="red", annotation_text="Current Spot")

    for zg in zero_gamma_levels:
        fig.add_vline(x=zg, line_dash="dot", line_color="green", annotation_text=f"Flip: {zg:.2f}")

    fig.update_layout(title="Net Gamma Exposure Profile",
                      xaxis_title="Spot Price",
                      yaxis_title="Gamma Exposure ($ / 1% move)",
                      template="plotly_white")

    return fig
