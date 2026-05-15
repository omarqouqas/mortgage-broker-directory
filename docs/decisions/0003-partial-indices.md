# 0003 — Partial indices on `is_active = true` deferred

- **Date:** 2026-05-15
- **Status:** Deferred
- **Author:** project owner + Claude Code
- **Scope:** Indexing strategy on `brokerages`, `brokers`, `broker_licenses`.

## Context

The initial schema migration (Session 2) added plain B-tree indices on `is_active` for `brokerages`, `brokers`, and `broker_licenses`. Because soft-delete via `is_active` is the canonical lifecycle path (see [[0001-initial-scope-clarifications]]), nearly every read query will include `WHERE is_active = true`. Postgres supports **partial indices** scoped to that predicate, which would yield smaller, denser indices and ignore tombstoned rows entirely.

## What we considered

Replacing the plain indices with partial variants on all three tables:

```sql
CREATE INDEX ix_brokerages_is_active ON brokerages (is_active) WHERE is_active = true;
CREATE INDEX ix_brokers_is_active ON brokers (is_active) WHERE is_active = true;
CREATE INDEX ix_broker_licenses_is_active ON broker_licenses (is_active) WHERE is_active = true;
```

Plus partial variants on the other lookup columns (`website_status`, `license_status`, etc.) scoped to active rows.

## Decision

Defer. Keep plain B-tree indices for now.

## Why

1. **No data on the active/inactive ratio.** The tables are empty. Partial indices win when the excluded predicate covers a meaningful fraction of rows — at zero rows we have no evidence either way.
2. **An empty table doesn't benefit from a partial index.** Index size savings only show up at scale; until at least one province is scraped end-to-end, the optimization is speculative.
3. **Partial indices are easy to add later as a non-breaking migration.** Switching is `DROP INDEX` + `CREATE INDEX ... WHERE is_active = true` in one Alembic file. We can't easily reverse the decision in the other direction without re-running the same migration backwards.

## Triggers for reconsideration

Reopen this decision when **any** of the following becomes true:

- **Post-Ontario-scrape ratio check.** After the FSRA scrape lands real data, if the active-to-inactive ratio is **worse than 60/40** (i.e. > 40% of rows have `is_active = false`), partial indices materially improve cache locality and shrink the index. Revisit.
- **EXPLAIN ANALYZE shows the plain index isn't selective enough.** If a `WHERE is_active = true AND ...` query in the read path falls back to a sequential scan or uses the `is_active` index with a row-filter step that touches a large fraction of the index, the partial variant is the correct fix.
- **Pre-launch index audit.** Before the frontend goes live (Step 6), do a final EXPLAIN pass over the top 10 read queries with realistic row counts.

## What it changes today

Nothing. Plain indices stay as written in the `f6958f02df98` initial-schema migration.
