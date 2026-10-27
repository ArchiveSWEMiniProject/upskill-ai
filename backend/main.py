"""FastAPI application entrypoint for UpSkill-AI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.auth.faculty_views import faculty_router
from backend.auth.security import jwt_secret
from backend.auth.views import auth_router
from backend.catalogue.views import catalogue_router
from backend.profile.routes import router as profile_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    jwt_secret()  # refuse to start without a signing secret
    yield


app = FastAPI(
    lifespan=lifespan,
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
