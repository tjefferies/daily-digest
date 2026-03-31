"""FastAPI application for EverCurrent.

Configures the main application with CORS middleware for local
frontend development and provides the digest pipeline endpoints.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from evercurrent.context.personas import get_persona

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

    Looks up the persona, optionally applies a phase override,
    and returns the digest response. Without an Anthropic client
    configured, returns an empty digest structure suitable for
    frontend development and testing.

    Args:
        persona_id: Slack user ID of the persona.
        phase_override: Optional workstream:phase override (e.g. "chassis:DVT").

    Returns:
        A dict with persona_id, generated_at, and sections list.

    Raises:
        HTTPException: 404 if persona not found, 400 if phase_override invalid.
    """
    persona = get_persona(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Unknown persona: {persona_id}")

    if phase_override is not None:
        parts = phase_override.split(":")
        if len(parts) != 2:  # noqa: PLR2004
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phase_override: {phase_override!r}. Expected 'workstream:phase'",
            )

    return {
        "persona_id": persona_id,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "sections": [],
        "phase_override": phase_override,
    }
