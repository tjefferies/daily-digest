"""FastAPI application for EverCurrent.

Configures the main application with CORS middleware for local
frontend development and provides the digest pipeline endpoints.
Wires the full 5-layer pipeline: Ingestion → Extraction → Scoring → Generation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from evercurrent.config.loader import get_config
from evercurrent.context.personas import get_persona
from evercurrent.generation.assembler import AsyncDigestAssembler
from evercurrent.graph.client import GraphClient
from evercurrent.llm.factory import create_async_llm_client
from evercurrent.pipeline import async_run_pipeline

if TYPE_CHECKING:
    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EverCurrent",
    description="Context-aware Slack daily digest for robotics hardware teams",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_config()["pipeline"]["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory atom store: populated by /pipeline/run, consumed by /digest.
_atom_store: list[Atom] = []


def clear_atom_store() -> None:
    """Clear the in-memory atom store.

    Used by tests to reset state between test cases.
    """
    _atom_store.clear()


async def _load_atoms_from_neo4j() -> list[Atom]:
    """Load atoms from Neo4j, returning empty list on failure.

    Returns:
        List of Atom objects from the graph, or empty list.
    """
    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        atoms = await graph.load_all_atoms()
        if atoms:
            logger.info("Loaded %d atoms from Neo4j for digest", len(atoms))
        return atoms
    except Exception:
        logger.warning("Failed to load atoms from Neo4j", exc_info=True)
        return []
    finally:
        await graph.close()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return application health status.

    Returns:
        A dict with status key indicating the app is running.
    """
    return {"status": "ok"}


@app.post("/pipeline/run")
async def pipeline_run() -> dict[str, Any]:
    """Trigger the extraction-to-digest pipeline.

    Runs the full Ingestion → Extraction → Filter → Validation pipeline
    and stores extracted atoms for subsequent /digest requests.

    Returns:
        A dict with status and processing stats.
    """
    client = create_async_llm_client()
    result = await async_run_pipeline(client)

    _atom_store.clear()
    _atom_store.extend(result.atoms)

    logger.info("Pipeline complete: %d atoms stored", len(result.atoms))
    return {
        "status": "complete",
        "stats": result.stats,
    }


@app.get("/digest/{persona_id}")
async def get_digest(
    persona_id: str,
    phase_override: str | None = None,
) -> dict[str, Any]:
    """Retrieve the generated digest for a specific persona.

    Tries atoms from: (1) in-memory store, (2) Neo4j graph.
    If both are empty, returns an empty digest structure.

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

    # Try in-memory store first, then Neo4j
    atoms: list[Atom] = list(_atom_store)
    if not atoms:
        try:
            atoms = await _load_atoms_from_neo4j()
        except Exception:
            logger.warning("Neo4j fallback failed in digest", exc_info=True)
            atoms = []

    if not atoms:
        return {
            "persona_id": persona_id,
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "sections": [],
            "phase_override": phase_override,
        }

    # Wire the assembler with available atoms
    client = create_async_llm_client()
    assembler = AsyncDigestAssembler(client)
    return await assembler.assemble(persona_id, atoms, phase_override)
