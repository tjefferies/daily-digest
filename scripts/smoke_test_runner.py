"""E2E smoke test: 3 random windows through the full pipeline.

Exercises every layer: ingestion (with semantic continuation detection
and FAISS-cached embeddings), 2-stage LLM extraction, validation,
confidence filtering, and Neo4j persistence.
"""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="  %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("smoke-test")

WINDOW_COUNT = 3


async def run_smoke_test() -> bool:
    """Run the full pipeline on 3 random windows.

    Returns:
        True if all stages succeed.
    """
    from evercurrent.config.loader import get_config
    from evercurrent.dataset.messages import load_messages
    from evercurrent.extraction.filter import confidence_filter
    from evercurrent.extraction.runner import AsyncExtractionRunner
    from evercurrent.extraction.validation import async_validate_atoms
    from evercurrent.graph.client import GraphClient
    from evercurrent.ingestion.cached_embedder import CachedEmbedder
    from evercurrent.ingestion.context_window import assemble_context_windows
    from evercurrent.ingestion.continuations import detect_continuations
    from evercurrent.ingestion.embeddings import SentenceTransformerEmbedder
    from evercurrent.ingestion.threads import group_by_thread
    from evercurrent.ingestion.vectorstore import VectorStore
    from evercurrent.llm.factory import create_async_llm_client
    from evercurrent.pipeline import _extract_standalones, _merge_continuations

    cfg = get_config()["pipeline"]

    # ── Stage 1: Ingestion ────────────────────────────────────────────────
    print("─── Stage 1: Ingestion ───")
    messages = load_messages()
    bundles = group_by_thread(messages)
    print(f"  Loaded {len(messages)} messages → {len(bundles)} threads")

    # ── Stage 2: Semantic continuation detection with FAISS cache ─────────
    print("\n─── Stage 2: Continuation Detection (semantic + FAISS) ───")
    vs_path = Path(cfg.get("vectorstore", {}).get("path", "data/vectorstore.index"))
    store = VectorStore.load(vs_path)
    embedder = SentenceTransformerEmbedder()
    cached = CachedEmbedder(embedder, store)

    standalones = _extract_standalones(messages, bundles)
    cont_matches = detect_continuations(bundles, standalones, embedder=cached)
    merged = _merge_continuations(bundles, cont_matches)
    print(f"  Standalones: {len(standalones)}, continuations merged: {merged}")
    hits, misses = cached.stats["cache_hits"], cached.stats["cache_misses"]
    print(f"  Embedding cache: {hits} hits, {misses} misses")

    # Save vectorstore
    store.save(vs_path)
    print(f"  VectorStore saved: {len(store)} embeddings → {vs_path}")

    # ── Stage 3: Select 3 random windows ──────────────────────────────────
    print("\n─── Stage 3: Context Windows (3 random) ───")
    all_windows = assemble_context_windows(bundles)
    if len(all_windows) < WINDOW_COUNT:
        print(f"  WARNING: Only {len(all_windows)} windows available")
        selected = all_windows
    else:
        selected = random.sample(all_windows, WINDOW_COUNT)
    print(f"  Selected {len(selected)} of {len(all_windows)} windows")
    for w in selected:
        mode = "compressed" if w.compressed else "full"
        print(f"    - {w.channel} thread_ts={w.thread_ts} ({mode})")

    # ── Stage 4: LLM Extraction (2-stage) ─────────────────────────────────
    print("\n─── Stage 4: LLM Extraction ───")
    client = create_async_llm_client()
    runner = AsyncExtractionRunner(client)
    raw_atoms = await runner.extract(selected)
    print(f"  Extracted {len(raw_atoms)} raw atoms from {len(selected)} windows")

    if not raw_atoms:
        print("  WARNING: No atoms extracted — check API key and model")
        return False

    # ── Stage 5: Validation ───────────────────────────────────────────────
    print("\n─── Stage 5: Validation ───")
    validated = raw_atoms
    for window in selected:
        validated = await async_validate_atoms(validated, client, window.thread_text)
    print(f"  Validated: {len(validated)} atoms")

    # ── Stage 6: Confidence filter ────────────────────────────────────────
    print("\n─── Stage 6: Confidence Filter ───")
    result = confidence_filter(validated)
    atoms = result.passed
    print(f"  Passed: {result.passed_count}, Filtered: {result.filtered_count}")

    # ── Stage 7: Neo4j persistence ────────────────────────────────────────
    print("\n─── Stage 7: Neo4j Persistence ───")
    neo4j_cfg = cfg["neo4j"]
    graph = GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )
    try:
        await graph.ensure_schema()
        await graph.persist_atoms(atoms)
        count = await graph.atom_count()
        print(f"  Persisted {len(atoms)} atoms (total in graph: {count})")
    except Exception as exc:
        print(f"  ERROR: Neo4j persistence failed: {exc}")
        print("  Is Neo4j running? Try: docker compose up neo4j -d")
        return False
    finally:
        await graph.close()

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n═══════════════════════════════════════")
    print("  Smoke Test Summary")
    print("═══════════════════════════════════════")
    print(f"  Windows processed:    {len(selected)}")
    print(f"  Atoms extracted:      {len(raw_atoms)}")
    print(f"  Atoms after filter:   {len(atoms)}")
    print(f"  Atoms in Neo4j:       {count}")
    print(f"  Embeddings cached:    {len(store)}")
    print(f"  Cache hits/misses:    {cached.stats['cache_hits']}/{cached.stats['cache_misses']}")
    print("═══════════════════════════════════════")

    for atom in atoms[:5]:
        print(f"  [{atom.type}] {atom.summary}")
    if len(atoms) > 5:
        print(f"  ... and {len(atoms) - 5} more")

    return True


if __name__ == "__main__":
    success = asyncio.run(run_smoke_test())
    sys.exit(0 if success else 1)
