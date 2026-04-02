"""Integration test: 2-window async pipeline writes atoms to Neo4j.

Requires: ANTHROPIC_API_KEY + Neo4j running (docker compose up neo4j).
Proves: ingestion → async extraction → validation → filter → Neo4j persist.
Uses async mode (not batch) for faster turnaround.
"""

from __future__ import annotations

import os
import random

import pytest

from digest.config.loader import get_config
from digest.dataset.messages import load_messages
from digest.extraction.filter import confidence_filter
from digest.extraction.runner import AsyncExtractionRunner
from digest.extraction.validation import async_validate_atoms_batch
from digest.graph.client import GraphClient
from digest.ingestion.context_window import assemble_context_windows
from digest.ingestion.threads import group_by_thread
from digest.llm.factory import create_async_llm_client


@pytest.mark.integration
class TestPipelineToNeo4j:
    """Run 2 random windows through async extraction and verify Neo4j."""

    @pytest.fixture(autouse=True)
    def _require_services(self) -> None:
        """Skip if API key or Neo4j not available."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

    @pytest.fixture
    async def graph(self):
        """Create a GraphClient connected to the running Neo4j."""
        cfg = get_config()["pipeline"]["neo4j"]
        client = GraphClient(uri=cfg["uri"], user=cfg["user"], password=cfg["password"])
        await client.ensure_schema()
        yield client
        await client.close()

    async def test_2_windows_produce_atoms_in_neo4j(self, graph: GraphClient) -> None:
        """2 random windows → async extract → validate → filter → Neo4j."""
        # Get atom count before
        count_before = await graph.atom_count()

        # Ingestion: pick 2 random windows
        messages = load_messages()
        bundles = group_by_thread(messages)
        windows = assemble_context_windows(bundles)
        selected = random.sample(windows, 2)

        print("\n  Selected windows:")
        for w in selected:
            print(f"    {w.channel} thread_ts={w.thread_ts}")

        # Extraction (async mode - individual calls, faster for 2 windows)
        client = create_async_llm_client()
        runner = AsyncExtractionRunner(client)
        raw_atoms = await runner.extract(selected)

        print(f"  Extracted: {len(raw_atoms)} raw atoms")
        assert len(raw_atoms) > 0, "No atoms extracted from 2 windows"

        # Validation - collect all (index, atom, context) tuples for batch
        window_text_by_ts = {w.thread_ts: w.thread_text for w in selected}
        atoms_with_context = []
        for i, atom in enumerate(raw_atoms):
            if atom.type in ("SPEC_CHANGE", "DECISION"):
                ctx = window_text_by_ts.get(atom.source.thread_ts, "")
                if ctx:
                    atoms_with_context.append((i, atom, ctx))

        validated = await async_validate_atoms_batch(atoms_with_context, raw_atoms)

        print(f"  After validation: {len(validated)} atoms")

        # Confidence filter
        result = confidence_filter(validated)
        atoms = result.passed

        print(f"  After filter: {len(atoms)} atoms (filtered {result.filtered_count})")

        # Persist to Neo4j
        await graph.persist_atoms(atoms)

        # Verify atoms are in Neo4j
        count_after = await graph.atom_count()
        new_atoms = count_after - count_before

        print(f"  Neo4j: {count_before} before → {count_after} after (+{new_atoms})")

        assert new_atoms >= len(atoms), (
            f"Expected at least {len(atoms)} new atoms in Neo4j, "
            f"but only {new_atoms} appeared. "
            f"Atoms are NOT making it to Neo4j!"
        )

        # Verify we can query them back
        all_atoms = await graph.load_all_atoms()
        neo4j_summaries = {a.summary for a in all_atoms}

        for atom in atoms:
            assert atom.summary in neo4j_summaries, (
                f"Atom '{atom.summary}' was persisted but not found "
                f"when querying Neo4j back. Read-after-write failed!"
            )

        print(f"  Read-after-write: all {len(atoms)} atoms verified in Neo4j")

        # Print what was written
        for a in atoms[:5]:
            print(f"    [{a.type}] {a.summary[:80]}")
        if len(atoms) > 5:
            print(f"    ... and {len(atoms) - 5} more")
