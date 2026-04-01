"""Tests for SQLAlchemy ORM models — schema structure validation."""

from __future__ import annotations

from evercurrent.db.models import (
    Atom,
    AtomType,
    Base,
    BatchLog,
    BundleMembership,
    BundleRole,
    ContextWindow,
    Message,
    ThreadBundle,
    UrgencyLevel,
)


class TestModelTablesExist:
    """Verify all model classes produce valid table metadata."""

    def test_message_table(self) -> None:
        """Message model has correct table name and columns."""
        assert Message.__tablename__ == "message"
        cols = {c.name for c in Message.__table__.columns}
        assert cols == {"message_ts", "thread_ts", "channel", "user_id", "raw"}

    def test_thread_bundle_table(self) -> None:
        """ThreadBundle model has correct table name and columns."""
        assert ThreadBundle.__tablename__ == "thread_bundle"
        cols = {c.name for c in ThreadBundle.__table__.columns}
        assert cols == {"root_message_ts", "channel", "created_at"}

    def test_bundle_membership_table(self) -> None:
        """BundleMembership model has correct table name and columns."""
        assert BundleMembership.__tablename__ == "bundle_membership"
        cols = {c.name for c in BundleMembership.__table__.columns}
        assert cols == {"message_ts", "bundle_ts", "role", "confidence", "ordinal"}

    def test_atom_table(self) -> None:
        """Atom model has correct table name and columns."""
        assert Atom.__tablename__ == "atom"
        cols = {c.name for c in Atom.__table__.columns}
        expected = {
            "atom_id",
            "type",
            "summary",
            "detail",
            "urgency",
            "confidence",
            "implicit_decision",
            "source",
            "source_bundle_ts",
            "created_at",
        }
        assert cols == expected


class TestEnums:
    """Verify enum values match the domain model."""

    def test_bundle_role_values(self) -> None:
        """BundleRole has root, reply, continuation."""
        assert {r.value for r in BundleRole} == {"root", "reply", "continuation"}

    def test_atom_type_values(self) -> None:
        """AtomType has all 8 types."""
        assert len(AtomType) == 8
        assert AtomType.DECISION.value == "DECISION"

    def test_urgency_level_values(self) -> None:
        """UrgencyLevel has low, medium, high, critical."""
        assert {u.value for u in UrgencyLevel} == {"low", "medium", "high", "critical"}


class TestMetadata:
    """Verify SQLAlchemy metadata for migrations."""

    def test_base_has_all_tables(self) -> None:
        """Base metadata includes all 6 tables."""
        table_names = set(Base.metadata.tables.keys())
        assert table_names == {
            "message",
            "thread_bundle",
            "bundle_membership",
            "context_window",
            "atom",
            "batch_log",
        }

    def test_context_window_table(self) -> None:
        """ContextWindow model has correct table name and columns."""
        assert ContextWindow.__tablename__ == "context_window"
        cols = {c.name for c in ContextWindow.__table__.columns}
        assert cols == {"bundle_ts", "channel", "compressed", "raw", "created_at"}

    def test_atom_fk_points_to_context_window(self) -> None:
        """Atom.source_bundle_ts FK references context_window, not thread_bundle."""
        atom_fks = {fk.target_fullname for fk in Atom.__table__.foreign_keys}
        assert "context_window.bundle_ts" in atom_fks

    def test_batch_log_table(self) -> None:
        """BatchLog model has correct table name and columns."""
        assert BatchLog.__tablename__ == "batch_log"
        cols = {c.name for c in BatchLog.__table__.columns}
        expected = {
            "id",
            "batch_id",
            "stage",
            "request_count",
            "status",
            "request_body",
            "response_body",
            "created_at",
            "completed_at",
        }
        assert cols == expected

    def test_foreign_keys_exist(self) -> None:
        """Key foreign key relationships are defined."""
        atom_fks = {fk.target_fullname for fk in Atom.__table__.foreign_keys}
        assert "context_window.bundle_ts" in atom_fks

        membership_fks = {fk.target_fullname for fk in BundleMembership.__table__.foreign_keys}
        assert "message.message_ts" in membership_fks
        assert "thread_bundle.root_message_ts" in membership_fks
