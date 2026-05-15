# Canadian Mortgage Broker Directory — Claude Code Project Starter

> Scope: Steps 1–3 of Frey Chu's 7-step directory build (Scrape, Clean, Verify). Steps 4–7 (specialty enrichment, visuals, amenities/filters, service areas) will be tackled in follow-up prompts.

---

## Project Overview

Building a comprehensive, enriched directory of all licensed mortgage brokers and agents in Canada, differentiated by **specialty-based filtering** (halal, newcomer programs, self-employed, B-lender access, commercial, construction, languages, etc.) — not just geography.

**Strategic context:** This directory feeds the parallel mortgage broker workflow SaaS targeting the same audience. The directory captures consumer-side traffic and surfaces "claim your listing" CTAs to brokers — every claim is a warm lead for the SaaS. The directory is both a top-of-funnel acquisition channel and a defensible data moat (the only directory enriched at the specialty layer, not the geography layer).

**Why this niche survives AI search:** Per the Frey Chu / Greg Isenberg discussion, directories that help users navigate complex, high-stakes decisions (senior living, medical, legal) remain valuable as LLMs reshape search. Choosing a mortgage broker is precisely such a decision — high-stakes, infrequent, outcome-sensitive, regulatory.

---

## Target Outcome of Steps 1–3

A clean, deduplicated, verified dataset of every active licensed mortgage broker/agent and brokerage in Canada with:

- Canonical name, license number, license tier, license status, license expiry
- Brokerage affiliation
- Province(s) of licensure (a human can hold multiple)
- Verified business contact info (phone, email, website)
- Website liveness flag (live / parked / placeholder / dead / unverified)
- Mortgage-relevance classification (real broker site vs. mismatched/defunct)
- Source URL + scrape timestamp for every field (audit trail)

Stored in PostgreSQL via Supabase, matching the existing SaaS stack.

---

## Architecture

Two-tier split — language-optimal for each tier, joined by the database:

```
┌──────────────────────┐  writes   ┌──────────────────────┐  reads   ┌──────────────────────┐
│  Python Pipeline     │──────────▶│  Postgres (Supabase) │─────────▶│  Next.js 15 Frontend │
│  scrape/clean/verify │           │  source of truth     │          │  (Steps 6+, deferred)│
└──────────────────────┘           └──────────────────────┘          └──────────────────────┘
     Runs nightly                                                       Vercel + ISR for SEO
```

This starter covers the **Python pipeline tier only**. The Next.js frontend is a separate project, started once the data layer is solid.

## Tech Stack — Python Pipeline

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12, strict type hints | Crawl4AI native; best data-cleaning ecosystem; mature AI tooling |
| Package mgmt | `uv` | Astral's Rust-based installer; 10–100× faster than pip/poetry; lockfile + script runner in one |
| Lint/format | `ruff` | Replaces black + isort + flake8 + pyupgrade; one fast tool |
| Type checking | `pyright` (strict) | Faster than mypy, better inference, official VS Code integration |
| Data models | Pydantic v2 | Validation everywhere — scrape outputs, API contracts, config |
| ORM | SQLModel (Pydantic + SQLAlchemy 2.x) | One model definition for validation and persistence |
| Database | Supabase (Postgres) | Hosted Postgres + auth/storage we'll want for frontend; cheap to start |
| Registry scraping | Playwright for Python | JS-rendered registries (FSRA, BCFSA, AMF) need a real browser |
| Bulk enrichment | Outscraper API | Google Maps data — language-agnostic HTTP API |
| Website verification | Crawl4AI | Native fit; built for LLM-friendly extraction |
| HTML parsing | `selectolax` | ~10× faster than BeautifulSoup at our volume |
| HTTP client | `httpx` (async) | Async-first, HTTP/2, modern requests replacement |
| Data cleaning | Polars | Faster than Pandas, lazy API, better for our scale |
| Fuzzy matching | `rapidfuzz` | C-backed; for dedup + brokerage matching |
| Phone parsing | `phonenumbers` | Google's lib; E.164 normalization, Canadian validation |
| Address parsing | Google Geocoding API | Skip libpostal complexity for v1; ~$5 per 1K lookups |
| LLM classification | Anthropic Python SDK + Batch API | Batch drops cost ~50% for the relevance classifier |
| Logging | `structlog` + Sentry | Structured JSON locally, Sentry in prod |
| Testing | `pytest` + `pytest-asyncio` + `vcrpy` | VCR records real HTTP for replayable scraper tests |
| Orchestration (v1) | CLI scripts + cron on a small VM | Pragmatic; revisit Prefect/Dagster only if complexity warrants |
| Compute (v1) | $5/mo Hetzner CX22 | Pipeline is bursty; no need for serverless yet |
| Secrets | `.env` locally, Hetzner env vars in prod | Doppler later if it grows |

## Tech Stack — Next.js Frontend (Steps 6+, deferred)

Documented here so the schema is designed with it in mind, **not in scope for this starter**:

| Layer | Choice |
|---|---|
| Framework | Next.js 15 (App Router) on Vercel |
| Rendering | ISR + on-demand revalidation; static-feel for ~15K broker pages |
| UI | Tailwind + shadcn/ui |
| Auth (broker claim flow) | Supabase Auth |
| Search | Postgres full-text + trigram for v1; Typesense/Meilisearch if warranted |
| Analytics | PostHog |

---

## Data Sources (Provincial Regulatory Registries)

Each province regulates mortgage brokers separately under provincial law (FSRA in Ontario operates under MBLAA; OSFI's B-20 sits above all of it for federally regulated lenders, but broker licensing is provincial). Public licensee databases:

| Province | Regulator | Notes |
|---|---|---|
| Ontario | FSRA | ~15,000 licensees, largest dataset. Public search at fsrao.ca |
| British Columbia | BCFSA | Public registrant search |
| Quebec | AMF | Register of firms and individuals — bilingual; preserve French diacritics |
| Alberta | RECA | Industry member search |
| Saskatchewan | FCAA | Mortgage Brokerage licensee search |
| Manitoba | MSC | Manitoba Securities Commission registrant database |
| New Brunswick | FCNB | Mortgage Broker Search |
| Nova Scotia | Service NS | Registry of mortgage brokers and lenders |
| Newfoundland & Labrador | Digital Gov & Service NL | Smaller list, may need manual CSV extraction |
| PEI | Office of the Superintendent of Insurance | Small list |
| Yukon / NWT / Nunavut | Territorial regulators | Smallest datasets — manual entry acceptable for v1 |

**Sequencing:** Build FSRA first as the reference scraper (largest dataset, most complex pagination). Pattern-match for the remaining provinces.

**Compliance:** All data is public regulatory record. Honor robots.txt, throttle requests, identify the bot in the user-agent. No login walls, no PII beyond what's publicly disclosed by the regulator.

---

## Database Schema

```sql
-- Core entities
CREATE TABLE brokerages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  legal_name TEXT NOT NULL,
  trade_name TEXT,
  primary_license_number TEXT,
  primary_province TEXT NOT NULL,
  head_office_address JSONB,  -- {street, city, province, postal_code, lat, lng}
  phone_e164 TEXT,
  email TEXT,
  website_url TEXT,
  website_status TEXT,  -- live | parked | placeholder | dead | unverified
  website_verified_at TIMESTAMPTZ,
  website_relevance TEXT,  -- mortgage_broker | realtor | defunct | unclear
  google_place_id TEXT,
  google_rating NUMERIC(2,1),
  google_review_count INT,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE brokers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,         -- "John Smith"
  display_name TEXT NOT NULL,           -- as it appears on registry
  designations TEXT[],                  -- FCSI, AMP, CIM, etc., parsed off the name
  primary_brokerage_id UUID REFERENCES brokerages(id),
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Many-to-many: a broker can be licensed in multiple provinces with different license numbers
CREATE TABLE broker_licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_id UUID REFERENCES brokers(id),
  province TEXT NOT NULL,
  license_number TEXT NOT NULL,
  license_tier TEXT NOT NULL,           -- agent | broker | brokerage_principal
  license_status TEXT NOT NULL,         -- active | suspended | expired | inactive
  license_issued_date DATE,
  license_expiry_date DATE,
  registry_source_url TEXT,
  raw_payload JSONB,                    -- full scraped record for audit
  scraped_at TIMESTAMPTZ NOT NULL,
  UNIQUE (province, license_number)
);

CREATE TABLE scrape_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,                 -- 'FSRA', 'BCFSA', 'OUTSCRAPER_GMAPS', etc.
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  records_scraped INT,
  records_new INT,
  records_updated INT,
  errors JSONB
);
```

---

## Step 1 — Scrape

### 1.1 Per-province scraper modules

Each province lives in `/scrapers/{province}.ts` and exports a `scrape()` function that:

- Hits the registry's public search UI via Playwright
- Paginates through all active licensees (FSRA: ~15,000; BC: ~5,000; AB/QC: large; others smaller)
- Writes raw JSON per record to `/data/raw/{province}/{license_number}.json`
- Respects rate limits — default to 1 request/second if not documented
- Writes a manifest to `/data/raw/{province}/_run_{timestamp}.json` with counts and errors

### 1.2 Google Maps enrichment via Outscraper

After brokerage names + cities are extracted from provincial registries:

- Batch-query Outscraper for `{brokerage_trade_name} {city}` per brokerage
- Capture: place_id, formatted address, phone, website, hours, rating, review_count
- Persist raw response to `/data/raw/gmaps/{place_id}.json`
- For ambiguous matches (multiple results), keep the top 3 and resolve in cleaning step

### 1.3 Idempotency

Re-running any scraper must not duplicate. Natural key: `(province, license_number)`. On re-scrape:

- New record → insert
- Existing record with changed fields → version into a `broker_license_history` table (skip in v1; just overwrite + log diff for now)
- Existing record unchanged → no-op

### 1.4 Compliance checklist

- [ ] User-agent identifies the project and includes contact email
- [ ] robots.txt checked for each domain before scraping
- [ ] No authenticated routes touched
- [ ] Rate limit ≥1 second between requests (more if explicitly documented)
- [ ] Each provincial regulator's terms of use reviewed and noted in `/docs/compliance/{province}.md`

---

## Step 2 — Clean

### 2.1 Name normalization

- Parse "Last, First" vs "First Last" formats — registries are inconsistent
- Strip professional designations (FCSI, AMP, CIM, MBA, P.Eng) into the `designations` array
- Title-case consistently while preserving French diacritics (é, ç, à) and apostrophes (O'Brien, D'Souza)
- Lowercase + strip + diacritic-normalize for the match key only; keep original `display_name`

### 2.2 Cross-province deduplication

A single human can hold licenses in Ontario, BC, and Alberta under three different license numbers. The dedup heuristic:

- Match key 1: normalized name + brokerage email domain
- Match key 2: normalized name + phone E.164
- Match key 3: normalized name + brokerage legal name (fuzzy, Jaro-Winkler ≥0.92)

Confidence scoring:
- ≥0.95 → auto-merge into single `brokers` row with multiple `broker_licenses`
- 0.85–0.95 → write to `/data/clean/_dedup_review.json` for manual review
- <0.85 → treat as separate humans

### 2.3 Brokerage matching

Brokers reference their brokerage as free text. To canonicalize:

1. Match by brokerage license number first (exact)
2. Then by trade name (fuzzy, ≥0.92)
3. Then create brokerage stub if no match

### 2.4 Address standardization

- Use Google Geocoding API (or libpostal locally to save cost) for Canadian addresses
- Capture lat/lng for later service-area calculations
- Validate postal code matches format `A1A 1A1`

### 2.5 Phone normalization

E.164 format (`+1XXXXXXXXXX`). Strip extensions into a separate field.

### 2.6 Active-only public dataset

Only `active` and `suspended` records appear in the public directory. Expired/inactive licenses archive into `broker_licenses_archive` for historical reference.

---

## Step 3 — Verify

### 3.1 Website liveness check (Crawl4AI)

For every brokerage with a `website_url`:

- Fetch homepage with Crawl4AI
- Categorize:
  - `live` — 200 status, real mortgage-related content
  - `parked` — domain parking page (GoDaddy, Sedo, etc.)
  - `placeholder` — "under construction", "coming soon", default WordPress/Wix landing
  - `dead` — 4xx/5xx, DNS failure, timeout >10s
  - `unverified` — couldn't determine, flag for retry
- Capture: HTTP status, final URL after redirects, page title, response time, HTML word count

### 3.2 Canonical contact extraction

- Parse phone numbers and email addresses from homepage + `/contact` page
- Compare against registry-listed and Google Maps-listed values
- If three sources agree → high confidence canonical
- If discrepant → flag for manual review, prefer Google Maps for phone, prefer website for email

### 3.3 Mortgage relevance classification

Use Claude to classify each live website:

```
Given this homepage content, classify the business as one of:
- mortgage_broker (primary business is mortgage brokering)
- realtor (real estate agent who lists mortgage on the side)
- lender (direct lender, not a broker)
- defunct (site exists but business appears closed)
- unclear

Content: {homepage_text_excerpt}
```

This catches realtor licensees who hold mortgage agent licenses but don't actively broker — they should be filtered out of the public directory or flagged differently.

### 3.4 Screenshot capture

- Playwright headless screenshot of homepage at 1440x900
- Store in Supabase Storage at `screenshots/brokerage/{id}.png`
- Used later in Step 5 for visual verification and trust signals

### 3.5 Verification audit log

Every verification attempt logs to `verification_attempts` table with timestamp, result, and a 500-char excerpt of what was seen. Enables:

- Nightly re-verification of stale records (>30 days)
- Debugging when a brokerage disputes their listing
- Trust signals on the public profile ("last verified 3 days ago")

---

## Quality Bar (Definition of Done for Steps 1–3)

- [ ] All 10 provinces have working scrapers (3 territories may use manual CSV for v1)
- [ ] ≥95% of broker records have a non-null brokerage affiliation
- [ ] ≥85% of brokerages have a verified `website_status` (any value other than `unverified`)
- [ ] ≥80% of live brokerage sites have a confirmed `mortgage_broker` relevance classification
- [ ] Cross-province dedup confidence ≥0.85 for all auto-merged records
- [ ] Full scrape → clean → verify pipeline runs end-to-end in <4 hours
- [ ] Every record traceable back to source URL + scrape timestamp
- [ ] Nightly cron re-verifies records older than 30 days

---

## Repository Structure

```
mortgage-broker-directory/
├── pyproject.toml               # uv-managed; deps, ruff, pyright config
├── uv.lock
├── .env.example
├── README.md
│
├── src/mbd/                     # `mbd` = mortgage broker directory
│   ├── __init__.py
│   ├── config.py                # Pydantic Settings — env vars, API keys
│   ├── db/
│   │   ├── models.py            # SQLModel definitions
│   │   ├── session.py           # async engine + session factory
│   │   └── migrations/          # Alembic
│   │
│   ├── scrapers/
│   │   ├── base.py              # ABC: scrape() -> AsyncIterator[RawRecord]
│   │   ├── fsra.py              # Ontario — reference implementation, build first
│   │   ├── bcfsa.py
│   │   ├── amf.py
│   │   ├── reca.py
│   │   └── ...
│   │
│   ├── enrichment/
│   │   ├── outscraper.py        # Google Maps batch enrichment
│   │   └── geocoder.py          # Google Geocoding wrapper
│   │
│   ├── cleaning/
│   │   ├── names.py             # Last,First parsing; designation stripping
│   │   ├── dedup.py             # Cross-province broker matching
│   │   ├── brokerages.py        # Brokerage canonicalization
│   │   ├── addresses.py         # Standardization via Geocoding
│   │   └── phones.py            # E.164 normalization
│   │
│   ├── verification/
│   │   ├── liveness.py          # Crawl4AI website liveness + categorization
│   │   ├── contacts.py          # Canonical phone/email extraction
│   │   ├── relevance.py         # Claude classifier (Batch API)
│   │   └── screenshots.py       # Playwright homepage screenshots
│   │
│   └── pipeline/
│       ├── run_scrape.py        # CLI: `mbd scrape --province ontario`
│       ├── run_clean.py         # CLI: `mbd clean`
│       ├── run_verify.py        # CLI: `mbd verify --stale-days 30`
│       └── full_pipeline.py     # CLI: `mbd run-all`
│
├── tests/
│   ├── cassettes/               # VCR recordings of registry responses
│   ├── test_scrapers/
│   ├── test_cleaning/
│   └── test_verification/
│
├── data/                        # gitignored
│   ├── raw/{province}/
│   ├── clean/
│   └── verified/
│
└── docs/
    └── compliance/{province}.md
```

CLI entry points exposed via `pyproject.toml`:

```toml
[project.scripts]
mbd = "mbd.pipeline.cli:app"  # Typer-based CLI
```

---

## What's Explicitly Out of Scope (Saved for Follow-up Prompts)

- **Step 4 — Specialty/inventory enrichment:** halal, newcomer programs, self-employed, B-lender panel, languages spoken, commercial/construction/private/reverse — all extracted from each broker's website by Claude
- **Step 5 — Logo/headshot extraction** via Claude Vision
- **Step 6 — Amenities filtering and search UX**
- **Step 7 — Service area determination** and programmatic local SEO page generation
- Next.js frontend / public directory UX
- Monetization layer (claim listing flow, paid placement, lead routing, broker tier upgrades)
- Disciplinary history scraping (FSRA enforcement actions, public proceedings)
- Cross-link with the mortgage broker SaaS app

---

## First Three Tasks for Claude Code

When this project kicks off, work in this order:

1. **Project bootstrap** — `uv init`, define `pyproject.toml` deps (pin core libs), wire up Pydantic Settings (`config.py`), define the SQLModel schema in `db/models.py`, generate the first Alembic migration, apply to Supabase. Hello-world test that proves the async session works.
2. **FSRA scraper** — Build `scrapers/fsra.py` end-to-end against the `BaseScraper` ABC. Ontario has the most licensees (~15K) and the most complex pagination, so it sets the pattern. Goal: full FSRA scrape committed to `data/raw/ontario/`, idempotent re-runs working, VCR cassettes captured for the test suite.
3. **Website liveness verifier** — Build `verification/liveness.py` since it's reusable across every brokerage regardless of province. Validate against 100 random brokerages from the FSRA scrape before scaling. Should categorize correctly into `live` / `parked` / `placeholder` / `dead` / `unverified` with >90% accuracy on a hand-labeled validation set.

After these three the path to v1 is mechanical: replicate the scraper pattern across remaining provinces, run cleaning + verification across the union, ship Step 4 for specialty differentiation.
