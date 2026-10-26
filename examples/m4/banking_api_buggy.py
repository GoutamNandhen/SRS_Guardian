"""Deliberately faulty review-only variant of the banking FastAPI service."""
from fastapi import FastAPI, APIRouter

app = FastAPI(title="M4 intentionally buggy banking example")
router = APIRouter(prefix="/payments")

@router.post("/transfer")
async def transfer_money(payload: dict):
    """Bug: accidentally permits transfers up to 20000 instead of 10000."""
    amount = payload.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        return {"accepted": False, "reason": "invalid"}
    return {"accepted": amount <= 20000}

app.include_router(router)
