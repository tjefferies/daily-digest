"""Slack message JSON schema and team roster definitions.

Defines the raw message format that the synthetic dataset produces
and the ingestion layer consumes. This is the contract between
Layers 0 (data) and 1 (ingestion).

The 8 channels and 20-person roster model a realistic AMR robotics
team spanning mechanical, electrical, firmware, and supply chain
disciplines across EVT/DVT development phases.
"""

from pydantic import BaseModel, Field

CHANNELS: list[str] = [
    "#chassis-design",
    "#drivetrain",
    "#thermal-management",
    "#power-systems",
    "#sensors",
    "#firmware",
    "#supply-chain",
    "#amr-general",
]
"""The 8 Slack channels for the AMR robotics team."""


class SlackReaction(BaseModel):
    """A single emoji reaction on a Slack message.

    Attributes:
        name: Emoji name (e.g. 'thumbsup', 'eyes', 'rotating_light').
        users: List of user_ids who applied this reaction.
    """

    name: str
    users: list[str] = Field(default_factory=list)


class SlackMessage(BaseModel):
    """Raw Slack message as ingested from the synthetic dataset.

    This schema mirrors Slack's message event payload, scoped to the
    fields the extraction pipeline needs. Thread replies have a
    thread_ts pointing to the parent message.

    Attributes:
        message_ts: Slack message timestamp (unique message ID).
        thread_ts: Parent thread timestamp, None for top-level messages.
        channel: Channel name including # prefix.
        user_id: Slack user ID of the message author.
        text: Raw message text content.
        reactions: Emoji reactions attached to this message.
    """

    message_ts: str
    thread_ts: str | None = None
    channel: str
    user_id: str
    text: str
    reactions: list[SlackReaction] = Field(default_factory=list)


class TeamMember(BaseModel):
    """A member of the AMR robotics team.

    Attributes:
        user_id: Slack user ID (e.g. 'U001').
        name: Full display name.
        title: Job title.
        primary_channels: Channels this person is most active in.
    """

    user_id: str
    name: str
    title: str
    primary_channels: list[str] = Field(default_factory=list)


def _build_roster() -> list[TeamMember]:
    """Construct the 20-person AMR robotics team roster."""
    raw: list[tuple[str, str, str, list[str]]] = [
        (
            "U001",
            "Maya Chen",
            "Senior Mechanical Engineer",
            ["#chassis-design", "#thermal-management"],
        ),
        ("U002", "Alex Rivera", "Drivetrain Lead", ["#drivetrain", "#amr-general"]),
        (
            "U003",
            "Priya Sharma",
            "Thermal Systems Engineer",
            ["#thermal-management", "#chassis-design"],
        ),
        ("U004", "James Okafor", "Power Electronics Engineer", ["#power-systems", "#firmware"]),
        ("U005", "Sarah Kim", "Sensor Integration Lead", ["#sensors", "#firmware"]),
        ("U006", "Marcus Johnson", "Firmware Engineer", ["#firmware", "#sensors"]),
        ("U007", "Elena Vasquez", "Supply Chain Manager", ["#supply-chain", "#amr-general"]),
        ("U008", "David Park", "Mechanical Design Engineer", ["#chassis-design", "#drivetrain"]),
        ("U009", "Aisha Patel", "Test Engineer", ["#amr-general", "#chassis-design"]),
        (
            "U010",
            "Ryan Torres",
            "Engineering Manager",
            ["#amr-general", "#chassis-design", "#drivetrain"],
        ),
        ("U011", "Lisa Wang", "Program Manager", ["#amr-general", "#supply-chain"]),
        ("U012", "Carlos Mendez", "Motor Systems Engineer", ["#drivetrain", "#power-systems"]),
        ("U013", "Nina Petrov", "Materials Engineer", ["#chassis-design", "#supply-chain"]),
        ("U014", "Kevin O'Brien", "Embedded Systems Engineer", ["#firmware", "#power-systems"]),
        (
            "U015",
            "Fatima Al-Hassan",
            "Quality Assurance Engineer",
            ["#amr-general", "#thermal-management"],
        ),
        ("U016", "Tom Nakamura", "LIDAR Systems Engineer", ["#sensors", "#amr-general"]),
        ("U017", "Deepa Krishnan", "Procurement Specialist", ["#supply-chain", "#amr-general"]),
        (
            "U018",
            "Michael Zhang",
            "Battery Systems Engineer",
            ["#power-systems", "#thermal-management"],
        ),
        ("U019", "Rachel Foster", "VP of Engineering", ["#amr-general"]),
        (
            "U020",
            "Jorge Castillo",
            "Chassis Structures Engineer",
            ["#chassis-design", "#drivetrain"],
        ),
    ]
    return [
        TeamMember(
            user_id=uid,
            name=name,
            title=title,
            primary_channels=channels,
        )
        for uid, name, title, channels in raw
    ]


class TeamRoster(BaseModel):
    """The full 20-person AMR robotics team roster.

    Provides the team member directory used by the synthetic dataset
    generator and the context backbone layer for collaborator lookups.

    Attributes:
        members: The complete list of team members.
    """

    members: list[TeamMember] = Field(
        default_factory=_build_roster,
    )
