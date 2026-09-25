-- ============================================================================
-- Verificación de la migración v3.1.0
-- Fecha: 2026-09-13
-- Proyecto: proy_scrapping_detail (scraper de calendario económico)
-- ============================================================================
-- Ejecutar después de 04_migration_3.1.0.sql y de un ciclo de scrapers.
-- Solo consultas de lectura: no modifica datos.
-- ============================================================================

\echo '=> [06] Verificación migración v3.1.0'

-- ----------------------------------------------------------------------------
-- 1. raw_payload de eventos nullable
-- ----------------------------------------------------------------------------
\echo '=> [06] 1. fact_economic_event.raw_payload'
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'fact_economic_event'
  AND column_name = 'raw_payload';
-- Esperado: is_nullable = 'YES'

-- ----------------------------------------------------------------------------
-- 2. Las 29 columnas de fact_economic_event
-- ----------------------------------------------------------------------------
\echo '=> [06] 2. Columnas de fact_economic_event'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'fact_economic_event'
ORDER BY ordinal_position;
-- Esperado: 29 filas

-- ----------------------------------------------------------------------------
-- 3. Auditoría del calendario
-- ----------------------------------------------------------------------------
\echo '=> [06] 3. audit_sync_run (calendario)'
SELECT script_name, status, COUNT(*) AS ejecuciones
FROM audit_sync_run
WHERE script_name = 'calendario'
GROUP BY script_name, status
ORDER BY script_name, status;

-- ----------------------------------------------------------------------------
-- 4. Checkpoint del calendario
-- ----------------------------------------------------------------------------
\echo '=> [06] 4. sync_checkpoint (calendario)'
SELECT script_name, last_event_id, records_processed, status, last_run_at
FROM sync_checkpoint
WHERE script_name = 'calendario';

-- ----------------------------------------------------------------------------
-- 5. Series de mercado del radar (muestra)
-- ----------------------------------------------------------------------------
\echo '=> [06] 5. fact_market_series (muestra)'
SELECT
    a.symbol,
    COUNT(*) AS filas,
    MIN(ms.timestamp_utc) AS primera,
    MAX(ms.timestamp_utc) AS ultima
FROM fact_market_series ms
JOIN dim_asset a ON a.asset_id = ms.asset_id
GROUP BY a.symbol
ORDER BY a.symbol
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 6. Universo de dim_asset por origen
-- ----------------------------------------------------------------------------
\echo '=> [06] 6. dim_asset por source_discovered_by'
SELECT source_discovered_by, COUNT(*) AS total
FROM dim_asset
WHERE is_active AND current_version
GROUP BY source_discovered_by
ORDER BY source_discovered_by;

-- ----------------------------------------------------------------------------
-- 7. Países del calendario
-- ----------------------------------------------------------------------------
\echo '=> [06] 7. dim_country'
SELECT country_code, country_name
FROM dim_country
ORDER BY country_code;

\echo '=> [06] Verificación finalizada'
-- ============================================================================
-- FIN verificación
-- ============================================================================
