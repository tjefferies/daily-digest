"""Tests for batch API rate limit safeguards."""

from __future__ import annotations

from evercurrent.extraction.batch_runner import _estimate_tokens, _split_into_sub_batches


class TestTokenEstimation:
    """Tests for input token estimation."""

    def test_estimate_tokens_simple(self) -> None:
        """Estimates ~4 chars per token."""
        assert _estimate_tokens("hello world") == 2  # 11 chars / 4 ≈ 2

    def test_estimate_tokens_empty(self) -> None:
        """Empty string returns 0."""
        assert _estimate_tokens("") == 0

    def test_estimate_batch_tokens(self) -> None:
        """Estimates total tokens for a list of requests."""
        requests = [
            {"params": {"messages": [{"content": "a" * 400}], "system": "b" * 100}},
            {"params": {"messages": [{"content": "c" * 200}], "system": ""}},
        ]
        # (400+100)/4 + (200+0)/4 = 125 + 50 = 175
        total = sum(
            _estimate_tokens(r["params"]["messages"][0]["content"] + r["params"].get("system", ""))
            for r in requests
        )
        assert total == 175


class TestSubBatchSplitting:
    """Tests for splitting large request lists into sub-batches."""

    def test_no_split_when_under_limit(self) -> None:
        """Returns single batch when under max size."""
        requests = [{"custom_id": str(i)} for i in range(5)]
        batches = _split_into_sub_batches(requests, max_per_batch=10)
        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_splits_evenly(self) -> None:
        """Splits into equal-sized sub-batches."""
        requests = [{"custom_id": str(i)} for i in range(20)]
        batches = _split_into_sub_batches(requests, max_per_batch=10)
        assert len(batches) == 2
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10

    def test_splits_with_remainder(self) -> None:
        """Last sub-batch can be smaller."""
        requests = [{"custom_id": str(i)} for i in range(15)]
        batches = _split_into_sub_batches(requests, max_per_batch=10)
        assert len(batches) == 2
        assert len(batches[0]) == 10
        assert len(batches[1]) == 5

    def test_empty_input(self) -> None:
        """Empty request list returns empty list."""
        assert _split_into_sub_batches([], max_per_batch=10) == []
