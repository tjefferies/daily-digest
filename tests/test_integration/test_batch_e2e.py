"""Integration test: real 5-window batch extraction end-to-end.

Requires: ANTHROPIC_API_KEY in .env or environment.
Proves: batch submit → poll → results retrieved → atoms parsed.
This is the real Anthropic API, not mocks.
"""

from __future__ import annotations

import os

import pytest
from anthropic import Anthropic

from evercurrent.dataset.messages import load_messages
from evercurrent.extraction.batch_runner import BatchExtractionRunner
from evercurrent.ingestion.context_window import assemble_context_windows
from evercurrent.ingestion.threads import group_by_thread


@pytest.mark.integration
class TestBatchE2ERealAPI:
    """Submit a real batch to Anthropic and verify the full round-trip."""

    @pytest.fixture(autouse=True)
    def _require_api_key(self) -> None:
        """Skip if ANTHROPIC_API_KEY is not set."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

    async def test_5_window_batch_produces_atoms(self) -> None:
        """5 real windows → batch submit → poll → results → parsed atoms."""
        messages = load_messages()
        bundles = group_by_thread(messages)
        windows = assemble_context_windows(bundles)[:5]

        assert len(windows) == 5

        client = Anthropic()
        runner = BatchExtractionRunner(client)

        # This calls the real Anthropic Batch API:
        #   1. Submits Stage 1 batch (5 requests)
        #   2. Polls every 5s until ended
        #   3. Retrieves results
        #   4. Submits Stage 2 batch (N enrichment requests)
        #   5. Polls again
        #   6. Retrieves + parses into Atom objects
        atoms = await runner.extract(windows)

        # We should get at least some atoms
        assert len(atoms) > 0, (
            "Batch API returned 0 atoms from 5 windows. "
            "Check: did the batch time out? Were results canceled?"
        )

        # Verify atom structure
        for atom in atoms:
            assert atom.summary, f"Atom has empty summary: {atom}"
            assert atom.type in {
                "DECISION", "SPEC_CHANGE", "ACTION_ITEM", "BLOCKER",
                "RISK", "TEST_RESULT", "STATUS_UPDATE", "QUESTION",
            }, f"Invalid atom type: {atom.type}"
            assert atom.source.channel.startswith("#"), (
                f"Channel should start with #: {atom.source.channel}"
            )
            assert 0.0 <= atom.confidence <= 1.0

        # Verify progress was tracked
        assert runner.stats["windows_processed"] == 5
        assert runner.stats["atoms_produced"] == len(atoms)

        # Verify progress dict was updated during polling
        assert runner.progress["total"] > 0, "Progress was never updated"

        print(f"\n  Batch E2E: 5 windows → {len(atoms)} atoms")
        for a in atoms[:5]:
            print(f"    [{a.type}] {a.summary[:80]}")
        if len(atoms) > 5:
            print(f"    ... and {len(atoms) - 5} more")
