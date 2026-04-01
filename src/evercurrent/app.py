"""FastAPI application for EverCurrent.

Configures the main application with CORS middleware for local
frontend development and provides the digest pipeline endpoints.
Wires the full 5-layer pipeline: Ingestion → Extraction → Scoring → Generation.

After pipeline/run, pre-generates digests for all 3 demo personas
so the frontend loads instantly without additional LLM calls.
Pipeline runs asynchronously in the background; poll /pipeline/status.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from evercurrent.config.loader import get_config
from evercurrent.context.personas import get_persona
from evercurrent.extraction.batch_runner import BatchExtractionRunner
from evercurrent.generation.assembler import AsyncDigestAssembler
from evercurrent.graph.client import GraphClient
from evercurrent.llm.factory import create_async_llm_client
from evercurrent.pipeline import async_run_pipeline

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Schedule background precook from Neo4j, don't block startup."""

    async def _background_precook() -> None:
        await asyncio.sleep(5)  # wait for Neo4j to be ready
        atoms = await _load_atoms_from_neo4j()
        if atoms:
            _atom_store.extend(atoms)
            await _precook_digests(atoms)
            logger.info("Background precook: %d atoms, %d digests", len(atoms), len(_digest_cache))

    asyncio.create_task(_background_precook())
    yield


app = FastAPI(
    title="EverCurrent",
    description="Context-aware Slack daily digest for robotics hardware teams",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_config()["pipeline"]["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo persona IDs matching frontend/src/components/PersonaSelector.tsx
_DEMO_PERSONAS = ["U001", "U007", "U010"]

# In-memory atom store: populated by /pipeline/run.
_atom_store: list[Atom] = []

# Pre-generated digest cache: persona_id → digest dict.
_digest_cache: dict[str, dict[str, Any]] = {}

# Pipeline run state for async status polling.
_pipeline_status: dict[str, Any] = {
    "state": "idle",  # idle | running | complete | failed
    "stage": "",
    "batch_id": "",
    "progress": {"total": 0, "succeeded": 0, "processing": 0, "errored": 0},
    "stats": {},
    "error": None,
}
_pipeline_task: asyncio.Task[None] | None = None
_batch_runner: Any = None  # Reference to active BatchExtractionRunner  # noqa: ANN401


def clear_atom_store() -> None:
    """Clear the in-memory atom store and digest cache.

    Used by tests to reset state between test cases.
    """
    _atom_store.clear()
    _digest_cache.clear()
    _pipeline_status.update(state="idle", stage="", stats={}, error=None)


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


async def _precook_digests(atoms: list[Atom]) -> None:
    """Pre-generate digests for all demo personas.

    Args:
        atoms: Extracted atoms from the pipeline.
    """
    if not atoms:
        return

    client = create_async_llm_client()
    assembler = AsyncDigestAssembler(client)

    for persona_id in _DEMO_PERSONAS:
        try:
            digest = await assembler.assemble(persona_id, atoms)
            _digest_cache[persona_id] = digest
            section_count = len(digest.get("sections", []))
            logger.info(
                "Pre-generated digest for %s: %d sections",
                persona_id,
                section_count,
            )
        except Exception:
            logger.warning(
                "Failed to pre-generate digest for %s",
                persona_id,
                exc_info=True,
            )


async def _run_pipeline_background() -> None:
    """Run the pipeline in the background, updating status as it progresses."""
    global _batch_runner  # noqa: PLW0603
    try:
        runner = BatchExtractionRunner(Anthropic())
        _batch_runner = runner
        _pipeline_status.update(
            state="running",
            stage="extraction",
            error=None,
            batch_id="",
            progress={"total": 0, "succeeded": 0, "processing": 0, "errored": 0},
        )

        client = create_async_llm_client()
        result = await async_run_pipeline(client, batch_runner=runner)

        _atom_store.clear()
        _atom_store.extend(result.atoms)
        _digest_cache.clear()

        # If no new atoms extracted (delta dedup skipped all), load from Neo4j
        atoms_for_digest = list(result.atoms)
        if not atoms_for_digest:
            atoms_for_digest = await _load_atoms_from_neo4j()
            _atom_store.extend(atoms_for_digest)

        logger.info(
            "Pipeline complete: %d new atoms, %d total for digest",
            len(result.atoms),
            len(atoms_for_digest),
        )

        _pipeline_status.update(
            stage="generating_digests",
            stats=result.stats,
            batch_id="",
            progress={"total": 0, "succeeded": 0, "processing": 0, "errored": 0},
        )

        await _precook_digests(atoms_for_digest)

        _pipeline_status.update(
            state="complete",
            stage="done",
            stats=result.stats,
        )
    except Exception as exc:
        logger.warning("Pipeline failed", exc_info=True)
        _pipeline_status.update(state="failed", error=str(exc))
    finally:
        _batch_runner = None


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return application health status.

    Returns:
        A dict with status key indicating the app is running.
    """
    return {"status": "ok"}


@app.post("/pipeline/run")
async def pipeline_run() -> dict[str, Any]:
    """Trigger the extraction-to-digest pipeline in the background.

    Returns immediately with status. Poll GET /pipeline/status for progress.

    Returns:
        A dict with status indicating the pipeline has started.
    """
    global _pipeline_task  # noqa: PLW0603

    if _pipeline_status["state"] == "running":
        return {"status": "already_running", "message": "Pipeline is already in progress"}

    _pipeline_task = asyncio.create_task(_run_pipeline_background())
    return {
        "status": "started",
        "message": "Pipeline started. Poll GET /pipeline/status for progress.",
    }


@app.get("/pipeline/status")
async def pipeline_status() -> dict[str, Any]:
    """Return current pipeline run status with batch progress.

    Returns:
        A dict with state, stage, batch_id, progress, stats, and error.
    """
    # Read live progress from the active batch runner
    progress = dict(_pipeline_status.get("progress", {}))
    batch_id = _pipeline_status.get("batch_id", "")
    stage = _pipeline_status["stage"]

    if _batch_runner is not None:
        progress = {
            "total": _batch_runner.progress["total"],
            "succeeded": _batch_runner.progress["succeeded"],
            "processing": _batch_runner.progress["processing"],
            "errored": _batch_runner.progress["errored"],
        }
        batch_id = _batch_runner.progress.get("batch_id", "")
        stage = _batch_runner.progress.get("stage", stage)

    return {
        "state": _pipeline_status["state"],
        "stage": stage,
        "batch_id": batch_id,
        "progress": progress,
        "stats": _pipeline_status["stats"],
        "error": _pipeline_status["error"],
    }


@app.get("/digest/{persona_id}")
async def get_digest(
    persona_id: str,
    phase_override: str | None = None,
) -> dict[str, Any]:
    """Retrieve the generated digest for a specific persona.

    Serves from pre-generated cache when available. Falls back to
    on-demand generation from in-memory atoms or Neo4j.

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

    # Return cached digest if available (no phase override)
    if phase_override is None and persona_id in _digest_cache:
        return _digest_cache[persona_id]

    # On-demand generation: try in-memory store first, then Neo4j
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

    # Generate on demand (phase override or uncached persona)
    client = create_async_llm_client()
    assembler = AsyncDigestAssembler(client)
    return await assembler.assemble(persona_id, atoms, phase_override)
