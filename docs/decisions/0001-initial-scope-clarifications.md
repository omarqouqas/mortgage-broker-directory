# 0001 — Initial scope clarifications for Steps 1–3

- **Date:** 2026-05-14
- **Status:** Accepted
- **Author:** project owner + Claude Code
- **Scope:** Steps 1–3 (scrape, clean, verify). Step 4 onwards unaffected.

## Context

Kickoff session for the Canadian Mortgage Broker Directory build. A recap pass over `CLAUDE.md` and `docs/strategy/01-steps-1-3-scrape-clean-verify.md` surfaced six scope ambiguities and one outdated framing claim. This ADR records the resolutions so future sessions don't have to re-derive them from chat history.

---

## 1. Geocoding deferred entirely

**Decision:** No Google Geocoding API calls in Steps 1–3. Schema changes: drop `brokerages.head_office_address JSONB`, replace with `brokerages.head_office_address_raw TEXT` holding the unparsed string from the regulator.

**Why:** Service-area features that need lat/lng are Step 6+. Geocoding 15K+ Canadian addresses costs real money and adds a third-party dependency to a milestone that doesn't require it.

**What it changes:** No `geocoder.py` module in this milestone. Address standardization (§2.4 of the strategy doc) reduces to postal-code regex validation only. Lat/lng work returns when frontend service-area filtering arrives.

## 2. Screenshots cut from Step 3

**Decision:** Remove §3.4 (Playwright screenshot capture + Supabase Storage upload) from the Step 3 verification module. No Storage bucket configured yet.

**Why:** The original 7-step plan placed screenshots in Step 5 (visuals). They drifted into the Step 3 scope without a Step 1–3 DoD requirement. Cutting them removes Supabase Storage setup, an extra Playwright pass per brokerage, and another failure mode from the verification pipeline.

**What it changes:** `verification/screenshots.py` is not built. Screenshot capture returns as a Step 5 task.

## 3. Website relevance — keyword heuristic, not LLM

**Decision:** Replace §3.3 LLM relevance classification with a deterministic keyword heuristic over extracted homepage text. Match a tuned vocabulary (e.g. `mortgage`, `broker`, `lender`, `rate`, `pre-approval`, `amortization`, `refinance`, `principal`, `closing costs`) and produce the same five-value output: `mortgage_broker | realtor | lender | defunct | unclear`. Schema field renamed `website_relevance_heuristic` so the method of classification is auditable from the column name.

**Why:** No Anthropic Batch API spend in this milestone (per CLAUDE.md's "no paid API spend without approval" rule). 15K Batch classifications is non-trivial money for an MVP signal that keywords can approximate. The real classifier returns as part of Step 4 alongside the specialty enrichment that already needs Anthropic spend.

**What it changes:** `verification/relevance.py` ships as pure-Python keyword logic, fast and offline. We accept lower precision (especially on realtor-vs-broker discrimination) in exchange for zero per-record cost.

## 4. Throughput target relaxed

**Decision:** DoD target changes from "<4 hours end-to-end" to "completes overnight (<12h)." Revisit after measuring real FSRA throughput.

**Why:** A sequential FSRA scrape at 1 req/sec on ~15K records is >4 hours on Ontario alone, before any other province runs. The original target was either assuming parallelism or wasn't grounded in real numbers. Better to set a target we can hit and tighten later.

**What it changes:** No premature optimization (concurrency, per-province parallelism) in v1. After we have measured per-province scrape times, we revisit.

## 5. License history deferred, diffs captured

**Decision:** No `broker_license_history` table in v1. Add `scrape_runs.diff_summary JSONB` to record per-run changes — records added/removed, fields updated, license-status transitions.

**Why:** Full versioning adds schema and write-path complexity for a feature no consumer uses yet. But losing the audit trail entirely is worse — disputes ("you have my expired license") and trend reporting both need a record of changes. JSONB on the run row is the cheap middle.

**What it changes:** Cleaning step writes a structured diff into `scrape_runs.diff_summary` on every run. Promotion to a proper history table is a future migration if/when we need point-in-time queries.

## 6. Territories — no automated scraping

**Decision:** Yukon, NWT, and Nunavut are skipped at the scraper layer. Manual entry only.

**Implementation:**
- `data/raw/territories/manual.csv` created with the canonical column set (matches the fields produced by provincial scrapers, denormalized for hand entry).
- `docs/compliance/territories.md` records the rationale and compliance posture.

**Why:** Territory licensee counts are tiny (single to low double digits each), and the three regulators have inconsistent reporting formats. Building three scrapers for ~30 records is uneconomic.

**What it changes:** Cleaning pipeline must read `manual.csv` alongside the provincial JSON in `data/raw/` and treat it as another source.

## 7. Framing correction — standalone, no SaaS upsell

**Decision:** This is a standalone directory business. Monetization is direct (Featured Broker subscriptions, pay-per-lead routing, lender affiliate revenue). It is NOT a top-of-funnel for a sibling broker SaaS.

**Why:** Earlier framing in the strategy doc described the directory as feeding a parallel broker workflow SaaS. That SaaS project is no longer the strategic anchor; the directory stands on its own monetization. Misframed product strategy leaks into priority calls (e.g., over-weighting "claim your listing" CTAs as lead-gen plumbing rather than revenue plumbing).

**What it changes:**
- `CLAUDE.md` Project section rewritten.
- `docs/strategy/01-steps-1-3-scrape-clean-verify.md` still contains the older framing in its "Strategic context" paragraph. Left untouched for now (historical reference); not load-bearing for the Steps 1–3 build itself.

## 8. Process — explicit confirmation gates

**Decision:** Pre-implementation confirmation required for: dependency additions (group `uv add` into logical batches, confirm each batch before installing), schema-changing migrations (propose migration plan first), Alembic application against any remote DB (only local/dev unless explicitly approved), and any paid API call.

**Why:** Owner is a solo builder; surprises in the dev environment or unexpected API spend are the most expensive mistakes. Cheap to ask, cheap to wait.

**What it changes:** Working norm for this project. Already encoded informally in `CLAUDE.md` ("What Claude Code should NOT do without asking"); this ADR makes the operational details (batch-by-batch `uv add` confirmation, no migration application without approval) explicit.

---

## Net schema impact

For the upcoming first Alembic migration:

- `brokerages.head_office_address JSONB` → `brokerages.head_office_address_raw TEXT`
- `brokerages.website_relevance` → `brokerages.website_relevance_heuristic`
- Remove screenshot-related columns (none in the current schema; remove screenshot module from the repository plan).
- Add `scrape_runs.diff_summary JSONB NULL`.
