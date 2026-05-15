# Territories — YT, NT, NU

## Decision

For Steps 1–3, the three territorial regulators are **not** scraped programmatically. Licensee data is entered manually into `data/raw/territories/manual.csv`. Decision recorded in [`docs/decisions/0001-initial-scope-clarifications.md`](../decisions/0001-initial-scope-clarifications.md#6-territories--no-automated-scraping).

## Rationale

- **Volume.** Licensee counts per territory are very small (single to low double digits each). Total expected territorial rows: <50.
- **Format heterogeneity.** Each territory's mortgage broker oversight lives in a different ministry/office, with no consistent public search UI or downloadable register.
- **Cost-benefit.** Building three province-style Playwright scrapers for ~30 total records is uneconomic vs. one-time manual entry plus an annual refresh check.

## Compliance posture

Same standard as the provinces:

- Data must come from public regulatory records only (no scraping behind logins, no PII beyond what the regulator publishes).
- Each row in `manual.csv` must include a `registry_source_url` pointing to the public page that establishes the licensee's status.
- A `scraped_at` timestamp (entry timestamp, for manual rows) is required.
- Refresh cadence: review territorial registers at least annually; capture refresh timestamps in `scrape_runs` with `source = 'TERRITORIES_MANUAL'`.

## Operating notes

- The CSV header in `data/raw/territories/manual.csv` is the canonical column set for territory entry. Cleaning code reads this CSV alongside provincial JSON exports.
- If a territory ever publishes a structured register, promote that territory to a real scraper module and drop its rows from `manual.csv`.
- This file is the **only** approved manual-entry path. Other provinces must remain scraped — manual entry there would defeat the audit trail.
