"""Tests for per-workstream phase diversity in the synthetic dataset.

Validates that messages reflect the phase vector from ADR-004:
DVT channels use vendor/tooling/validation vocabulary, EVT channels
use design-decision/early-test vocabulary, and end-effector references
use concept-stage vocabulary.
"""

from digest.dataset.messages import load_messages

# ---------- vocabulary helpers ----------

_DVT_TERMS = frozenset(
    {
        "dvt",
        "vendor",
        "tooling",
        "qualification",
        "validation",
        "fixture",
        "production",
        "mold",
    }
)

_EVT_TERMS = frozenset(
    {
        "evt",
        "prototype",
        "design",
        "calibration",
        "early test",
        "breadboard",
        "first article",
    }
)

_CONCEPT_TERMS = frozenset(
    {
        "concept",
        "feasibility",
        "trade study",
        "whiteboard",
    }
)


def _channel_text(channel: str) -> str:
    """Join all message text for a channel into one lowercase string."""
    messages = load_messages()
    return " ".join(m.text.lower() for m in messages if m.channel == channel)


def _has_any_term(text: str, terms: frozenset[str]) -> list[str]:
    """Return which terms from the set appear in the text."""
    return [t for t in terms if t in text]


# ---------- DVT workstreams ----------


class TestChassisDVTPhase:
    """#chassis-design should reflect DVT-phase vocabulary."""

    def test_has_dvt_vocabulary(self) -> None:
        """Chassis messages use DVT terms (vendor, tooling, validation)."""
        text = _channel_text("#chassis-design")
        found = _has_any_term(text, _DVT_TERMS)
        assert len(found) >= 3, f"Only found DVT terms: {found}"

    def test_mentions_dvt_explicitly(self) -> None:
        """Chassis messages explicitly mention 'DVT'."""
        text = _channel_text("#chassis-design")
        assert "dvt" in text


class TestDrivetrainDVTPhase:
    """#drivetrain should reflect DVT-phase vocabulary."""

    def test_has_dvt_vocabulary(self) -> None:
        """Drivetrain messages use DVT terms."""
        text = _channel_text("#drivetrain")
        found = _has_any_term(text, _DVT_TERMS)
        assert len(found) >= 3, f"Only found DVT terms: {found}"

    def test_mentions_dvt_explicitly(self) -> None:
        """Drivetrain messages explicitly mention 'DVT'."""
        text = _channel_text("#drivetrain")
        assert "dvt" in text


class TestPowerSystemsDVTPhase:
    """#power-systems should reflect DVT-phase vocabulary."""

    def test_has_dvt_vocabulary(self) -> None:
        """Power systems messages use DVT terms."""
        text = _channel_text("#power-systems")
        found = _has_any_term(text, _DVT_TERMS)
        assert len(found) >= 2, f"Only found DVT terms: {found}"


class TestSupplyChainDVTPhase:
    """#supply-chain should reflect DVT-phase vocabulary."""

    def test_has_dvt_vocabulary(self) -> None:
        """Supply chain messages use DVT terms."""
        text = _channel_text("#supply-chain")
        found = _has_any_term(text, _DVT_TERMS)
        assert len(found) >= 4, f"Only found DVT terms: {found}"

    def test_mentions_vendor_qualification(self) -> None:
        """Supply chain discusses vendor qualification."""
        text = _channel_text("#supply-chain")
        assert "vendor" in text


# ---------- EVT workstreams ----------


class TestThermalEVTPhase:
    """#thermal-management should reflect EVT-phase vocabulary."""

    def test_has_evt_vocabulary(self) -> None:
        """Thermal messages use EVT terms (design, prototype, etc.)."""
        text = _channel_text("#thermal-management")
        found = _has_any_term(text, _EVT_TERMS)
        assert len(found) >= 2, f"Only found EVT terms: {found}"

    def test_has_design_decisions(self) -> None:
        """Thermal messages discuss design decisions."""
        text = _channel_text("#thermal-management")
        assert "design" in text


class TestSensorsEVTPhase:
    """#sensors should reflect EVT-phase vocabulary."""

    def test_has_evt_vocabulary(self) -> None:
        """Sensors messages use EVT terms."""
        text = _channel_text("#sensors")
        found = _has_any_term(text, _EVT_TERMS)
        assert len(found) >= 2, f"Only found EVT terms: {found}"

    def test_has_calibration_work(self) -> None:
        """Sensors messages discuss calibration (EVT-stage activity)."""
        text = _channel_text("#sensors")
        assert "calibrat" in text


class TestFirmwareEVTPhase:
    """#firmware should reflect EVT-phase vocabulary."""

    def test_has_evt_vocabulary(self) -> None:
        """Firmware messages use EVT terms."""
        text = _channel_text("#firmware")
        found = _has_any_term(text, _EVT_TERMS)
        assert len(found) >= 2, f"Only found EVT terms: {found}"


# ---------- Cross-phase consistency ----------


class TestPhaseConsistency:
    """DVT channels should have more DVT vocabulary than EVT channels."""

    def test_dvt_channels_richer_in_dvt_terms(self) -> None:
        """DVT-phase channels collectively use more DVT terms than EVT channels."""
        dvt_channels = ["#chassis-design", "#drivetrain", "#power-systems", "#supply-chain"]
        evt_channels = ["#thermal-management", "#sensors", "#firmware"]
        dvt_text = " ".join(_channel_text(ch) for ch in dvt_channels)
        evt_text = " ".join(_channel_text(ch) for ch in evt_channels)
        dvt_hits = len(_has_any_term(dvt_text, _DVT_TERMS))
        evt_hits = len(_has_any_term(evt_text, _DVT_TERMS))
        assert dvt_hits > evt_hits, f"DVT channels had {dvt_hits} DVT terms, EVT had {evt_hits}"

    def test_evt_channels_richer_in_evt_terms(self) -> None:
        """EVT-phase channels collectively use more EVT terms than DVT channels."""
        dvt_channels = ["#chassis-design", "#drivetrain", "#power-systems", "#supply-chain"]
        evt_channels = ["#thermal-management", "#sensors", "#firmware"]
        dvt_text = " ".join(_channel_text(ch) for ch in dvt_channels)
        evt_text = " ".join(_channel_text(ch) for ch in evt_channels)
        dvt_hits = len(_has_any_term(dvt_text, _EVT_TERMS))
        evt_hits = len(_has_any_term(evt_text, _EVT_TERMS))
        assert evt_hits >= dvt_hits, f"EVT channels had {evt_hits} EVT terms, DVT had {dvt_hits}"
