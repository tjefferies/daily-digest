"""SQLAlchemy async ORM models for the Daily Digest Tool BCNF schema.

Maps the Postgres tables for messages, thread bundles, bundle
memberships, and atoms. Uses JSONB for raw message payloads and
atom source provenance. All operations are async via asyncpg.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Use JSONB on Postgres, JSON on SQLite (for testing)
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class BundleRole(enum.Enum):
    """Role of a message within a thread bundle."""

    root = "root"
    reply = "reply"
    continuation = "continuation"


class AtomType(enum.Enum):
    """Type of extracted information atom."""

    DECISION = "DECISION"
    SPEC_CHANGE = "SPEC_CHANGE"
    ACTION_ITEM = "ACTION_ITEM"
    BLOCKER = "BLOCKER"
    RISK = "RISK"
    TEST_RESULT = "TEST_RESULT"
    STATUS_UPDATE = "STATUS_UPDATE"
    QUESTION = "QUESTION"


class UrgencyLevel(enum.Enum):
    """Urgency level of an atom."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Message(Base):
    """A Slack message with full raw payload stored as JSONB.

    Attributes:
        message_ts: Slack message timestamp (primary key).
        thread_ts: Parent thread timestamp, None for top-level.
        channel: Channel name including # prefix.
        user_id: Slack user ID of the message author.
        raw: Full Slack message payload as JSONB.
    """

    __tablename__ = "message"

    message_ts: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Slack message timestamp, unique ID within a channel",
    )
    thread_ts: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("message.message_ts", deferrable=True, initially="DEFERRED"),
        nullable=True,
        comment="Parent thread timestamp; NULL for top-level messages",
    )
    channel: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Slack channel name with # prefix (e.g. #chassis-design)",
    )
    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Slack user ID of the message author (e.g. U001)",
    )
    raw: Mapped[dict] = mapped_column(
        JsonType,
        nullable=False,
        comment="Full Slack API message payload as JSONB for replay/debugging",
    )

    __table_args__ = (
        Index("idx_message_thread", "thread_ts"),
        Index("idx_message_channel", "channel"),
        {"comment": "Raw Slack messages ingested from the API or fixture data"},
    )


class ThreadBundle(Base):
    """A thread bundle identified by its root message.

    Attributes:
        root_message_ts: Root message timestamp (primary key, FK to message).
        channel: Channel where the thread lives.
        created_at: When this bundle was created.
    """

    __tablename__ = "thread_bundle"

    root_message_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("message.message_ts"),
        primary_key=True,
        comment="Root message timestamp; also FK to message table",
    )
    channel: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Channel where this thread lives",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        comment="When this bundle was first persisted to Postgres",
    )

    memberships: Mapped[list[BundleMembership]] = relationship(
        back_populates="bundle",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        {"comment": "Thread bundles grouping related messages into conversational units"},
    )


class BundleMembership(Base):
    """Maps a message to its thread bundle with role and confidence.

    Attributes:
        message_ts: Message timestamp (primary key, FK to message).
        bundle_ts: Bundle root timestamp (FK to thread_bundle).
        role: Whether this message is root, reply, or continuation.
        confidence: Match confidence (1.0 for structural, <1.0 for semantic).
        ordinal: Position within the bundle.
    """

    __tablename__ = "bundle_membership"

    message_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("message.message_ts"),
        primary_key=True,
        comment="FK to message; a message belongs to exactly one bundle",
    )
    bundle_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("thread_bundle.root_message_ts"),
        nullable=False,
        comment="FK to thread_bundle; which bundle this message belongs to",
    )
    role: Mapped[BundleRole] = mapped_column(
        Enum(BundleRole, name="bundle_role"),
        nullable=False,
        comment="Role: root (thread starter), reply (explicit), or continuation (semantic match)",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment="Match confidence: 1.0 for structural, cosine similarity for semantic",
    )
    ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Position within the bundle (0-indexed, chronological)",
    )

    bundle: Mapped[ThreadBundle] = relationship(back_populates="memberships")

    __table_args__ = (
        CheckConstraint("confidence > 0.0 AND confidence <= 1.0", name="ck_confidence"),
        Index("idx_membership_bundle", "bundle_ts"),
        {"comment": "Maps messages to thread bundles with role, confidence, and ordering"},
    )


class ContextWindow(Base):
    """The assembled text sent to the LLM for extraction.

    One bundle produces exactly one context window. Stores the
    full window as JSONB (thread_text, message_range, token estimate)
    for reproducibility - you can see exactly what the LLM received.

    Attributes:
        bundle_ts: FK to thread_bundle (primary key, 1:1 with bundle).
        channel: Channel where the thread lives.
        compressed: Whether the window was compressed to fit token limit.
        raw: Full context window as JSONB (thread_text, message_range, etc.).
        created_at: When this window was assembled.
    """

    __tablename__ = "context_window"

    bundle_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("thread_bundle.root_message_ts"),
        primary_key=True,
        comment="FK to thread_bundle; 1:1 relationship (one window per bundle)",
    )
    channel: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Channel where the source thread lives",
    )
    compressed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the window was compressed to fit within LLM token limits",
    )
    raw: Mapped[dict] = mapped_column(
        JsonType,
        nullable=False,
        comment="Full context window as JSONB: thread_text, message_range, token estimate",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        comment="When this context window was assembled",
    )

    bundle: Mapped[ThreadBundle] = relationship(backref="context_window")
    atoms: Mapped[list[Atom]] = relationship(back_populates="context_window")

    __table_args__ = (
        Index("idx_cw_channel", "channel"),
        Index("idx_cw_compressed", "compressed"),
        Index("idx_cw_created", "created_at"),
        {"comment": "Assembled text windows sent to the LLM for atom extraction"},
    )


class Atom(Base):
    """An extracted information atom linked to its source context window.

    Attributes:
        atom_id: UUID primary key.
        type: One of 8 atom types.
        summary: One-line summary.
        detail: Expanded explanation.
        urgency: Urgency level.
        confidence: LLM confidence score.
        implicit_decision: Whether this was implicit.
        source: Full LLM-returned provenance as JSONB.
        source_bundle_ts: FK to the context window that produced this atom.
        created_at: When this atom was created.
    """

    __tablename__ = "atom"

    atom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key; generated by the pipeline, not the LLM",
    )
    type: Mapped[AtomType] = mapped_column(
        Enum(AtomType, name="atom_type"),
        nullable=False,
        comment="Atom type (8 types: DECISION, SPEC_CHANGE, etc.)",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="One-line summary of what happened",
    )
    detail: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Expanded explanation with context and implications",
    )
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level"),
        nullable=False,
        comment="Urgency: low, medium, high, or critical",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="LLM extraction confidence [0.0-1.0]; halved if validation fails",
    )
    implicit_decision: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this decision was implicit (stated without formal agreement)",
    )
    source: Mapped[dict] = mapped_column(
        JsonType,
        nullable=False,
        comment="Provenance JSONB: channel, thread_ts, message_range, key_participants",
    )
    source_bundle_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("context_window.bundle_ts"),
        nullable=False,
        comment="FK to context_window; which LLM input produced this atom",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        comment="When this atom was extracted and persisted",
    )

    context_window: Mapped[ContextWindow] = relationship(back_populates="atoms")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_atom_confidence",
        ),
        Index("idx_atom_bundle", "source_bundle_ts"),
        Index("idx_atom_type", "type"),
        Index("idx_atom_created", "created_at"),
        {"comment": "Extracted information atoms with LLM provenance and scoring metadata"},
    )


class BatchLog(Base):
    """Audit log for LLM batch API requests and responses.

    Stores the full request/response JSONB for debugging,
    cost tracking, and replay.

    Attributes:
        id: Auto-increment primary key.
        batch_id: Anthropic batch ID (e.g. msgbatch_...).
        stage: Pipeline stage (extraction_stage1, extraction_stage2, etc.).
        request_count: Number of requests in the batch.
        status: Final batch status (ended, canceled, etc.).
        request_body: Full JSON request body sent to Anthropic API.
        response_body: Full JSON response body received from Anthropic API.
        created_at: When the batch was submitted.
        completed_at: When the batch finished.
    """

    __tablename__ = "batch_log"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-increment primary key",
    )
    batch_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Anthropic batch ID (e.g. msgbatch_01...)",
    )
    stage: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Pipeline stage: extraction_stage1, extraction_stage2, validation",
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of individual requests in this batch",
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="submitted",
        comment="Final batch status: submitted, processing, ended, canceled, errored",
    )
    request_body: Mapped[dict] = mapped_column(
        JsonType,
        nullable=False,
        comment="Full JSON request body sent to Anthropic Batch API",
    )
    response_body: Mapped[dict | None] = mapped_column(
        JsonType,
        nullable=True,
        comment="Full JSON response body from Anthropic; NULL until batch completes",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        comment="When the batch was submitted to Anthropic",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the batch finished processing; NULL if still running",
    )

    __table_args__ = (
        Index("idx_batch_log_batch_id", "batch_id"),
        Index("idx_batch_log_stage", "stage"),
        {"comment": "Audit log for Anthropic Batch API requests/responses"},
    )
