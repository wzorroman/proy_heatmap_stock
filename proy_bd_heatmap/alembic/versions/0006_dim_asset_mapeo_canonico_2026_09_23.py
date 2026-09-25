"""dim_asset: Tipo 1 + mapeo canónico de claves lógicas (F4.5/F4.5b)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-23 23:50 UTC

F4.5 · Resolver SCD2 en dim_asset (D7 → Tipo 1).
F4.5b · dim_asset: logical_key + resolución SCD2 (M-DAT-06 / M-DAT-13).

`dim_asset` se declaró SCD Tipo 2 (`valid_from`, `valid_to`,
`current_version`) pero `symbol` es `UNIQUE` global
(`dim_asset_symbol_key`): nunca puede existir una segunda versión del
mismo símbolo. Las vistas y funciones filtran `current_version` sin
necesidad y `idx_dim_asset_symbol` duplica la unicidad. Decisión (D7,
aplicada): **Tipo 1**, que es la capacidad real que consume el
ecosistema (heatmap + radar V4 + fases F5-F9 del roadmap).

La migración:

1. Recrea (CREATE OR REPLACE) las 2 funciones y las 2 vistas que
   referencian `current_version`, dejándolas filtrando solo `is_active`.
   `vw_heatmap_event_impact` no se toca: depende de `vw_heatmap_enriched`
   y conserva exactamente las mismas columnas.
2. Añade las columnas de la resolución (F4.5b / D2-D3):
   `logical_key`, `is_canonical`, `role`, `feed_delay_s`.
3. Backfill de `feed_delay_s` por asset_class (equity/etf/share_class →
   900 s, future → 600 s, resto → 0 s).
4. Materializa el mapeo canónico de las 6 claves lógicas de F2.5
   (VIX, DXY, TLT, US10Y, ORO, OIL): 1 primario canónico por clave,
   0..n respaldos; alta del símbolo `TVC:DXY` (U.S. Dollar Index) que no
   existía en el universo.
5. Crea índice único parcial `uq_dim_asset_canonical_logical_key`
   (1 canónico por clave lógica), identidad que el radar V5 consumirá en
   F2.5 (resolución de símbolos macro por logical_key).
6. Elimina `idx_dim_asset_symbol` (duplica `dim_asset_symbol_key`) y
   reconstruye `idx_dim_asset_active`/`idx_dim_asset_class` sin la
   columna `current_version` que va a desaparecer.
7. Hace el **DROP de las 3 columnas SCD2**.

Consumidores afectados (código y SQL) se corrigen junto con esta
revisión; los archivos 0001/0002 ya aplicados no se tocan.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Funciones/vistas recreadas SIN current_version (Tipo 1)
# ---------------------------------------------------------------------------

_DDL_FUNCIONES = r"""
-- ==== 1) upsert_heatmap_snapshot (sin current_version) ====
CREATE OR REPLACE FUNCTION public.upsert_heatmap_snapshot(p_symbol character varying, p_timestamp_utc timestamp with time zone, p_price_heatmap numeric, p_daily_change_pct numeric, p_market_cap numeric, p_stream_status character varying, p_raw_vector jsonb, p_raw_metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id
    FROM dim_asset
    WHERE symbol = p_symbol AND is_active
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

-- ==== 2) upsert_market_series (sin current_version) ====
CREATE OR REPLACE FUNCTION public.upsert_market_series(p_asset_symbol character varying, p_timestamp_utc timestamp with time zone, p_close numeric, p_volume numeric, p_rsi numeric, p_cci20 numeric, p_bbpower numeric, p_adx numeric, p_pivot_camarilla_r3 numeric, p_perf_w numeric, p_change_pct numeric, p_raw_payload jsonb DEFAULT NULL::jsonb, p_source_checksum character varying DEFAULT NULL::character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id
    FROM dim_asset
    WHERE symbol = p_asset_symbol AND is_active
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
"""

_DDL_VIEWS = r"""
-- ==== 3) vw_heatmap_enriched (sin current_version; columnas idénticas) ====
CREATE OR REPLACE VIEW public.vw_heatmap_enriched AS
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
  WHERE ((a.asset_class = ANY (ARRAY['equity'::text, 'etf'::text])) AND (a.is_active = true));

-- ==== 4) vw_market_live (sin current_version) ====
CREATE OR REPLACE VIEW public.vw_market_live AS
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
  WHERE ((ms.timestamp_utc >= (now() - '7 days'::interval)) AND (a.is_active = true));
"""

# ---------------------------------------------------------------------------
# Columnas + mapeo canónico + reindexación + DROP SCD2
# ---------------------------------------------------------------------------

_DDL_COLUMNAS = r"""
-- ==== 2) columnas de resolución (F4.5b / D2-D3) ====
ALTER TABLE public.dim_asset
    ADD COLUMN logical_key character varying(20),
    ADD COLUMN is_canonical boolean NOT NULL DEFAULT false,
    ADD COLUMN role character varying(10) CONSTRAINT chk_dim_asset_role CHECK (role IN ('primary', 'fallback')),
    ADD COLUMN feed_delay_s integer;

COMMENT ON COLUMN public.dim_asset.logical_key IS 'Clave lógica F2.5 (macro): VIX | DXY | TLT | US10Y | ORO | OIL. NULO si el activo no es clave macro.';
COMMENT ON COLUMN public.dim_asset.is_canonical IS 'TRUE = símbolo canónico de su logical_key (1 por clave, ver uq_dim_asset_canonical_logical_key).';
COMMENT ON COLUMN public.dim_asset.role IS 'primary = fuente canónica | fallback = respaldo del radar (NULO si no es clave lógica).';
COMMENT ON COLUMN public.dim_asset.feed_delay_s IS 'Retardo de alimentación esperado en segundos (equity/etf/share_class≈900, future≈600, resto≈0).';

-- ==== 3) backfill feed_delay_s por asset_class ====
-- share_class del heatmap aparece en la col. asset_class de altas del scraper
-- (common|preferred|unit): se trata como equity a efectos de feed_delay.
UPDATE public.dim_asset
   SET feed_delay_s = 900
 WHERE COALESCE(asset_class, '') IN ('equity', 'etf', 'common', 'preferred', 'unit');

UPDATE public.dim_asset
   SET feed_delay_s = 600
 WHERE asset_class = 'future';

UPDATE public.dim_asset
   SET feed_delay_s = 0
 WHERE asset_class IS NULL
    OR asset_class NOT IN ('equity', 'etf', 'common', 'preferred', 'unit', 'future');

-- ==== 4) mapeo canónico de las 6 claves lógicas (F2.5) ====
-- Alta de TVC:DXY (U.S. Dollar Index) — no existía en dim_asset.
INSERT INTO public.dim_asset (
    asset_id, symbol, ticker, exchange, asset_class, share_class,
    sector, sector_es, company_name, logo_id,
    source_discovered_by, source_category, is_active,
    logical_key, is_canonical, role, feed_delay_s,
    created_at, updated_at, slug, url_logo
)
SELECT
    nextval('public.dim_asset_asset_id_seq'),
    'TVC:DXY', 'DXY', 'TVC', 'index', NULL,
    NULL, NULL, 'DXY — U.S. Dollar Index (canónico)', NULL,
    'mapeo_canonico', NULL, TRUE,
    'DXY', TRUE, 'primary', 0,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, NULL
WHERE NOT EXISTS (SELECT 1 FROM public.dim_asset WHERE symbol = 'TVC:DXY');

SELECT setval('public.dim_asset_asset_id_seq',
              (SELECT MAX(asset_id) FROM public.dim_asset));

-- VIX: TVC:VIX canónico (índice nativo 0 s); CBOE:VX1! respaldo (futuro 600 s)
UPDATE public.dim_asset
   SET logical_key = 'VIX', is_canonical = TRUE,  role = 'primary',  feed_delay_s = 0
 WHERE symbol = 'TVC:VIX';
UPDATE public.dim_asset
   SET logical_key = 'VIX', is_canonical = FALSE, role = 'fallback', feed_delay_s = 600
 WHERE symbol = 'CBOE:VX1!';

-- DXY: TVC:DXY canónico (alta); ICEUS:DX1! y AMEX:UUP respaldos
UPDATE public.dim_asset
   SET logical_key = 'DXY', is_canonical = FALSE, role = 'fallback', feed_delay_s = 600
 WHERE symbol = 'ICEUS:DX1!';
UPDATE public.dim_asset
   SET logical_key = 'DXY', is_canonical = FALSE, role = 'fallback', feed_delay_s = 900
 WHERE symbol = 'AMEX:UUP';

-- ORO: OANDA:XAUUSD canónico; SAXO:XAUUSD respaldo (spot 0 s)
UPDATE public.dim_asset
   SET logical_key = 'ORO', is_canonical = TRUE,  role = 'primary',  feed_delay_s = 0
 WHERE symbol = 'OANDA:XAUUSD';
UPDATE public.dim_asset
   SET logical_key = 'ORO', is_canonical = FALSE, role = 'fallback', feed_delay_s = 0
 WHERE symbol = 'SAXO:XAUUSD';

-- OIL: AMEX:USO canónico (etf 900 s); NYMEX:CL1! respaldo (futuro 600 s)
UPDATE public.dim_asset
   SET logical_key = 'OIL', is_canonical = TRUE,  role = 'primary',  feed_delay_s = 900
 WHERE symbol = 'AMEX:USO';
UPDATE public.dim_asset
   SET logical_key = 'OIL', is_canonical = FALSE, role = 'fallback', feed_delay_s = 600
 WHERE symbol = 'NYMEX:CL1!';

-- TLT: NASDAQ:TLT canónico (etf 900 s); CBOT:ZB1! respaldo (futuro 600 s)
UPDATE public.dim_asset
   SET logical_key = 'TLT', is_canonical = TRUE,  role = 'primary',  feed_delay_s = 900
 WHERE symbol = 'NASDAQ:TLT';
UPDATE public.dim_asset
   SET logical_key = 'TLT', is_canonical = FALSE, role = 'fallback', feed_delay_s = 600
 WHERE symbol = 'CBOT:ZB1!';

-- US10Y: TVC:US10Y único canónico (yield 0 s)
UPDATE public.dim_asset
   SET logical_key = 'US10Y', is_canonical = TRUE, role = 'primary', feed_delay_s = 0
 WHERE symbol = 'TVC:US10Y';
"""

_DDL_REINDEX = r"""
-- ==== 5) 1 canónico por clave lógica ====
CREATE UNIQUE INDEX uq_dim_asset_canonical_logical_key
    ON public.dim_asset USING btree (logical_key)
    WHERE (logical_key IS NOT NULL AND is_canonical);

-- ==== 6) índices de dim_asset sin current_version ====
DROP INDEX public.idx_dim_asset_active;
DROP INDEX public.idx_dim_asset_class;
-- idx_dim_asset_symbol duplica la unicidad dim_asset_symbol_key (M-DAT-13)
DROP INDEX public.idx_dim_asset_symbol;

CREATE INDEX idx_dim_asset_active
    ON public.dim_asset USING btree (is_active)
    WHERE is_active;

CREATE INDEX idx_dim_asset_class
    ON public.dim_asset USING btree (asset_class)
    WHERE is_active;
"""

_DDL_DROP_SCD2 = r"""
-- ==== 7) DROP de las columnas SCD Tipo 2 (D7 → Tipo 1) ====
ALTER TABLE public.dim_asset
    DROP COLUMN valid_from,
    DROP COLUMN valid_to,
    DROP COLUMN current_version;

COMMENT ON TABLE public.dim_asset IS 'Activos financieros (Tipo 1 — D7). Compartida por heatmap y radar V4.';
"""

# ---------------------------------------------------------------------------
# downgrade: revierte F4.5/F4.5b
# ---------------------------------------------------------------------------

_DOWN_FUNCIONES = r"""
CREATE OR REPLACE FUNCTION public.upsert_heatmap_snapshot(p_symbol character varying, p_timestamp_utc timestamp with time zone, p_price_heatmap numeric, p_daily_change_pct numeric, p_market_cap numeric, p_stream_status character varying, p_raw_vector jsonb, p_raw_metadata jsonb) RETURNS void
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

CREATE OR REPLACE FUNCTION public.upsert_market_series(p_asset_symbol character varying, p_timestamp_utc timestamp with time zone, p_close numeric, p_volume numeric, p_rsi numeric, p_cci20 numeric, p_bbpower numeric, p_adx numeric, p_pivot_camarilla_r3 numeric, p_perf_w numeric, p_change_pct numeric, p_raw_payload jsonb DEFAULT NULL::jsonb, p_source_checksum character varying DEFAULT NULL::character varying) RETURNS void
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
"""

_DOWN_VIEWS = r"""
CREATE OR REPLACE VIEW public.vw_heatmap_enriched AS
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

CREATE OR REPLACE VIEW public.vw_market_live AS
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
"""

_DOWN = r"""
-- ============ downgrade: revierte F4.5/F4.5b ============
DROP INDEX public.uq_dim_asset_canonical_logical_key;

ALTER TABLE public.dim_asset
    DROP COLUMN logical_key,
    DROP COLUMN is_canonical,
    DROP COLUMN role,
    DROP COLUMN feed_delay_s;

DELETE FROM public.dim_asset WHERE symbol = 'TVC:DXY';

SELECT setval('public.dim_asset_asset_id_seq',
              (SELECT MAX(asset_id) FROM public.dim_asset));

ALTER TABLE public.dim_asset
    ADD COLUMN valid_from timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN valid_to timestamp with time zone DEFAULT 'infinity'::timestamp with time zone NOT NULL,
    ADD COLUMN current_version boolean DEFAULT true NOT NULL;

COMMENT ON TABLE public.dim_asset IS 'Activos financieros versionados (SCD Tipo 2). Compartida por heatmap y radar V4.';

DROP INDEX public.idx_dim_asset_active;
DROP INDEX public.idx_dim_asset_class;

CREATE INDEX idx_dim_asset_active
    ON public.dim_asset USING btree (is_active, current_version)
    WHERE (is_active AND current_version);

CREATE INDEX idx_dim_asset_class
    ON public.dim_asset USING btree (asset_class)
    WHERE (is_active AND current_version);

CREATE INDEX idx_dim_asset_symbol ON public.dim_asset USING btree (symbol);
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL_FUNCIONES)
        cur.execute(_DDL_VIEWS)
        cur.execute(_DDL_COLUMNAS)
        cur.execute(_DDL_REINDEX)
        cur.execute(_DDL_DROP_SCD2)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)
        cur.execute(_DOWN_FUNCIONES)
        cur.execute(_DOWN_VIEWS)