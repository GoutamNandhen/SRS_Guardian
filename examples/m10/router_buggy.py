"""Trusted M10 negative sample: rejects only transfers above 20000."""
from fastapi import APIRouter

router = APIRouter(prefix="/payments")

@router.post("/transfer")
async def transfer_money(payload: dict):
    amount = payload.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        return {"accepted": False}
    return {"accepted": amount <= 20000}
