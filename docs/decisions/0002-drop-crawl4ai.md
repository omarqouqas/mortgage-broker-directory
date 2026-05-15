# 0002 — Drop Crawl4AI in favor of httpx + selectolax + markdownify

- **Date:** 2026-05-14
- **Status:** Accepted
- **Supersedes (partially):** the Crawl4AI line in `CLAUDE.md` stack table and §3.1 of `docs/strategy/01-steps-1-3-scrape-clean-verify.md`

## Context

Original plan used Crawl4AI for the website-verification fetcher (§3.1) on the premise that it provided LLM-friendly content extraction. Dry-resolving `crawl4ai==0.8.6` against PyPI before committing to Batch B surfaced the actual transitive cost:

- ~80 transitive packages
- Includes (as **base** deps, not opt-in extras): `unclecode-litellm` (a fork of litellm), `openai`, `tiktoken`, `huggingface-hub`, `tokenizers`, `nltk`, `scipy`, `shapely`, `trimesh`, `rtree`, three Playwright packages (`playwright`, `playwright-stealth`, `patchright`), `pillow`, `numpy`
- Heavy ML stack (`torch`, `transformers`, `sentence-transformers`) is opt-in via `[torch] / [transformer] / [cosine] / [all]` extras — **not** pulled in base

So Crawl4AI's base install is not "ML-heavy" in the torch sense, but it does ship a full LLM-SDK stack (litellm + openai + tiktoken + huggingface-hub) plus geometry libs (shapely/trimesh/rtree) for features we will not use.

## Decision

Drop `crawl4ai` from the project. Build the website-verification fetcher directly from:

- `httpx[http2]` — async fetch with redirect handling
- `selectolax` — fast HTML parsing (already specified in CLAUDE.md as the preferred parser)
- `markdownify` — HTML → markdown conversion for downstream keyword classification (deps: `beautifulsoup4`, `six`; bs4 is used internally by markdownify only — our parser remains selectolax)
- `playwright` — fallback for JS-rendered pages

## Why

1. **Philosophy fit.** Step 4 specialty classification goes through the Anthropic SDK per `CLAUDE.md`. Crawl4AI's value-adds (LLM extraction strategies, cosine/transformer similarity, visual extraction) are features we have explicitly decided not to use.
2. **Compliance fit.** Crawl4AI ships `patchright` (a Playwright fork that evades bot detection). Our scraping rules ("Honor robots.txt always; no CAPTCHA solving; identify the bot in User-Agent") are the opposite stance from a stealth fork. Better to not have it installed at all.
3. **Disk + supply-chain footprint.** ~75 fewer transitive packages. Smaller attack surface, faster `uv sync`, cleaner Renovate/Dependabot noise.
4. **Replacement cost is small.** The §3.3 keyword heuristic operates on flat text — we don't need Crawl4AI's "smart extraction." A ~30-line fetcher + markdown converter does the job.

## What changes

- `CLAUDE.md` stack table updated.
- `requirements` (Batch B): `crawl4ai` removed; `markdownify` added.
- `verification/liveness.py` (Task #3) will be implemented as a direct `httpx` + `selectolax` + `markdownify` pipeline.
- `docs/strategy/01-steps-1-3-scrape-clean-verify.md` §3.1 still references Crawl4AI; left as historical record — this ADR is the operative source.

## Trade-offs accepted

- We don't get Crawl4AI's content-quality heuristics for stripping nav/footer noise. For the keyword classifier (which scans for terms like "mortgage", "broker", "amortization"), nav/footer noise is irrelevant. If we ever need cleaned main-content extraction, we'll add it deliberately.
- We don't get Crawl4AI's built-in caching or browser pooling. We'll build minimal versions of those in `verification/liveness.py` when needed (or not — for one-shot homepage fetches we may not need either).
