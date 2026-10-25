"""FastAPI application entrypoint for UpSkill-AI."""

from fastapi import FastAPI

from backend.auth.faculty_views import faculty_router
from backend.auth.views import auth_router
from backend.catalogue.views import catalogue_router
from backend.middleware import CorrelationIdMiddleware, register_error_handlers
from backend.profile.routes import router as profile_router

app = FastAPI(
    title="UpSkill-AI API",
    description="AI-powered upskilling recommendation and automation system",
    version="0.2.0",
)

# Register Correlation ID and sanitized error handlers (CA-11, NFR-SEC-10)
app.add_middleware(CorrelationIdMiddleware)
register_error_handlers(app)

# Mount module routers
app.include_router(profile_router)
app.include_router(auth_router)
app.include_router(faculty_router)
app.include_router(catalogue_router)


@app.get("/")
def read_root():
    return {"message": "UpSkill-AI API is running"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/test/trigger-error")
def trigger_test_error():
    """Test endpoint that raises an unexpected exception to verify error sanitization (TC-F4-13)."""
    raise RuntimeError(
        "Unexpected internal failure with secret_token=XYZ123 and db_internal_id=999"
    )
