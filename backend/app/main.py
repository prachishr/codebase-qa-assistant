from fastapi import FastAPI  # type: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings

app = FastAPI(
    title="Codebase QA Assistant API",
    description="Backend API for the Codebase QA Assistant",
    version="1.0.0"
)

allowed_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://codebase-qa-assistant-frontend.vercel.app"
]

if settings.FRONTEND_URL and settings.FRONTEND_URL not in allowed_origins:
    allowed_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Codebase QA Assistant API is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.repositories import router as repository_router
app.include_router(auth_router, prefix="/api/v1")
app.include_router(repository_router, prefix="/api/v1")

from backend.app.api.v1.conversations import router as conversations_router

app.include_router(
    conversations_router,
    prefix="/api/v1"
)