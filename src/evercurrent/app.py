"""FastAPI application for EverCurrent.

Configures the main application with CORS middleware for local
frontend development and provides a health check endpoint.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="EverCurrent",
    description="Context-aware Slack daily digest for robotics hardware teams",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return application health status.

    Returns:
        A dict with status key indicating the app is running.
    """
    return {"status": "ok"}
