# 0004 — FSRA data access blocked; pivot to open-data outreach

- **Date:** 2026-05-15
- **Status:** Accepted
- **Author:** project owner + Claude Code
- **Scope:** Step 1 (ingest) sequencing across provinces; Ontario specifically.

## Context

Pre-flight check on the FSRA mortgage broker search page (`mbsweblist.fsco.gov.on.ca/agents.aspx`) ahead of writing the Ontario ingester. Findings:

1. **`robots.txt` is a blanket disallow:**
   ```
   User-agent: *
   Disallow: /
   ```
   Every path is disallowed for every crawler.

2. **FSRA's Open Data catalog** lists the licensed mortgage broker dataset as a **candidate for public release**, currently *"under review."* No public CSV or API endpoint exists today.

Per [[0001-initial-scope-clarifications]] and CLAUDE.md's compliance rules: **honor robots.txt always.** A blanket disallow means we will not scrape this page, full stop. No user-agent rotation, no CAPTCHA solving, no API endpoint sniffing, no working around the block.

## Decision

1. **Do not scrape `mbsweblist.fsco.gov.on.ca`.** Period.
2. **Pursue legitimate access** by emailing FSRA's open-data team (sent 2026-05-15), referencing the catalog page that already lists this dataset as a release candidate. Ask for either release timing or an interim machine-readable export.
3. **FOI request as fallback** if no substantive response within 14 days (by **2026-05-29**). Ontario's *Freedom of Information and Protection of Privacy Act* obligates a response within 30 calendar days.
4. **Do not block other work on Ontario.** Sequence the actual ingest work against the next province with legitimately accessible data, not by province size.

## Why

- Working around a blanket disallow would (a) violate our own compliance rule in CLAUDE.md, (b) put the project at legal risk in a regulated industry, (c) jeopardize future legitimate access by signaling we will scrape anyway.
- Open-data outreach has near-zero cost and a non-trivial chance of unblocking the dataset cleanly — FSRA itself already lists it as a release candidate.
- FOI is slow but binding; using it as the *fallback* (not the first move) keeps the relationship cooperative.

## Architectural implication

The "scrape each province" frame in `docs/strategy/01-steps-1-3-scrape-clean-verify.md` is **wrong**. Provinces fall into at least four access categories, and the one with the most brokers turns out to be the most restrictive:

| Access category | Example handling | ABC type |
|---|---|---|
| Open data CSV / dataset | scheduled download → diff against last snapshot | `BaseCSVImporter` |
| Documented API | authenticated client → paginated pull | `BaseAPIClient` |
| Scrapable HTML registry | Playwright/httpx + selectolax | `BaseScraper` |
| `robots.txt`-blocked | no automated access; outreach + FOI | n/a — manual or external |

Module-layout consequences:

- New directory `src/mbd/ingesters/` (replacing the prior `src/mbd/scrapers/` plan in `session-01-recap.md` and `session-02-recap.md`).
- The single `BaseScraper` ABC is replaced by a family of ingester ABCs, one per access category, all declared in `src/mbd/ingesters/base.py`.
- Each province module (`src/mbd/ingesters/{province}.py`) implements whichever ABC matches its access category.
- The CLI verb stays `mbd scrape` (user-facing word for "go pull the data") but the underlying implementation may not be a literal scraper. CLAUDE.md `## Commands` updated to reflect that.

## New sequencing for Step 1

1. **Short follow-up access-survey session** *before* any ingester code is written:
   - Confirm BC's BCFSA registrar access policy (HTML? CSV? `robots.txt`?).
   - Confirm Alberta's RECA registry access policy.
   - Spot-check Quebec (AMF), Saskatchewan (FCAA), Manitoba (FICOM).
2. **Pick the first province** by *access availability* (cleanest legitimate path), not by broker count.
3. **Implement the ingester for that province** as the reference implementation, simultaneously defining the ingester ABC contracts in `src/mbd/ingesters/base.py`.
4. **Ontario re-enters the queue** once FSRA responds, or 30 days post-FOI — whichever happens first.

## What it changes today

- This ADR + CLAUDE.md terminology updates (scrapers → ingesters; "Scraping rules" → "Data access rules").
- Session 3 plan changes from "FSRA scraper" to **"provincial access survey, then first ingester (province TBD)."**
- `docs/compliance/ontario.md` is still required when Ontario re-enters the queue — capture the outreach trail + the `robots.txt` finding so future contributors don't re-discover the block.

## Open follow-ups

- Draft the FSRA outreach email (project owner; not Claude's job to send).
- Calendar the FOI fallback for **2026-05-29** if no substantive reply.
- Track outreach status persistently — TBD whether that lives in this repo (e.g., `docs/access-tracker.md`) or off-repo.

## Reopen triggers

- FSRA publishes the dataset (open data CSV or API) → switch Ontario from "blocked" to "CSV import" or "API client" category and slot it back into the sequence.
- FSRA grants a one-off export → ingest it, store provenance + retrieval date, and revisit cadence for refresh.
- FOI denies access → escalate (appeal to IPC, or accept Ontario as a manual-entry province for v1).
