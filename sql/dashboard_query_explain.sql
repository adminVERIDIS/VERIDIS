-- VERIDIS - EXPLAIN ANALYZE for the optimized dashboard query
-- Update these psql variables before execution.

\set tenant_id '550e8400-e29b-41d4-a716-446655440000'
\set organisation_id '660e8400-e29b-41d4-a716-446655440001'
\set rapport_id '770e8400-e29b-41d4-a716-446655440002'

EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
WITH rapport_scope AS MATERIALIZED (
    SELECT
        rap.id,
        rap.entreprise_id
    FROM rapports_csrd rap
    WHERE rap.id = :'rapport_id'::uuid
      AND rap.organisation_id = :'organisation_id'::uuid
    LIMIT 1
),
reponses_filtrees AS MATERIALIZED (
    SELECT
        r.rapport_id,
        r.code_esrs,
        r.statut,
        r.score,
        r.valeur,
        r.updated_at,
        r.requirement_id
    FROM reponses_esrs r
    JOIN rapport_scope rs ON rs.id = r.rapport_id
    WHERE r.tenant_id = :'tenant_id'::uuid
      AND r.statut IN ('complete', 'partiel', 'valide')
)
SELECT
    rf.rapport_id,
    rf.code_esrs,
    rf.statut,
    rf.score,
    rf.valeur,
    rf.updated_at,
    req.intitule,
    req.severite,
    e.raison_sociale,
    e.secteur_naf
FROM reponses_filtrees rf
JOIN rapport_scope rs ON rs.id = rf.rapport_id
JOIN esrs_requirements req ON req.id = rf.requirement_id
JOIN entreprises e ON e.id = rs.entreprise_id
ORDER BY
    CASE req.severite
        WHEN 'critique' THEN 1
        WHEN 'majeur' THEN 2
        WHEN 'mineur' THEN 3
        ELSE 4
    END,
    rf.score ASC;
