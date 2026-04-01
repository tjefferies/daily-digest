"""SQLAlchemy async ORM models for the EverCurrent BCNF schema.

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

    message_ts: Mapped[str] = mapped_column(String, primary_key=True)
    thread_ts: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("message.message_ts", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    raw: Mapped[dict] = mapped_column(JsonType, nullable=False)

    __table_args__ = (
        Index("idx_message_thread", "thread_ts"),
        Index("idx_message_channel", "channel"),
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
    )
    channel: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
    )

    memberships: Mapped[list[BundleMembership]] = relationship(
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
    atoms: Mapped[list[Atom]] = relationship(
        back_populates="bundle",
        cascade="all, delete-orphan",
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
    )
    bundle_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("thread_bundle.root_message_ts"),
        nullable=False,
    )
    role: Mapped[BundleRole] = mapped_column(
        Enum(BundleRole, name="bundle_role"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    bundle: Mapped[ThreadBundle] = relationship(back_populates="memberships")

    __table_args__ = (
        CheckConstraint("confidence > 0.0 AND confidence <= 1.0", name="ck_confidence"),
        Index("idx_membership_bundle", "bundle_ts"),
    )


class Atom(Base):
    """An extracted information atom linked to its source bundle.

    Attributes:
        atom_id: UUID primary key.
        type: One of 8 atom types.
        summary: One-line summary.
        detail: Expanded explanation.
        urgency: Urgency level.
        confidence: LLM confidence score.
        implicit_decision: Whether this was implicit.
        source: Full LLM-returned provenance as JSONB.
        source_bundle_ts: FK to the thread bundle that produced this atom.
        created_at: When this atom was created.
    """

    __tablename__ = "atom"

    atom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[AtomType] = mapped_column(
        Enum(AtomType, name="atom_type"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    implicit_decision: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    source: Mapped[dict] = mapped_column(JsonType, nullable=False)
    source_bundle_ts: Mapped[str] = mapped_column(
        String,
        ForeignKey("thread_bundle.root_message_ts"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
    )

    bundle: Mapped[ThreadBundle] = relationship(back_populates="atoms")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_atom_confidence",
        ),
        Index("idx_atom_bundle", "source_bundle_ts"),
        Index("idx_atom_type", "type"),
        Index("idx_atom_created", "created_at"),
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
        request_summary: Summary of requests (custom_ids, token estimates).
        response_summary: Summary of results (succeeded/failed counts).
        created_at: When the batch was submitted.
        completed_at: When the batch finished.
    """

    __tablename__ = "batch_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="submitted")
    request_summary: Mapped[dict] = mapped_column(JsonType, nullable=False)
    response_summary: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_batch_log_batch_id", "batch_id"),
        Index("idx_batch_log_stage", "stage"),
    )
