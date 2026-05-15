"""SQLModel definitions.

Schema differs from `docs/strategy/01-steps-1-3-scrape-clean-verify.md` in the
ways recorded in `docs/decisions/0001-initial-scope-clarifications.md`:

- `brokerages.head_office_address_raw TEXT` (was `head_office_address JSONB`) — geocoding deferred
- `brokerages.website_relevance_heuristic` (was `website_relevance`) — keyword classifier
- `is_active` + `updated_at` on brokerages, brokers, AND broker_licenses (independent lifecycles)
- `scrape_runs.diff_summary JSONB` added — per-run audit trail in lieu of a history table
- Screenshot/Storage columns omitted — moved to Step 5
- FKs use `ondelete=RESTRICT` (not SET NULL) — soft-delete via `is_active` is the canonical
  path; hard DELETEs are blocked to prevent silent orphans. FK columns are NOT NULL.
- `updated_at` is maintained by a Postgres `BEFORE UPDATE` trigger (`set_updated_at()`)
  installed by the initial migration. The ORM `onupdate=func.now()` hook is kept as a
  belt-and-suspenders fallback; both are intentional. Raw SQL UPDATEs go through the trigger.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any, ClassVar

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _pk_uuid_col() -> sa.Column[Any]:
    return sa.Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)


def _created_at_col() -> sa.Column[Any]:
    return sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def _updated_at_col() -> sa.Column[Any]:
    """Maintained by a Postgres BEFORE UPDATE trigger (`set_updated_at()`).

    The `onupdate=func.now()` ORM hook here is a belt-and-suspenders fallback;
    the trigger is the source of truth and catches raw SQL UPDATEs (bulk upserts,
    Alembic data migrations, Polars-driven cleaning passes).
    """
    return sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


def _is_active_col() -> sa.Column[Any]:
    return sa.Column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )


class Brokerage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "brokerages"  # pyright: ignore[reportIncompatibleVariableOverride]  # SQLModel parent declares this as declared_attr[Unknown]; concrete str override is intentional
    __table_args__ = (
        sa.Index("ix_brokerages_is_active", "is_active"),
        sa.Index("ix_brokerages_website_status", "website_status"),
        sa.Index("ix_brokerages_primary_province", "primary_province"),
        sa.Index("ix_brokerages_google_place_id", "google_place_id"),
        sa.Index(
            "ix_brokerages_legal_name_primary_province",
            "legal_name",
            "primary_province",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_pk_uuid_col())

    legal_name: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    trade_name: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    primary_license_number: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )
    primary_province: str = Field(sa_column=sa.Column(sa.Text, nullable=False))

    head_office_address_raw: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )

    phone_e164: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    email: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    website_url: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))

    website_status: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    website_verified_at: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True)
    )
    website_relevance_heuristic: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )

    google_place_id: str | None = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    google_rating: float | None = Field(
        default=None, sa_column=sa.Column(sa.Numeric(2, 1), nullable=True)
    )
    google_review_count: int | None = Field(
        default=None, sa_column=sa.Column(sa.Integer, nullable=True)
    )

    is_active: bool = Field(default=True, sa_column=_is_active_col())
    scraped_at: datetime = Field(default_factory=_utcnow, sa_column=_created_at_col())
    updated_at: datetime = Field(default_factory=_utcnow, sa_column=_updated_at_col())


class Broker(SQLModel, table=True):
    __tablename__: ClassVar[str] = "brokers"  # pyright: ignore[reportIncompatibleVariableOverride]  # SQLModel parent declares this as declared_attr[Unknown]; concrete str override is intentional
    __table_args__ = (
        sa.Index("ix_brokers_is_active", "is_active"),
        sa.Index("ix_brokers_primary_brokerage_id", "primary_brokerage_id"),
        sa.Index("ix_brokers_canonical_name", "canonical_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_pk_uuid_col())

    canonical_name: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    display_name: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    designations: list[str] = Field(
        default_factory=list,
        sa_column=sa.Column(pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
    )
    primary_brokerage_id: uuid.UUID = Field(
        sa_column=sa.Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("brokerages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )

    is_active: bool = Field(default=True, sa_column=_is_active_col())
    scraped_at: datetime = Field(default_factory=_utcnow, sa_column=_created_at_col())
    updated_at: datetime = Field(default_factory=_utcnow, sa_column=_updated_at_col())


class BrokerLicense(SQLModel, table=True):
    __tablename__: ClassVar[str] = "broker_licenses"  # pyright: ignore[reportIncompatibleVariableOverride]  # SQLModel parent declares this as declared_attr[Unknown]; concrete str override is intentional
    __table_args__ = (
        sa.UniqueConstraint("province", "license_number"),
        sa.Index("ix_broker_licenses_is_active", "is_active"),
        sa.Index("ix_broker_licenses_broker_id", "broker_id"),
        sa.Index("ix_broker_licenses_license_status", "license_status"),
        sa.Index("ix_broker_licenses_license_expiry_date", "license_expiry_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_pk_uuid_col())

    broker_id: uuid.UUID = Field(
        sa_column=sa.Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("brokers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    province: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    license_number: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    license_tier: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    license_status: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    license_issued_date: date | None = Field(
        default=None, sa_column=sa.Column(sa.Date, nullable=True)
    )
    license_expiry_date: date | None = Field(
        default=None, sa_column=sa.Column(sa.Date, nullable=True)
    )
    registry_source_url: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )
    raw_payload: dict[str, Any] | None = Field(
        default=None, sa_column=sa.Column(pg.JSONB, nullable=True)
    )

    is_active: bool = Field(default=True, sa_column=_is_active_col())
    scraped_at: datetime = Field(default_factory=_utcnow, sa_column=_created_at_col())
    updated_at: datetime = Field(default_factory=_utcnow, sa_column=_updated_at_col())


class ScrapeRun(SQLModel, table=True):
    __tablename__: ClassVar[str] = "scrape_runs"  # pyright: ignore[reportIncompatibleVariableOverride]  # SQLModel parent declares this as declared_attr[Unknown]; concrete str override is intentional
    __table_args__ = (
        sa.Index(
            "ix_scrape_runs_source_started_at",
            "source",
            sa.text("started_at DESC"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_pk_uuid_col())
    source: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    started_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True)
    )
    records_scraped: int | None = Field(
        default=None, sa_column=sa.Column(sa.Integer, nullable=True)
    )
    records_new: int | None = Field(default=None, sa_column=sa.Column(sa.Integer, nullable=True))
    records_updated: int | None = Field(
        default=None, sa_column=sa.Column(sa.Integer, nullable=True)
    )
    errors: dict[str, Any] | None = Field(
        default=None, sa_column=sa.Column(pg.JSONB, nullable=True)
    )
    # Captures per-run change records in lieu of a full broker_license_history table.
    diff_summary: dict[str, Any] | None = Field(
        default=None, sa_column=sa.Column(pg.JSONB, nullable=True)
    )
