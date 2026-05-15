# Local Supabase setup

This project's smoke tests and migrations run against a **local** Supabase stack only. The cloud project is off-limits during Steps 1–3. `src/mbd/config.py` enforces this with a validator that rejects any DB URL whose host is not `127.0.0.1` / `localhost` / `host.docker.internal`.

## One-time setup

1. Install the Supabase CLI ([docs](https://supabase.com/docs/guides/local-development/cli/getting-started)).
2. From the repo root:

   ```bash
   supabase init
   supabase start
   ```

   `supabase start` boots local Postgres + Studio + auth + storage in Docker.

3. Note the local Postgres port. The CLI defaults to **`54322`** for Postgres (the API runs on `54321` — different service). The `supabase start` output prints all ports; if yours differs, update `.env.local`.

4. Copy the env template and edit the URL:

   ```bash
   cp .env.example .env.local
   ```

   The default value in `.env.example` already targets `127.0.0.1:54322`, so unless your local port differs, no edit needed.

## Environment file separation

| File             | Purpose                                          | Committed? |
|------------------|--------------------------------------------------|------------|
| `.env.example`   | Template; safe to commit.                        | Yes        |
| `.env.local`     | Your local Supabase URL + dev secrets.           | **No** — gitignored. |
| `.env`           | **Do not use.** Reserved for prod, never local.  | n/a        |

`config.py` reads `.env.local` specifically — not `.env`. This separation is intentional: the smoke test must NEVER point at the cloud Supabase project. A second guard exists (`Settings._must_be_local`) that raises a `ValidationError` if you somehow get a non-local URL into `.env.local`.

## Daily workflow

```bash
supabase start                          # boot the stack
uv run pytest tests/test_async_session.py  # smoke test
supabase stop                           # shut it down when done
```

If a test or migration fails complaining about the host being non-local, you've pointed at the cloud project — fix `.env.local` before retrying.

## Resetting

```bash
supabase db reset      # drops + recreates the local DB; re-runs migrations
```

Useful when an experimental migration leaves the schema in a weird state. **Never** run this with anything but the local stack pointed at.
