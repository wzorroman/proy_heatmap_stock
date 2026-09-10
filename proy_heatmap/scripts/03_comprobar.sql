SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'fact_market_series' 
  AND indexname = 'idx_fact_market_series_date';

-- La salida deberia ser
-- indexname                   | indexdef
-- ----------------------------+---------------------------------------------------------------
-- idx_fact_market_series_date | CREATE INDEX idx_fact_market_series_date 
--                             | ON ONLY public.fact_market_series 
--                             | USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date))



SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'fact_%' OR tablename LIKE 'dim_%';

-- tablename |
-- dim_asset
-- dim_country
-- dim_time
-- fact_market_series
-- fact_heatmap_snapshot
-- fact_economic_event

-- ---- VERIFICACIONES ----
-- 1. Conteos generales
SELECT 
    (SELECT COUNT(*) FROM dim_asset) AS total_activos,
    (SELECT COUNT(*) FROM fact_heatmap_snapshot) AS total_snapshots,
    (SELECT COUNT(DISTINCT asset_id) FROM fact_heatmap_snapshot) AS activos_con_datos;

-- 2. Verificar que los datos clave están poblados
SELECT 
    a.symbol,
    a.ticker,
    a.exchange,
    a.sector,
    h.price,
    h.daily_change_pct,
    h.market_cap,
    h.stream_status,
    jsonb_array_length(h.raw_vector) AS vector_len
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker IN ('NVDA', 'TSLA', 'AAPL', 'MU', 'SNDK')
ORDER BY a.ticker;

--3. Verificar los símbolos con logo_id largo 
SELECT symbol, ticker, company_name, logo_id
FROM dim_asset
WHERE LENGTH(logo_id) > 50
ORDER BY LENGTH(logo_id) DESC
LIMIT 5;

-- 4. Verificar que se guardó el vector completo en raw_vector
SELECT 
    a.ticker,
    h.raw_vector->0 AS field_0_asset_class,
    h.raw_vector->3 AS field_3_daily_change,
    h.raw_vector->25 AS field_25_price,
    h.raw_vector->29 AS field_29_stream_status,
    jsonb_array_length(h.raw_vector) AS total_elementos
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker = 'NVDA';

-- 5. Verificar el raw_metadata
SELECT 
    a.ticker,
    h.raw_metadata->>'company_name' AS company,
    h.raw_metadata->>'sector' AS sector,
    h.raw_metadata->>'ticker' AS ticker_in_meta,
    h.raw_metadata->'logo'->>'logoid' AS logo_id
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker = 'NVDA';


-- 1. Total de hechos (debería ser 19812)
SELECT COUNT(*) FROM fact_heatmap_snapshot;

-- 2. ¿Cuántos precios no son nulos?
SELECT COUNT(price) AS precios_validos FROM fact_heatmap_snapshot;

-- 3. ¿Cuántos raw_vector no son nulos?
SELECT COUNT(raw_vector) AS vectores_validos FROM fact_heatmap_snapshot;

-- 4. ¿La longitud del vector guardado?
SELECT 
    a.ticker,
    jsonb_array_length(h.raw_vector) AS longitud_vector
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker = 'NVDA';
-- Debería dar 30

-- 5. Métricas ya extraídas
SELECT 
    a.ticker,
    h.price,
    h.daily_change_pct,
    h.market_cap,
    h.stream_status,
    h.raw_metadata->>'sector' AS sector,
    h.raw_metadata->>'company_name' AS company
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.ticker IN ('NVDA', 'TSLA', 'MU');


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
