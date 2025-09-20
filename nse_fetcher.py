import requests
import json
import zlib
import brotli

class NSEFetcher:
    def __init__(self):
        self._session = requests.Session()
        self._headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'
        }
        self._base_url = "https://www.nseindia.com"
        self._option_chain_url = f"{self._base_url}/api/option-chain-indices?symbol="

        self._set_cookies()

    def _set_cookies(self):
        try:
            option_chain_page_url = f"{self._base_url}/option-chain"
            self._session.get(option_chain_page_url, headers=self._headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Error setting cookies: {e}")

    def fetch_option_chain(self, symbol):
        try:
            url = f"{self._option_chain_url}{symbol}"
            response = self._session.get(url, headers=self._headers, timeout=10)
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                try:
                    decompressed_data = zlib.decompress(response.content, 16+zlib.MAX_WBITS)
                    return json.loads(decompressed_data.decode('utf-8'))
                except zlib.error:
                    try:
                        decompressed_data = zlib.decompress(response.content, -zlib.MAX_WBITS)
                        return json.loads(decompressed_data.decode('utf-8'))
                    except zlib.error:
                        try:
                            decompressed_data = brotli.decompress(response.content)
                            return json.loads(decompressed_data.decode('utf-8'))
                        except Exception as e:
                            print(f"Failed to decompress with gzip, deflate, and brotli: {e}")
                            return None
        except Exception as e:
            print(f"Error fetching or processing data for {symbol}: {e}")
            return None


if __name__ == '__main__':
    fetcher = NSEFetcher()
    nifty_data = fetcher.fetch_option_chain('NIFTY')
    if nifty_data:
        print("Successfully fetched and processed Nifty option chain data.")
        with open('nifty_data.json', 'w') as f:
            json.dump(nifty_data, f, indent=2)
        print("Data saved to nifty_data.json")
    else:
        print("Failed to fetch Nifty option chain data.")
