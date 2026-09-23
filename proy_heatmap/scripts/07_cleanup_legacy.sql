-- ============================================================================
-- Limpieza de funciones no usadas por el scraper v3.1.0
-- Fecha: 2026-09-13
-- Proyecto: proy_scrapping_detail (scraper de calendario económico)
-- ============================================================================
-- La función upsert_market_series() NO se usa por el scraper v3.1.0
-- (usa INSERT ... ON CONFLICT batch vía execute_values).
-- Se mantiene por compatibilidad; el DROP está comentado por seguridad.
--
-- NO eliminar upsert_heatmap_snapshot(): la usa el proyecto heatmap.
-- ============================================================================

\echo '=> [07] Limpieza de funciones legacy'

-- ----------------------------------------------------------------------------
-- 1. Verificar si upsert_market_series() tiene dependencias
-- ----------------------------------------------------------------------------
\echo '=> [07] 1. Dependencias de upsert_market_series'
SELECT
    dependent_ns.nspname AS schema_name,
    dependent_view.relname AS dependent_object
FROM pg_depend
JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid
JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
WHERE pg_depend.refobjid = 'upsert_market_series'::regprocedure;

-- Si no hay dependencias, se puede eliminar (descomentar manualmente):
-- DROP FUNCTION IF EXISTS upsert_market_series(
--     character varying, timestamp with time zone, numeric, numeric,
--     numeric, numeric, numeric, numeric, numeric, numeric, numeric,
--     jsonb, character varying
-- );

-- ----------------------------------------------------------------------------
-- 2. Verificar si upsert_heatmap_snapshot() tiene dependencias
--    (ESTA SÍ se usa por el proyecto heatmap — NO eliminar)
-- ----------------------------------------------------------------------------
\echo '=> [07] 2. Dependencias de upsert_heatmap_snapshot'
SELECT
    dependent_ns.nspname AS schema_name,
    dependent_view.relname AS dependent_object
FROM pg_depend
JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid
JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
WHERE pg_depend.refobjid = 'upsert_heatmap_snapshot'::regprocedure;
-- NO eliminar esta función: la usa el heatmap

\echo '=> [07] Limpieza finalizada (sin cambios destructivos)'
-- ============================================================================
-- FIN limpieza
-- ============================================================================
