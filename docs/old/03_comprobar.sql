-- =============================================================================
-- CHECKLIST — heatmap_stock v1.0.2 (corte 2026-09-11)
-- =============================================================================

-- 0. Esquema por defecto
SELECT tablename FROM pg_tables
WHERE schemaname = 'public' AND (tablename LIKE 'fact_%' OR tablename LIKE 'dim_%')
ORDER BY tablename;

-- 1. dim_asset — columnas de la taxonomía / seed (v1.0.2)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'dim_asset'
ORDER BY ordinal_position;

-- 2. Índices nuevos de dim_asset
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'dim_asset'
  AND indexname IN ('idx_dim_asset_symbol', 'idx_dim_asset_class', 'idx_dim_asset_active')
ORDER BY indexname;

-- 3. share_class poblada y distribución asset_class (después del seed)
SELECT asset_class, share_class, COUNT(*) AS filas
FROM dim_asset
WHERE is_active AND current_version
GROUP BY asset_class, share_class
ORDER BY asset_class, share_class;

-- 4. source_discovered_by (primer-gana)
SELECT source_discovered_by, COUNT(*) AS filas
FROM dim_asset
GROUP BY source_discovered_by ORDER BY source_discovered_by;

-- 5. sync_checkpoint.last_event_id debe ser bigint (V4 RAW)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'sync_checkpoint' AND column_name = 'last_event_id';

-- 6. fact_economic_event — event_id BIGINT y columna importance escala V4
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'fact_economic_event'
  AND column_name IN ('event_id', 'importance', 'actual_raw');

-- 7. Firma de upsert_market_series (debe incluir p_raw_payload y p_source_checksum)
SELECT pg_get_function_arguments(
    'upsert_market_series(character varying, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, jsonb, character varying)'::regprocedure
) AS args;

-- 8. BRIN en cada partición de fact_market_series (PostgreSQL 15 no lo propaga)
SELECT
    child.relname AS particion,
    idx.relname AS indice
FROM pg_inherits i
JOIN pg_class child  ON i.inhrelid = child.oid
JOIN pg_class parent ON i.inhparent = parent.oid
JOIN pg_namespace n  ON n.oid = parent.relnamespace
LEFT JOIN pg_index pi
    ON pi.indrelid = child.oid
LEFT JOIN pg_class idx
    ON idx.oid = pi.indexrelid
   AND idx.relname LIKE '%_ts_brin'
WHERE parent.relname = 'fact_market_series'
  AND n.nspname = 'public'
ORDER BY child.relname;

-- 9. Particiones de los hechos
SELECT
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_range
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child  ON pg_inherits.inhrelid = child.oid
JOIN pg_namespace n  ON n.oid = parent.relnamespace
WHERE parent.relname IN ('fact_heatmap_snapshot', 'fact_market_series')
  AND n.nspname = 'public'
ORDER BY parent.relname, child.relname;

-- 10. Vistas
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

-- =============================================================================
-- VERIFICACIONES DE DATOS (tras ejecutar el seed y un ciclo de scrapers)
-- =============================================================================

-- 1. Conteos generales
SELECT
    (SELECT COUNT(*) FROM dim_asset) AS total_activos,
    (SELECT COUNT(*) FROM fact_heatmap_snapshot) AS total_snapshots,
    (SELECT COUNT(*) FROM fact_market_series) AS total_series,
    (SELECT COUNT(*) FROM fact_economic_event) AS total_eventos,
    (SELECT COUNT(*) FROM dim_time) AS total_dias;

-- 2. vw_heatmap_enriched restringida a equity/etf (debe excluir radar V4)
SELECT asset_class, COUNT(*) AS filas
FROM vw_heatmap_enriched
GROUP BY asset_class;

-- 3. Vista de market live con asset_class/source_category
SELECT * FROM vw_market_live LIMIT 5;

-- 4. Verificar que los datos clave del heatmap están poblados
SELECT
    a.symbol,
    a.ticker,
    a.exchange,
    a.sector,
    a.asset_class,
    a.share_class,
    h.price_heatmap,
    h.daily_change_pct,
    h.market_cap,
    h.stream_status,
    jsonb_array_length(h.raw_vector) AS vector_len
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker IN ('NVDA', 'TSLA', 'AAPL', 'MU', 'SNDK')
ORDER BY a.ticker;

-- =============================================================================
-- Limpieza completa de tablas de datos
-- Conserva: estructura, índices, particiones, vistas y funciones
-- Elimina: todos los registros
-- =============================================================================

-- 1. Tablas de hechos (con CASCADE por las particiones y FKs)
TRUNCATE TABLE fact_heatmap_snapshot CASCADE;
TRUNCATE TABLE fact_market_series CASCADE;
TRUNCATE TABLE fact_economic_event CASCADE;

-- 2. Dimensión de activos
TRUNCATE TABLE dim_asset RESTART IDENTITY CASCADE;

-- 3. Dimensión de países (por si acaso hay datos)
TRUNCATE TABLE dim_country CASCADE;

-- 4. Dimensión de tiempo
TRUNCATE TABLE dim_time CASCADE;

-- 5. Auditoría y checkpoints
TRUNCATE TABLE audit_sync_run RESTART IDENTITY CASCADE;
TRUNCATE TABLE sync_checkpoint RESTART IDENTITY CASCADE;

-- =============================================================================
-- Verificación
-- =============================================================================
SELECT
    'dim_asset' AS tabla, COUNT(*) AS filas FROM dim_asset
UNION ALL SELECT 'dim_country', COUNT(*) FROM dim_country
UNION ALL SELECT 'dim_time', COUNT(*) FROM dim_time
UNION ALL SELECT 'fact_heatmap_snapshot', COUNT(*) FROM fact_heatmap_snapshot
UNION ALL SELECT 'fact_market_series', COUNT(*) FROM fact_market_series
UNION ALL SELECT 'fact_economic_event', COUNT(*) FROM fact_economic_event
UNION ALL SELECT 'audit_sync_run', COUNT(*) FROM audit_sync_run
UNION ALL SELECT 'sync_checkpoint', COUNT(*) FROM sync_checkpoint;