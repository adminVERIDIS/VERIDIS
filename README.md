# PROMPT #2 - ScoreGauge + Dashboard Query Optimization

Livrable pour VERIDIS, SaaS CSRD premium.

## Files

```text
components/ScoreGauge.tsx
components/index.ts
sql/001_dashboard_indexes_up.sql
sql/001_dashboard_indexes_down.sql
sql/dashboard_query_optimized.sql
sql/dashboard_query_explain.sql
sql/expected_plan_after_optimization.txt
scripts/pgbench-dashboard-query.sql
scripts/run-dashboard-pgbench.ps1
monitoring/prometheus-dashboard-p95-alert.yml
docs/dba-justification.md
```

## ScoreGauge

- React + TypeScript strict
- SVG pure + Framer Motion
- No Recharts, no Chart.js, no D3
- 270 degree gauge open at the bottom
- ticks every 10 points
- labels at 0, 25, 50, 75, 100
- animated needle/cursor
- central value in JetBrains Mono fallback stack
- optional detail badge + shadcn/ui tooltip
- accessible `role="meter"`

## SQL

Run index creation outside a transaction:

```bash
psql "$DATABASE_URL" -f sql/001_dashboard_indexes_up.sql
```

Validate:

```bash
psql "$DATABASE_URL" -f sql/dashboard_query_explain.sql
```

Rollback:

```bash
psql "$DATABASE_URL" -f sql/001_dashboard_indexes_down.sql
```

## Performance Test

```powershell
.\scripts\run-dashboard-pgbench.ps1 `
  -DatabaseUrl $env:DATABASE_URL `
  -TenantId "550e8400-e29b-41d4-a716-446655440000" `
  -OrganisationId "660e8400-e29b-41d4-a716-446655440001" `
  -RapportId "770e8400-e29b-41d4-a716-446655440002"
```

## Monitoring

Use `monitoring/prometheus-dashboard-p95-alert.yml` with an application histogram named:

```text
veridis_dashboard_query_duration_seconds_bucket{query="dashboard_esrs"}
```

Target alert: p95 above 100 ms for 5 minutes.
