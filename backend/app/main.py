from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.documents import router as documents_router

app = FastAPI(
    title="SRS Guardian API",
    description="AI-assisted review platform for Software Requirement Specifications",
    version="0.1.0",
)

app.include_router(documents_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

