-- VERIDIS - Dashboard CSRD indexes rollback
-- PostgreSQL 16
-- Production-safe: DROP INDEX CONCURRENTLY must be executed outside a transaction.

SET lock_timeout = '5s';
SET statement_timeout = '15min';

DROP INDEX CONCURRENTLY IF EXISTS idx_reponses_esrs_dashboard_covering;
DROP INDEX CONCURRENTLY IF EXISTS idx_rapports_csrd_dashboard_guard;
DROP INDEX CONCURRENTLY IF EXISTS idx_entreprises_dashboard_lookup;
DROP INDEX CONCURRENTLY IF EXISTS idx_esrs_requirements_dashboard_lookup;

-- Optional rollback if the alternative organisation_id index was used.
DROP INDEX CONCURRENTLY IF EXISTS idx_reponses_esrs_dashboard_covering_with_org;
