"""FastAPI application entrypoint for UpSkill-AI."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from backend.auth.faculty_views import faculty_router
from backend.auth.security import jwt_secret
from backend.auth.views import auth_router
from backend.catalogue.views import catalogue_router
from backend.database import database_url
from backend.gap.routes import router as gap_router
from backend.middleware import CorrelationIdMiddleware, register_error_handlers
from backend.profile import resume_cleanup
from backend.profile.routes import router as profile_router
from backend.skills.routes import router as skills_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    jwt_secret()  # refuse to start without a real signing secret
    # ...or with the example database password. Tests that swap in their own
    # session leave DATABASE_URL unset, so it is only checked when present.
    if os.environ.get("DATABASE_URL"):
        database_url()
    interval = resume_cleanup.interval_seconds()
    cleanup = (
        asyncio.create_task(resume_cleanup.purge_periodically(interval)) if interval > 0 else None
    )
    yield
    if cleanup:
        cleanup.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup


app = FastAPI(
    lifespan=lifespan,
    title="UpSkill-AI API",
    description="AI-powered upskilling recommendation and automation system",
    version="0.2.0",
)

# Register Correlation ID and sanitized error handlers (CA-11, NFR-SEC-10)
app.add_middleware(CorrelationIdMiddleware)
register_error_handlers(app)

# Mount module routers
app.include_router(profile_router)
app.include_router(skills_router)
app.include_router(auth_router)
app.include_router(faculty_router)
app.include_router(catalogue_router)
app.include_router(gap_router)


@app.get("/")
def read_root():
    return {"message": "UpSkill-AI API is running"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

