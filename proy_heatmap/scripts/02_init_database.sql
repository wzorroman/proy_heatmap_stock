-- ============================================================================
-- Inicialización completa de heatmap_stock
-- Compatible con: heatmap scraper + radar V4 + calendario económico V4 RAW
-- Versión: 2026-09-11 (v1.0.2 del proyecto)
-- PostgreSQL 15+
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Extensiones y search_path
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- opcional, para búsquedas difusas futuras

SET search_path = public;

-- ============================================================================
-- 1. DIMENSIONES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.1 dim_asset — SCD Tipo 2, compartida por heatmap + radar V4
-- ----------------------------------------------------------------------------
CREATE TABLE dim_asset (
    asset_id              SERIAL          PRIMARY KEY,
    symbol                VARCHAR(50)     NOT NULL,
    ticker                TEXT            NOT NULL,
    exchange              TEXT            NOT NULL,
    asset_class           TEXT,
    share_class           VARCHAR(20),
    sector                TEXT,
    sector_es             TEXT,
    company_name          TEXT,
    logo_id               TEXT,
    source_discovered_by  VARCHAR(50),
    source_category       VARCHAR(50),
    is_active             BOOLEAN         NOT NULL DEFAULT TRUE,
    valid_from            TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to              TIMESTAMPTZ     NOT NULL DEFAULT 'infinity',
    current_version       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dim_asset_symbol_key UNIQUE (symbol)
);

COMMENT ON TABLE  dim_asset IS 'Activos financieros versionados (SCD Tipo 2). Compartida por heatmap y radar V4.';
COMMENT ON COLUMN dim_asset.symbol              IS 'Clave natural {EXCHANGE}:{TICKER}, ej. "NASDAQ:NVDA".';
COMMENT ON COLUMN dim_asset.asset_class         IS 'equity | etf | crypto | forex | future | yield | index | commodity';
COMMENT ON COLUMN dim_asset.share_class         IS 'Clase de acción del heatmap: common | preferred | unit (col. asset_class del CSV).';
COMMENT ON COLUMN dim_asset.source_discovered_by IS 'Scraper que dio de alta el símbolo: heatmap | radar_v4.';
COMMENT ON COLUMN dim_asset.source_category     IS 'Categoría del config.py del radar (ej. SEMICONDUCTORES).';

CREATE INDEX idx_dim_asset_active
    ON dim_asset (is_active, current_version)
    WHERE is_active AND current_version;

CREATE INDEX idx_dim_asset_symbol ON dim_asset (symbol);

CREATE INDEX idx_dim_asset_class
    ON dim_asset (asset_class)
    WHERE is_active AND current_version;

-- ----------------------------------------------------------------------------
-- 1.2 dim_country — catálogo para calendario económico
-- ----------------------------------------------------------------------------
CREATE TABLE dim_country (
    country_code   VARCHAR(5)   PRIMARY KEY,
    country_name   VARCHAR(100),
    region         VARCHAR(50),
    currency_code  VARCHAR(5)
);

COMMENT ON TABLE dim_country IS 'Catálogo de países del calendario económico.';

-- ----------------------------------------------------------------------------
-- 1.3 dim_time — calendario generado (uso futuro)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_time (
    date_id         INTEGER      PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE         NOT NULL,
    year            SMALLINT     NOT NULL,
    quarter         SMALLINT     NOT NULL,
    month           SMALLINT     NOT NULL,
    month_name      VARCHAR(20),
    day_of_month    SMALLINT     NOT NULL,
    day_of_week     SMALLINT     NOT NULL,      -- 1=Lunes … 7=Domingo
    week_number     SMALLINT     NOT NULL,
    is_weekend      BOOLEAN      NOT NULL,
    is_holiday      BOOLEAN      NOT NULL DEFAULT FALSE,
    trading_session VARCHAR(20)
);

COMMENT ON TABLE dim_time IS 'Dimensión temporal para análisis avanzado (calendario).';

-- ============================================================================
-- 2. HECHOS PARTICIONADOS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 fact_heatmap_snapshot — particionada mensual por timestamp_utc
--     Poblada por: scrapper_heatmap_v0.py / v1.py
-- ----------------------------------------------------------------------------
CREATE TABLE fact_heatmap_snapshot (
    asset_id          INTEGER       NOT NULL,
    timestamp_utc     TIMESTAMPTZ   NOT NULL,
    price_heatmap     NUMERIC(18,6),
    daily_change_pct  NUMERIC(12,6),
    market_cap        NUMERIC(18,0),
    stream_status     VARCHAR(30),
    raw_vector        JSONB,
    raw_metadata      JSONB,
    ingested_at       TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_checksum   VARCHAR(64),
    PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

COMMENT ON TABLE  fact_heatmap_snapshot IS 'Snapshots del heatmap TradingView. Particionada mensual.';
COMMENT ON COLUMN fact_heatmap_snapshot.price_heatmap IS 'Precio de cierre del activo (renombrado de "price" por coexistencia con radar).';

CREATE INDEX idx_fact_heatmap_ts_desc
    ON fact_heatmap_snapshot (timestamp_utc DESC);

CREATE INDEX idx_fact_heatmap_mcap
    ON fact_heatmap_snapshot (market_cap DESC)
    WHERE market_cap IS NOT NULL;

CREATE INDEX idx_fact_heatmap_change
    ON fact_heatmap_snapshot (daily_change_pct)
    WHERE daily_change_pct IS NOT NULL;

CREATE INDEX idx_fact_heatmap_raw_vector
    ON fact_heatmap_snapshot USING GIN (raw_vector);

-- ----------------------------------------------------------------------------
-- 2.2 fact_market_series — particionada mensual por timestamp_utc
--     Poblada por: scraper_live_tradingview_v4.py (radar)
--     Tipos alineados con la salida real del endpoint (volume fraccional, etc.)
-- ----------------------------------------------------------------------------
CREATE TABLE fact_market_series (
    asset_id            INTEGER       NOT NULL,
    timestamp_utc       TIMESTAMPTZ   NOT NULL,
    close               NUMERIC(20,8),
    volume              NUMERIC(20,8),
    rsi                 NUMERIC(10,4),
    cci20               NUMERIC(10,4),
    bbpower             NUMERIC(10,4),
    adx                 NUMERIC(10,4),
    pivot_camarilla_r3  NUMERIC(18,6),
    perf_w              NUMERIC(12,8),
    change_pct          NUMERIC(12,8),
    raw_payload         JSONB,
    ingested_at         TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_checksum     VARCHAR(64),
    PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

COMMENT ON TABLE  fact_market_series IS 'Series técnicas del radar V4. Particionada mensual.';
COMMENT ON COLUMN fact_market_series.volume     IS 'NUMERIC(20,8): cripto llega fraccional; acciones/futuros enteros caben igual.';
COMMENT ON COLUMN fact_market_series.raw_payload IS 'JSON crudo del endpoint. NULL si el ETL no lo captura.';
COMMENT ON COLUMN fact_market_series.source_checksum IS 'SHA-256 hex del row canónico.';

CREATE INDEX idx_fact_market_series_ts_desc
    ON fact_market_series (timestamp_utc DESC);

CREATE INDEX idx_fact_market_series_rsi
    ON fact_market_series (rsi)
    WHERE rsi IS NOT NULL;

CREATE INDEX idx_fact_market_series_close
    ON fact_market_series (close)
    WHERE close IS NOT NULL;

CREATE INDEX idx_fact_market_series_date
    ON fact_market_series (CAST(timestamp_utc AT TIME ZONE 'UTC' AS date));

-- ============================================================================
-- 3. HECHO NO PARTICIONADO — calendario económico V4 RAW
-- ============================================================================

CREATE TABLE fact_economic_event (
    -- Identidad
    event_id          BIGINT       PRIMARY KEY,           -- id int64 de TradingView
    title             TEXT,
    country           VARCHAR(5)   REFERENCES dim_country(country_code),
    indicator         TEXT,
    event_ticker      VARCHAR(50),                        -- ej. ECONOMICS:JPFER
    comment           TEXT,
    category          VARCHAR(100),                       -- código (lbr, prce, mny, …)
    period            VARCHAR(20),                        -- ej. Aug
    reference_date    TIMESTAMPTZ,
    source            TEXT,
    source_url        TEXT,

    -- Valores publicados
    actual            NUMERIC(18,6),
    previous          NUMERIC(18,6),
    forecast          NUMERIC(18,6),
    actual_raw        NUMERIC(30,8),                      -- unidad base (float64 del API)
    previous_raw      NUMERIC(30,8),
    forecast_raw      NUMERIC(30,8),
    actual_display    TEXT,                               -- "$1.2B" — formateado en ETL
    previous_display  TEXT,
    forecast_display  TEXT,

    -- Metadatos de impacto
    currency          VARCHAR(5),
    unit              VARCHAR(20),
    importance        SMALLINT,                           -- -1 … 3 (escala V4)

    -- Tiempos
    event_timestamp   TIMESTAMPTZ  NOT NULL,
    captured_at       TIMESTAMPTZ,
    first_seen_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Trazabilidad
    raw_payload       JSONB        NOT NULL,              -- reconstruido por ETL
    payload_checksum  VARCHAR(64)
);

COMMENT ON TABLE  fact_economic_event IS 'Calendario económico V4 RAW. Ingesta sin filtro de importancia.';
COMMENT ON COLUMN fact_economic_event.event_id   IS 'id int64 de economic-calendar.tradingview.com. Clave estable.';
COMMENT ON COLUMN fact_economic_event.importance IS 'V4 RAW: -1=sin dato, 0=baja, 1=media, 2=alta, 3=muy alta. Filtro "relevante" → importance BETWEEN 1 AND 3.';
COMMENT ON COLUMN fact_economic_event.actual_raw IS 'Valor en unidad base (ej. 1207500000000.0).';
COMMENT ON COLUMN fact_economic_event.captured_at IS 'timestamp_captura del scraper (ingesta puntual).';

CREATE INDEX idx_fact_economic_event_ts
    ON fact_economic_event (event_timestamp DESC);

CREATE INDEX idx_fact_economic_event_country
    ON fact_economic_event (country);

CREATE INDEX idx_fact_economic_event_country_ts
    ON fact_economic_event (country, event_timestamp DESC);

CREATE INDEX idx_fact_economic_event_importance
    ON fact_economic_event (importance)
    WHERE importance BETWEEN 1 AND 3;

CREATE INDEX idx_fact_economic_event_ticker
    ON fact_economic_event (event_ticker)
    WHERE event_ticker IS NOT NULL;

CREATE INDEX idx_fact_economic_event_captured
    ON fact_economic_event (captured_at DESC);

-- ============================================================================
-- 4. AUDITORÍA Y CONTROL
-- ============================================================================

CREATE TABLE audit_sync_run (
    run_id            SERIAL        PRIMARY KEY,
    script_name       VARCHAR(100)  NOT NULL,
    run_start         TIMESTAMPTZ   NOT NULL,
    run_end           TIMESTAMPTZ,
    records_fetched   INTEGER       NOT NULL DEFAULT 0,
    records_upserted  INTEGER       NOT NULL DEFAULT 0,
    records_failed    INTEGER       NOT NULL DEFAULT 0,
    status            VARCHAR(20)   NOT NULL,           -- RUNNING | SUCCESS | PARTIAL_FAIL | FAILED
    error_message     TEXT,
    source_params     JSONB,
    execution_mode    VARCHAR(30)                        -- cron | manual | backfill
);

CREATE INDEX idx_audit_sync_run_script
    ON audit_sync_run (script_name, run_start DESC);

COMMENT ON TABLE audit_sync_run IS 'Histórico de ejecuciones de los scrapers (heatmap, radar, calendario).';

CREATE TABLE sync_checkpoint (
    checkpoint_id      SERIAL        PRIMARY KEY,
    script_name        VARCHAR(100)  NOT NULL UNIQUE,
    last_timestamp     TIMESTAMPTZ   NOT NULL,
    last_event_id      BIGINT,
    records_processed  INTEGER       NOT NULL DEFAULT 0,
    last_run_at        TIMESTAMPTZ   NOT NULL,
    status             VARCHAR(20)   NOT NULL           -- ACTIVE | PAUSED | COMPLETED
);

COMMENT ON TABLE sync_checkpoint IS 'Checkpoints de reanudación. Una fila por scraper.';

-- ============================================================================
-- 5. FUNCIONES PL/pgSQL
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5.1 Wrapper inmutable para índice GIN de búsqueda en inglés
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION text_to_tsvector_english(input_text TEXT)
RETURNS tsvector
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT to_tsvector('english', COALESCE(input_text, ''));
$$;

CREATE INDEX idx_fact_economic_event_title_gin
    ON fact_economic_event USING GIN (text_to_tsvector_english(title));

-- ----------------------------------------------------------------------------
-- 5.2 UPSERT del heatmap (snapshot puntual por símbolo)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION upsert_heatmap_snapshot(
    p_symbol           VARCHAR,
    p_timestamp_utc    TIMESTAMPTZ,
    p_price_heatmap    NUMERIC,
    p_daily_change_pct NUMERIC,
    p_market_cap       NUMERIC,
    p_stream_status    VARCHAR,
    p_raw_vector       JSONB,
    p_raw_metadata     JSONB
) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id
    FROM dim_asset
    WHERE symbol = p_symbol AND is_active AND current_version
    LIMIT 1;

    IF v_asset_id IS NULL THEN
        INSERT INTO dim_asset (symbol, ticker, exchange, source_discovered_by)
        VALUES (
            p_symbol,
            split_part(p_symbol, ':', 2),
            split_part(p_symbol, ':', 1),
            'heatmap'
        )
        RETURNING asset_id INTO v_asset_id;
    END IF;

    INSERT INTO fact_heatmap_snapshot (
        asset_id, timestamp_utc, price_heatmap, daily_change_pct,
        market_cap, stream_status, raw_vector, raw_metadata
    ) VALUES (
        v_asset_id, p_timestamp_utc, p_price_heatmap, p_daily_change_pct,
        p_market_cap, p_stream_status, p_raw_vector, p_raw_metadata
    )
    ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
        price_heatmap    = EXCLUDED.price_heatmap,
        daily_change_pct = EXCLUDED.daily_change_pct,
        market_cap       = EXCLUDED.market_cap,
        stream_status    = EXCLUDED.stream_status,
        raw_vector       = EXCLUDED.raw_vector,
        raw_metadata     = EXCLUDED.raw_metadata,
        ingested_at      = CURRENT_TIMESTAMP;
END;
$$;

-- ----------------------------------------------------------------------------
-- 5.3 UPSERT de series técnicas (radar V4)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION upsert_market_series(
    p_asset_symbol       VARCHAR,
    p_timestamp_utc      TIMESTAMPTZ,
    p_close              NUMERIC,
    p_volume             NUMERIC,
    p_rsi                NUMERIC,
    p_cci20              NUMERIC,
    p_bbpower            NUMERIC,
    p_adx                NUMERIC,
    p_pivot_camarilla_r3 NUMERIC,
    p_perf_w             NUMERIC,
    p_change_pct         NUMERIC,
    p_raw_payload        JSONB   DEFAULT NULL,
    p_source_checksum    VARCHAR DEFAULT NULL
) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id
    FROM dim_asset
    WHERE symbol = p_asset_symbol AND is_active AND current_version
    LIMIT 1;

    IF v_asset_id IS NULL THEN
        RAISE EXCEPTION 'Activo no registrado en dim_asset: %', p_asset_symbol;
    END IF;

    INSERT INTO fact_market_series (
        asset_id, timestamp_utc, close, volume,
        rsi, cci20, bbpower, adx,
        pivot_camarilla_r3, perf_w, change_pct,
        raw_payload, source_checksum
    ) VALUES (
        v_asset_id, p_timestamp_utc, p_close, p_volume,
        p_rsi, p_cci20, p_bbpower, p_adx,
        p_pivot_camarilla_r3, p_perf_w, p_change_pct,
        p_raw_payload, p_source_checksum
    )
    ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
        close              = EXCLUDED.close,
        volume             = EXCLUDED.volume,
        rsi                = EXCLUDED.rsi,
        cci20              = EXCLUDED.cci20,
        bbpower            = EXCLUDED.bbpower,
        adx                = EXCLUDED.adx,
        pivot_camarilla_r3 = EXCLUDED.pivot_camarilla_r3,
        perf_w             = EXCLUDED.perf_w,
        change_pct         = EXCLUDED.change_pct,
        raw_payload        = COALESCE(EXCLUDED.raw_payload, fact_market_series.raw_payload),
        source_checksum    = COALESCE(EXCLUDED.source_checksum, fact_market_series.source_checksum),
        ingested_at        = CURRENT_TIMESTAMP;
END;
$$;

-- ============================================================================
-- 6. VISTAS ANALÍTICAS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6.1 vw_market_live — series técnicas del radar V4, últimos 7 días
-- ----------------------------------------------------------------------------
CREATE VIEW vw_market_live AS
SELECT
    a.symbol,
    a.ticker,
    a.asset_class,
    a.source_category,
    ms.timestamp_utc,
    ms.close,
    ms.volume,
    ms.rsi,
    ms.cci20,
    ms.bbpower,
    ms.adx,
    ms.pivot_camarilla_r3,
    ms.perf_w,
    ms.change_pct,
    CASE
        WHEN ms.rsi < 30 AND ms.change_pct > 0 THEN 'OVERSOLD_REVERSAL'
        WHEN ms.rsi > 70 AND ms.change_pct < 0 THEN 'OVERBOUGHT_REVERSAL'
        WHEN ms.adx > 25 THEN 'TRENDING'
        ELSE 'NEUTRAL'
    END AS signal_status
FROM fact_market_series ms
JOIN dim_asset a ON a.asset_id = ms.asset_id
WHERE ms.timestamp_utc >= NOW() - INTERVAL '7 days'
  AND a.is_active = TRUE
  AND a.current_version = TRUE;

COMMENT ON VIEW vw_market_live IS 'Series técnicas del radar V4 en ventana de 7 días con señal derivada.';

-- ----------------------------------------------------------------------------
-- 6.2 vw_heatmap_enriched — heatmap restringido a equity/etf
-- ----------------------------------------------------------------------------
CREATE VIEW vw_heatmap_enriched AS
SELECT
    h.asset_id,
    a.symbol,
    a.ticker,
    a.company_name,
    a.sector,
    h.timestamp_utc,
    h.price_heatmap,
    h.daily_change_pct,
    h.market_cap,
    CASE
        WHEN h.daily_change_pct > 0 THEN 'BUY'
        WHEN h.daily_change_pct < 0 THEN 'SELL'
        ELSE 'NEUTRAL'
    END AS market_direction,
    ABS(h.daily_change_pct) AS color_intensity,
    (
        SELECT ms.rsi
        FROM fact_market_series ms
        WHERE ms.asset_id = h.asset_id
          AND ms.timestamp_utc <= h.timestamp_utc
          AND ms.rsi IS NOT NULL
        ORDER BY ms.timestamp_utc DESC
        LIMIT 1
    ) AS last_rsi
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.asset_class IN ('equity', 'etf')
  AND a.is_active = TRUE
  AND a.current_version = TRUE;

COMMENT ON VIEW vw_heatmap_enriched IS 'Heatmap enriquecido. Restringido a equity/etf para excluir activos del radar V4.';

-- ----------------------------------------------------------------------------
-- 6.3 vw_heatmap_event_impact — heatmap × eventos USD importantes
-- ----------------------------------------------------------------------------
CREATE VIEW vw_heatmap_event_impact AS
SELECT
    h.*,
    e.event_id,
    e.title,
    e.country,
    e.importance,
    e.category,
    e.event_timestamp,
    e.actual,
    e.forecast,
    e.previous,
    e.currency,
    e.unit,
    EXTRACT(EPOCH FROM (h.timestamp_utc - e.event_timestamp)) / 3600.0
        AS hours_since_event
FROM vw_heatmap_enriched h
JOIN fact_economic_event e
    ON e.currency = 'USD'
   AND e.importance BETWEEN 1 AND 3
   AND e.event_timestamp BETWEEN h.timestamp_utc - INTERVAL '6 hours'
                             AND h.timestamp_utc + INTERVAL '6 hours';

COMMENT ON VIEW vw_heatmap_event_impact IS 'Cruce heatmap × eventos USD de importancia media+ en ventana ±6 h.';

-- ============================================================================
-- 7. PARTICIONES INICIALES
-- ============================================================================

-- Septiembre, octubre, noviembre y diciembre de 2026.
-- El scraper V4 crea automáticamente la del mes en curso;
-- create_partitions.py mantiene 3 meses de adelanto.

CREATE TABLE fact_heatmap_snapshot_2026_09
    PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

CREATE TABLE fact_heatmap_snapshot_2026_10
    PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

CREATE TABLE fact_heatmap_snapshot_2026_11
    PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

CREATE TABLE fact_heatmap_snapshot_2026_12
    PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE TABLE fact_market_series_2026_09
    PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

CREATE TABLE fact_market_series_2026_10
    PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

CREATE TABLE fact_market_series_2026_11
    PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

CREATE TABLE fact_market_series_2026_12
    PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- ----------------------------------------------------------------------------
-- 7.1 BRIN por partición de fact_market_series (PostgreSQL 15 no propaga
--     el índice BRIN desde el padre a las particiones hijas)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT child.relname AS partition_name
        FROM pg_inherits i
        JOIN pg_class child  ON i.inhrelid = child.oid
        JOIN pg_class parent ON i.inhparent = parent.oid
        JOIN pg_namespace n  ON n.oid = parent.relnamespace
        WHERE parent.relname = 'fact_market_series'
          AND n.nspname = 'public'
    LOOP
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON %I USING BRIN (timestamp_utc)',
            r.partition_name || '_ts_brin', r.partition_name
        );
    END LOOP;
END
$$;

-- ============================================================================
-- 8. SEED — dim_country (11 países del config.py del radar)
-- ============================================================================

INSERT INTO dim_country (country_code, country_name, region, currency_code) VALUES
    ('US','United States','Americas','USD'),
    ('CA','Canada','Americas','CAD'),
    ('GB','United Kingdom','Europe','GBP'),
    ('DE','Germany','Europe','EUR'),
    ('FR','France','Europe','EUR'),
    ('IT','Italy','Europe','EUR'),
    ('ES','Spain','Europe','EUR'),
    ('CH','Switzerland','Europe','CHF'),
    ('CN','China','Asia','CNY'),
    ('JP','Japan','Asia','JPY'),
    ('AU','Australia','Oceania','AUD');

-- ============================================================================
-- FIN — heatmap_stock inicializada
-- ============================================================================