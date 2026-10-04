"""Minimal FastAPI application entrypoint for UpSkill-AI."""

from fastapi import FastAPI

app = FastAPI(
    title="UpSkill-AI API",
    description="AI-powered upskilling recommendation and automation system",
    version="0.1.0",
)


@app.get("/")
def read_root():
    return {"message": "UpSkill-AI API is running"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
