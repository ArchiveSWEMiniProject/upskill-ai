"""Minimal FastAPI application entrypoint for UpSkill-AI."""

from fastapi import FastAPI

from backend.profile.routes import router as profile_router

app = FastAPI(
    title="UpSkill-AI API",
    description="AI-powered upskilling recommendation and automation system",
    version="0.1.0",
)

app.include_router(profile_router)


@app.get("/")
def read_root():
    return {"message": "UpSkill-AI API is running"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
