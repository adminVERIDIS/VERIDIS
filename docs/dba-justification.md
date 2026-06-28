# VERIDIS Dashboard Query Optimization

## Objective

Target: p95 below 100 ms on PostgreSQL 16 for the dashboard query over `reponses_esrs` at 10M+ rows.

## Main Fixes

1. Filter `reponses_esrs` through a partial covering index:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reponses_esrs_dashboard_covering
ON reponses_esrs (tenant_id, rapport_id, statut, requirement_id)
INCLUDE (code_esrs, score, valeur, updated_at)
WHERE statut IN ('complete', 'partiel', 'valide');
```

This removes the old pattern where `idx_reponses_esrs_rapport` found rows by `rapport_id`, then filtered `tenant_id` and `statut` afterwards.

2. Guard the report scope first:

```sql
WITH rapport_scope AS MATERIALIZED (...)
```

The query validates `rapport_id + organisation_id` once, then uses that scoped report to read responses. This keeps tenant and organisation checks explicit without denormalizing.

3. Use index-only lookup indexes on dimension tables:

```sql
idx_rapports_csrd_dashboard_guard
idx_entreprises_dashboard_lookup
idx_esrs_requirements_dashboard_lookup
```

These reduce heap visits for columns displayed on every dashboard load.

4. Keep the final sort in memory.

The `ORDER BY CASE req.severite ...` cannot be fully satisfied by an index across the join unless `severite_rank` is persisted or denormalized. After filtering to one report, this sort should run over a small result set and remain cheap.

## Validation Command

```bash
psql "$DATABASE_URL" -f sql/001_dashboard_indexes_up.sql
psql "$DATABASE_URL" -f sql/dashboard_query_explain.sql
```

Check for:

- `Index Only Scan using idx_reponses_esrs_dashboard_covering`
- low shared read blocks after cache warmup
- no `Seq Scan` on `reponses_esrs`
- execution time below 100 ms at p95 in load testing

## Important Schema Note

The corrected prompt proposed an index on `reponses_esrs(tenant_id, organisation_id, rapport_id, ...)`. The provided query does not show `organisation_id` on `reponses_esrs`; it is checked through `rapports_csrd`.

The runnable migration therefore avoids that column. If `reponses_esrs.organisation_id` really exists, use the alternative index included as a comment in `001_dashboard_indexes_up.sql`.
