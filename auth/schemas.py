from pydantic import BaseModel

class KiteCredentials(BaseModel):
    api_key: str
    api_secret: str
    request_token: str
    access_token: str
