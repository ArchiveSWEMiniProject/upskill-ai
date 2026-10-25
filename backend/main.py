"""FastAPI application entrypoint for UpSkill-AI."""

from fastapi import FastAPI

from backend.auth.faculty_views import faculty_router
from backend.auth.views import auth_router
from backend.catalogue.views import catalogue_router
from backend.profile.routes import router as profile_router

app = FastAPI(
    title="UpSkill-AI API",
    description="AI-powered upskilling recommendation and automation system",
    version="0.2.0",
)

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
