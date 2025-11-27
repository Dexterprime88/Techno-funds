from fastapi import FastAPI
from auth.router import router as auth_router
from services.kite_api.router import router as kite_api_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth")
app.include_router(kite_api_router, prefix="/kite")

@app.get("/")
def read_root():
    return {"Hello": "World"}
