"""Tests for three buried cross-workstream signals per section 9.4.

Validates that the synthetic dataset contains the three deliberately
planted signals that test the extraction pipeline's ability to surface
cross-workstream impact from buried thread context.
"""

from digest.dataset.messages import load_messages
from digest.dataset.schema import SlackMessage


def _get_thread(
    messages: list[SlackMessage],
    thread_ts: str,
) -> list[SlackMessage]:
    """Get all messages in a thread, ordered by timestamp.

    Args:
        messages: Full message list.
        thread_ts: The thread parent timestamp.

    Returns:
        Ordered list of messages in the thread.
    """
    thread = [m for m in messages if m.message_ts == thread_ts or m.thread_ts == thread_ts]
    return sorted(thread, key=lambda m: m.message_ts)


class TestSignal1MagnesiumHousing:
    """Signal 1: Magnesium housing implicit decision in #chassis-design.

    A weight-reduction thread where the decision to prototype in
    magnesium is buried mid-thread. This is an implicit DECISION
    with procurement and certification impact.
    """

    def test_magnesium_thread_exists(self) -> None:
        """A thread in #chassis-design mentions magnesium housing."""
        messages = load_messages()
        chassis_msgs = [m for m in messages if m.channel == "#chassis-design"]
        magnesium_mentions = [m for m in chassis_msgs if "magnesium" in m.text.lower()]
        assert len(magnesium_mentions) >= 2

    def test_magnesium_decision_is_buried(self) -> None:
        """The magnesium decision is not in the thread opener."""
        messages = load_messages()
        chassis_msgs = [m for m in messages if m.channel == "#chassis-design"]
        mag_msgs = [m for m in chassis_msgs if "magnesium" in m.text.lower()]
        first_mag = min(mag_msgs, key=lambda m: m.message_ts)
        if first_mag.thread_ts:
            thread = _get_thread(messages, first_mag.thread_ts)
        else:
            thread = _get_thread(messages, first_mag.message_ts)
        decision_msgs = [
            m
            for m in thread
            if "magnesium" in m.text.lower()
            and ("prototype" in m.text.lower() or "let's" in m.text.lower())
        ]
        assert len(decision_msgs) >= 1
        for dm in decision_msgs:
            position = thread.index(dm)
            assert position >= 2, f"Magnesium decision at position {position}, should be 2+"

    def test_magnesium_has_supply_chain_impact(self) -> None:
        """The thread references supply chain implications."""
        messages = load_messages()
        chassis_msgs = [m for m in messages if m.channel == "#chassis-design"]
        mag_msgs = [m for m in chassis_msgs if "magnesium" in m.text.lower()]
        first_mag = min(mag_msgs, key=lambda m: m.message_ts)
        thread_ts = first_mag.thread_ts or first_mag.message_ts
        thread = _get_thread(messages, thread_ts)
        thread_text = " ".join(m.text.lower() for m in thread)
        assert (
            "supply chain" in thread_text or "vendor" in thread_text or "lead time" in thread_text
        )


class TestSignal2ThermalInterfaceRootCause:
    """Signal 2: Motor overheating root cause in thermal interface.

    A motor overheating failure whose root cause implicates the
    chassis/thermal interface material. Originating in thermal
    discussion, affects chassis and drivetrain workstreams.
    """

    def test_motor_overheating_thread_exists(self) -> None:
        """A thread discusses motor overheating / thermal shutdown."""
        messages = load_messages()
        thermal_msgs = [m for m in messages if m.channel == "#thermal-management"]
        overheating = [
            m
            for m in thermal_msgs
            if "thermal shutdown" in m.text.lower()
            or "overheating" in m.text.lower()
            or "winding temp" in m.text.lower()
        ]
        assert len(overheating) >= 1

    def test_root_cause_is_chassis_machining(self) -> None:
        """Root cause traces to chassis-related issue (machining/TIM)."""
        messages = load_messages()
        thermal_msgs = [m for m in messages if m.channel == "#thermal-management"]
        overheat = [
            m
            for m in thermal_msgs
            if "thermal shutdown" in m.text.lower() or "winding temp" in m.text.lower()
        ]
        first = min(overheat, key=lambda m: m.message_ts)
        thread_ts = first.thread_ts or first.message_ts
        thread = _get_thread(messages, thread_ts)
        thread_text = " ".join(m.text.lower() for m in thread)
        has_chassis_ref = "chassis" in thread_text or "machining" in thread_text
        has_tim_ref = (
            "thermal interface" in thread_text
            or "thermal pad" in thread_text
            or "gap pad" in thread_text
        )
        assert has_chassis_ref and has_tim_ref

    def test_root_cause_is_buried(self) -> None:
        """The root cause revelation is not in the first message."""
        messages = load_messages()
        thermal_msgs = [m for m in messages if m.channel == "#thermal-management"]
        overheat = [
            m
            for m in thermal_msgs
            if "thermal shutdown" in m.text.lower() or "winding temp" in m.text.lower()
        ]
        first = min(overheat, key=lambda m: m.message_ts)
        thread_ts = first.thread_ts or first.message_ts
        thread = _get_thread(messages, thread_ts)
        root_cause = [
            m
            for m in thread
            if "air gap" in m.text.lower()
            or "step" in m.text.lower()
            or "machining" in m.text.lower()
        ]
        assert len(root_cause) >= 1
        for rc in root_cause:
            position = thread.index(rc)
            assert position >= 2, f"Root cause at position {position}, should be 2+"


class TestSignal3FPGALeadTime:
    """Signal 3: FPGA lead time blocking drivetrain milestone.

    A supply chain alert about FPGA lead time that affects
    workstreams beyond supply chain (firmware, drivetrain).
    """

    def test_fpga_lead_time_in_supply_chain(self) -> None:
        """FPGA lead time alert exists in #supply-chain."""
        messages = load_messages()
        sc_msgs = [m for m in messages if m.channel == "#supply-chain"]
        fpga_msgs = [m for m in sc_msgs if "fpga" in m.text.lower() or "artix" in m.text.lower()]
        assert len(fpga_msgs) >= 1

    def test_fpga_also_in_firmware(self) -> None:
        """FPGA lead time concern also appears in #firmware."""
        messages = load_messages()
        fw_msgs = [m for m in messages if m.channel == "#firmware"]
        fpga_lead = [
            m
            for m in fw_msgs
            if "lead time" in m.text.lower()
            and ("fpga" in m.text.lower() or "artix" in m.text.lower())
        ]
        assert len(fpga_lead) >= 1

    def test_fpga_mentions_cross_workstream_impact(self) -> None:
        """The FPGA discussion references impact on other workstreams."""
        messages = load_messages()
        sc_msgs = [m for m in messages if m.channel == "#supply-chain"]
        fpga_msgs = [m for m in sc_msgs if "fpga" in m.text.lower() or "artix" in m.text.lower()]
        first = min(fpga_msgs, key=lambda m: m.message_ts)
        thread_ts = first.thread_ts or first.message_ts
        thread = _get_thread(messages, thread_ts)
        thread_text = " ".join(m.text.lower() for m in thread)
        has_dvt_ref = "dvt" in thread_text
        has_firmware_ref = "firmware" in thread_text or "bitstream" in thread_text
        assert has_dvt_ref or has_firmware_ref
