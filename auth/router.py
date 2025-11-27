from fastapi import APIRouter
from . import crud, schemas

router = APIRouter()

@router.post("/credentials", response_model=schemas.KiteCredentials)
def set_credentials(credentials: schemas.KiteCredentials):
    return crud.save_credentials(credentials)

@router.get("/credentials", response_model=schemas.KiteCredentials)
def get_credentials():
    return crud.get_credentials()
