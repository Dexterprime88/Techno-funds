import json
from datetime import datetime

class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.records = self.data.get('records', {})
        self.option_chain_data = self.records.get('data', [])
        self.underlying_value = self.records.get('underlyingValue', 0.0)

    def get_expiry_dates(self):
        return self.records.get('expiryDates', [])

    def get_underlying_value(self):
        return self.underlying_value

    def get_current_week_expiry(self):
        """
        Returns the nearest weekly expiry date.
        """
        expiry_dates = self.get_expiry_dates()
        return expiry_dates[0] if expiry_dates else None

    def get_current_month_expiry(self):
        """
        Returns the nearest month-end expiry date.
        This is determined by finding the last expiry date for the current month.
        If no expiry for the current month, it takes the next month's last expiry.
        """
        expiry_dates_str = self.get_expiry_dates()
        if not expiry_dates_str:
            return None

        expiry_dates = [datetime.strptime(date_str, "%d-%b-%Y") for date_str in expiry_dates_str]

        # Group expiries by month
        expiries_by_month = {}
        for date in expiry_dates:
            month_key = (date.year, date.month)
            if month_key not in expiries_by_month:
                expiries_by_month[month_key] = []
            expiries_by_month[month_key].append(date)

        # Find the last expiry for each month
        monthly_expiries = [max(dates) for dates in expiries_by_month.values()]
        monthly_expiries.sort()

        # Find the first monthly expiry from now
        now = datetime.now()
        for expiry in monthly_expiries:
            # Check if the expiry is in the future or in the current month
            if expiry.year > now.year or (expiry.year == now.year and expiry.month >= now.month):
                 return expiry.strftime("%d-%b-%Y")

        return monthly_expiries[0].strftime("%d-%b-%Y") if monthly_expiries else None

    def _get_atm_strike(self):
        """
        Finds the strike price closest to the underlying value.
        """
        if not self.option_chain_data:
            return 0

        strike_prices = sorted(list(set(item['strikePrice'] for item in self.option_chain_data if 'strikePrice' in item)))

        if not strike_prices:
            return 0

        return min(strike_prices, key=lambda x: abs(x - self.underlying_value))

    def get_processed_option_chain(self, expiry_date, num_strikes=10, itm_only=False):
        """
        Returns the processed option chain data for a specific expiry date,
        with filtering options.
        """

        full_chain = []
        for item in self.option_chain_data:
            if item.get('expiryDate') == expiry_date:
                strike_price = item.get('strikePrice', 0)

                ce_data = item.get('CE', {})
                call_oi = ce_data.get('openInterest', 0)

                pe_data = item.get('PE', {})
                put_oi = pe_data.get('openInterest', 0)

                full_chain.append({'strike': strike_price, 'call_oi': call_oi, 'put_oi': put_oi})

        if not full_chain:
            return []

        # Sort by strike price
        full_chain.sort(key=lambda x: x['strike'])

        # Filter by number of strikes around ATM
        atm_strike = self._get_atm_strike()
        atm_index = -1
        for i, item in enumerate(full_chain):
            if item['strike'] == atm_strike:
                atm_index = i
                break

        if atm_index == -1:
            return []

        start_index = max(0, atm_index - num_strikes)
        end_index = min(len(full_chain), atm_index + num_strikes + 1)

        filtered_chain = full_chain[start_index:end_index]

        if itm_only:
            itm_chain = []
            for item in filtered_chain:
                # ITM Call: strike < underlying
                if item['strike'] < self.underlying_value:
                    itm_chain.append({'strike': item['strike'], 'call_oi': item['call_oi'], 'put_oi': 0})
                # ITM Put: strike > underlying
                elif item['strike'] > self.underlying_value:
                    itm_chain.append({'strike': item['strike'], 'call_oi': 0, 'put_oi': item['put_oi']})
            return itm_chain

        return filtered_chain


if __name__ == '__main__':
    try:
        with open('nifty_data.json', 'r') as f:
            test_data = json.load(f)

        processor = DataProcessor(test_data)

        weekly_expiry = processor.get_current_week_expiry()
        monthly_expiry = processor.get_current_month_expiry()

        print(f"Current week expiry: {weekly_expiry}")
        print(f"Current month expiry: {monthly_expiry}")

        if weekly_expiry:
            print("\n--- Weekly Expiry Data (5 strikes around ATM) ---")
            processed_data = processor.get_processed_option_chain(weekly_expiry, num_strikes=5)
            for item in processed_data:
                print(f"Strike: {item['strike']}, Call OI: {item['call_oi']}, Put OI: {item['put_oi']}")

            print("\n--- Weekly Expiry Data (ITM only, 5 strikes around ATM) ---")
            processed_data_itm = processor.get_processed_option_chain(weekly_expiry, num_strikes=5, itm_only=True)
            for item in processed_data_itm:
                print(f"Strike: {item['strike']}, Call OI: {item['call_oi']}, Put OI: {item['put_oi']}")

    except FileNotFoundError:
        print("nifty_data.json not found. Please run nse_fetcher.py first.")
    except Exception as e:
        print(f"An error occurred: {e}")
