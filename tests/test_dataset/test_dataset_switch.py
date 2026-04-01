"""Tests for dataset switching between full and demo modes."""

from __future__ import annotations

from unittest.mock import patch

from digest.dataset import messages


class TestDatasetSwitch:
    """Tests for the dataset config toggle."""

    def setup_method(self) -> None:
        """Reset cached messages between tests."""
        messages._CACHED_MESSAGES = None
        messages._CACHED_DATASET = None

    def teardown_method(self) -> None:
        """Reset cached messages after tests."""
        messages._CACHED_MESSAGES = None
        messages._CACHED_DATASET = None

    def test_full_dataset_loads_307_messages(self) -> None:
        """Full dataset should have 307 messages."""
        with patch("digest.dataset.messages.get_config") as mock_cfg:
            mock_cfg.return_value = {"pipeline": {"dataset": "full"}}
            msgs = messages.load_messages()
            assert len(msgs) == 307

    def test_demo_dataset_loads_18_messages(self) -> None:
        """Demo dataset should have 18 messages."""
        with patch("digest.dataset.messages.get_config") as mock_cfg:
            mock_cfg.return_value = {"pipeline": {"dataset": "demo"}}
            msgs = messages.load_messages()
            assert len(msgs) == 18

    def test_default_is_full(self) -> None:
        """Missing dataset key defaults to full."""
        with patch("digest.dataset.messages.get_config") as mock_cfg:
            mock_cfg.return_value = {"pipeline": {}}
            msgs = messages.load_messages()
            assert len(msgs) == 307

    def test_cache_invalidated_on_switch(self) -> None:
        """Switching dataset config reloads messages."""
        with patch("digest.dataset.messages.get_config") as mock_cfg:
            mock_cfg.return_value = {"pipeline": {"dataset": "full"}}
            full_msgs = messages.load_messages()

            mock_cfg.return_value = {"pipeline": {"dataset": "demo"}}
            demo_msgs = messages.load_messages()

            assert len(full_msgs) == 307
            assert len(demo_msgs) == 18
