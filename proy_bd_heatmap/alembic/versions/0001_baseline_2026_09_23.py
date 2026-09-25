"""baseline - esquema heatmap_stock (estado 2026-09-23)

Revision ID: 0001
Revises:
Create Date: 2026-09-23 14:56 UTC

Baseline generado desde pg_dump --schema-only de la BD viva
(10 tablas base + 27 particiones + 3 vistas + 2 funciones + pg_trgm).
Contiene SOLO esquema (sin datos). El seed de catálogos va en revisiones
posteriores.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_DDL = r"""
--
--



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET search_path = public;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: text_to_tsvector_english(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.text_to_tsvector_english(input_text text) RETURNS tsvector
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
    SELECT to_tsvector('english', COALESCE(input_text, ''));
$$;


--
-- Name: upsert_heatmap_snapshot(character varying, timestamp with time zone, numeric, numeric, numeric, character varying, jsonb, jsonb); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.upsert_heatmap_snapshot(p_symbol character varying, p_timestamp_utc timestamp with time zone, p_price_heatmap numeric, p_daily_change_pct numeric, p_market_cap numeric, p_stream_status character varying, p_raw_vector jsonb, p_raw_metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: upsert_market_series(character varying, timestamp with time zone, numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, jsonb, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.upsert_market_series(p_asset_symbol character varying, p_timestamp_utc timestamp with time zone, p_close numeric, p_volume numeric, p_rsi numeric, p_cci20 numeric, p_bbpower numeric, p_adx numeric, p_pivot_camarilla_r3 numeric, p_perf_w numeric, p_change_pct numeric, p_raw_payload jsonb DEFAULT NULL::jsonb, p_source_checksum character varying DEFAULT NULL::character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_sync_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_sync_run (
    run_id integer NOT NULL,
    script_name character varying(100) NOT NULL,
    run_start timestamp with time zone NOT NULL,
    run_end timestamp with time zone,
    records_fetched integer DEFAULT 0 NOT NULL,
    records_upserted integer DEFAULT 0 NOT NULL,
    records_failed integer DEFAULT 0 NOT NULL,
    status character varying(20) NOT NULL,
    error_message text,
    source_params jsonb,
    execution_mode character varying(30)
);


--
-- Name: TABLE audit_sync_run; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_sync_run IS 'Histórico de ejecuciones de los scrapers (heatmap, radar, calendario).';


--
-- Name: audit_sync_run_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_sync_run_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_sync_run_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_sync_run_run_id_seq OWNED BY public.audit_sync_run.run_id;


--
-- Name: dim_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_asset (
    asset_id integer NOT NULL,
    symbol character varying(50) NOT NULL,
    ticker text NOT NULL,
    exchange text NOT NULL,
    asset_class text,
    share_class character varying(20),
    sector text,
    sector_es text,
    company_name text,
    logo_id text,
    source_discovered_by character varying(50),
    source_category character varying(50),
    is_active boolean DEFAULT true NOT NULL,
    valid_from timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_to timestamp with time zone DEFAULT 'infinity'::timestamp with time zone NOT NULL,
    current_version boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    slug text,
    url_logo text
);


--
-- Name: TABLE dim_asset; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.dim_asset IS 'Activos financieros versionados (SCD Tipo 2). Compartida por heatmap y radar V4.';


--
-- Name: COLUMN dim_asset.symbol; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_asset.symbol IS 'Clave natural {EXCHANGE}:{TICKER}, ej. "NASDAQ:NVDA".';


--
-- Name: COLUMN dim_asset.asset_class; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_asset.asset_class IS 'equity | etf | crypto | forex | future | yield | index | commodity';


--
-- Name: COLUMN dim_asset.share_class; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_asset.share_class IS 'Clase de acción del heatmap: common | preferred | unit (col. asset_class del CSV).';


--
-- Name: COLUMN dim_asset.source_discovered_by; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_asset.source_discovered_by IS 'Scraper que dio de alta el símbolo: heatmap | radar_v4.';


--
-- Name: COLUMN dim_asset.source_category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_asset.source_category IS 'Categoría del config.py del radar (ej. SEMICONDUCTORES).';


--
-- Name: dim_asset_asset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dim_asset_asset_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dim_asset_asset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dim_asset_asset_id_seq OWNED BY public.dim_asset.asset_id;


--
-- Name: dim_country; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_country (
    country_code character varying(5) NOT NULL,
    country_name character varying(100),
    region character varying(50),
    currency_code character varying(5)
);


--
-- Name: TABLE dim_country; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.dim_country IS 'Catálogo de países del calendario económico.';


--
-- Name: dim_time; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_time (
    date_id integer NOT NULL,
    full_date date NOT NULL,
    year smallint NOT NULL,
    quarter smallint NOT NULL,
    month smallint NOT NULL,
    month_name character varying(20),
    day_of_month smallint NOT NULL,
    day_of_week smallint NOT NULL,
    week_number smallint NOT NULL,
    is_weekend boolean NOT NULL,
    is_holiday boolean DEFAULT false NOT NULL,
    trading_session character varying(20)
);


--
-- Name: TABLE dim_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.dim_time IS 'Dimensión temporal para análisis avanzado (calendario).';


--
-- Name: dim_trading_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_trading_session (
    session_date date NOT NULL,
    is_session boolean DEFAULT false NOT NULL,
    is_early_close boolean DEFAULT false NOT NULL,
    opens_at timestamp with time zone,
    closes_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE dim_trading_session; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.dim_trading_session IS 'Sesiones de trading XNYS (exchange_calendars), fuente del gate F2.2 (E-BD-01, E-BD-06, E-OPS-01).';


--
-- Name: COLUMN dim_trading_session.session_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_trading_session.session_date IS 'Fecha de sesión (ET, sin tz).';


--
-- Name: COLUMN dim_trading_session.is_session; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_trading_session.is_session IS 'True si la Bolsa de NY está abierta ese día (lun-vie sin feriados).';


--
-- Name: COLUMN dim_trading_session.is_early_close; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_trading_session.is_early_close IS 'True si cierra antes de las 16:00 ET (post-Navidad, día antes de feriados).';


--
-- Name: COLUMN dim_trading_session.opens_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_trading_session.opens_at IS 'Horario de apertura en UTC.';


--
-- Name: COLUMN dim_trading_session.closes_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dim_trading_session.closes_at IS 'Horario de cierre en UTC (respeta cierres anticipados).';


--
-- Name: fact_economic_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_economic_event (
    event_id bigint NOT NULL,
    title text,
    country character varying(5),
    indicator text,
    event_ticker character varying(50),
    comment text,
    category character varying(100),
    period character varying(20),
    reference_date timestamp with time zone,
    source text,
    source_url text,
    actual numeric(18,6),
    previous numeric(18,6),
    forecast numeric(18,6),
    actual_raw numeric(30,8),
    previous_raw numeric(30,8),
    forecast_raw numeric(30,8),
    actual_display text,
    previous_display text,
    forecast_display text,
    currency character varying(5),
    unit character varying(20),
    importance smallint,
    event_timestamp timestamp with time zone NOT NULL,
    captured_at timestamp with time zone,
    first_seen_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    raw_payload jsonb,
    payload_checksum character varying(64)
);


--
-- Name: TABLE fact_economic_event; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.fact_economic_event IS 'Calendario económico V4 RAW. Ingesta sin filtro de importancia.';


--
-- Name: COLUMN fact_economic_event.event_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_economic_event.event_id IS 'id int64 de economic-calendar.tradingview.com. Clave estable.';


--
-- Name: COLUMN fact_economic_event.actual_raw; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_economic_event.actual_raw IS 'Valor en unidad base (ej. 1207500000000.0).';


--
-- Name: COLUMN fact_economic_event.importance; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_economic_event.importance IS 'V4 RAW: -1=sin dato, 0=baja, 1=media, 2=alta, 3=muy alta. Filtro "relevante" → importance BETWEEN 1 AND 3.';


--
-- Name: COLUMN fact_economic_event.captured_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_economic_event.captured_at IS 'timestamp_captura del scraper (ingesta puntual).';


--
-- Name: fact_heatmap_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_heatmap_snapshot (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    price_heatmap numeric(18,6),
    daily_change_pct numeric(12,6),
    market_cap numeric(18,0),
    stream_status character varying(30),
    raw_vector jsonb,
    raw_metadata jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64)
)
PARTITION BY RANGE (timestamp_utc);


--
-- Name: TABLE fact_heatmap_snapshot; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.fact_heatmap_snapshot IS 'Snapshots del heatmap TradingView. Particionada mensual.';


--
-- Name: COLUMN fact_heatmap_snapshot.price_heatmap; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_heatmap_snapshot.price_heatmap IS 'Precio de cierre del activo (renombrado de "price" por coexistencia con radar).';


--
-- Name: fact_heatmap_snapshot_2026_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_heatmap_snapshot_2026_09 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    price_heatmap numeric(18,6),
    daily_change_pct numeric(12,6),
    market_cap numeric(18,0),
    stream_status character varying(30),
    raw_vector jsonb,
    raw_metadata jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64)
);


--
-- Name: fact_heatmap_snapshot_2026_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_heatmap_snapshot_2026_10 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    price_heatmap numeric(18,6),
    daily_change_pct numeric(12,6),
    market_cap numeric(18,0),
    stream_status character varying(30),
    raw_vector jsonb,
    raw_metadata jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64)
);


--
-- Name: fact_heatmap_snapshot_2026_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_heatmap_snapshot_2026_11 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    price_heatmap numeric(18,6),
    daily_change_pct numeric(12,6),
    market_cap numeric(18,0),
    stream_status character varying(30),
    raw_vector jsonb,
    raw_metadata jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64)
);


--
-- Name: fact_heatmap_snapshot_2026_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_heatmap_snapshot_2026_12 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    price_heatmap numeric(18,6),
    daily_change_pct numeric(12,6),
    market_cap numeric(18,0),
    stream_status character varying(30),
    raw_vector jsonb,
    raw_metadata jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64)
);


--
-- Name: fact_market_bar_15m; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
)
PARTITION BY RANGE (bar_start_utc);


--
-- Name: TABLE fact_market_bar_15m; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.fact_market_bar_15m IS 'Barras de 15 min por activo (agregación de fact_market_series). Particionada mensual por bar_start_utc.';


--
-- Name: COLUMN fact_market_bar_15m.bar_start_utc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.bar_start_utc IS 'Inicio de la barra (frontera 15 min UTC).';


--
-- Name: COLUMN fact_market_bar_15m.session_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.session_date IS 'Fecha de sesión a la que pertenece la barra (UTC).';


--
-- Name: COLUMN fact_market_bar_15m.open; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.open IS 'Primer close del tick más temprano de la barra.';


--
-- Name: COLUMN fact_market_bar_15m.high; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.high IS 'Máximo de close dentro de la barra.';


--
-- Name: COLUMN fact_market_bar_15m.low; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.low IS 'Mínimo de close dentro de la barra.';


--
-- Name: COLUMN fact_market_bar_15m.close; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.close IS 'Último close (último tick) de la barra.';


--
-- Name: COLUMN fact_market_bar_15m.volume_delta; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.volume_delta IS 'Diferencia de volumen dentro de la barra (volume_n - volume_1). NULL si no hay volumen (yields/índices/spot).';


--
-- Name: COLUMN fact_market_bar_15m.n_ticks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.n_ticks IS 'Número de ticks de fact_market_series que componen la barra.';


--
-- Name: COLUMN fact_market_bar_15m.is_regular; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.is_regular IS 'True si la barra está dentro de la sesión regular del activo (XNYS para equity/ETF).';


--
-- Name: COLUMN fact_market_bar_15m.close_quality; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.close_quality IS 'Calidad del cierre según F4.1b: definitive / provisional / unknown.';


--
-- Name: COLUMN fact_market_bar_15m.last_tick_offset_s; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_bar_15m.last_tick_offset_s IS 'Segundos desde el boundary de cierre hasta el último tick (negativo si el tick es posterior).';


--
-- Name: fact_market_bar_15m_2026_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2026_09 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2026_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2026_10 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2026_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2026_11 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2026_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2026_12 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_01; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_01 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_02; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_02 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_03 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_04 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_05 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_06 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_07 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_08 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_09 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_10 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_11 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_bar_15m_2027_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_bar_15m_2027_12 (
    asset_id integer NOT NULL,
    bar_start_utc timestamp with time zone NOT NULL,
    session_date date NOT NULL,
    open numeric(20,8),
    high numeric(20,8),
    low numeric(20,8),
    close numeric(20,8),
    volume_delta numeric(30,8),
    n_ticks smallint NOT NULL,
    is_regular boolean NOT NULL,
    close_quality text DEFAULT 'unknown'::text NOT NULL,
    last_tick_offset_s integer,
    CONSTRAINT fact_market_bar_15m_close_quality_check CHECK ((close_quality = ANY (ARRAY['definitive'::text, 'provisional'::text, 'unknown'::text])))
);


--
-- Name: fact_market_series; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
)
PARTITION BY RANGE (timestamp_utc);


--
-- Name: TABLE fact_market_series; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.fact_market_series IS 'Series técnicas del radar V4. Particionada mensual.';


--
-- Name: COLUMN fact_market_series.volume; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_series.volume IS 'NUMERIC(20,8): cripto llega fraccional; acciones/futuros enteros caben igual.';


--
-- Name: COLUMN fact_market_series.raw_payload; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_series.raw_payload IS 'JSON crudo del endpoint. NULL si el ETL no lo captura.';


--
-- Name: COLUMN fact_market_series.source_checksum; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.fact_market_series.source_checksum IS 'SHA-256 hex del row canónico.';


--
-- Name: fact_market_series_2026_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_03 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_04 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_05 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_06 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_07 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_08 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_09 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_10 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_11 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: fact_market_series_2026_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_market_series_2026_12 (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(20,8),
    volume numeric(20,8),
    rsi numeric(10,4),
    cci20 numeric(10,4),
    bbpower numeric(10,4),
    adx numeric(10,4),
    pivot_camarilla_r3 numeric(18,6),
    perf_w numeric(12,8),
    change_pct numeric(12,8),
    raw_payload jsonb,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_checksum character varying(64),
    update_mode character varying(30),
    cycle_id uuid,
    fetched_at timestamp with time zone,
    feed_delay_s integer,
    premarket_close numeric(20,8),
    premarket_change numeric(12,8),
    premarket_volume numeric(30,8),
    gap numeric(12,8)
);


--
-- Name: sync_checkpoint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_checkpoint (
    checkpoint_id integer NOT NULL,
    script_name character varying(100) NOT NULL,
    last_timestamp timestamp with time zone NOT NULL,
    last_event_id bigint,
    records_processed integer DEFAULT 0 NOT NULL,
    last_run_at timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL
);


--
-- Name: TABLE sync_checkpoint; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sync_checkpoint IS 'Checkpoints de reanudación. Una fila por scraper.';


--
-- Name: sync_checkpoint_checkpoint_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sync_checkpoint_checkpoint_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sync_checkpoint_checkpoint_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sync_checkpoint_checkpoint_id_seq OWNED BY public.sync_checkpoint.checkpoint_id;


--
-- Name: vw_heatmap_enriched; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vw_heatmap_enriched AS
 SELECT h.asset_id,
    a.symbol,
    a.ticker,
    a.company_name,
    a.sector,
    h.timestamp_utc,
    h.price_heatmap,
    h.daily_change_pct,
    h.market_cap,
        CASE
            WHEN (h.daily_change_pct > (0)::numeric) THEN 'BUY'::text
            WHEN (h.daily_change_pct < (0)::numeric) THEN 'SELL'::text
            ELSE 'NEUTRAL'::text
        END AS market_direction,
    abs(h.daily_change_pct) AS color_intensity,
    ( SELECT ms.rsi
           FROM public.fact_market_series ms
          WHERE ((ms.asset_id = h.asset_id) AND (ms.timestamp_utc <= h.timestamp_utc) AND (ms.rsi IS NOT NULL))
          ORDER BY ms.timestamp_utc DESC
         LIMIT 1) AS last_rsi
   FROM (public.fact_heatmap_snapshot h
     JOIN public.dim_asset a ON ((a.asset_id = h.asset_id)))
  WHERE ((a.asset_class = ANY (ARRAY['equity'::text, 'etf'::text])) AND (a.is_active = true) AND (a.current_version = true));


--
-- Name: VIEW vw_heatmap_enriched; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.vw_heatmap_enriched IS 'Heatmap enriquecido. Restringido a equity/etf para excluir activos del radar V4.';


--
-- Name: vw_heatmap_event_impact; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vw_heatmap_event_impact AS
 SELECT h.asset_id,
    h.symbol,
    h.ticker,
    h.company_name,
    h.sector,
    h.timestamp_utc,
    h.price_heatmap,
    h.daily_change_pct,
    h.market_cap,
    h.market_direction,
    h.color_intensity,
    h.last_rsi,
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
    (EXTRACT(epoch FROM (h.timestamp_utc - e.event_timestamp)) / 3600.0) AS hours_since_event
   FROM (public.vw_heatmap_enriched h
     JOIN public.fact_economic_event e ON ((((e.currency)::text = 'USD'::text) AND ((e.importance >= 1) AND (e.importance <= 3)) AND ((e.event_timestamp >= (h.timestamp_utc - '06:00:00'::interval)) AND (e.event_timestamp <= (h.timestamp_utc + '06:00:00'::interval))))));


--
-- Name: VIEW vw_heatmap_event_impact; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.vw_heatmap_event_impact IS 'Cruce heatmap × eventos USD de importancia media+ en ventana ±6 h.';


--
-- Name: vw_market_live; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vw_market_live AS
 SELECT a.symbol,
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
            WHEN ((ms.rsi < (30)::numeric) AND (ms.change_pct > (0)::numeric)) THEN 'OVERSOLD_REVERSAL'::text
            WHEN ((ms.rsi > (70)::numeric) AND (ms.change_pct < (0)::numeric)) THEN 'OVERBOUGHT_REVERSAL'::text
            WHEN (ms.adx > (25)::numeric) THEN 'TRENDING'::text
            ELSE 'NEUTRAL'::text
        END AS signal_status
   FROM (public.fact_market_series ms
     JOIN public.dim_asset a ON ((a.asset_id = ms.asset_id)))
  WHERE ((ms.timestamp_utc >= (now() - '7 days'::interval)) AND (a.is_active = true) AND (a.current_version = true));


--
-- Name: VIEW vw_market_live; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.vw_market_live IS 'Series técnicas del radar V4 en ventana de 7 días con señal derivada.';


--
-- Name: fact_heatmap_snapshot_2026_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot ATTACH PARTITION public.fact_heatmap_snapshot_2026_09 FOR VALUES FROM ('2026-09-01 00:00:00-05') TO ('2026-10-01 00:00:00-05');


--
-- Name: fact_heatmap_snapshot_2026_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot ATTACH PARTITION public.fact_heatmap_snapshot_2026_10 FOR VALUES FROM ('2026-10-01 00:00:00-05') TO ('2026-11-01 00:00:00-05');


--
-- Name: fact_heatmap_snapshot_2026_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot ATTACH PARTITION public.fact_heatmap_snapshot_2026_11 FOR VALUES FROM ('2026-11-01 00:00:00-05') TO ('2026-12-01 00:00:00-05');


--
-- Name: fact_heatmap_snapshot_2026_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot ATTACH PARTITION public.fact_heatmap_snapshot_2026_12 FOR VALUES FROM ('2026-12-01 00:00:00-05') TO ('2027-01-01 00:00:00-05');


--
-- Name: fact_market_bar_15m_2026_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2026_09 FOR VALUES FROM ('2026-08-31 19:00:00-05') TO ('2026-09-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2026_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2026_10 FOR VALUES FROM ('2026-09-30 19:00:00-05') TO ('2026-10-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2026_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2026_11 FOR VALUES FROM ('2026-10-31 19:00:00-05') TO ('2026-11-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2026_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2026_12 FOR VALUES FROM ('2026-11-30 19:00:00-05') TO ('2026-12-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_01; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_01 FOR VALUES FROM ('2026-12-31 19:00:00-05') TO ('2027-01-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_02; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_02 FOR VALUES FROM ('2027-01-31 19:00:00-05') TO ('2027-02-28 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_03 FOR VALUES FROM ('2027-02-28 19:00:00-05') TO ('2027-03-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_04 FOR VALUES FROM ('2027-03-31 19:00:00-05') TO ('2027-04-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_05 FOR VALUES FROM ('2027-04-30 19:00:00-05') TO ('2027-05-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_06 FOR VALUES FROM ('2027-05-31 19:00:00-05') TO ('2027-06-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_07 FOR VALUES FROM ('2027-06-30 19:00:00-05') TO ('2027-07-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_08 FOR VALUES FROM ('2027-07-31 19:00:00-05') TO ('2027-08-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_09 FOR VALUES FROM ('2027-08-31 19:00:00-05') TO ('2027-09-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_10 FOR VALUES FROM ('2027-09-30 19:00:00-05') TO ('2027-10-31 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_11 FOR VALUES FROM ('2027-10-31 19:00:00-05') TO ('2027-11-30 19:00:00-05');


--
-- Name: fact_market_bar_15m_2027_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m ATTACH PARTITION public.fact_market_bar_15m_2027_12 FOR VALUES FROM ('2027-11-30 19:00:00-05') TO ('2027-12-31 19:00:00-05');


--
-- Name: fact_market_series_2026_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_03 FOR VALUES FROM ('2026-03-01 00:00:00-05') TO ('2026-04-01 00:00:00-05');


--
-- Name: fact_market_series_2026_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_04 FOR VALUES FROM ('2026-04-01 00:00:00-05') TO ('2026-05-01 00:00:00-05');


--
-- Name: fact_market_series_2026_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_05 FOR VALUES FROM ('2026-05-01 00:00:00-05') TO ('2026-06-01 00:00:00-05');


--
-- Name: fact_market_series_2026_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_06 FOR VALUES FROM ('2026-06-01 00:00:00-05') TO ('2026-07-01 00:00:00-05');


--
-- Name: fact_market_series_2026_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_07 FOR VALUES FROM ('2026-07-01 00:00:00-05') TO ('2026-08-01 00:00:00-05');


--
-- Name: fact_market_series_2026_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_08 FOR VALUES FROM ('2026-08-01 00:00:00-05') TO ('2026-09-01 00:00:00-05');


--
-- Name: fact_market_series_2026_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_09 FOR VALUES FROM ('2026-09-01 00:00:00-05') TO ('2026-10-01 00:00:00-05');


--
-- Name: fact_market_series_2026_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_10 FOR VALUES FROM ('2026-10-01 00:00:00-05') TO ('2026-11-01 00:00:00-05');


--
-- Name: fact_market_series_2026_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_11 FOR VALUES FROM ('2026-11-01 00:00:00-05') TO ('2026-12-01 00:00:00-05');


--
-- Name: fact_market_series_2026_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series ATTACH PARTITION public.fact_market_series_2026_12 FOR VALUES FROM ('2026-12-01 00:00:00-05') TO ('2027-01-01 00:00:00-05');


--
-- Name: audit_sync_run run_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_sync_run ALTER COLUMN run_id SET DEFAULT nextval('public.audit_sync_run_run_id_seq'::regclass);


--
-- Name: dim_asset asset_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_asset ALTER COLUMN asset_id SET DEFAULT nextval('public.dim_asset_asset_id_seq'::regclass);


--
-- Name: sync_checkpoint checkpoint_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_checkpoint ALTER COLUMN checkpoint_id SET DEFAULT nextval('public.sync_checkpoint_checkpoint_id_seq'::regclass);


--
-- Name: audit_sync_run audit_sync_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_sync_run
    ADD CONSTRAINT audit_sync_run_pkey PRIMARY KEY (run_id);


--
-- Name: dim_asset dim_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_asset
    ADD CONSTRAINT dim_asset_pkey PRIMARY KEY (asset_id);


--
-- Name: dim_asset dim_asset_symbol_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_asset
    ADD CONSTRAINT dim_asset_symbol_key UNIQUE (symbol);


--
-- Name: dim_country dim_country_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_country
    ADD CONSTRAINT dim_country_pkey PRIMARY KEY (country_code);


--
-- Name: dim_time dim_time_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_time
    ADD CONSTRAINT dim_time_pkey PRIMARY KEY (date_id);


--
-- Name: dim_trading_session dim_trading_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_trading_session
    ADD CONSTRAINT dim_trading_session_pkey PRIMARY KEY (session_date);


--
-- Name: fact_economic_event fact_economic_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_economic_event
    ADD CONSTRAINT fact_economic_event_pkey PRIMARY KEY (event_id);


--
-- Name: fact_heatmap_snapshot fact_heatmap_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot
    ADD CONSTRAINT fact_heatmap_snapshot_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_heatmap_snapshot_2026_09 fact_heatmap_snapshot_2026_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot_2026_09
    ADD CONSTRAINT fact_heatmap_snapshot_2026_09_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_heatmap_snapshot_2026_10 fact_heatmap_snapshot_2026_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot_2026_10
    ADD CONSTRAINT fact_heatmap_snapshot_2026_10_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_heatmap_snapshot_2026_11 fact_heatmap_snapshot_2026_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot_2026_11
    ADD CONSTRAINT fact_heatmap_snapshot_2026_11_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_heatmap_snapshot_2026_12 fact_heatmap_snapshot_2026_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_heatmap_snapshot_2026_12
    ADD CONSTRAINT fact_heatmap_snapshot_2026_12_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_bar_15m fact_market_bar_15m_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m
    ADD CONSTRAINT fact_market_bar_15m_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2026_09 fact_market_bar_15m_2026_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2026_09
    ADD CONSTRAINT fact_market_bar_15m_2026_09_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2026_10 fact_market_bar_15m_2026_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2026_10
    ADD CONSTRAINT fact_market_bar_15m_2026_10_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2026_11 fact_market_bar_15m_2026_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2026_11
    ADD CONSTRAINT fact_market_bar_15m_2026_11_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2026_12 fact_market_bar_15m_2026_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2026_12
    ADD CONSTRAINT fact_market_bar_15m_2026_12_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_01 fact_market_bar_15m_2027_01_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_01
    ADD CONSTRAINT fact_market_bar_15m_2027_01_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_02 fact_market_bar_15m_2027_02_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_02
    ADD CONSTRAINT fact_market_bar_15m_2027_02_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_03 fact_market_bar_15m_2027_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_03
    ADD CONSTRAINT fact_market_bar_15m_2027_03_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_04 fact_market_bar_15m_2027_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_04
    ADD CONSTRAINT fact_market_bar_15m_2027_04_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_05 fact_market_bar_15m_2027_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_05
    ADD CONSTRAINT fact_market_bar_15m_2027_05_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_06 fact_market_bar_15m_2027_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_06
    ADD CONSTRAINT fact_market_bar_15m_2027_06_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_07 fact_market_bar_15m_2027_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_07
    ADD CONSTRAINT fact_market_bar_15m_2027_07_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_08 fact_market_bar_15m_2027_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_08
    ADD CONSTRAINT fact_market_bar_15m_2027_08_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_09 fact_market_bar_15m_2027_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_09
    ADD CONSTRAINT fact_market_bar_15m_2027_09_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_10 fact_market_bar_15m_2027_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_10
    ADD CONSTRAINT fact_market_bar_15m_2027_10_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_11 fact_market_bar_15m_2027_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_11
    ADD CONSTRAINT fact_market_bar_15m_2027_11_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_bar_15m_2027_12 fact_market_bar_15m_2027_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_bar_15m_2027_12
    ADD CONSTRAINT fact_market_bar_15m_2027_12_pkey PRIMARY KEY (asset_id, bar_start_utc);


--
-- Name: fact_market_series fact_market_series_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series
    ADD CONSTRAINT fact_market_series_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_03 fact_market_series_2026_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_03
    ADD CONSTRAINT fact_market_series_2026_03_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_04 fact_market_series_2026_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_04
    ADD CONSTRAINT fact_market_series_2026_04_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_05 fact_market_series_2026_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_05
    ADD CONSTRAINT fact_market_series_2026_05_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_06 fact_market_series_2026_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_06
    ADD CONSTRAINT fact_market_series_2026_06_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_07 fact_market_series_2026_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_07
    ADD CONSTRAINT fact_market_series_2026_07_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_08 fact_market_series_2026_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_08
    ADD CONSTRAINT fact_market_series_2026_08_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_09 fact_market_series_2026_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_09
    ADD CONSTRAINT fact_market_series_2026_09_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_10 fact_market_series_2026_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_10
    ADD CONSTRAINT fact_market_series_2026_10_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_11 fact_market_series_2026_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_11
    ADD CONSTRAINT fact_market_series_2026_11_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: fact_market_series_2026_12 fact_market_series_2026_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_market_series_2026_12
    ADD CONSTRAINT fact_market_series_2026_12_pkey PRIMARY KEY (asset_id, timestamp_utc);


--
-- Name: sync_checkpoint sync_checkpoint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_checkpoint
    ADD CONSTRAINT sync_checkpoint_pkey PRIMARY KEY (checkpoint_id);


--
-- Name: sync_checkpoint sync_checkpoint_script_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_checkpoint
    ADD CONSTRAINT sync_checkpoint_script_name_key UNIQUE (script_name);


--
-- Name: idx_fact_heatmap_change; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_heatmap_change ON ONLY public.fact_heatmap_snapshot USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_09_daily_change_pct_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_09_daily_change_pct_idx ON public.fact_heatmap_snapshot_2026_09 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);


--
-- Name: idx_fact_heatmap_mcap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_heatmap_mcap ON ONLY public.fact_heatmap_snapshot USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_09_market_cap_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_09_market_cap_idx ON public.fact_heatmap_snapshot_2026_09 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);


--
-- Name: idx_fact_heatmap_raw_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_heatmap_raw_vector ON ONLY public.fact_heatmap_snapshot USING gin (raw_vector);


--
-- Name: fact_heatmap_snapshot_2026_09_raw_vector_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_09_raw_vector_idx ON public.fact_heatmap_snapshot_2026_09 USING gin (raw_vector);


--
-- Name: idx_fact_heatmap_ts_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_heatmap_ts_desc ON ONLY public.fact_heatmap_snapshot USING btree (timestamp_utc DESC);


--
-- Name: fact_heatmap_snapshot_2026_09_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_09_timestamp_utc_idx ON public.fact_heatmap_snapshot_2026_09 USING btree (timestamp_utc DESC);


--
-- Name: fact_heatmap_snapshot_2026_10_daily_change_pct_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_10_daily_change_pct_idx ON public.fact_heatmap_snapshot_2026_10 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_10_market_cap_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_10_market_cap_idx ON public.fact_heatmap_snapshot_2026_10 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_10_raw_vector_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_10_raw_vector_idx ON public.fact_heatmap_snapshot_2026_10 USING gin (raw_vector);


--
-- Name: fact_heatmap_snapshot_2026_10_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_10_timestamp_utc_idx ON public.fact_heatmap_snapshot_2026_10 USING btree (timestamp_utc DESC);


--
-- Name: fact_heatmap_snapshot_2026_11_daily_change_pct_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_11_daily_change_pct_idx ON public.fact_heatmap_snapshot_2026_11 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_11_market_cap_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_11_market_cap_idx ON public.fact_heatmap_snapshot_2026_11 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_11_raw_vector_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_11_raw_vector_idx ON public.fact_heatmap_snapshot_2026_11 USING gin (raw_vector);


--
-- Name: fact_heatmap_snapshot_2026_11_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_11_timestamp_utc_idx ON public.fact_heatmap_snapshot_2026_11 USING btree (timestamp_utc DESC);


--
-- Name: fact_heatmap_snapshot_2026_12_daily_change_pct_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_12_daily_change_pct_idx ON public.fact_heatmap_snapshot_2026_12 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_12_market_cap_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_12_market_cap_idx ON public.fact_heatmap_snapshot_2026_12 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);


--
-- Name: fact_heatmap_snapshot_2026_12_raw_vector_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_12_raw_vector_idx ON public.fact_heatmap_snapshot_2026_12 USING gin (raw_vector);


--
-- Name: fact_heatmap_snapshot_2026_12_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_heatmap_snapshot_2026_12_timestamp_utc_idx ON public.fact_heatmap_snapshot_2026_12 USING btree (timestamp_utc DESC);


--
-- Name: idx_fact_market_bar_15m_bar_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_bar_15m_bar_start ON ONLY public.fact_market_bar_15m USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2026_09_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_09_bar_start_utc_idx ON public.fact_market_bar_15m_2026_09 USING btree (bar_start_utc DESC);


--
-- Name: idx_fact_market_bar_15m_session_asset; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_bar_15m_session_asset ON ONLY public.fact_market_bar_15m USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2026_09_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_09_session_date_asset_id_idx ON public.fact_market_bar_15m_2026_09 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2026_10_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_10_bar_start_utc_idx ON public.fact_market_bar_15m_2026_10 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2026_10_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_10_session_date_asset_id_idx ON public.fact_market_bar_15m_2026_10 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2026_11_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_11_bar_start_utc_idx ON public.fact_market_bar_15m_2026_11 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2026_11_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_11_session_date_asset_id_idx ON public.fact_market_bar_15m_2026_11 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2026_12_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_12_bar_start_utc_idx ON public.fact_market_bar_15m_2026_12 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2026_12_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2026_12_session_date_asset_id_idx ON public.fact_market_bar_15m_2026_12 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_01_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_01_bar_start_utc_idx ON public.fact_market_bar_15m_2027_01 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_01_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_01_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_01 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_02_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_02_bar_start_utc_idx ON public.fact_market_bar_15m_2027_02 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_02_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_02_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_02 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_03_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_03_bar_start_utc_idx ON public.fact_market_bar_15m_2027_03 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_03_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_03_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_03 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_04_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_04_bar_start_utc_idx ON public.fact_market_bar_15m_2027_04 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_04_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_04_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_04 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_05_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_05_bar_start_utc_idx ON public.fact_market_bar_15m_2027_05 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_05_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_05_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_05 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_06_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_06_bar_start_utc_idx ON public.fact_market_bar_15m_2027_06 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_06_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_06_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_06 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_07_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_07_bar_start_utc_idx ON public.fact_market_bar_15m_2027_07 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_07_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_07_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_07 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_08_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_08_bar_start_utc_idx ON public.fact_market_bar_15m_2027_08 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_08_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_08_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_08 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_09_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_09_bar_start_utc_idx ON public.fact_market_bar_15m_2027_09 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_09_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_09_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_09 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_10_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_10_bar_start_utc_idx ON public.fact_market_bar_15m_2027_10 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_10_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_10_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_10 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_11_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_11_bar_start_utc_idx ON public.fact_market_bar_15m_2027_11 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_11_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_11_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_11 USING btree (session_date, asset_id);


--
-- Name: fact_market_bar_15m_2027_12_bar_start_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_12_bar_start_utc_idx ON public.fact_market_bar_15m_2027_12 USING btree (bar_start_utc DESC);


--
-- Name: fact_market_bar_15m_2027_12_session_date_asset_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_bar_15m_2027_12_session_date_asset_id_idx ON public.fact_market_bar_15m_2027_12 USING btree (session_date, asset_id);


--
-- Name: idx_fact_market_series_close; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_series_close ON ONLY public.fact_market_series USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_03_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_03_close_idx ON public.fact_market_series_2026_03 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: idx_fact_market_series_rsi; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_series_rsi ON ONLY public.fact_market_series USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_03_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_03_rsi_idx ON public.fact_market_series_2026_03 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: idx_fact_market_series_ts_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_series_ts_desc ON ONLY public.fact_market_series USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_03_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_03_timestamp_utc_idx ON public.fact_market_series_2026_03 USING btree (timestamp_utc DESC);


--
-- Name: idx_fact_market_series_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_market_series_date ON ONLY public.fact_market_series USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_03_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_03_timezone_idx ON public.fact_market_series_2026_03 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_03_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_03_ts_brin ON public.fact_market_series_2026_03 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_04_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_04_close_idx ON public.fact_market_series_2026_04 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_04_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_04_rsi_idx ON public.fact_market_series_2026_04 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_04_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_04_timestamp_utc_idx ON public.fact_market_series_2026_04 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_04_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_04_timezone_idx ON public.fact_market_series_2026_04 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_04_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_04_ts_brin ON public.fact_market_series_2026_04 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_05_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_05_close_idx ON public.fact_market_series_2026_05 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_05_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_05_rsi_idx ON public.fact_market_series_2026_05 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_05_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_05_timestamp_utc_idx ON public.fact_market_series_2026_05 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_05_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_05_timezone_idx ON public.fact_market_series_2026_05 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_05_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_05_ts_brin ON public.fact_market_series_2026_05 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_06_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_06_close_idx ON public.fact_market_series_2026_06 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_06_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_06_rsi_idx ON public.fact_market_series_2026_06 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_06_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_06_timestamp_utc_idx ON public.fact_market_series_2026_06 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_06_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_06_timezone_idx ON public.fact_market_series_2026_06 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_06_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_06_ts_brin ON public.fact_market_series_2026_06 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_07_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_07_close_idx ON public.fact_market_series_2026_07 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_07_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_07_rsi_idx ON public.fact_market_series_2026_07 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_07_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_07_timestamp_utc_idx ON public.fact_market_series_2026_07 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_07_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_07_timezone_idx ON public.fact_market_series_2026_07 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_07_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_07_ts_brin ON public.fact_market_series_2026_07 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_08_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_08_close_idx ON public.fact_market_series_2026_08 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_08_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_08_rsi_idx ON public.fact_market_series_2026_08 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_08_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_08_timestamp_utc_idx ON public.fact_market_series_2026_08 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_08_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_08_timezone_idx ON public.fact_market_series_2026_08 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_08_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_08_ts_brin ON public.fact_market_series_2026_08 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_09_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_09_close_idx ON public.fact_market_series_2026_09 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_09_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_09_rsi_idx ON public.fact_market_series_2026_09 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_09_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_09_timestamp_utc_idx ON public.fact_market_series_2026_09 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_09_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_09_timezone_idx ON public.fact_market_series_2026_09 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_09_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_09_ts_brin ON public.fact_market_series_2026_09 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_10_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_10_close_idx ON public.fact_market_series_2026_10 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_10_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_10_rsi_idx ON public.fact_market_series_2026_10 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_10_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_10_timestamp_utc_idx ON public.fact_market_series_2026_10 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_10_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_10_timezone_idx ON public.fact_market_series_2026_10 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_10_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_10_ts_brin ON public.fact_market_series_2026_10 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_11_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_11_close_idx ON public.fact_market_series_2026_11 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_11_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_11_rsi_idx ON public.fact_market_series_2026_11 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_11_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_11_timestamp_utc_idx ON public.fact_market_series_2026_11 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_11_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_11_timezone_idx ON public.fact_market_series_2026_11 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_11_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_11_ts_brin ON public.fact_market_series_2026_11 USING brin (timestamp_utc);


--
-- Name: fact_market_series_2026_12_close_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_12_close_idx ON public.fact_market_series_2026_12 USING btree (close) WHERE (close IS NOT NULL);


--
-- Name: fact_market_series_2026_12_rsi_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_12_rsi_idx ON public.fact_market_series_2026_12 USING btree (rsi) WHERE (rsi IS NOT NULL);


--
-- Name: fact_market_series_2026_12_timestamp_utc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_12_timestamp_utc_idx ON public.fact_market_series_2026_12 USING btree (timestamp_utc DESC);


--
-- Name: fact_market_series_2026_12_timezone_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_12_timezone_idx ON public.fact_market_series_2026_12 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));


--
-- Name: fact_market_series_2026_12_ts_brin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fact_market_series_2026_12_ts_brin ON public.fact_market_series_2026_12 USING brin (timestamp_utc);


--
-- Name: idx_audit_sync_run_script; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_sync_run_script ON public.audit_sync_run USING btree (script_name, run_start DESC);


--
-- Name: idx_dim_asset_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_asset_active ON public.dim_asset USING btree (is_active, current_version) WHERE (is_active AND current_version);


--
-- Name: idx_dim_asset_class; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_asset_class ON public.dim_asset USING btree (asset_class) WHERE (is_active AND current_version);


--
-- Name: idx_dim_asset_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_asset_slug ON public.dim_asset USING btree (slug);


--
-- Name: idx_dim_asset_symbol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dim_asset_symbol ON public.dim_asset USING btree (symbol);


--
-- Name: idx_fact_economic_event_captured; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_captured ON public.fact_economic_event USING btree (captured_at DESC);


--
-- Name: idx_fact_economic_event_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_country ON public.fact_economic_event USING btree (country);


--
-- Name: idx_fact_economic_event_country_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_country_ts ON public.fact_economic_event USING btree (country, event_timestamp DESC);


--
-- Name: idx_fact_economic_event_importance; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_importance ON public.fact_economic_event USING btree (importance) WHERE ((importance >= 1) AND (importance <= 3));


--
-- Name: idx_fact_economic_event_ticker; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_ticker ON public.fact_economic_event USING btree (event_ticker) WHERE (event_ticker IS NOT NULL);


--
-- Name: idx_fact_economic_event_title_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_title_gin ON public.fact_economic_event USING gin (public.text_to_tsvector_english(title));


--
-- Name: idx_fact_economic_event_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fact_economic_event_ts ON public.fact_economic_event USING btree (event_timestamp DESC);


--
-- Name: fact_heatmap_snapshot_2026_09_daily_change_pct_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_change ATTACH PARTITION public.fact_heatmap_snapshot_2026_09_daily_change_pct_idx;


--
-- Name: fact_heatmap_snapshot_2026_09_market_cap_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_mcap ATTACH PARTITION public.fact_heatmap_snapshot_2026_09_market_cap_idx;


--
-- Name: fact_heatmap_snapshot_2026_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_heatmap_snapshot_pkey ATTACH PARTITION public.fact_heatmap_snapshot_2026_09_pkey;


--
-- Name: fact_heatmap_snapshot_2026_09_raw_vector_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_raw_vector ATTACH PARTITION public.fact_heatmap_snapshot_2026_09_raw_vector_idx;


--
-- Name: fact_heatmap_snapshot_2026_09_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_ts_desc ATTACH PARTITION public.fact_heatmap_snapshot_2026_09_timestamp_utc_idx;


--
-- Name: fact_heatmap_snapshot_2026_10_daily_change_pct_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_change ATTACH PARTITION public.fact_heatmap_snapshot_2026_10_daily_change_pct_idx;


--
-- Name: fact_heatmap_snapshot_2026_10_market_cap_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_mcap ATTACH PARTITION public.fact_heatmap_snapshot_2026_10_market_cap_idx;


--
-- Name: fact_heatmap_snapshot_2026_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_heatmap_snapshot_pkey ATTACH PARTITION public.fact_heatmap_snapshot_2026_10_pkey;


--
-- Name: fact_heatmap_snapshot_2026_10_raw_vector_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_raw_vector ATTACH PARTITION public.fact_heatmap_snapshot_2026_10_raw_vector_idx;


--
-- Name: fact_heatmap_snapshot_2026_10_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_ts_desc ATTACH PARTITION public.fact_heatmap_snapshot_2026_10_timestamp_utc_idx;


--
-- Name: fact_heatmap_snapshot_2026_11_daily_change_pct_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_change ATTACH PARTITION public.fact_heatmap_snapshot_2026_11_daily_change_pct_idx;


--
-- Name: fact_heatmap_snapshot_2026_11_market_cap_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_mcap ATTACH PARTITION public.fact_heatmap_snapshot_2026_11_market_cap_idx;


--
-- Name: fact_heatmap_snapshot_2026_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_heatmap_snapshot_pkey ATTACH PARTITION public.fact_heatmap_snapshot_2026_11_pkey;


--
-- Name: fact_heatmap_snapshot_2026_11_raw_vector_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_raw_vector ATTACH PARTITION public.fact_heatmap_snapshot_2026_11_raw_vector_idx;


--
-- Name: fact_heatmap_snapshot_2026_11_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_ts_desc ATTACH PARTITION public.fact_heatmap_snapshot_2026_11_timestamp_utc_idx;


--
-- Name: fact_heatmap_snapshot_2026_12_daily_change_pct_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_change ATTACH PARTITION public.fact_heatmap_snapshot_2026_12_daily_change_pct_idx;


--
-- Name: fact_heatmap_snapshot_2026_12_market_cap_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_mcap ATTACH PARTITION public.fact_heatmap_snapshot_2026_12_market_cap_idx;


--
-- Name: fact_heatmap_snapshot_2026_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_heatmap_snapshot_pkey ATTACH PARTITION public.fact_heatmap_snapshot_2026_12_pkey;


--
-- Name: fact_heatmap_snapshot_2026_12_raw_vector_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_raw_vector ATTACH PARTITION public.fact_heatmap_snapshot_2026_12_raw_vector_idx;


--
-- Name: fact_heatmap_snapshot_2026_12_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_heatmap_ts_desc ATTACH PARTITION public.fact_heatmap_snapshot_2026_12_timestamp_utc_idx;


--
-- Name: fact_market_bar_15m_2026_09_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2026_09_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2026_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2026_09_pkey;


--
-- Name: fact_market_bar_15m_2026_09_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2026_09_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2026_10_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2026_10_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2026_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2026_10_pkey;


--
-- Name: fact_market_bar_15m_2026_10_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2026_10_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2026_11_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2026_11_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2026_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2026_11_pkey;


--
-- Name: fact_market_bar_15m_2026_11_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2026_11_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2026_12_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2026_12_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2026_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2026_12_pkey;


--
-- Name: fact_market_bar_15m_2026_12_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2026_12_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_01_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_01_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_01_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_01_pkey;


--
-- Name: fact_market_bar_15m_2027_01_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_01_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_02_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_02_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_02_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_02_pkey;


--
-- Name: fact_market_bar_15m_2027_02_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_02_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_03_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_03_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_03_pkey;


--
-- Name: fact_market_bar_15m_2027_03_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_03_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_04_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_04_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_04_pkey;


--
-- Name: fact_market_bar_15m_2027_04_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_04_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_05_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_05_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_05_pkey;


--
-- Name: fact_market_bar_15m_2027_05_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_05_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_06_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_06_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_06_pkey;


--
-- Name: fact_market_bar_15m_2027_06_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_06_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_07_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_07_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_07_pkey;


--
-- Name: fact_market_bar_15m_2027_07_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_07_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_08_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_08_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_08_pkey;


--
-- Name: fact_market_bar_15m_2027_08_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_08_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_09_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_09_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_09_pkey;


--
-- Name: fact_market_bar_15m_2027_09_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_09_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_10_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_10_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_10_pkey;


--
-- Name: fact_market_bar_15m_2027_10_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_10_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_11_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_11_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_11_pkey;


--
-- Name: fact_market_bar_15m_2027_11_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_11_session_date_asset_id_idx;


--
-- Name: fact_market_bar_15m_2027_12_bar_start_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_bar_start ATTACH PARTITION public.fact_market_bar_15m_2027_12_bar_start_utc_idx;


--
-- Name: fact_market_bar_15m_2027_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_bar_15m_pkey ATTACH PARTITION public.fact_market_bar_15m_2027_12_pkey;


--
-- Name: fact_market_bar_15m_2027_12_session_date_asset_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_bar_15m_session_asset ATTACH PARTITION public.fact_market_bar_15m_2027_12_session_date_asset_id_idx;


--
-- Name: fact_market_series_2026_03_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_03_close_idx;


--
-- Name: fact_market_series_2026_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_03_pkey;


--
-- Name: fact_market_series_2026_03_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_03_rsi_idx;


--
-- Name: fact_market_series_2026_03_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_03_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_03_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_03_timezone_idx;


--
-- Name: fact_market_series_2026_04_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_04_close_idx;


--
-- Name: fact_market_series_2026_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_04_pkey;


--
-- Name: fact_market_series_2026_04_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_04_rsi_idx;


--
-- Name: fact_market_series_2026_04_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_04_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_04_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_04_timezone_idx;


--
-- Name: fact_market_series_2026_05_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_05_close_idx;


--
-- Name: fact_market_series_2026_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_05_pkey;


--
-- Name: fact_market_series_2026_05_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_05_rsi_idx;


--
-- Name: fact_market_series_2026_05_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_05_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_05_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_05_timezone_idx;


--
-- Name: fact_market_series_2026_06_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_06_close_idx;


--
-- Name: fact_market_series_2026_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_06_pkey;


--
-- Name: fact_market_series_2026_06_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_06_rsi_idx;


--
-- Name: fact_market_series_2026_06_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_06_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_06_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_06_timezone_idx;


--
-- Name: fact_market_series_2026_07_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_07_close_idx;


--
-- Name: fact_market_series_2026_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_07_pkey;


--
-- Name: fact_market_series_2026_07_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_07_rsi_idx;


--
-- Name: fact_market_series_2026_07_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_07_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_07_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_07_timezone_idx;


--
-- Name: fact_market_series_2026_08_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_08_close_idx;


--
-- Name: fact_market_series_2026_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_08_pkey;


--
-- Name: fact_market_series_2026_08_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_08_rsi_idx;


--
-- Name: fact_market_series_2026_08_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_08_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_08_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_08_timezone_idx;


--
-- Name: fact_market_series_2026_09_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_09_close_idx;


--
-- Name: fact_market_series_2026_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_09_pkey;


--
-- Name: fact_market_series_2026_09_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_09_rsi_idx;


--
-- Name: fact_market_series_2026_09_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_09_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_09_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_09_timezone_idx;


--
-- Name: fact_market_series_2026_10_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_10_close_idx;


--
-- Name: fact_market_series_2026_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_10_pkey;


--
-- Name: fact_market_series_2026_10_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_10_rsi_idx;


--
-- Name: fact_market_series_2026_10_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_10_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_10_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_10_timezone_idx;


--
-- Name: fact_market_series_2026_11_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_11_close_idx;


--
-- Name: fact_market_series_2026_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_11_pkey;


--
-- Name: fact_market_series_2026_11_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_11_rsi_idx;


--
-- Name: fact_market_series_2026_11_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_11_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_11_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_11_timezone_idx;


--
-- Name: fact_market_series_2026_12_close_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_close ATTACH PARTITION public.fact_market_series_2026_12_close_idx;


--
-- Name: fact_market_series_2026_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.fact_market_series_pkey ATTACH PARTITION public.fact_market_series_2026_12_pkey;


--
-- Name: fact_market_series_2026_12_rsi_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_rsi ATTACH PARTITION public.fact_market_series_2026_12_rsi_idx;


--
-- Name: fact_market_series_2026_12_timestamp_utc_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_ts_desc ATTACH PARTITION public.fact_market_series_2026_12_timestamp_utc_idx;


--
-- Name: fact_market_series_2026_12_timezone_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_fact_market_series_date ATTACH PARTITION public.fact_market_series_2026_12_timezone_idx;


--
-- Name: fact_economic_event fact_economic_event_country_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_economic_event
    ADD CONSTRAINT fact_economic_event_country_fkey FOREIGN KEY (country) REFERENCES public.dim_country(country_code);


--
--



"""

_DOWN = r"""
-- ============ downgrade: revertir en orden inverso ============
DROP VIEW IF EXISTS public.vw_market_live CASCADE;
DROP VIEW IF EXISTS public.vw_heatmap_event_impact CASCADE;
DROP VIEW IF EXISTS public.vw_heatmap_enriched CASCADE;
DROP FUNCTION IF EXISTS public.text_to_tsvector_english(text) CASCADE;
DROP FUNCTION IF EXISTS public.upsert_heatmap_snapshot CASCADE;
DROP FUNCTION IF EXISTS public.upsert_market_series CASCADE;
DROP TABLE IF EXISTS public.fact_market_series CASCADE;
DROP TABLE IF EXISTS public.fact_heatmap_snapshot CASCADE;
DROP TABLE IF EXISTS public.fact_market_bar_15m CASCADE;
DROP TABLE IF EXISTS public.fact_economic_event CASCADE;
DROP TABLE IF EXISTS public.dim_asset CASCADE;
DROP TABLE IF EXISTS public.dim_trading_session CASCADE;
DROP TABLE IF EXISTS public.dim_time CASCADE;
DROP TABLE IF EXISTS public.dim_country CASCADE;
DROP TABLE IF EXISTS public.audit_sync_run CASCADE;
DROP TABLE IF EXISTS public.sync_checkpoint CASCADE;
DROP SEQUENCE IF EXISTS public.dim_asset_asset_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.audit_sync_run_run_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.sync_checkpoint_checkpoint_id_seq CASCADE;
DROP EXTENSION IF EXISTS pg_trgm;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)
