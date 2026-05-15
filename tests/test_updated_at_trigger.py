"""Smoke test: the `set_updated_at` Postgres trigger fires on raw SQL UPDATE.

The ORM `onupdate=func.now()` hook only fires on ORM-mediated UPDATEs. The
initial-schema migration installs a `BEFORE UPDATE` trigger so that raw SQL
(bulk upserts, Alembic data migrations, Polars cleaning passes) also bumps
`updated_at`. This test verifies the trigger by issuing a raw SQL UPDATE that
bypasses the ORM entirely.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = REPO_ROOT / ".env.local"

pytestmark = pytest.mark.skipif(
    not ENV_LOCAL.exists(),
    reason=(
        "No .env.local at repo root — copy .env.example and run "
        "`supabase start` + `alembic upgrade head` first."
    ),
)


@pytest.mark.asyncio
async def test_updated_at_trigger_fires_on_raw_sql_update() -> None:
    from mbd.db.session import get_session, reset_engine

    brokerage_id = uuid.uuid4()
    try:
        async with get_session() as session:
            await session.execute(
                text(
                    "INSERT INTO brokerages (id, legal_name, primary_province) "
                    "VALUES (:id, :name, :prov)"
                ),
                {"id": brokerage_id, "name": "Trigger Smoke Test", "prov": "ON"},
            )
            await session.commit()

            initial_updated_at = (
                await session.execute(
                    text("SELECT updated_at FROM brokerages WHERE id = :id"),
                    {"id": brokerage_id},
                )
            ).scalar_one()

        await asyncio.sleep(1)

        async with get_session() as session:
            await session.execute(
                text("UPDATE brokerages SET legal_name = :n WHERE id = :id"),
                {"n": "Trigger Smoke Test (updated)", "id": brokerage_id},
            )
            await session.commit()

            new_updated_at = (
                await session.execute(
                    text("SELECT updated_at FROM brokerages WHERE id = :id"),
                    {"id": brokerage_id},
                )
            ).scalar_one()

        assert new_updated_at > initial_updated_at, (
            f"trigger did not bump updated_at on raw SQL UPDATE: "
            f"before={initial_updated_at!r} after={new_updated_at!r}"
        )

        async with get_session() as session:
            await session.execute(
                text("DELETE FROM brokerages WHERE id = :id"),
                {"id": brokerage_id},
            )
            await session.commit()
    finally:
        await reset_engine()
