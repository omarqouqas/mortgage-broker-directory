# Canadian Mortgage Broker Directory

## Project

A specialty-filterable directory of every licensed mortgage broker in Canada. Differentiator: filter by specialty (halal, newcomer, self-employed, B-lender, private, languages) — not just geography.

**Standalone directory business. Monetization is direct: Featured Broker subscriptions, pay-per-lead routing, lender affiliate revenue. No SaaS upsell.**

Built by one person (me) in evenings/weekends.

## Stack

- **Python 3.12** strict typed, `uv` for package management
- **Postgres** via Supabase, **SQLModel** (Pydantic v2 + SQLAlchemy 2.x), **Alembic** for migrations
- **Playwright** for JS-rendered registry scraping
- **httpx + selectolax + markdownify** for plain-HTTP website fetching, parsing, and markdown conversion (Crawl4AI dropped — see ADR 0002)
- **Outscraper** for Google Maps enrichment
- **Anthropic Python SDK** (Sonnet 4.6, Batch API + prompt caching) for specialty classification
- **Polars** for data cleaning, **rapidfuzz** for fuzzy matching, **phonenumbers** for E.164 normalization
- **httpx** (async, HTTP/2) for plain HTTP
- **selectolax** for HTML parsing (not BeautifulSoup)
- **structlog** + Sentry for observability
- **Typer** for the CLI
- Tests: **pytest** + **pytest-asyncio** + **vcrpy**

## Commands

```bash
uv sync                              # install deps from lockfile
uv run mbd scrape --province ontario # run a provincial ingester (scraper, CSV importer, or API client — see ADR 0004)
uv run mbd clean                     # run the cleaning pass
uv run mbd verify --stale-days 30    # verify websites older than 30 days
uv run mbd enrich --all              # Step 4 specialty enrichment (costs money)
uv run pytest                        # run all tests
uv run pytest -k fsra                # run ingester tests for FSRA only
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run pyright                       # type check
uv run alembic revision --autogenerate -m "msg"  # new migration
uv run alembic upgrade head          # apply migrations
```

## Conventions

- **Async by default** for I/O. Use `httpx.AsyncClient`, `async def` scrapers, `asyncpg` driver.
- **Pydantic v2 everywhere.** All scraper outputs, config, classifier I/O are Pydantic models. No raw dicts crossing module boundaries.
- **SQLModel for persistence** — one class definition serves both validation and ORM. No separate Pydantic + SQLAlchemy classes.
- **Strict typing.** `pyright` strict mode passes. No `Any` unless justified in a comment.
- **Structured logging.** `structlog.get_logger()`, never `print()`. Every ingester logs run-id, province, record count.
- **Pure functions where possible.** Side effects (DB writes, network calls) at the edges of modules, not buried inside transformation functions.
- **No magic.** Explicit > implicit. No metaclass tricks, no decorators that hide control flow.
- **Module structure:** provincial **data ingesters** go in `src/mbd/ingesters/{province}.py`. Each implements whichever ABC fits its access category — `BaseScraper` for HTML scraping, `BaseCSVImporter` for open-data downloads, `BaseAPIClient` for registries with documented APIs — all declared in `src/mbd/ingesters/base.py`. Same module-per-task pattern applies to `enrichment/`, `cleaning/`, `verification/`. (Not all sources are scraped — see ADR 0004.)

## Data conventions

- **Provinces** stored as 2-letter codes (`ON`, `BC`, `QC`, `AB`, ...).
- **Phone numbers** stored in E.164 (`+14165551234`).
- **Postal codes** stored uppercase with space (`A1A 1A1`).
- **Names** preserve original diacritics and apostrophes; normalized match key is separate.
- **License numbers** stored as-is from the regulator (do not strip leading zeros).
- **Source URLs** stored on every record — every field traces back to where it came from.
- **Soft-delete via `is_active`,** never hard-delete records that have been public.

## Data access rules (compliance)

- **Honor `robots.txt` always.** Check before adding any new domain. **If a regulator blocks scraping via robots.txt, do not work around it** — pursue open-data release / API access / direct contact / FOI instead (see ADR 0004 for the FSRA precedent).
- User-agent must identify the project + a contact email.
- Default rate limit: 1 req/sec/domain. Slower if the regulator's terms specify.
- No authenticated routes. No CAPTCHA solving. No scraping behind login walls.
- For open-data CSV / API access, store the source URL + retrieval timestamp on every record, same as scraped data — provenance is non-negotiable regardless of ingest mechanism.
- Each province's compliance notes live in `docs/compliance/{province}.md` — read before writing the ingester.

## What Claude Code should NOT do without asking

- Add new top-level dependencies (`uv add ...`) — propose them in chat first.
- Change the database schema after the first migration is applied — propose a migration plan first.
- Run `alembic upgrade head` against production DB — only against local/dev.
- Spend money on external APIs (Anthropic Batch, Outscraper, Geocoding) during normal sessions — only when explicitly approved.
- Commit + push without summarizing what changed and asking.

## Reference docs (read on demand, not auto-loaded)

- `docs/strategy/01-steps-1-3-scrape-clean-verify.md` — full Steps 1–3 build plan (note: the "scrape every province" framing is superseded by ADR 0004)
- `docs/strategy/02-step-4-specialty-enrichment.md` — full Step 4 plan (don't read until Steps 1–3 are shipped)
- `docs/compliance/{province}.md` — regulator-specific compliance notes
- `docs/decisions/` — accepted ADRs; ADR 0004 in particular changes ingest sequencing

## Out of scope (for now)

- Next.js frontend — separate project, starts after Steps 1–3 ship
- Stripe / claim flow / lead routing — designed in schema, implemented in Step 6
- Step 5 (visuals) and Step 6 (frontend) and Step 7 (programmatic SEO) — separate prompts later
