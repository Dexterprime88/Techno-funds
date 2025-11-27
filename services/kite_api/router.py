from fastapi import APIRouter
from . import kite

router = APIRouter()

@router.get("/option-chain/{instrument}")
def get_option_chain(instrument: str):
    # In a real application, you would call the Kite API here.
    # For now, we'll return a sample response.
    return {
        "instrument": instrument,
        "calls": [
            {"strike": 17000, "oi": 100000, "oi_change": 1000, "delta": 0.5, "ltp": 100},
            {"strike": 17100, "oi": 120000, "oi_change": -500, "delta": 0.4, "ltp": 80},
        ],
        "puts": [
            {"strike": 17000, "oi": 90000, "oi_change": 2000, "delta": -0.5, "ltp": 90},
            {"strike": 16900, "oi": 110000, "oi_change": -1000, "delta": -0.6, "ltp": 110},
        ],
    }
