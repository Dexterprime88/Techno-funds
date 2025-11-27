from .schemas import KiteCredentials

credentials_storage = {}

def save_credentials(credentials: KiteCredentials):
    credentials_storage["kite_credentials"] = credentials.dict()
    return credentials_storage["kite_credentials"]

def get_credentials():
    return credentials_storage.get("kite_credentials")
