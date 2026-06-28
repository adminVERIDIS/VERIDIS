-- VERIDIS - Dashboard CSRD indexes
-- PostgreSQL 16
-- Production-safe: CREATE INDEX CONCURRENTLY must be executed outside a transaction.

SET lock_timeout = '5s';
SET statement_timeout = '15min';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reponses_esrs_dashboard_covering
ON reponses_esrs (
    tenant_id,
    rapport_id,
    statut,
    requirement_id
)
INCLUDE (
    code_esrs,
    score,
    valeur,
    updated_at
)
WHERE statut IN ('complete', 'partiel', 'valide');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rapports_csrd_dashboard_guard
ON rapports_csrd (
    id,
    organisation_id
)
INCLUDE (
    entreprise_id
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entreprises_dashboard_lookup
ON entreprises (
    id
)
INCLUDE (
    raison_sociale,
    secteur_naf
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_esrs_requirements_dashboard_lookup
ON esrs_requirements (
    id
)
INCLUDE (
    intitule,
    severite
);

ANALYZE reponses_esrs;
ANALYZE rapports_csrd;
ANALYZE entreprises;
ANALYZE esrs_requirements;

-- Commentaire DBA apres code:
-- Le prompt corrigé proposait organisation_id dans l'index reponses_esrs.
-- Cet index serait invalide si reponses_esrs ne possède pas réellement cette colonne.
-- Si la colonne existe déjà, l'index alternatif suivant peut remplacer le premier index:
--
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reponses_esrs_dashboard_covering_with_org
-- ON reponses_esrs (
--     tenant_id,
--     organisation_id,
--     rapport_id,
--     statut,
--     requirement_id
-- )
-- INCLUDE (
--     code_esrs,
--     score,
--     valeur,
--     updated_at
-- )
-- WHERE statut IN ('complete', 'partiel', 'valide');
