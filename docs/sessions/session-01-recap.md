# Session 1 recap — 2026-05-14

Bootstrap session for the Canadian Mortgage Broker Directory. Project state goes from "strategy docs only" → "scaffolded Python pipeline with 4 of 5 dependency batches installed; no migration applied, no remote DB touched."

---

## What shipped

### Documentation / decisions

- **`CLAUDE.md`** — Project section rewritten to standalone framing (NOT a SaaS funnel). Stack table updated: Crawl4AI line replaced with `httpx + selectolax + markdownify`.
- **`docs/decisions/0001-initial-scope-clarifications.md`** — eight scope decisions from the kickoff (see "Decisions made" below).
- **`docs/decisions/0002-drop-crawl4ai.md`** — substitution justified by a dry-resolution that showed ~80 transitive packages including a litellm fork + openai + tiktoken + huggingface-hub for features we won't use.
- **`docs/compliance/territories.md`** — YT/NT/NU skipped at the scraper layer.
- **`docs/dev/local-supabase.md`** — local-Supabase setup, port 54322 note, `.env.local` vs `.env` separation, "never point at cloud" warning.
- **`data/raw/territories/manual.csv`** — header-only placeholder for hand entry. `.gitignore` updated to exempt this file from the bulk `data/raw/` ignore.

### Code scaffolding

```
mortgage-broker-directory/
├── pyproject.toml           # hatchling+uv, ruff/pyright/pytest config inline
├── alembic.ini              # script_location → src/mbd/db/migrations
├── .python-version          # 3.12
├── .env.example             # template; copies to .env.local (gitignored)
├── src/mbd/
│   ├── config.py            # Pydantic Settings + LOCAL-only DB URL validator
│   ├── db/
│   │   ├── models.py        # 4 SQLModels — schema deltas per ADR-0001 applied
│   │   ├── session.py       # cached AsyncEngine + AsyncSession factory
│   │   └── migrations/      # Alembic env.py (async mode), script.py.mako, versions/
│   └── pipeline/
│       └── cli.py           # Typer app — `mbd hello` works; multi-command shape locked in
└── tests/
    └── test_async_session.py  # SELECT 1 smoke test; skips if .env.local missing
```

### Dependencies installed (Batches A → D)

| Batch | Packages added |
|---|---|
| **A. Core data/types** | `pydantic`, `pydantic-settings`, `sqlmodel`, `sqlalchemy[asyncio]`, `alembic`, `asyncpg` |
| **B. Scraping (revised)** | `playwright`, `httpx[http2]`, `selectolax`, `markdownify` *(crawl4ai dropped — see ADR-0002)* |
| **C. Cleaning** | `polars`, `rapidfuzz`, `phonenumbers` |
| **D. Observability / CLI** | `structlog`, `sentry-sdk`, `typer` |

Net venv: ~50 packages on Python 3.12.13. **No `playwright install` yet** (browser binaries gated to Task #2 — FSRA scraper).

### Verified

- All four batches' top-level packages import cleanly.
- End-to-end fetcher pipeline (httpx HTTP/2 client + selectolax parse + markdownify) verified on canned HTML.
- `polars`, `rapidfuzz` (Jaro-Winkler), `phonenumbers` (E.164) spot-checked.
- `structlog` JSON renderer emits proper JSON.
- `uv run mbd hello` → `mbd: bootstrap entry point is live.`
- `uv run mbd --help` shows the multi-command shape ready for `scrape`/`clean`/`verify`.
- 4 SQLModel tables registered with all ADR-0001 schema deltas applied.

---

## Decisions made (ADR-0001 + ADR-0002)

1. **Geocoding deferred** — `head_office_address_raw TEXT` instead of JSONB; no Geocoding API spend.
2. **Screenshots cut from Step 3** — moves to Step 5; no Supabase Storage setup.
3. **Website relevance classifier = keyword heuristic** — column renamed `website_relevance_heuristic`; LLM classifier waits for Step 4.
4. **Throughput target relaxed** — "<12h overnight" instead of "<4h end-to-end."
5. **License history deferred** — captured per-run via `scrape_runs.diff_summary JSONB`.
6. **Territories** — no scrapers; manual.csv + compliance doc.
7. **Standalone business framing** — CLAUDE.md corrected; no SaaS upsell.
8. **Confirmation gates** — `uv add` batched and per-batch approved; no migration application without explicit approval; no paid API calls.

Plus mid-session:

9. **Soft-delete + `updated_at` on three tables** — `brokerages`, `brokers`, AND `broker_licenses` (independent lifecycles; each can deactivate without the others).
10. **Python pinned to 3.12** — uv had defaulted to system Python 3.14.4; pinned via `.python-version` + `requires-python = ">=3.12,<3.13"` to avoid wheel-availability risk on bleeding-edge transitives.
11. **Crawl4AI dropped** — dry-resolution showed it pulls a full LLM-SDK stack as base deps (not opt-in); replaced with `httpx + selectolax + markdownify`. ADR-0002.

---

## Key technical points worth remembering

- **`src/mbd/config.py` has a hard validator** (`_must_be_local`) that refuses any DB URL whose host isn't `127.0.0.1` / `localhost` / `host.docker.internal`. The smoke test can't accidentally connect to the cloud Supabase project even if `.env.local` is misconfigured — the Settings model raises a `ValidationError` first.
- **`.env.local`, not `.env`** is the file `config.py` reads. `.env` is reserved for prod / never used locally. Both are gitignored.
- **Alembic env uses async mode via asyncpg** — same driver as runtime, no psycopg2 to install.
- **`mbd.db.migrations.env` imports `mbd.db.models`** to populate `SQLModel.metadata` before autogenerate runs. If you add new models, make sure they're reachable from that import.
- **The `cli.py` `@app.callback()` is intentional** — it forces Typer multi-command shape so `mbd <subcommand>` stays stable when there's only one subcommand registered.

---

## Pending — picks up tomorrow

### Step 1: Batch E — dev deps *(no DB needed)*

```bash
uv add --dev pytest pytest-asyncio vcrpy ruff pyright
```

Then verify:

```bash
uv run pytest          # smoke test should SKIP (no .env.local yet) — that's correct
uv run ruff check .    # expect clean
uv run ruff format --check .
uv run pyright         # SQLModel + strict mode can be noisy; report errors, don't relax config without asking
```

### Step 2: Bring up local Supabase

```bash
supabase init                          # one-time
supabase start                         # boots local PG on :54322 (+ Studio etc.)
cp .env.example .env.local             # one-time; default URL targets 127.0.0.1:54322
```

See `docs/dev/local-supabase.md` for the full setup notes.

### Step 3: Generate the first Alembic migration *(needs local DB up — autogenerate compares against live schema)*

```bash
uv run alembic revision --autogenerate -m "initial schema"
```

This writes a new file under `src/mbd/db/migrations/versions/`. **Do NOT apply it yet.** Review the generated SQL first:

```bash
ls src/mbd/db/migrations/versions/
# read the generated revision; verify it creates 4 tables with the ADR-0001 deltas
```

Then, only after review, with explicit approval:

```bash
uv run alembic upgrade head
```

### Step 4: Smoke test the async session

```bash
uv run pytest tests/test_async_session.py -v
```

Should now PASS (was skipping before because `.env.local` didn't exist).

### Step 5: Task #2 (FSRA scraper) — separate session

After the smoke test passes, the next milestone is the FSRA reference scraper. That includes `playwright install` (browser binaries), the `BaseScraper` ABC, idempotency logic, and VCR cassette capture.

---

## Resume command — read me first tomorrow

```bash
cat docs/sessions/session-01-recap.md
```

Or, if you want the bare minimum context-load for Claude:

> "Resume from `docs/sessions/session-01-recap.md` — start with Batch E."

---

## Open threads / nice-to-haves (not blocking)

- `docs/strategy/01-steps-1-3-scrape-clean-verify.md` still contains the older "feeds the SaaS" framing and the Crawl4AI references. Left intentionally as historical record — the ADRs are operative. Could be scrubbed if it starts confusing future sessions.
- No `README.md` yet (intentional — `pyproject.toml` doesn't reference one). Add when the project has something to say externally.
- `markdownify` pulls `beautifulsoup4` + `six` as transitives. `html2text` is zero-dep alternative if we want a leaner option later; bs4 isn't what we parse with so it's currently a non-issue.
- `playwright` browser binaries (Chromium/Firefox/Webkit) not installed yet — that's a Task #2 step.
