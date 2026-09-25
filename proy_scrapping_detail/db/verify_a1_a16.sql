-- Verificación A1-A16 · heatmap_stock · F0.1
-- Consultas del Anexo A (Informe v3). Ajustadas al esquema real.
-- Rango de datos verificado: fact_market_series 2026-03-17 → 2026-09-18.

-- A1 · Ticks fuera de sesión (H4, E-OPS-01)
SELECT date_trunc('hour', s.timestamp_utc AT TIME ZONE 'America/New_York') AS hora_et,
       count(*) AS ticks, count(DISTINCT s.close) AS closes_distintos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 04:00+00' AND s.timestamp_utc < '2026-09-18 04:00+00'
GROUP BY 1 ORDER BY 1;

-- A2 · Volumen acumulado (H3)
SELECT s.timestamp_utc AT TIME ZONE 'America/New_York' AS ts_et, s.volume,
       s.volume - lag(s.volume) OVER (ORDER BY s.timestamp_utc) AS delta
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 12:00+00' AND s.timestamp_utc < '2026-09-18 02:00+00'
ORDER BY s.timestamp_utc;

-- A3 · Escala de importancia (H5, E-BD-03)
SELECT importance, count(*) AS n,
       array_agg(DISTINCT title) FILTER (WHERE title ~* 'non.?farm|cpi|fed interest|gdp|core pce|unemployment') AS ejemplos
FROM fact_economic_event
WHERE country = 'US'
GROUP BY 1 ORDER BY 1;

-- A4 · captured_at nulo en eventos en vivo (H10, E-CAL-02)
SELECT date_trunc('day', first_seen_at) AS dia, count(*) AS eventos,
       count(*) FILTER (WHERE captured_at IS NULL) AS sin_captured_at
FROM fact_economic_event
GROUP BY 1 ORDER BY 1 DESC LIMIT 14;

-- A5 · Límites de partición (H11, E-BD-02). Ejecutar con TIME ZONE 'America/Lima' y 'UTC'.
SELECT i.inhparent::regclass AS tabla, c.relname AS particion,
       pg_get_expr(c.relpartbound, c.oid) AS limites
FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
ORDER BY 1, 2;

-- A6 · Duración del ciclo (H8)
WITH t AS (
  SELECT a.symbol, s.timestamp_utc
  FROM fact_market_series s JOIN dim_asset a USING (asset_id)
  WHERE a.symbol IN ('AMEX:SPY', 'TVC:VIX')
    AND s.timestamp_utc >= '2026-09-17 14:00+00' AND s.timestamp_utc < '2026-09-17 15:00+00')
SELECT p.timestamp_utc AS spy,
       min(v.timestamp_utc) - p.timestamp_utc AS desfase
FROM t p JOIN t v ON v.symbol = 'TVC:VIX' AND v.timestamp_utc >= p.timestamp_utc
WHERE p.symbol = 'AMEX:SPY'
GROUP BY p.timestamp_utc ORDER BY 1;

-- A7 · Huecos entre ticks (H8, H17)
WITH g AS (
  SELECT s.timestamp_utc - lag(s.timestamp_utc) OVER (ORDER BY s.timestamp_utc) AS gap
  FROM fact_market_series s JOIN dim_asset a USING (asset_id)
  WHERE a.symbol = 'AMEX:SPY'
    AND s.timestamp_utc >= '2026-09-14 13:00+00' AND s.timestamp_utc < '2026-09-18 21:00+00')
SELECT percentile_cont(ARRAY[0.5, 0.9, 0.99]) WITHIN GROUP (ORDER BY gap) AS p50_p90_p99,
       max(gap) AS gap_max,
       count(*) FILTER (WHERE gap > interval '4 minutes') AS huecos_mayores_4_min
FROM g;

-- A8 · Cierres redondos y nulos (H9)
SELECT a.symbol, count(*) AS n, count(DISTINCT s.close) AS distintos,
       count(*) FILTER (WHERE s.close = round(s.close)) AS enteros,
       count(*) FILTER (WHERE s.close IS NULL) AS nulos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol IN ('TVC:VIX', 'CBOE:VX1!', 'TVC:US10Y', 'TVC:US02Y')
  AND s.timestamp_utc >= now() - interval '7 days'
GROUP BY 1;

-- A9 · Sorpresas computables (Q8, H14)
SELECT importance, count(*) AS total,
       count(*) FILTER (WHERE actual_raw IS NOT NULL AND forecast_raw IS NOT NULL) AS con_sorpresa
FROM fact_economic_event
GROUP BY 1 ORDER BY 1;

-- A10 · UTC del histórico (H15, Q4)
SELECT date_trunc('hour', s.timestamp_utc AT TIME ZONE 'UTC') AS hora_utc,
       count(*) AS ticks, count(DISTINCT s.close) AS closes_distintos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 00:00+00' AND s.timestamp_utc < '2026-09-19 00:00+00'
GROUP BY 1 ORDER BY 1;

-- A11 · Nulos por símbolo (Q6, E-RAD-04)
SELECT a.symbol, count(*) AS n,
       round(100.0 * count(*) FILTER (WHERE s.close  IS NULL) / count(*), 2) AS pct_close_nulo,
       round(100.0 * count(*) FILTER (WHERE s.rsi    IS NULL) / count(*), 2) AS pct_rsi_nulo,
       round(100.0 * count(*) FILTER (WHERE s.volume IS NULL) / count(*), 2) AS pct_volumen_nulo
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE s.timestamp_utc >= now() - interval '7 days'
GROUP BY 1
HAVING count(*) FILTER (WHERE s.close IS NULL OR s.rsi IS NULL) > 0
ORDER BY pct_close_nulo DESC, pct_rsi_nulo DESC;

-- A12 · Composición del último snapshot (E-HM-01)
SELECT a.exchange, a.share_class, count(*) AS n
FROM fact_heatmap_snapshot h JOIN dim_asset a USING (asset_id)
WHERE h.timestamp_utc = (SELECT max(timestamp_utc) FROM fact_heatmap_snapshot)
GROUP BY 1, 2 ORDER BY n DESC;

-- A13 · Índices sin uso (E-BD-08)
SELECT relname AS tabla, indexrelname AS indice, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS tamano
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
LIMIT 30;

-- A14 · logo_id nulo por origen (E-HM-05)
SELECT source_discovered_by, count(*) AS n, count(*) FILTER (WHERE logo_id IS NULL) AS sin_logo
FROM dim_asset GROUP BY 1;

-- A15 · Auditoría por script y estado (E-RAD-05, E-OPS-03)
SELECT script_name, status, count(*) AS corridas, min(run_start) AS primera, max(run_start) AS ultima
FROM audit_sync_run GROUP BY 1, 2 ORDER BY 1, 2;

-- A16 · Índices de dim_asset (E-BD-04)
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'dim_asset' ORDER BY indexname;