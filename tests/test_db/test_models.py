"""Tests for SQLAlchemy ORM models — schema structure validation."""

from __future__ import annotations

from evercurrent.db.models import (
    Atom,
    AtomType,
    Base,
    BundleMembership,
    BundleRole,
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
            "atom_id", "type", "summary", "detail", "urgency",
            "confidence", "implicit_decision", "source",
            "source_bundle_ts", "created_at",
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
        """Base metadata includes all 4 tables."""
        table_names = set(Base.metadata.tables.keys())
        assert table_names == {"message", "thread_bundle", "bundle_membership", "atom"}

    def test_foreign_keys_exist(self) -> None:
        """Key foreign key relationships are defined."""
        atom_fks = {
            fk.target_fullname
            for fk in Atom.__table__.foreign_keys
        }
        assert "thread_bundle.root_message_ts" in atom_fks

        membership_fks = {
            fk.target_fullname
            for fk in BundleMembership.__table__.foreign_keys
        }
        assert "message.message_ts" in membership_fks
        assert "thread_bundle.root_message_ts" in membership_fks
