-- ============================================================================
-- Retención de raw_payload de eventos (6 meses)
-- Fecha: 2026-09-13
-- Proyecto: proy_scrapping_detail (scraper de calendario económico)
-- ============================================================================
-- Pone a NULL el raw_payload de eventos con más de 6 meses de antigüedad.
-- El JSONB de cada fila pesa ~792 bytes; 6 meses ≈ 1.5–3 MB en BD.
-- Los datos estructurados (actual, previous, forecast, etc.) se conservan.
--
-- Requiere haber aplicado 04_migration_3.1.0.sql (raw_payload nullable).
-- Frecuencia recomendada: mensual (cron).
-- ============================================================================

\echo '=> [05] Retención de raw_payload de eventos (> 6 meses)'

-- ----------------------------------------------------------------------------
-- 1. Contar cuántos eventos serían afectados (dry-run)
-- ----------------------------------------------------------------------------
\echo '=> [05] Dry-run: eventos candidatos'
SELECT COUNT(*) AS eventos_a_retener
FROM fact_economic_event
WHERE captured_at < NOW() - INTERVAL '6 months'
  AND raw_payload IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 2. Ejecutar la retención
-- ----------------------------------------------------------------------------
\echo '=> [05] Aplicando retención'
UPDATE fact_economic_event
SET raw_payload = NULL
WHERE captured_at < NOW() - INTERVAL '6 months'
  AND raw_payload IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. Verificar resultado
-- ----------------------------------------------------------------------------
\echo '=> [05] Verificación: distribución raw_payload'
SELECT
    COUNT(*) FILTER (WHERE raw_payload IS NOT NULL) AS con_raw,
    COUNT(*) FILTER (WHERE raw_payload IS NULL)     AS sin_raw,
    COUNT(*)                                         AS total
FROM fact_economic_event;

\echo '=> [05] Retención finalizada'
-- ============================================================================
-- FIN retención
-- ============================================================================
