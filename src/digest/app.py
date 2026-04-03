"""FastAPI application for Daily Digest Tool.

Configures the main application with CORS middleware for local
frontend development and provides the digest pipeline endpoints.
Wires extraction (Ingestion → Extraction → Validation → Filter)
with scoring and generation to produce per-persona digests.

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

from digest.config.loader import get_config
from digest.context.personas import get_persona
from digest.db.session import get_session_factory
from digest.extraction.batch_runner import BatchExtractionRunner
from digest.generation.assembler import AsyncDigestAssembler
from digest.graph.client import GraphClient
from digest.llm.factory import create_async_llm_client
from digest.pipeline import async_run_pipeline
from digest.scoring.composite import score_atoms

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from digest.models.atom import Atom

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
    title="Daily Digest Tool",
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


async def _load_atoms_from_neo4j(date: str | None = None) -> list[Atom]:
    """Load atoms from Neo4j, optionally filtered by date.

    Args:
        date: Optional ISO date string (e.g. "2026-04-01") to filter atoms.

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
        if date:
            atoms = await graph.load_atoms_by_date(date)
        else:
            atoms = await graph.load_all_atoms()
        if atoms:
            logger.info("Loaded %d atoms from Neo4j (date=%s)", len(atoms), date)
        return atoms
    except Exception:
        logger.warning("Failed to load atoms from Neo4j", exc_info=True)
        return []
    finally:
        await graph.close()


async def _precook_digests(atoms: list[Atom]) -> None:
    """Pre-generate digests and persist :DIGEST edges to Neo4j.

    Uses asyncio.gather to generate all 3 persona digests concurrently.
    Also scores atoms per persona and persists :DIGEST relationships
    with score and created_at properties to Neo4j.

    Args:
        atoms: Extracted atoms from the pipeline.
    """
    if not atoms:
        return

    client = create_async_llm_client()
    assembler = AsyncDigestAssembler(client)
    created_at = datetime.now(tz=UTC).isoformat()

    async def _generate_one(persona_id: str) -> None:
        try:
            digest = await assembler.assemble(persona_id, atoms)
            _digest_cache[persona_id] = digest
            section_count = len(digest.get("sections", []))
            logger.info(
                "Pre-generated digest for %s: %d sections",
                persona_id,
                section_count,
            )
            # Persist :DigestRun + :INCLUDES edges to Neo4j
            await _persist_digest_to_neo4j(persona_id, atoms, created_at, digest)
        except Exception:
            logger.warning(
                "Failed to pre-generate digest for %s",
                persona_id,
                exc_info=True,
            )

    await asyncio.gather(*[_generate_one(pid) for pid in _DEMO_PERSONAS])


async def _persist_digest_to_neo4j(
    persona_id: str,
    atoms: list[Atom],
    created_at: str,
    digest: dict[str, Any],
) -> None:
    """Persist digest to Neo4j: :DigestRun node + :INCLUDES edges.

    Creates the graph structure:
    :Person -[:HAS_DIGEST]-> :DigestRun -[:INCLUDES {score}]-> :Atom

    Args:
        persona_id: Persona user_id.
        atoms: Atoms that were scored.
        created_at: ISO timestamp for this run.
        digest: The generated digest dict with sections.
    """
    import json

    persona = get_persona(persona_id)
    if persona is None:
        return

    run_date = created_at[:10]
    sections_json = json.dumps(digest.get("sections", []))
    generated_at = digest.get("generated_at", created_at)

    scored = score_atoms(atoms, persona)
    scored_pairs = [(str(sa.atom.atom_id), sa.score) for sa in scored]

    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        await graph.persist_digest_run(
            persona_id,
            run_date,
            sections_json,
            generated_at,
        )
        await graph.persist_digest_includes(persona_id, run_date, scored_pairs)
    except Exception:
        logger.warning(
            "Failed to persist digest to Neo4j for %s",
            persona_id,
            exc_info=True,
        )
    finally:
        await graph.close()


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


async def _clear_demo_data() -> None:
    """Clear all Postgres data so demo re-runs extract fresh atoms.

    Truncates all tables via raw SQL to bypass FK constraints.
    """
    from sqlalchemy import text

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("DELETE FROM atom"))
        await session.execute(text("DELETE FROM context_window"))
        await session.execute(text("DELETE FROM bundle_membership"))
        await session.execute(text("DELETE FROM thread_bundle"))
        await session.execute(text("DELETE FROM message"))
        await session.execute(text("DELETE FROM batch_log"))
        await session.commit()
    logger.info("Cleared Postgres demo data for fresh run")


@app.post("/pipeline/run")
async def pipeline_run(fresh: bool = False) -> dict[str, Any]:
    """Trigger the extraction-to-digest pipeline in the background.

    Returns immediately with status. Poll GET /pipeline/status for progress.

    Args:
        fresh: If True, clear Postgres data first so dedup doesn't skip
            previously processed bundles. Required for demo re-runs.

    Returns:
        A dict with status indicating the pipeline has started.
    """
    global _pipeline_task  # noqa: PLW0603

    if _pipeline_status["state"] == "running":
        return {"status": "already_running", "message": "Pipeline is already in progress"}

    if fresh:
        try:
            await _clear_demo_data()
        except Exception:
            logger.warning("Failed to clear demo data", exc_info=True)

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


async def _resolve_atoms() -> list[Atom]:
    """Load atoms for digest generation from in-memory store or Neo4j.

    Returns:
        List of Atom objects.
    """
    atoms = list(_atom_store)
    if atoms:
        return atoms

    try:
        return await _load_atoms_from_neo4j()
    except Exception:
        logger.warning("Neo4j fallback failed in digest", exc_info=True)
        return []


async def _load_digest_from_graph(
    persona_id: str,
    target_date: str,
) -> dict[str, Any] | None:
    """Load a rendered digest from Neo4j :DigestRun node.

    Falls back to re-generating from :DIGEST scored edges if no
    rendered version exists.

    Args:
        persona_id: Persona user_id.
        target_date: ISO date string to filter by.

    Returns:
        Digest dict with sections, or None if no data.
    """
    import json

    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        # Try rendered :DigestRun first (no LLM call needed)
        run = await graph.load_digest_run(persona_id, target_date)
        if run:
            return {
                "persona_id": persona_id,
                "generated_at": str(run["generated_at"]),
                "sections": json.loads(run["sections_json"]),
            }

        # Fallback: re-generate from :INCLUDES scored edges
        results = await graph.load_digest_atoms(persona_id, target_date)
        if not results:
            return None
        atoms = [atom for atom, _score in results]
        client = create_async_llm_client()
        assembler = AsyncDigestAssembler(client)
        return await assembler.assemble(persona_id, atoms)
    except Exception:
        logger.warning("Failed to load digest from graph", exc_info=True)
        return None
    finally:
        await graph.close()


@app.get("/digest/dates")
async def get_digest_dates() -> list[str]:
    """Return available DigestRun dates from Neo4j, most recent first.

    Returns:
        List of ISO date strings (e.g. ["2026-04-02", "2026-04-01", ...]).
    """
    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        async with graph._driver.session() as session:
            result = await session.run(
                "MATCH (dr:DigestRun) WHERE dr.run_date <= date('2026-04-02')"
                " RETURN DISTINCT dr.run_date AS d ORDER BY d DESC",
            )
            return [str(r["d"]) for r in await result.data()]
    except Exception:
        logger.warning("Failed to load digest dates", exc_info=True)
        return []
    finally:
        await graph.close()


@app.get("/digest/{persona_id}")
async def get_digest(
    persona_id: str,
    phase_override: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Retrieve the generated digest for a specific persona.

    Serves from pre-generated cache when available. For date-filtered
    queries, loads pre-scored atoms from Neo4j :DIGEST edges.

    Args:
        persona_id: Slack user ID of the persona.
        phase_override: Optional workstream:phase override (e.g. "chassis:DVT").
        date: Optional ISO date string (e.g. "2026-04-01") to filter by
            :DIGEST edge created_at.

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

    # Date filter: use :DIGEST edges from Neo4j (never fall through to cache)
    if date is not None:
        result = await _load_digest_from_graph(persona_id, date)
        if result:
            return result
        return {
            "persona_id": persona_id,
            "generated_at": f"{date}T00:00:00+00:00",
            "sections": [],
        }

    # Return cached digest if available (no override)
    if phase_override is None and persona_id in _digest_cache:
        return _digest_cache[persona_id]

    atoms = await _resolve_atoms()
    if not atoms:
        return {
            "persona_id": persona_id,
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "sections": [],
            "phase_override": phase_override,
        }

    client = create_async_llm_client()
    assembler = AsyncDigestAssembler(client)
    return await assembler.assemble(persona_id, atoms, phase_override)


@app.get("/source/{atom_id}")
async def get_source_thread(atom_id: str) -> dict[str, Any]:
    """Return the source thread messages for an atom.

    Looks up the atom's source channel and thread_ts in Neo4j,
    then finds the matching thread in the loaded fixture data.

    Args:
        atom_id: UUID of the atom.

    Returns:
        Dict with channel, thread_ts, and messages list.
    """
    from digest.dataset.messages import _DEMO_PATH, _FIXTURE_PATH, _load_from_fixture

    # Look up atom source from Neo4j
    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        async with graph._driver.session() as session:
            result = await session.run(
                "MATCH (a:Atom {atom_id: $id}) "
                "RETURN a.channel AS channel, a.thread_ts AS thread_ts",
                id=atom_id,
            )
            record = await result.single()
    finally:
        await graph.close()

    if not record:
        raise HTTPException(status_code=404, detail=f"Atom not found: {atom_id}")

    channel = record["channel"]
    thread_ts = record["thread_ts"]

    # Search both fixtures for the matching thread
    all_messages = _load_from_fixture(_FIXTURE_PATH) + _load_from_fixture(_DEMO_PATH)
    thread_msgs = [
        {"user_id": m.user_id, "text": m.text, "ts": m.message_ts}
        for m in all_messages
        if m.channel == channel and (m.message_ts == thread_ts or m.thread_ts == thread_ts)
    ]
    thread_msgs.sort(key=lambda m: m["ts"])

    return {
        "channel": channel,
        "thread_ts": thread_ts,
        "messages": thread_msgs,
    }
