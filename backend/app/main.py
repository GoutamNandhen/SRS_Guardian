from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.documents import router as documents_router
from backend.app.api.requirements import router as requirements_router
from backend.app.api.issues import router as issues_router
from backend.app.api.contradictions import router as contradictions_router
from backend.app.api.review_reports import router as review_reports_router
from backend.app.api.profile import router as profile_router
from backend.app.api.code_traceability import router as code_traceability_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SRS Guardian API",
    description="AI-assisted review platform for Software Requirement Specifications",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api")
app.include_router(requirements_router, prefix="/api")
app.include_router(issues_router, prefix="/api")
app.include_router(contradictions_router, prefix="/api")
app.include_router(review_reports_router, prefix="/api")
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(code_traceability_router, prefix="/api")




@app.get("/health")
def health_check() -> dict[str, str]:
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

