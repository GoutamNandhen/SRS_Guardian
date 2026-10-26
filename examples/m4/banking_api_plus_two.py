"""M11 controlled negative fixture: a narrow transfer-limit violation at +2 only.

This is an intentionally faulty, repository-owned FastAPI test application.
Not representative of real-world project accuracy.
"""
from fastapi import FastAPI, APIRouter

app = FastAPI(title="M11 deliberately narrow faulty banking fixture")
router = APIRouter(prefix="/payments")


@router.post("/transfer")
async def transfer_money(payload: dict):
    amount = payload.get("amount")
    if type(amount) is not int or amount < 0:
        return {"accepted": False, "reason": "invalid"}
    return {"accepted": amount <= 10000 or amount == 10002}


app.include_router(router)
