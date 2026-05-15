"""Smoke test for the async session factory.

Skipped unless `.env.local` exists at the repo root — the user is expected to
`cp .env.example .env.local` and run `supabase start` before invoking this.
The config validator separately enforces that the DB URL is local-only.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = REPO_ROOT / ".env.local"

pytestmark = pytest.mark.skipif(
    not ENV_LOCAL.exists(),
    reason=(
        "No .env.local at repo root — copy .env.example and run "
        "`supabase start` (see docs/dev/local-supabase.md)."
    ),
)


@pytest.mark.asyncio
async def test_async_session_select_one() -> None:
    """Open an async session and execute a trivial query."""
    from mbd.db.session import get_session, reset_engine

    try:
        async with get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await reset_engine()
