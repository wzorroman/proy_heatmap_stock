-- Función wrapper INMUTABLE para text search en inglés
CREATE OR REPLACE FUNCTION text_to_tsvector_english(input_text TEXT)
RETURNS TSVECTOR AS $$
    SELECT to_tsvector('english', COALESCE(input_text, ''));
$$ LANGUAGE sql IMMUTABLE;

-- =============================================================================
-- 1. DIMENSIONES
-- =============================================================================

-- DIMENSIÓN DE ACTIVOS (Slowly Changing Dimension - Tipo 2)
CREATE TABLE IF NOT EXISTS dim_asset (
    asset_id         SERIAL PRIMARY KEY,
    symbol           VARCHAR(50) UNIQUE NOT NULL,   -- "NASDAQ:NVDA"  (constraint-1)
    ticker           TEXT,                          -- "NVDA"
    exchange         TEXT,                          -- "NASDAQ"
    asset_class      TEXT,                          -- "common", "etf"
    sector           TEXT,                          -- "Electronic Technology"
    sector_es        TEXT,                          -- "Tecnología electrónica"
    company_name     TEXT,
    logo_id          TEXT,                          -- puede ser muy largo (ej. Digital Realty Trust)
    
    -- Gestión de versiones (SCD Tipo 2)
    is_active        BOOLEAN DEFAULT TRUE,
    valid_from       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    valid_to         TIMESTAMPTZ DEFAULT 'infinity',
    current_version  BOOLEAN DEFAULT TRUE,
    
    -- Metadatos de control
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    
    -- Redundacia más débil y nunca se activará porque el constraint 1 lo bloquea primero.
    -- CONSTRAINT uk_asset_symbol_active UNIQUE (symbol, current_version)
);

-- Índice para búsqueda rápida de activos activos
CREATE INDEX IF NOT EXISTS idx_dim_asset_active ON dim_asset (is_active, current_version) 
WHERE is_active AND current_version;

-- Índice para joins por símbolo
CREATE INDEX IF NOT EXISTS idx_dim_asset_symbol ON dim_asset (symbol);


-- DIMENSIÓN DE PAÍSES (para calendario económico)
CREATE TABLE IF NOT EXISTS dim_country (
    country_code     VARCHAR(5) PRIMARY KEY,
    country_name     VARCHAR(100),
    region           VARCHAR(50),
    currency_code    VARCHAR(5)
);

-- DIMENSIÓN DE TIEMPO (opcional, para análisis temporal avanzado)
CREATE TABLE IF NOT EXISTS dim_time (
    date_id          INTEGER PRIMARY KEY,  -- YYYYMMDD
    full_date        DATE NOT NULL,
    year             SMALLINT NOT NULL,
    quarter          SMALLINT NOT NULL,
    month            SMALLINT NOT NULL,
    month_name       VARCHAR(20),
    day_of_month     SMALLINT NOT NULL,
    day_of_week      SMALLINT NOT NULL,    -- 1=Monday, 7=Sunday
    week_number      SMALLINT NOT NULL,
    is_weekend       BOOLEAN DEFAULT FALSE,
    is_holiday       BOOLEAN DEFAULT FALSE,
    trading_session  VARCHAR(20)           -- "US", "EU", "ASIA"
);


-- =============================================================================
-- 2. HECHOS: SERIES TEMPORALES (Indicadores Técnicos)
-- =============================================================================

-- TABLA DE HECHOS PRINCIPAL con particionamiento por rango (mensual)
-- Las particiones específicas se crearán con el script externo de mantenimiento.
CREATE TABLE IF NOT EXISTS fact_market_series (
    asset_id         INTEGER NOT NULL REFERENCES dim_asset(asset_id),
    timestamp_utc    TIMESTAMPTZ NOT NULL,
    
    -- Métricas clave (columnas tipadas para consultas rápidas)
    close            NUMERIC(18,6),
    volume           BIGINT,
    rsi              NUMERIC(10,4),
    cci20            NUMERIC(10,4),
    bbpower          NUMERIC(10,4),
    adx              NUMERIC(10,4),
    pivot_camarilla_r3 NUMERIC(18,6),
    perf_w           NUMERIC(10,4),
    change_pct       NUMERIC(10,4),
    
    -- Payload crudo (defensa contra cambios en API)
    raw_payload      JSONB,
    
    -- Metadatos de ingesta
    ingested_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source_checksum  VARCHAR(64),          -- Para detectar cambios en el payload
    
    PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

-- Índices globales (se heredan automáticamente a cada partición)
CREATE INDEX IF NOT EXISTS idx_fact_market_series_ts_desc ON fact_market_series (timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_fact_market_series_rsi ON fact_market_series (rsi) WHERE rsi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fact_market_series_close ON fact_market_series (close) WHERE close IS NOT NULL;
-- Índice por fecha (inmutable porque usamos UTC fijo)
CREATE INDEX IF NOT EXISTS idx_fact_market_series_date 
    ON fact_market_series ( CAST(timestamp_utc AT TIME ZONE 'UTC' AS date) );

    
-- =============================================================================
-- 3. HECHOS: SNAPSHOTS DEL HEATMAP
-- =============================================================================

-- Versión elástica: solo 4 columnas tipadas, el resto en JSONB
CREATE TABLE IF NOT EXISTS fact_heatmap_snapshot (
    asset_id         INTEGER NOT NULL REFERENCES dim_asset(asset_id),
    timestamp_utc    TIMESTAMPTZ NOT NULL,
    
    -- Métricas críticas extraídas (tipadas para joins y filtros)
    price            NUMERIC(18,6),
    daily_change_pct NUMERIC(12,6),
    market_cap       NUMERIC(18,0),        -- BIGINT no es suficiente para 5.5T
    stream_status    VARCHAR(30),
    
    -- Vectores completos (futuro-proofing)
    raw_vector       JSONB,                -- d[0..29] completo
    raw_metadata     JSONB,                -- logo, sector, etc.
    
    -- Metadatos de ingesta
    ingested_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source_checksum  VARCHAR(64),
    
    PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

-- Índices globales
CREATE INDEX IF NOT EXISTS idx_fact_heatmap_ts_desc ON fact_heatmap_snapshot (timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_fact_heatmap_mcap ON fact_heatmap_snapshot (market_cap DESC) 
    WHERE market_cap IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fact_heatmap_change ON fact_heatmap_snapshot (daily_change_pct) 
    WHERE daily_change_pct IS NOT NULL;

-- Índice GIN para búsquedas dentro de JSONB (si se necesita)
CREATE INDEX IF NOT EXISTS idx_fact_heatmap_raw_vector ON fact_heatmap_snapshot USING GIN (raw_vector);


-- =============================================================================
-- 4. HECHOS: CALENDARIO ECONÓMICO
-- =============================================================================

-- Todos los campos de la API guardados, con normalización diferida en vistas
CREATE TABLE IF NOT EXISTS fact_economic_event (
    event_id         VARCHAR(100) PRIMARY KEY,
    title            TEXT,
    country          VARCHAR(5) REFERENCES dim_country(country_code),
    importance       INTEGER,                     -- 1=Alta, 2=Media, 3=Baja
    category         VARCHAR(100),
    event_timestamp  TIMESTAMPTZ NOT NULL,
    
    -- Valores numéricos tipados (cuando existen)
    actual           NUMERIC(18,6),
    forecast         NUMERIC(18,6),
    previous         NUMERIC(18,6),
    actual_raw       TEXT,        -- Original tal cual vino (ej: "1.2M")
    forecast_raw     TEXT,
    previous_raw     TEXT,
    
    currency         VARCHAR(5),
    unit             VARCHAR(20),
    
    -- Payload completo (defensa contra cambios)
    raw_payload      JSONB NOT NULL,
    
    -- Metadatos de ingesta
    first_seen_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Checksum para detectar actualizaciones (cambio de forecast -> actual)
    payload_checksum VARCHAR(64)
);

-- Índices para consultas por fecha e importancia
CREATE INDEX IF NOT EXISTS idx_fact_economic_event_ts ON fact_economic_event (event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fact_economic_event_country ON fact_economic_event (country);
CREATE INDEX IF NOT EXISTS idx_fact_economic_event_importance ON fact_economic_event (importance) 
    WHERE importance <= 2;  -- Solo eventos relevantes

-- Índice para búsquedas en título
CREATE INDEX IF NOT EXISTS idx_fact_economic_event_title_gin 
    ON fact_economic_event USING GIN (text_to_tsvector_english(title));

-- =============================================================================
-- 5. AUDITORÍA Y CONTROL DE INGESTA
-- =============================================================================

-- Registro de ejecuciones de scripts (resiliencia operativa)
CREATE TABLE IF NOT EXISTS audit_sync_run (
    run_id           SERIAL PRIMARY KEY,
    script_name      VARCHAR(100) NOT NULL,
    run_start        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    run_end          TIMESTAMPTZ,
    
    -- Métricas de la ejecución
    records_fetched  INTEGER DEFAULT 0,
    records_upserted INTEGER DEFAULT 0,
    records_failed   INTEGER DEFAULT 0,
    
    -- Estado y errores
    status           VARCHAR(20) DEFAULT 'RUNNING',  -- 'RUNNING', 'SUCCESS', 'PARTIAL_FAIL', 'FAILED'
    error_message    TEXT,
    
    -- Contexto
    source_params    JSONB,      -- Parámetros usados (países, rango, etc.)
    execution_mode   VARCHAR(30) -- 'cron', 'manual', 'backfill'
);

CREATE INDEX IF NOT EXISTS idx_audit_sync_run_script ON audit_sync_run (script_name, run_start DESC);

-- Checkpoint para sincronizadores (reanudación de backfills)
CREATE TABLE IF NOT EXISTS sync_checkpoint (
    checkpoint_id    SERIAL PRIMARY KEY,
    script_name      VARCHAR(100) NOT NULL,
    last_timestamp   TIMESTAMPTZ NOT NULL,
    last_event_id    VARCHAR(100),   -- Para el calendario
    records_processed INTEGER DEFAULT 0,
    last_run_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status           VARCHAR(20) DEFAULT 'ACTIVE',
    UNIQUE (script_name)
);


-- =============================================================================
-- 6. VISTAS ANALÍTICAS (Normalización diferida - útiles para el futuro Dashboard)
-- =============================================================================

-- Vista para unir Series Temporales con activos activos
CREATE OR REPLACE VIEW vw_market_live AS
SELECT 
    a.symbol,
    a.ticker,
    a.exchange,
    a.sector,
    m.timestamp_utc,
    m.close,
    m.volume,
    m.rsi,
    m.cci20,
    m.bbpower,
    m.adx,
    m.change_pct,
    m.perf_w,
    CASE 
        WHEN m.rsi < 30 AND m.change_pct > 0 THEN 'OVERSOLD_REVERSAL'
        WHEN m.rsi > 70 AND m.change_pct < 0 THEN 'OVERBOUGHT_REVERSAL'
        WHEN m.rsi BETWEEN 40 AND 60 THEN 'NEUTRAL'
        ELSE 'TRENDING'
    END AS signal_status
FROM fact_market_series m
JOIN dim_asset a ON m.asset_id = a.asset_id
WHERE a.is_active = TRUE 
  AND a.current_version = TRUE
  AND m.timestamp_utc >= (NOW() - INTERVAL '7 days');

-- Vista para Heatmap enriquecido con métricas técnicas
CREATE OR REPLACE VIEW vw_heatmap_enriched AS
SELECT 
    a.symbol,
    a.ticker,
    a.sector,
    h.timestamp_utc,
    h.price,
    h.daily_change_pct,
    h.market_cap,
    CASE 
        WHEN h.daily_change_pct > 0 THEN 'BUY'
        WHEN h.daily_change_pct < 0 THEN 'SELL'
        ELSE 'NEUTRAL'
    END AS market_direction,
    ABS(h.daily_change_pct) AS color_intensity,
    (
        SELECT m.rsi 
        FROM fact_market_series m 
        WHERE m.asset_id = h.asset_id 
          AND m.timestamp_utc <= h.timestamp_utc 
        ORDER BY m.timestamp_utc DESC 
        LIMIT 1
    ) AS last_rsi
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON h.asset_id = a.asset_id
WHERE a.is_active = TRUE 
  AND a.current_version = TRUE;

-- Vista para cruce Heatmap + Calendario (impacto de eventos en movimientos)
CREATE OR REPLACE VIEW vw_heatmap_event_impact AS
SELECT 
    h.symbol,
    h.sector,
    h.price,
    h.daily_change_pct,
    h.timestamp_utc AS heatmap_time,
    e.title AS event_title,
    e.country,
    e.importance,
    e.event_timestamp,
    EXTRACT(EPOCH FROM (h.timestamp_utc - e.event_timestamp)) / 3600 AS hours_since_event
FROM vw_heatmap_enriched h
LEFT JOIN fact_economic_event e 
    ON e.country = (SELECT country_code FROM dim_country WHERE currency_code = 'USD')
    AND e.event_timestamp BETWEEN h.timestamp_utc - INTERVAL '6 hours' AND h.timestamp_utc
WHERE e.importance <= 2;


-- =============================================================================
-- 7. FUNCIONES DE INGESTA (Idempotencia + Resiliencia)
-- =============================================================================

-- Función para UPSERT de series temporales
CREATE OR REPLACE FUNCTION upsert_market_series(
    p_asset_symbol VARCHAR,
    p_timestamp_utc TIMESTAMPTZ,
    p_close NUMERIC,
    p_volume BIGINT,
    p_rsi NUMERIC,
    p_cci20 NUMERIC,
    p_bbpower NUMERIC,
    p_adx NUMERIC,
    p_pivot_camarilla_r3 NUMERIC,
    p_perf_w NUMERIC,
    p_change_pct NUMERIC,
    p_raw_payload JSONB
)
RETURNS VOID AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id 
    FROM dim_asset 
    WHERE symbol = p_asset_symbol AND current_version = TRUE;
    
    IF v_asset_id IS NULL THEN
        INSERT INTO dim_asset (symbol) 
        VALUES (p_asset_symbol)
        RETURNING asset_id INTO v_asset_id;
    END IF;
    
    INSERT INTO fact_market_series (
        asset_id, timestamp_utc, close, volume, rsi, cci20, bbpower, 
        adx, pivot_camarilla_r3, perf_w, change_pct, raw_payload
    ) VALUES (
        v_asset_id, p_timestamp_utc, p_close, p_volume, p_rsi, p_cci20, p_bbpower,
        p_adx, p_pivot_camarilla_r3, p_perf_w, p_change_pct, p_raw_payload
    )
    ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        rsi = EXCLUDED.rsi,
        cci20 = EXCLUDED.cci20,
        bbpower = EXCLUDED.bbpower,
        adx = EXCLUDED.adx,
        pivot_camarilla_r3 = EXCLUDED.pivot_camarilla_r3,
        perf_w = EXCLUDED.perf_w,
        change_pct = EXCLUDED.change_pct,
        raw_payload = EXCLUDED.raw_payload,
        ingested_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;


-- Función para UPSERT de Heatmap
CREATE OR REPLACE FUNCTION upsert_heatmap_snapshot(
    p_symbol VARCHAR,
    p_timestamp_utc TIMESTAMPTZ,
    p_price NUMERIC,
    p_daily_change_pct NUMERIC,
    p_market_cap NUMERIC,
    p_stream_status VARCHAR,
    p_raw_vector JSONB,
    p_raw_metadata JSONB
)
RETURNS VOID AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id 
    FROM dim_asset 
    WHERE symbol = p_symbol AND current_version = TRUE;
    
    IF v_asset_id IS NULL THEN
        INSERT INTO dim_asset (symbol) VALUES (p_symbol)
        RETURNING asset_id INTO v_asset_id;
    END IF;
    
    INSERT INTO fact_heatmap_snapshot (
        asset_id, timestamp_utc, price, daily_change_pct, 
        market_cap, stream_status, raw_vector, raw_metadata
    ) VALUES (
        v_asset_id, p_timestamp_utc, p_price, p_daily_change_pct,
        p_market_cap, p_stream_status, p_raw_vector, p_raw_metadata
    )
    ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
        price = EXCLUDED.price,
        daily_change_pct = EXCLUDED.daily_change_pct,
        market_cap = EXCLUDED.market_cap,
        stream_status = EXCLUDED.stream_status,
        raw_vector = EXCLUDED.raw_vector,
        raw_metadata = EXCLUDED.raw_metadata,
        ingested_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;
