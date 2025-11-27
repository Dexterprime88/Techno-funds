from kiteconnect import KiteConnect
from auth.crud import get_credentials

def get_kite_client():
    credentials = get_credentials()
    if not credentials:
        raise Exception("Kite credentials not set")

    kite = KiteConnect(api_key=credentials["api_key"])
    kite.set_access_token(credentials["access_token"])
    return kite
