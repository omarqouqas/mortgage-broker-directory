# Canadian Mortgage Broker Directory — Step 4: Specialty Enrichment

> Scope: Step 4 of Frey Chu's 7-step directory build — **Inventory/Specialty Enrichment**. Builds on Steps 1–3 (Scrape, Clean, Verify) which produced a verified dataset of every active broker + brokerage + website.

---

## Why This Step Is the Whole Game

Steps 1–3 give us geography and contact data. **Anyone with a scraper and a credit card can replicate that** — FSRA's registry is public, Outscraper is a vendor.

Step 4 is where the directory becomes uncopiable, and where the *revenue* lives. Differentiating brokers by **specialty** (halal, newcomer, self-employed, B-lender access, languages spoken, commercial, construction, private, etc.) is what serves actual user intent. Nobody Googles "mortgage broker near me" anymore — they Google "halal mortgage Mississauga" or "self-employed mortgage broker Toronto." We rank for the long tail of specialty + geography queries, and those queries are where leads convert and brokers will pay to be featured.

This is a **standalone directory business**. Monetization is direct: paid Featured tiers, lead-routing fees from brokers, lender affiliate revenue. There is no SaaS upsell. Every product decision in this step should optimize for the directory's own P&L — not for a future SaaS handoff.

---

## What Steps 1–3 Handed Off

- `brokerages` table with verified `website_url` and `website_relevance = 'mortgage_broker'`
- ~15K Ontario brokers + brokerages (more as other provinces come online)
- Verified, deduplicated, classified-as-relevant dataset

## Target Outcome of Step 4

For every brokerage with a live, mortgage-relevant website:

- **Specialties** assigned across 6 categories with confidence scores and evidence excerpts
- **Languages spoken** detected
- **Lender panel** extracted where listed (many brokers publish this)
- **Provenance** for every assignment — which page, which excerpt, when classified, which model version

Result: every public broker profile shows accurate, filterable, evidence-backed specialties. The directory can serve queries like:

- "Halal mortgage broker in Ontario who speaks Arabic"
- "Self-employed mortgage broker in Toronto with B-lender access"
- "Newcomer mortgage specialist in Mississauga who speaks Mandarin"

These are the queries with intent. These are the queries that convert.

---

## The Specialty Taxonomy — Revenue-Tiered

The taxonomy lives in a versioned config file (`src/mbd/taxonomy/specialties.yaml`) and is loaded into the `specialties` table on each migration.

**Critical: not all specialties are worth equal investment.** Standalone monetization (Featured tiers, lead routing, lender affiliates) is concentrated in a handful of high-margin niches. The taxonomy is therefore tiered by revenue value, and classification quality investment is tiered to match.

### Tier 1 — Revenue priority (build the moat here)

These are the specialties with the richest broker margins, highest lender CPLs, and weakest competing directories. Classification quality must be excellent: hand-labeled validation, dedicated calibration examples, manual spot-checks on every classifier run.

| Slug | Why it monetizes |
|---|---|
| `halal_sharia_compliant` | Underserved niche; ~2M Muslim Canadians; halal lenders (Eqraz, Manzil, CHFC, Ijara) pay $300–500/closed referral; almost no quality directory exists |
| `new_to_canada` | Big bank newcomer programs are aggressively marketed; high CPL ($75–150); rich affiliate stack (insurance, legal, settlement services) |
| `self_employed_bfs` | B-lender margins are 50–100bps higher than A-lender; brokers compete hard for these clients; willing to pay premium for placement |
| `b_lender` (lender access) | Same logic — high-margin alt lending; broker specialty signals matter |
| `private_mortgage` | Highest margin segment in mortgage brokering; brokers pay aggressively for qualified leads |
| `commercial_mortgage` | Different audience entirely (business owners), high deal sizes, premium leads |
| `bruised_credit` / `bankruptcy_consumer_proposal` | Highest-margin alt lending, brokers will pay 2–3× standard CPL for qualified leads |
| `construction_mortgage` | Niche product, specialist brokers, willing to pay for qualified leads |

### Tier 2 — Useful for filtering, modest monetization

These improve UX and SEO but don't independently drive premium pricing. Standard classification quality (no extra calibration examples beyond Tier 1's reuse).

`residential_purchase`, `residential_refinance`, `residential_renewal`, `first_time_homebuyer`, `real_estate_investor`, `rental_property_buyer`, `heloc`, `second_mortgage`, `reverse_mortgage_chip`, `bridge_financing`, `non_resident_foreign_buyer`, `high_net_worth`, `multi_unit_2_to_4`, `multi_unit_5_plus`, `mixed_use_commercial`

### Tier 3 — Long tail, best-effort

Useful for completeness and discovery. Classification happens in the same pass but isn't validated against hand-labeled sets.

`t4a_contractor`, `divorce_separation`, `inherited_property`, `senior_55_plus`, `rural_property`, `mobile_manufactured_home`, `vacation_property`

### Languages spoken (separate filter axis)

ISO 639-1 codes. Priority set for the Canadian market: `fr`, `zh-yue` (Cantonese), `zh` (Mandarin), `pa` (Punjabi), `es`, `ur`, `hi`, `ar`, `tl` (Tagalog), `it`, `pt`, `fa` (Persian), `ko`, `vi`, `ru`, `uk`, `so` (Somali), `gu`, `ta`, `pl`, `de`, `bn`. English is assumed default and not stored.

Languages are revenue-relevant in combination with Tier 1 specialties — "halal mortgage broker who speaks Arabic" or "Mandarin-speaking newcomer specialist" are the high-converting compound queries.

### Service style (Tier 3, low priority)

`digital_first_application`, `in_person_meetings`, `weekend_availability`, `evening_availability`, `same_day_pre_approval`, `multilingual_team`

**Taxonomy versioning:** Every classification stores the taxonomy version it used. When we add specialties to the taxonomy, prior classifications stay valid; new specialties get classified in the next nightly pass.

**Tier in the schema:** the `specialties` table has a `revenue_tier` column (1/2/3) so downstream code — SEO page generation, Featured tier pricing, lead-routing logic — can prioritize accordingly.

---

## Schema Additions

```sql
CREATE TABLE specialties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,                    -- 'self_employed_bfs'
  category TEXT NOT NULL,                       -- 'product' | 'client' | 'lender' | 'language' | 'religious' | 'service'
  revenue_tier SMALLINT NOT NULL,               -- 1 = high-margin priority, 2 = standard, 3 = long tail
  display_name TEXT NOT NULL,                   -- 'Self-Employed / Business-for-Self'
  description TEXT NOT NULL,                    -- one-paragraph definition used in classifier prompt
  detection_hints JSONB,                        -- {synonyms: [...], anti_signals: [...]}
  display_order INT,
  is_active BOOLEAN DEFAULT TRUE,
  taxonomy_version INT NOT NULL                 -- which release introduced this
);

CREATE TABLE broker_specialty_assignments (
  broker_id UUID REFERENCES brokers(id) ON DELETE CASCADE,
  specialty_id UUID REFERENCES specialties(id),
  confidence NUMERIC(3,2) NOT NULL,             -- 0.00 – 1.00
  evidence_excerpt TEXT,                        -- max 300 chars
  evidence_page_url TEXT,                       -- which page the excerpt came from
  classified_at TIMESTAMPTZ NOT NULL,
  classifier_model TEXT NOT NULL,               -- 'claude-sonnet-4-6'
  classifier_run_id UUID REFERENCES enrichment_runs(id),
  PRIMARY KEY (broker_id, specialty_id)
);

CREATE TABLE lenders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  legal_name TEXT NOT NULL UNIQUE,              -- 'Equitable Bank'
  trade_names TEXT[],                           -- ['Equitable Trust', 'EQB']
  tier TEXT NOT NULL,                           -- 'a_lender' | 'monoline' | 'b_lender' | 'credit_union' | 'private_mic'
  is_halal BOOLEAN DEFAULT FALSE,               -- Eqraz, Manzil, CHFC, Ijara
  province_coverage TEXT[],                     -- which provinces they lend in
  website TEXT,
  notes TEXT
);

CREATE TABLE broker_lender_relationships (
  broker_id UUID REFERENCES brokers(id),
  lender_id UUID REFERENCES lenders(id),
  confidence NUMERIC(3,2),
  evidence_excerpt TEXT,
  evidence_page_url TEXT,
  PRIMARY KEY (broker_id, lender_id)
);

CREATE TABLE broker_websites (
  brokerage_id UUID PRIMARY KEY REFERENCES brokerages(id) ON DELETE CASCADE,
  sitemap_urls TEXT[],
  pages_crawled JSONB,                          -- [{url, page_type, content_md, crawled_at, etag}]
  total_word_count INT,
  last_crawled_at TIMESTAMPTZ,
  crawl_status TEXT                             -- 'success' | 'partial' | 'failed'
);

CREATE TABLE enrichment_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  taxonomy_version INT NOT NULL,
  classifier_model TEXT NOT NULL,
  brokers_processed INT,
  total_input_tokens BIGINT,
  total_output_tokens BIGINT,
  estimated_cost_usd NUMERIC(10,2),
  errors JSONB
);

-- Monetization tables (designed in now, used in Step 6+ when claim flow ships)

CREATE TABLE broker_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_id UUID UNIQUE REFERENCES brokers(id),  -- 1:1 with the broker we already have
  supabase_auth_user_id UUID UNIQUE NOT NULL,    -- Supabase Auth ID
  email TEXT NOT NULL,
  email_verified_at TIMESTAMPTZ,
  claim_verified_at TIMESTAMPTZ,                  -- when ownership was confirmed
  claim_verification_method TEXT,                 -- 'email_on_brokerage_domain' | 'phone_callback' | 'manual_admin'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_account_id UUID REFERENCES broker_accounts(id),
  tier TEXT NOT NULL,                             -- 'free' | 'featured' | 'featured_plus' | 'lead_gen'
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT NOT NULL,                           -- 'active' | 'past_due' | 'cancelled' | 'trialing'
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  consumer_email TEXT NOT NULL,
  consumer_phone TEXT,
  consumer_postal_code TEXT,
  requested_specialty_slugs TEXT[],               -- what the consumer filtered for
  requested_language_codes TEXT[],
  requested_province TEXT,
  consumer_message TEXT,
  matched_broker_ids UUID[],                      -- up to 3 brokers routed to
  status TEXT NOT NULL,                           -- 'new' | 'delivered' | 'responded' | 'closed' | 'rejected'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE lead_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  broker_id UUID REFERENCES brokers(id),
  delivered_at TIMESTAMPTZ NOT NULL,
  broker_response_status TEXT,                    -- 'accepted' | 'declined' | 'no_response' | 'reported_low_quality'
  broker_responded_at TIMESTAMPTZ,
  price_charged_usd NUMERIC(8,2),
  stripe_payment_intent_id TEXT,
  disputed BOOLEAN DEFAULT FALSE,
  refunded BOOLEAN DEFAULT FALSE
);

-- Pricing config (per specialty × province) lives in YAML; this is a cache for fast reads
CREATE TABLE lead_pricing (
  specialty_slug TEXT NOT NULL,
  province TEXT NOT NULL,
  price_usd NUMERIC(8,2) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (specialty_slug, province)
);
```

---

## Pipeline Stages for Step 4

### Stage 4.1 — Multi-page site crawl

For every brokerage with `website_status = 'live'` and `website_relevance = 'mortgage_broker'`:

1. **Page discovery:**
   - Try `sitemap.xml` first
   - Fall back to homepage crawl + follow internal links matching priority patterns:
     - `/about`, `/about-us`, `/team`, `/who-we-are`
     - `/services`, `/products`, `/mortgage-types`, `/solutions`
     - `/lenders`, `/our-lenders`, `/partners`
     - `/specialties`, `/specialty`, `/specializations`
     - `/languages`, `/multilingual`
     - `/faq`, `/frequently-asked-questions`
     - `/halal`, `/sharia`, `/islamic`
     - `/newcomer`, `/new-to-canada`, `/immigrants`
     - `/self-employed`, `/business-for-self`, `/bfs`
     - `/commercial`, `/construction`, `/private-mortgage`
   - Cap at 10 pages per domain

2. **Crawl with Crawl4AI** (markdown output mode), polite throttle (1 req/sec/domain), cache to `data/crawled/{brokerage_id}/`

3. **Store in `broker_websites.pages_crawled`** with ETag for cache validation on re-crawls

### Stage 4.2 — Classification with Claude (Batch API + prompt caching)

The classification prompt is the moat. Architecture:

```
[STATIC, CACHED PORTION — ~3K tokens, cached for 1h]
- Role definition
- Full taxonomy with slug + display_name + description + detection_hints for each specialty
- Output schema (JSON)
- Calibration examples (5–10 worked examples covering edge cases)

[DYNAMIC PORTION — ~30–50K tokens per broker]
- Broker name, brokerage name, province
- Concatenated markdown of all crawled pages with page_url separators
```

**Why prompt caching matters:** the taxonomy + examples (~3K tokens) is identical across all 15K broker classifications. Caching it cuts input cost ~90% on the cached portion.

**Why Batch API matters:** non-interactive classification cuts cost ~50% on top of caching. Combined, the full Ontario classification run lands around **$0.05–0.08 per broker**, ~$1,000 total for 15K. Affordable enough to re-run the full set when the taxonomy version bumps.

**Output schema** (Pydantic, used as Claude's structured output):

```python
class SpecialtyAssignment(BaseModel):
    specialty_slug: str
    confidence: float  # 0.0–1.0
    evidence_excerpt: str | None  # max 300 chars
    evidence_page_url: str | None

class LenderMention(BaseModel):
    lender_legal_name: str  # canonical from `lenders` table; classifier outputs string, code resolves
    confidence: float
    evidence_excerpt: str | None
    evidence_page_url: str | None

class BrokerEnrichmentOutput(BaseModel):
    broker_id: UUID
    specialties: list[SpecialtyAssignment]
    lenders_mentioned: list[LenderMention]
    overall_confidence: float  # how rich was the source content
    notes: str | None  # classifier observations (e.g., "site is sparse, low signal")
```

**Confidence calibration anchors** (included in the prompt examples):

| Confidence | Anchor |
|---|---|
| 1.00 | Dedicated landing page or explicit `<h1>` for the specialty |
| 0.85 | Explicit Services-page bullet or repeated mentions across multiple pages |
| 0.65 | Mentioned in About / FAQ but not featured |
| 0.45 | Mentioned once in passing |
| 0.25 | Inferred from related context (e.g., "we work with new Canadians" → infers `new_to_canada`) |
| <0.20 | Not surfaced in public directory |

**Public directory threshold:** assignments with `confidence ≥ 0.45` show on the public profile. `0.20–0.45` stay in DB for internal analytics and corrections flagging, but don't render publicly.

**Tier-aware classification quality:** during classifier prompt iteration (see First Three Tasks below), the calibration examples deliberately over-represent Tier 1 specialties. The classifier sees 5–10 worked examples for halal, newcomer, self-employed, B-lender, private — and 1–2 worked examples each for Tier 2/3 specialties. This is intentional: the classifier's failure modes on Tier 1 directly cost revenue, while failure modes on Tier 3 cost a marginal SEO improvement.

### Stage 4.3 — Lender resolution

The classifier outputs free-text lender names ("Equitable Bank", "EQB", "Equitable Trust"). A post-processor resolves them against the `lenders` table using:

1. Exact match on `legal_name` or any `trade_names` entry
2. Fuzzy match (rapidfuzz, ≥0.92) with manual-review queue for misses
3. Unknown lenders → write to `lenders_unmatched_queue.json` for periodic taxonomy expansion

Seed the `lenders` table on first run with ~50 known Canadian lenders (the script `seeds/load_lenders.py` does this). Sources for the canonical list: CMBA member directory, Mortgage Professionals Canada partner list.

### Stage 4.4 — Cross-signal validation

Once first-pass classification completes, run validation passes:

1. **Google reviews signal:** scan each brokerage's Google reviews (from Outscraper) for specialty keywords. A broker classified as `self_employed_bfs` whose reviews repeatedly thank them for self-employed expertise = strong cross-signal (bump confidence). Conversely, classified-as `halal_sharia_compliant` with no reviews ever mentioning halal/Sharia/Islamic = downgrade confidence.

2. **Lender-implies-specialty rules:** if `lenders_mentioned` includes Eqraz/Manzil/CHFC/Ijara → auto-assign `halal_sharia_compliant` at confidence 0.95. If `lenders_mentioned` includes ≥3 B-lenders → auto-assign `b_lender` access tag at confidence 0.85.

3. **Anti-signals:** if the site explicitly says "we don't work with X" — exclude X. (Rare but happens — e.g., some brokerages explicitly state they don't do private mortgages.)

---

## Cost & Throughput Estimates

**Per-broker cost (Sonnet 4.6, with prompt caching + Batch API):**

| Component | Tokens | Cost |
|---|---|---|
| Cached prompt (taxonomy + examples) | ~3K | ~$0.001 |
| Dynamic input (broker site content) | ~40K | ~$0.06 |
| Output (structured JSON) | ~1.5K | ~$0.011 |
| **Total / broker** | | **~$0.07** |

**Ontario full run:** ~15K brokers × $0.07 = **~$1,050**, one-time. Re-runs on taxonomy bumps: same. Nightly incremental (only changed sites, ~2% / day): ~$20/day.

**Throughput:** Batch API completes within 24h. Crawl is the bottleneck — at 1 req/sec/domain with parallelism across 15K domains, full crawl runs in ~4–6 hours.

---

## Quality Bar (Definition of Done for Step 4)

- [ ] ≥80% of live broker websites have at least one specialty assigned at confidence ≥ 0.45
- [ ] ≥95% of language detections cross-validate against an independent second-pass classifier run (consistency check)
- [ ] Hand-labeled validation set (100 randomly-sampled brokers) shows ≥85% precision and ≥70% recall on top-3 specialties
- [ ] Lender resolution: ≥90% of classifier-mentioned lenders resolve to canonical `lenders` table entries
- [ ] All assignments stored with evidence excerpt + source URL (no opaque classifications)
- [ ] Cost stays under $1,500 for full Ontario classification

---

## Repo Additions

```
src/mbd/
├── taxonomy/
│   ├── specialties.yaml         # source of truth — versioned
│   ├── lenders_seed.yaml        # ~50 known Canadian lenders
│   └── load.py                  # syncs YAML → DB on migration
│
├── enrichment/
│   ├── crawl.py                 # Stage 4.1 — multi-page crawl via Crawl4AI
│   ├── page_discovery.py        # sitemap parsing + heuristic link following
│   ├── classify.py              # Stage 4.2 — Anthropic Batch API + prompt caching
│   ├── prompts/
│   │   ├── classification_system.md
│   │   └── calibration_examples.yaml
│   ├── resolve_lenders.py       # Stage 4.3 — free-text → canonical lender
│   └── validate.py              # Stage 4.4 — cross-signals, anti-signals
│
└── pipeline/
    └── run_enrich.py            # CLI: `mbd enrich --brokerage-ids ... ` or `--all`
```

---

## Monetization Roadmap (Standalone)

Step 4's enrichment quality directly determines which of these revenue streams open up and when.

### Tier 1 revenue stream: Featured Broker subscription (ships in Step 6)

```
Free                  $0/mo    Auto-generated profile, no edits
Featured              $39/mo   Claim listing, edit profile, photos, top placement in 1 specialty
Featured Plus         $99/mo   Top placement in 3 specialties, lead-capture form, analytics
```

Target by month 12: 100–200 paid Featured subscribers = $4K–8K MRR. Hits these targets only if Tier 1 specialty classifications are clean — brokers who see themselves listed wrong don't pay.

### Tier 2 revenue stream: Pay-per-lead routing

Consumer fills out the directory lead form filtered by Tier 1 specialty + city + language → routed to up to 3 matching Featured brokers → broker pays per delivered lead.

```
General residential         $25–40/lead
Self-employed               $60–90/lead
New-to-Canada               $60–90/lead
Halal mortgage              $80–120/lead
Private mortgage            $100–150/lead
Commercial mortgage         $150–300/lead
```

`lead_pricing` table holds the price per specialty × province. Brokers opt into lead routing as an add-on to Featured; we don't sell leads to free-tier listings (protects supply/demand economics).

Target by month 18: $5K–10K/mo additional MRR from leads. This is the line item with the most upside and the most operational risk — lead quality disputes will be the single biggest support burden, so the `disputed` + `refunded` fields exist for a reason and dispute rate is the metric to watch obsessively.

### Tier 3 revenue stream: Lender affiliate partnerships

Halal lenders (Eqraz, Manzil, CHFC, Ijara) and newcomer mortgage programs pay $50–500 per closed loan. Negotiated 1:1 — phone-call sales, but high-margin.

Sequence: launch month 9 once we have demonstrable traffic. Reach out to halal lenders first (smallest, most relationship-driven, biggest beneficiaries of our `halal_sharia_compliant` filter).

### Tier 4 revenue stream: Adjacent service affiliates

Home insurance (Square One, Apollo), real estate lawyers, moving services, home inspection. $5–30/lead, low effort, layer on after traffic is established.

---

## Strategic Tie-Ins

**Claim-listing feedback loop:** Once a broker claims their listing, their corrections (specialties added/removed, languages confirmed, lender panel updated) become a labeled training set. After ~500 claim corrections we can fine-tune a smaller, cheaper classifier (Haiku) and reserve Sonnet for ambiguous cases — useful both for cost reduction and as a *proof-of-data-quality* talking point with lender affiliate partners.

**Specialty pages as SEO pages:** Every `{specialty} mortgage broker in {city}` combination becomes a generated Next.js page in Step 6. Prioritize generating Tier 1 specialty pages first (80 cities × 8 Tier 1 specialties = 640 high-value pages) before generating the long-tail 8,000 pages. These pages are the directory's compounding asset — they rank for high-intent queries, and they're what brokers see when they Google themselves and discover the directory.

**Halal sub-directory spinoff:** The `halal_sharia_compliant` filter + seeded halal-lender data + halal-specialist broker classifications is the seed of a standalone Halal Finance Canada directory if you ever want to spin it off. The data infrastructure built here makes that spinoff cost ~zero, and the spinoff would unlock a separate audience and a separate set of monetization partners (Wahed, Manzil Invest for halal investing, takaful insurance providers, halal credit cards). Treat this as a real option, not just a thought experiment — once you have 50+ verified halal-specialist brokers and 4 halal lenders profiled, the standalone halal directory is launchable in a weekend.

**Trust infrastructure as moat:** Because this is a standalone business with no SaaS halo, trust signals are load-bearing. Every broker profile should display:
- FSRA/BCFSA license number with a link to the regulator's verification page
- "Last verified [date]" timestamp from the verification pipeline
- Methodology link explaining how specialties are determined and corrections handled
- A clear "Report inaccuracy" link that creates a ticket and triggers re-verification

These cost almost nothing to build but are what make the directory genuinely defensible as an SEO and editorial property. They're also what convince lender affiliate partners to sign deals.

---

## First Three Tasks for Claude Code

1. **Taxonomy + lenders seed loaded into DB** — write `src/mbd/taxonomy/specialties.yaml` + `lenders_seed.yaml` with the initial taxonomy from this prompt. Each specialty entry includes `revenue_tier`. Build `taxonomy/load.py` to sync YAML → Postgres on migration. Verify with `SELECT slug, revenue_tier FROM specialties ORDER BY revenue_tier, slug;` returning all rows correctly tiered.

2. **Multi-page crawl for a single brokerage** — pick one well-known Toronto brokerage with a rich site (True North Mortgage or similar). Build `enrichment/crawl.py` end-to-end. Goal: page discovery → polite crawl → markdown stored in `broker_websites.pages_crawled`. Validate the page discovery heuristic catches About/Services/Lenders pages, and explicitly catches the high-monetization signal pages (`/halal`, `/sharia`, `/islamic`, `/newcomer`, `/self-employed`, `/business-for-self`, `/private-mortgage`).

3. **Classifier prototype against 12 hand-picked brokerages — Tier 1 heavy** — write the classification prompt, run it (non-batched, interactive Sonnet) against 12 brokerages deliberately spanning Tier 1 specialties: 2 halal-focused, 2 newcomer-focused, 2 self-employed-focused, 1 commercial, 1 private mortgage, 1 bruised-credit specialist, 1 multilingual generalist, 1 sparse-site control, 1 obvious mismatch (e.g., realtor with mortgage license). Eyeball the outputs against ground-truth labels you hand-write before running the classifier. Iterate on prompt + calibration examples until **Tier 1 precision is ≥90%**. **Only then** wire up the Batch API for the full run.

After step 3, the full Ontario enrichment is a ~$1K, one-night batch job — but the value isn't the cost saving, it's that Tier 1 quality is locked in before scaling. Then Step 5 (visual verification of logos/headshots, important for Featured tier presentation) and Step 6 (the public frontend + claim flow + Stripe + lead routing) become the next prompts.
