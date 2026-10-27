"""M3 demo API: approved test oracles, fixed synthetic targets, no uploaded-code execution."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from backend.app.services.conformance_verification import (
    TARGETS, UnsupportedRequirement, parse_transfer_rule, plan_cases, verify_trusted_demo,
)

router = APIRouter(prefix="/conformance", tags=["Conformance — trusted demo"])


class PreviewRequest(BaseModel):
    req_key: str = Field(min_length=1, max_length=100)
    requirement_text: str = Field(min_length=1, max_length=1200)


class DemoRunRequest(PreviewRequest):
    target_id: Literal["demo_correct", "demo_buggy"]
    oracle_approved: bool = False


@router.get("/targets")
def get_demo_targets():
    return {"demo_only": True,
            "targets": [{"id": k, "description": v["description"]} for k, v in TARGETS.items()]}


@router.post("/preview")
def preview_conformance(request: PreviewRequest):
    try:
        rule = parse_transfer_rule(request.req_key, request.requirement_text)
    except UnsupportedRequirement as exc:
        return {"supported": False, "decision": "needs_human_clarification",
                "reason": str(exc), "demo_only": True}
    return {"supported": True, "decision": "not_executed", "demo_only": True,
            "threshold": rule.threshold, "draft_cases": plan_cases(rule),
            "oracle_assumption": "Reviewer must approve that JSON accepted=false denotes rejection",
            "note": "Preview alone does not verify a code link or software behavior."}


@router.post("/demo/run")
async def execute_demo(request: DemoRunRequest):
    try:
        return await verify_trusted_demo(req_key=request.req_key,
                                         text=request.requirement_text,
                                         target_id=request.target_id,
                                         oracle_approved=request.oracle_approved)
    except (ValueError, UnsupportedRequirement) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
