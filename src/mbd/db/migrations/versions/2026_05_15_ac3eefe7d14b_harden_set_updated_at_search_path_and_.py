"""harden set_updated_at search_path and rename desc index

Revision ID: ac3eefe7d14b
Revises: f6958f02df98
Create Date: 2026-05-15 16:20:39.945467
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = 'ac3eefe7d14b'
down_revision: str | None = 'f6958f02df98'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Pin search_path on set_updated_at() per Supabase linter hardening
    #    guidance (mutable search_path can be hijacked by per-session settings).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER
        SET search_path = pg_catalog, public
        AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # 2. Rename the composite DESC index so the ordering is visible from the name.
    op.execute(
        "ALTER INDEX ix_scrape_runs_source_started_at "
        "RENAME TO ix_scrape_runs_source_started_at_desc;"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_scrape_runs_source_started_at_desc "
        "RENAME TO ix_scrape_runs_source_started_at;"
    )

    # Restore set_updated_at() without the pinned search_path.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
