"""Operator-buildable FastAPI test target, NOT an uploaded-code executor.

Use fixed example to exercise M4 protocol end-to-end after Docker is installed.
"""
from fastapi import FastAPI, APIRouter

app = FastAPI(title="M4 banking example")
router = APIRouter(prefix="/payments")

@router.post("/transfer")
async def transfer_money(payload: dict):
    """Reject transfers above 10000 rupees, matching example requirement."""
    amount = payload.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        return {"accepted": False, "reason": "invalid"}
    return {"accepted": amount <= 10000}

app.include_router(router)
