from fastapi import APIRouter, HTTPException
from . import crud, schemas
from kiteconnect import KiteConnect

router = APIRouter()

@router.post("/credentials", response_model=schemas.KiteCredentials)
def set_credentials(credentials: schemas.KiteCredentials):
    return crud.save_credentials(credentials)

@router.get("/credentials", response_model=schemas.KiteCredentials)
def get_credentials():
    return crud.get_credentials()

@router.post("/generate-token", response_model=dict)
def generate_token(token_request: schemas.TokenRequest):
    try:
        kite = KiteConnect(api_key=token_request.api_key)
        data = kite.generate_session(token_request.request_token, api_secret=token_request.api_secret)
        access_token = data["access_token"]

        # Create the full credentials object to be stored
        full_credentials = schemas.KiteCredentials(
            api_key=token_request.api_key,
            api_secret=token_request.api_secret,
            request_token=token_request.request_token,
            access_token=access_token
        )

        # Save the complete credentials for use by other services
        crud.save_credentials(full_credentials)

        return {"access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
