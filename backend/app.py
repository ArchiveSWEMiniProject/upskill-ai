from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.dashboard import models as dashboard_models  # noqa: F401
from backend.dashboard.routes import router as dashboard_router
from backend.database import Base, engine
from backend.evidence import models as evidence_models  # noqa: F401
from backend.progress import models as progress_models  # noqa: F401
from backend.progress.exceptions import DomainError
from backend.progress.routes import router as progress_router

app = FastAPI(title="UpSkill-AI M3 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Student-Id"],
)
app.include_router(progress_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code, content={"code": exc.code, "detail": exc.message}
    )


@app.get("/health")
def health():
    return {"status": "ok"}


def create_m3_tables() -> None:
    """Local bootstrap only; replace with team-owned Alembic migrations."""
    Base.metadata.create_all(bind=engine)
