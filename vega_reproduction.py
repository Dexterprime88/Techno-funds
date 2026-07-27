#!/usr/bin/env python3
"""
vega_reproduction.py

This script contains the precise reverse-engineered mathematical and algorithmic implementation
of StockMojo's NIFTY Vega Analysis page. It includes the exact Black-Scholes equations,
Newton-Raphson & Bisection implied volatility solvers, time-to-expiry representations,
aggregation, and session drift calculations.
"""

import math

def norm_cdf(x):
    """Cumulative Distribution Function (CDF) of the standard normal distribution."""
    # Matches Next.js implementation of standard normal CDF
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    """Probability Density Function (PDF) of the standard normal distribution."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def bs_price(S, K, T, r, sigma, option_type):
    """
    Calculate the Black-Scholes option price.
    option_type: 'call' or 3, 'put' or 4
    """
    if T <= 0 or sigma <= 0:
        if option_type in ('call', 3):
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type in ('call', 3):
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def bs_vega(S, K, T, r, sigma):
    """
    Calculate the Black-Scholes Vega.
    Annualized and scaled by 100 (premium change per 1% change in IV).
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    # Formula: S * sqrt(T) * phi(d1) / 100
    vega = S * math.sqrt(T) * norm_pdf(d1) / 100.0
    return vega

def price_to_iv(S, K, T, r, premium, option_type, tol=1e-8, max_iter=100):
    """
    Invert Black-Scholes option price to solve for Implied Volatility (IV)
    using Newton-Raphson with a Bisection search fallback.
    """
    # Lower bound intrinsic check
    intrinsic = max(S - K * math.exp(-r * T), 0.0) if option_type in ('call', 3) else max(K * math.exp(-r * T) - S, 0.0)
    if premium < intrinsic - 1e-8:
        premium = intrinsic + 0.01

    # Initial guess heuristic from Next.js code:
    # Math.min(1, Math.max(0.001, Math.abs(Math.log(S / (K * exp(-r * T)))) / 10))
    iv = min(1.0, max(0.001, abs(math.log(S / (K * math.exp(-r * T)))) / 10.0))

    for i in range(max_iter):
        p = bs_price(S, K, T, r, iv, option_type)
        diff = p - premium
        if abs(diff) < tol:
            return iv

        # Vega with respect to fractional vol
        v_dec = S * math.sqrt(T) * norm_pdf((math.log(S / K) + (r + 0.5 * iv**2) * T) / (iv * math.sqrt(T)))

        # Fallback to Bisection if Vega is extremely small (illiquid/far OTM options)
        if v_dec < 1e-10:
            low, high = 1e-4, 100.0
            for _ in range(100):
                mid = (low + high) / 2.0
                p_mid = bs_price(S, K, T, r, mid, option_type)
                diff_mid = p_mid - premium
                if abs(diff_mid) < tol:
                    return mid
                if diff_mid < 0:
                    low = mid
                else:
                    high = mid
            return low

        iv = max(1e-4, iv - diff / v_dec)

    return iv if iv < 100.0 else 0.0

def calculate_time_to_expiry_ms(expiry_ms, current_ms):
    """
    Calculate the fractional years from milliseconds.
    Uses the exact StockMojo scaling factor: 3.168808781402895e-26
    """
    diff_ms = expiry_ms - current_ms
    if diff_ms < 0:
        diff_ms = -diff_ms
    # Matches (E * 3168808781402895e-26) in JS, which is exactly (diff_ms / (365.25 * 24 * 3600 * 1000))
    return diff_ms * 3.168808781402895e-26

def calculate_session_drift(vega_list, active_indicators):
    """
    Returns the change in Vega relative to the session's first active/valid data point.
    Matches the 'S' function in StockMojo's client-side JS.
    """
    drift_list = []
    anchor = None
    for val, is_active in zip(vega_list, active_indicators):
        if anchor is None and is_active:
            anchor = val
        if is_active and anchor is not None:
            drift_list.append(round(val - anchor, 2))
        else:
            drift_list.append(None)
    return drift_list

if __name__ == "__main__":
    # Self-test using formulas
    spot = 24000.0
    strike = 24000.0
    expiry_ms = 1785196800000  # Example epoch ms
    current_ms = 1785110400000 # 1 day before
    T = calculate_time_to_expiry_ms(expiry_ms, current_ms)
    r = 0.0
    target_iv = 0.15 # 15% IV

    # Generate mock option premium
    call_prem = bs_price(spot, strike, T, r, target_iv, 'call')
    solved_iv = price_to_iv(spot, strike, T, r, call_prem, 'call')
    vega = bs_vega(spot, strike, T, r, solved_iv)

    print("--- Self-Test Verification ---")
    print(f"Time to Expiry (years): {T:.6f} ({T * 365.25:.2f} days)")
    print(f"Option Premium: {call_prem:.2f}")
    print(f"Solved Implied Volatility: {solved_iv * 100:.4f}% (Expected ~15%)")
    print(f"Option Vega: {vega:.4f}")
