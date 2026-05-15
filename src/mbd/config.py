"""Pydantic Settings — typed env-var configuration.

Reads from `.env.local` only (NOT `.env`). The DB URL is validated to point at
a local host; cloud Supabase URLs are rejected to prevent accidents during the
Steps 1-3 build (see docs/decisions/0001-initial-scope-clarifications.md).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    supabase_db_url_async: str = Field(
        description=(
            "asyncpg URL for local Supabase Postgres, e.g. "
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
        ),
    )
    user_agent_email: str = Field(default="hello@example.com")
    sentry_dsn: str | None = Field(default=None)

    @field_validator("supabase_db_url_async")
    @classmethod
    def _must_be_local(cls, v: str) -> str:
        local_hosts = ("127.0.0.1", "localhost", "host.docker.internal")
        if not any(h in v for h in local_hosts):
            raise ValueError(
                "supabase_db_url_async must point at local Postgres "
                f"({', '.join(local_hosts)}). Cloud URLs are disallowed by config."
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy settings accessor — instantiating Settings hits the filesystem."""
    return Settings()  # type: ignore[call-arg]
