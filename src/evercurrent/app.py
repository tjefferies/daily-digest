"""FastAPI application for EverCurrent.

Configures the main application with CORS middleware for local
frontend development and provides stub endpoints for the digest pipeline.
"""

from typing import Any

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


@app.post("/pipeline/run")
async def pipeline_run() -> dict[str, str]:
    """Trigger the extraction-to-digest pipeline.

    Stub endpoint that returns immediately. Will be wired to the
    real pipeline layers as they are implemented.

    Returns:
        A dict indicating this is a stub response.
    """
    return {"status": "stub"}


@app.get("/digest/{persona_id}")
async def get_digest(
    persona_id: str,
    phase_override: str | None = None,
) -> dict[str, Any]:
    """Retrieve the generated digest for a specific persona.

    Stub endpoint returning an empty digest structure. Will be
    wired to real digest generation as pipeline layers are built.

    Args:
        persona_id: Slack user ID of the persona.
        phase_override: Optional workstream:phase override (e.g. "chassis:DVT").

    Returns:
        A dict with persona_id and empty sections list.
    """
    return {
        "persona_id": persona_id,
        "sections": [],
        "phase_override": phase_override,
    }
