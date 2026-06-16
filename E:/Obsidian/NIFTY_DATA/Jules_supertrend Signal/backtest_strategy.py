import pandas as pd
import numpy as np
import os
import glob
from pathlib import Path

def rational_quadratic_kernel(x, y, alpha, c):
    """
    Computes the Rational Quadratic kernel.
    k(x, y) = (1 + ||x - y||^2 / (2 * alpha * c^2)) ^ (-alpha)
    """
    distance_sq = (x - y) ** 2
    return (1.0 + distance_sq / (2.0 * alpha * (c ** 2))) ** (-alpha)

def apply_rq_smoothing(series, lookback=8, alpha=8.0, c=1.0):
    """
    Applies Nadaraya-Watson kernel regression with RQ kernel.
    TradingView's implementation usually uses a window (lookback).
    The kernel weights are computed relative to the current bar.
    """
    smoothed = pd.Series(index=series.index, dtype=float)
    n = len(series)

    # Precompute weights for a given lookback window
    # x is current bar index (e.g., 0), y goes from 0 to lookback-1
    weights = np.array([rational_quadratic_kernel(0, i, alpha, c) for i in range(lookback)])
    weight_sum = np.sum(weights)

    for i in range(n):
        if i < lookback - 1:
            # Not enough data, just use a simple SMA or raw value
            smoothed.iloc[i] = series.iloc[i]
            continue

        # Extract the window
        window = series.iloc[i - lookback + 1 : i + 1]
        # window is length `lookback`, ordered oldest to newest.
        # We align weights such that index 0 corresponds to the current bar (newest),
        # i.e., distance=0 is the newest bar, distance=1 is the previous bar, etc.
        # So we reverse the window to match weights [0, 1, ..., lookback-1]

        val = np.sum(window.values[::-1] * weights) / weight_sum
        smoothed.iloc[i] = val

    return smoothed

def calculate_supertrend(df, atr_period=10, factor=3.0):
    """
    Calculates Supertrend on the DataFrame assuming it has
    RQ_Smoothed_High, RQ_Smoothed_Low, RQ_Smoothed_Close
    """
    # Calculate True Range using Smoothed Data
    df['prev_close'] = df['RQ_Smoothed_Close'].shift(1)

    tr1 = df['RQ_Smoothed_High'] - df['RQ_Smoothed_Low']
    tr2 = (df['RQ_Smoothed_High'] - df['prev_close']).abs()
    tr3 = (df['RQ_Smoothed_Low'] - df['prev_close']).abs()

    df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean() # Simple Moving Average for ATR, matching typical TradingView simple ATR

    # Calculate basic upper and lower bands
    hl2 = (df['RQ_Smoothed_High'] + df['RQ_Smoothed_Low']) / 2
    df['Basic_UB'] = hl2 + (factor * df['ATR'])
    df['Basic_LB'] = hl2 - (factor * df['ATR'])

    # Calculate Final Bands
    df['Final_UB'] = 0.0
    df['Final_LB'] = 0.0
    df['Supertrend'] = 0.0
    df['Trend'] = 0 # 1 for Bullish, -1 for Bearish

    for i in range(1, len(df)):
        # Final Upper Band
        if df['Basic_UB'].iloc[i] < df['Final_UB'].iloc[i-1] or df['RQ_Smoothed_Close'].iloc[i-1] > df['Final_UB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_UB'] = df['Basic_UB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_UB'] = df['Final_UB'].iloc[i-1]

        # Final Lower Band
        if df['Basic_LB'].iloc[i] > df['Final_LB'].iloc[i-1] or df['RQ_Smoothed_Close'].iloc[i-1] < df['Final_LB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_LB'] = df['Basic_LB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_LB'] = df['Final_LB'].iloc[i-1]

        # Supertrend
        if df['Supertrend'].iloc[i-1] == df['Final_UB'].iloc[i-1]:
            if df['RQ_Smoothed_Close'].iloc[i] <= df['Final_UB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
                df.loc[df.index[i], 'Trend'] = -1
            else:
                df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
                df.loc[df.index[i], 'Trend'] = 1
        elif df['Supertrend'].iloc[i-1] == df['Final_LB'].iloc[i-1]:
            if df['RQ_Smoothed_Close'].iloc[i] >= df['Final_LB'].iloc[i]:
                df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
                df.loc[df.index[i], 'Trend'] = 1
            else:
                df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
                df.loc[df.index[i], 'Trend'] = -1

    return df

def run_backtest(data_path, lookback=8, weight=8.0, atr_period=10, factor=3.0, sl_atr_multiplier=2.5):
    """
    Runs the backtest on the given CSV file.
    """
    df = pd.read_csv(data_path)

    # Ensure required columns exist
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            # Fallback for lowercase or other variations
            matched = [c for c in df.columns if c.lower() == col.lower()]
            if matched:
                df = df.rename(columns={matched[0]: col})
            else:
                print(f"Error: Required column '{col}' missing from {data_path}")
                return None

    # Apply RQ Smoothing
    print("Applying RQ Smoothing...")
    df['RQ_Smoothed_Open'] = apply_rq_smoothing(df['Open'], lookback=lookback, alpha=weight, c=lookback)
    df['RQ_Smoothed_High'] = apply_rq_smoothing(df['High'], lookback=lookback, alpha=weight, c=lookback)
    df['RQ_Smoothed_Low'] = apply_rq_smoothing(df['Low'], lookback=lookback, alpha=weight, c=lookback)
    df['RQ_Smoothed_Close'] = apply_rq_smoothing(df['Close'], lookback=lookback, alpha=weight, c=lookback)

    # Calculate Supertrend
    print("Calculating Supertrend...")
    df = calculate_supertrend(df, atr_period=atr_period, factor=factor)

    # Implement 2-bar confirmation
    df['Trend_1'] = df['Trend'].shift(1)
    df['Confirmed_Trend'] = 0

    current_confirmed_trend = 0
    for i in range(2, len(df)):
        if df['Trend'].iloc[i] == df['Trend_1'].iloc[i] and df['Trend'].iloc[i] != 0:
            current_confirmed_trend = df['Trend'].iloc[i]
        df.loc[df.index[i], 'Confirmed_Trend'] = current_confirmed_trend

    # Trading Logic
    print("Running Trading Logic...")
    position = 0 # 1 for Long, -1 for Short
    entry_price = 0.0
    stop_loss = 0.0

    trades = []

    for i in range(3, len(df)): # Start from 3 to have valid previous data
        current_trend = df['Confirmed_Trend'].iloc[i-1]
        prev_trend = df['Confirmed_Trend'].iloc[i-2]

        current_open = df['Open'].iloc[i]
        current_high = df['High'].iloc[i]
        current_low = df['Low'].iloc[i]
        current_atr = df['ATR'].iloc[i-1] # Use previous bar's ATR to avoid lookahead

        if pd.isna(current_atr) or current_atr == 0:
            continue

        # Check Stop Loss first if in position
        if position == 1:
            if current_low <= stop_loss:
                # Stop loss hit
                exit_price = stop_loss
                trades.append({
                    'type': 'Long Exit (SL)',
                    'index': i,
                    'price': exit_price,
                    'pnl': exit_price - entry_price
                })
                position = 0
        elif position == -1:
            if current_high >= stop_loss:
                # Stop loss hit
                exit_price = stop_loss
                trades.append({
                    'type': 'Short Exit (SL)',
                    'index': i,
                    'price': exit_price,
                    'pnl': entry_price - exit_price
                })
                position = 0

        # Check for Trend Flip / Entry
        if current_trend != prev_trend:
            # Exit existing position if not already stopped out
            if position == 1:
                trades.append({
                    'type': 'Long Exit (Flip)',
                    'index': i,
                    'price': current_open,
                    'pnl': current_open - entry_price
                })
                position = 0
            elif position == -1:
                trades.append({
                    'type': 'Short Exit (Flip)',
                    'index': i,
                    'price': current_open,
                    'pnl': entry_price - current_open
                })
                position = 0

            # Enter new position
            if current_trend == 1:
                position = 1
                entry_price = current_open
                stop_loss = entry_price - (sl_atr_multiplier * current_atr)
                trades.append({
                    'type': 'Long Entry',
                    'index': i,
                    'price': entry_price,
                    'sl': stop_loss
                })
                if current_low <= stop_loss:
                    trades.append({
                        'type': 'Long Exit (SL on Entry)',
                        'index': i,
                        'price': stop_loss,
                        'pnl': stop_loss - entry_price
                    })
                    position = 0
            elif current_trend == -1:
                position = -1
                entry_price = current_open
                stop_loss = entry_price + (sl_atr_multiplier * current_atr)
                trades.append({
                    'type': 'Short Entry',
                    'index': i,
                    'price': entry_price,
                    'sl': stop_loss
                })
                if current_high >= stop_loss:
                    trades.append({
                        'type': 'Short Exit (SL on Entry)',
                        'index': i,
                        'price': stop_loss,
                        'pnl': entry_price - stop_loss
                    })
                    position = 0

    # Close open position at end
    if position == 1:
         trades.append({
            'type': 'Long Exit (End)',
            'index': len(df)-1,
            'price': df['Close'].iloc[-1],
            'pnl': df['Close'].iloc[-1] - entry_price
         })
    elif position == -1:
         trades.append({
            'type': 'Short Exit (End)',
            'index': len(df)-1,
            'price': df['Close'].iloc[-1],
            'pnl': entry_price - df['Close'].iloc[-1]
         })

    return df, trades


if __name__ == "__main__":
    raw_folder = Path("E:/Obsidian/NIFTY_DATA/raw")
    csv_files = glob.glob(str(raw_folder / "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {raw_folder}")
    else:
        for file in csv_files:
            print(f"\nProcessing {file}...")
            df_result, trades = run_backtest(
                file,
                lookback=8,
                weight=8.0,
                atr_period=10,
                factor=3.0,
                sl_atr_multiplier=2.5
            )

            if df_result is not None:
                # Summary
                pnls = [t['pnl'] for t in trades if 'pnl' in t]
                total_pnl = sum(pnls)
                wins = len([p for p in pnls if p > 0])
                losses = len([p for p in pnls if p <= 0])

                print(f"--- Results for {os.path.basename(file)} ---")
                print(f"Total Trades: {len(pnls)}")
                print(f"Wins: {wins}, Losses: {losses}")
                print(f"Total PnL: {total_pnl:.2f}")
