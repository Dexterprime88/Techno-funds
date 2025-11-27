from fastapi import APIRouter, HTTPException
from .kite import get_kite_client
import pandas as pd
import re

router = APIRouter()

# Helper function to find the nearest strike price
def get_atm_strike(strike_list, current_price):
    return min(strike_list, key=lambda x: abs(x - current_price))

@router.get("/option-chain/{instrument_name}")
def get_option_chain(instrument_name: str):
    try:
        kite_client = get_kite_client()

        # 1. Fetch all instruments to find the correct option symbols
        instruments = kite_client.instruments("NFO")
        df = pd.DataFrame(instruments)

        # 2. Get the live quote for the underlying index to find the current price
        instrument_map = {
            "NIFTY": "NSE:NIFTY 50",
            "BANKNIFTY": "NSE:NIFTY BANK"
        }
        underlying_name = instrument_name.upper()
        if underlying_name not in instrument_map:
            raise HTTPException(status_code=400, detail="Invalid instrument. Use NIFTY or BANKNIFTY.")

        quote = kite_client.quote(instrument_map[underlying_name])
        if not quote:
            raise HTTPException(status_code=404, detail="Could not fetch quote for the underlying instrument.")
        current_price = quote[instrument_map[underlying_name]]['last_price']

        # 3. Filter for the nearest expiry date options for the selected instrument
        options_df = df[(df['name'] == underlying_name) & (df['segment'] == 'NFO-OPT')]
        nearest_expiry = options_df['expiry'].min()
        options_df = options_df[options_df['expiry'] == nearest_expiry]

        strike_list = sorted(options_df['strike'].unique())

        # 4. Find the ATM strike
        atm_strike = get_atm_strike(strike_list, current_price)
        atm_index = strike_list.index(atm_strike)

        # 5. Select the 2 ITM and 2 OTM strikes (total of 5 strikes)
        selected_strikes = strike_list[max(0, atm_index - 2) : atm_index + 3]

        # 6. Filter the dataframe to just our selected strikes
        filtered_df = options_df[options_df['strike'].isin(selected_strikes)]

        call_options = filtered_df[filtered_df['instrument_type'] == 'CE']
        put_options = filtered_df[filtered_df['instrument_type'] == 'PE']

        # 7. Fetch OI data for the selected option contracts
        call_symbols = call_options['tradingsymbol'].tolist()
        put_symbols = put_options['tradingsymbol'].tolist()

        all_symbols = call_symbols + put_symbols
        # The quote endpoint can be used to get OI data
        oi_data = kite_client.quote(all_symbols)

        def format_option_data(option_series, symbol_list):
            results = []
            for symbol in symbol_list:
                data = oi_data.get(symbol)
                if data:
                    # Find the corresponding row in the dataframe to get the strike
                    strike_price = option_series[option_series['tradingsymbol'] == symbol]['strike'].iloc[0]
                    results.append({
                        "strike": float(strike_price),
                        "oi": data['oi'],
                        "oi_change": data['oi_day_high'] - data['oi_day_low'], # A simple way to represent change
                        "ltp": data['last_price'],
                        "delta": 0, # Note: Kite Connect does not provide Greeks directly via this endpoint.
                    })
            return sorted(results, key=lambda x: x['strike'])

        formatted_calls = format_option_data(call_options, call_symbols)
        formatted_puts = format_option_data(put_options, put_symbols)

        return {
            "instrument": underlying_name,
            "calls": formatted_calls,
            "puts": formatted_puts,
            "live_price": current_price
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
