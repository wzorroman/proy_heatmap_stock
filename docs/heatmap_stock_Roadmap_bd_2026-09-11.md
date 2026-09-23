# Roadmap de Mejoras — Esquema `heatmap_stock` · Corte BD 2026-09-11

> **Sistema:** Base de Datos `heatmap_stock` (PostgreSQL 15+)
> **Fuentes de análisis:** `informes/tipos_datos_obtenidos_2026-09-11.md` y `informes/tipos_datos_obtenidos_2026-08-23.md` (cortes de `DATOS_LIVE`), `docs/SCHEMA_heatmap_stock.md`, `proy_heatmap/scripts/02_init_database.sql`, `config.py` del radar V4.
> **Fecha del informe:** 2026-09-11

---

## Contexto del corte

El nuevo informe de datos cambia **dos cosas grandes** respecto al corte anterior (2026-08-23):

1. **El calendario migró a V4 RAW (22 columnas)** — ya no es el esquema V3 normalizado de 16 columnas. Esto rompe casi todo el mapeo propuesto antes.
2. **La población LIVE quedó consolidada 110/110** y `CBOE-VX1` dejó de tener volumen nulo (detalle menor).

Las incompatibilidades de las **series de mercado** siguen casi idénticas; las del **calendario** son ahora más profundas. Este documento propone los ajustes concretos y constituye el roadmap de migración de la base de datos.

---

## 1. Cambios respecto al análisis anterior

| Punto | Corte 2026-08-23 | Corte 2026-09-11 | Impacto |
|---|---|---|---|
| Esquema calendario | V3 normalizado (16 cols) | **V4 RAW (22 cols)** | Rehacer mapeo completo |
| `importance` | 1=baja, 2=media, 3=alta | **−1/0/1/2/3** (sin dato/baja/media/alta/muy alta) | 4 valores útiles vs 3 en BD |
| `event_id` | slug (`us-nfp-20260905`) | **id int64 (403508)** | Tipo y semántica distintos |
| `actualRaw`/`previousRaw`/`forecastRaw` | TEXT (`"1.2M"`) | **float64 (1207500000000.0)** | Tipo distinto |
| Campos nuevos | — | `indicator`, `ticker`, `comment`, `period`, `referenceDate`, `source`, `source_url` | Sin destino en BD |
| Símbolos LIVE | 110 (31+80 en arranque) | 110 consolidados 7 días | OK |
| `CBOE-VX1` volumen | 100% NaN | **0% NaN** | Detalle |
| Bitcoin volume | decimal | decimal | Sigue |

---

## 2. Ajustes a `fact_market_series` (series)

Las incompatibilidades siguen siendo las mismas que en el corte anterior. Cambios requeridos:

```sql
-- 2.1 volume BIGINT rompe cripto fraccional (BINANCE/BITSTAMP)
ALTER TABLE fact_market_series
  ALTER COLUMN volume TYPE NUMERIC(20,8);

-- 2.2 close y perf_w al límite de precisión para cripto/FX
-- NUMERIC(18,6) trunca Perf.W (0.3868670615221213 → 0.3869)
ALTER TABLE fact_market_series
  ALTER COLUMN perf_w TYPE NUMERIC(12,8),
  ALTER COLUMN change_pct TYPE NUMERIC(12,8),
  ALTER COLUMN close TYPE NUMERIC(20,8);

-- 2.3 Añadir raw_payload y source_checksum (V4 aún NO los genera,
--     pero la tabla los declara; hay que decidir: generarlos en ETL o drop)
-- Opción A: rellenar en ETL con el JSON original del endpoint.
-- Opción B: eliminar las columnas hasta que el scraper las produzca.
-- Recomendación: A (generarlos en el ETL del nuevo servicio).
```

### `dim_asset` — falta modelar activos no-accionarios

Los 110 símbolos cubren **8 clases distintas** de activos:

```sql
-- Nuevo campo para distinguir el origen y la clase del activo
ALTER TABLE dim_asset
  ADD COLUMN source_discovered_by VARCHAR(50),        -- 'heatmap' | 'radar_v4' | ...
  ADD COLUMN source_category VARCHAR(50);             -- 'SENTIMIENTO', 'FOREX_CENTINELA', ...

-- Verificar que asset_class se puebla con la clase correcta para no-acciones:
-- 'equity' (default heatmap), 'etf', 'crypto', 'forex', 'future', 'yield', 'index', 'commodity'
-- V4 no la trae explícita → derivar en ETL desde config.py + exchange del símbolo.
```

### Índices adicionales para el patrón de consulta del radar

```sql
-- El PK compuesto ya cubre (asset_id, timestamp_utc), pero para consultas
-- por rango temporal sobre toda la tabla conviene:
CREATE INDEX IF NOT EXISTS idx_fact_market_series_ts_brin
  ON fact_market_series USING BRIN (timestamp_utc);
-- BRIN es muy eficiente en tablas append-only particionadas por timestamp.
```

---

## 3. Ajustes a `fact_economic_event` (calendario V4 RAW)

Aquí está el grueso del trabajo. El mapeo V4 RAW → esquema actual requiere cambios estructurales.

### 3.1 Mapeo directo V4 RAW → esquema actual

| CSV V4 RAW (22) | `fact_economic_event` actual | Acción |
|---|---|---|
| `id` (int64) | `event_id VARCHAR(100) PK` | ⚠️ cast o cambio de tipo |
| `title` | `title TEXT` | ✅ |
| `country` | `country VARCHAR(5) FK` | ✅ (poblar `dim_country`) |
| `indicator` | — | ➕ nueva columna |
| `ticker` (`ECONOMICS:JPFER`) | — | ➕ nueva columna |
| `comment` | — | ➕ nueva columna o `raw_payload` |
| `category` | `category VARCHAR(100)` | ✅ |
| `period` (`Aug`) | — | ➕ nueva columna |
| `referenceDate` | — | ➕ nueva columna |
| `source` | — | ➕ nueva columna |
| `source_url` | — | ➕ nueva columna |
| `actual` (float64) | `actual NUMERIC(18,6)` | ✅ |
| `previous` (float64) | `previous NUMERIC(18,6)` | ✅ |
| `forecast` (float64) | `forecast NUMERIC(18,6)` | ✅ |
| `actualRaw` (float64) | `actual_raw TEXT` | ❌ cambio de tipo |
| `previousRaw` (float64) | `previous_raw TEXT` | ❌ cambio de tipo |
| `forecastRaw` (float64) | `forecast_raw TEXT` | ❌ cambio de tipo |
| `currency` | `currency VARCHAR(5)` | ✅ |
| `unit` | `unit VARCHAR(20)` | ✅ |
| `importance` (−1..3) | `importance INTEGER (1..3)` | ❌ **CRÍTICO** |
| `date` (ISO ms) | `event_timestamp TIMESTAMPTZ` | ✅ |
| `timestamp_captura` | `first_seen_at`, `last_updated_at` | ✅ derivar |
| — | `raw_payload JSONB NOT NULL` | ❌ reconstruir en ETL |
| — | `payload_checksum VARCHAR(64)` | ❌ generar en ETL |

### 3.2 DDL propuesto

```sql
-- 3.2.1 importance: V4 usa -1..3 (5 estados), BD usa 1..3 (3 estados)
-- DECISIÓN: adoptar la escala de V4 (más rica) y ajustar vistas.
ALTER TABLE fact_economic_event
  ALTER COLUMN importance TYPE SMALLINT;
COMMENT ON COLUMN fact_economic_event.importance IS
  'Escala V4 RAW: -1=sin dato, 0=baja, 1=media, 2=alta, 3=muy alta. Filtro "alta/media" en vistas → importance >= 1';

-- 3.2.2 actualRaw/previousRaw/forecastRaw: V4 trae float64, no TEXT.
-- DECISIÓN: conservar ambos. La BD debe guardar el valor raw numérico Y su
-- representación formateada legible. V4 no trae el texto → derivar.
ALTER TABLE fact_economic_event
  ALTER COLUMN actual_raw TYPE NUMERIC(30,8) USING actual_raw::numeric,
  ALTER COLUMN previous_raw TYPE NUMERIC(30,8) USING previous_raw::numeric,
  ALTER COLUMN forecast_raw TYPE NUMERIC(30,8) USING forecast_raw::numeric;
-- Nota: los valores raw son ~1e12 (JPY) → NUMERIC(30,8) sobra.

-- 3.2.3 event_id: V4 trae int64. Opciones:
--  A. Cambiar PK a BIGINT (más limpio, idempotente con el id de TradingView)
--  B. Mantener VARCHAR y castear 'tv_403508' en ETL
-- DECISIÓN recomendada: A, porque el id de TradingView ES estable y único.
ALTER TABLE fact_economic_event
  ALTER COLUMN event_id TYPE BIGINT USING NULLIF(event_id,'')::bigint;
-- Si se prefiere prefijo por si algún día se mezclan fuentes:
-- ALTER COLUMN event_id TYPE VARCHAR(50) y en ETL: 'tv_' || id::text

-- 3.2.4 Nuevas columnas para campos V4 sin destino
ALTER TABLE fact_economic_event
  ADD COLUMN indicator       TEXT,
  ADD COLUMN event_ticker    VARCHAR(50),      -- 'ECONOMICS:JPFER'
  ADD COLUMN period          VARCHAR(20),      -- 'Aug'
  ADD COLUMN reference_date  TIMESTAMPTZ,      -- date de referencia del dato
  ADD COLUMN source          TEXT,             -- 'Ministry of Finance'
  ADD COLUMN source_url      TEXT,
  ADD COLUMN comment         TEXT;

-- 3.2.5 captured_at separado de first_seen/last_updated
-- V4 solo trae 'timestamp_captura'; first_seen y last_updated se derivan
-- en ETL: first_seen = MIN(captured_at) por event_id; last_updated = MAX.
ALTER TABLE fact_economic_event
  ADD COLUMN captured_at TIMESTAMPTZ;
-- first_seen_at y last_updated_at se mantienen como columnas derivadas.

-- 3.2.6 raw_payload NOT NULL: V4 no lo produce. Se reconstruye en ETL
-- con el JSON original de la respuesta. Mantener NOT NULL.
-- 3.2.7 payload_checksum: hash del raw_payload, generado en ETL.
```

### 3.3 Ajuste de índices y vistas

```sql
-- El índice actual WHERE importance <= 2 ya no aplica con la nueva escala.
-- Reemplazar por:
DROP INDEX IF EXISTS idx_fact_economic_event_importance;
CREATE INDEX idx_fact_economic_event_importance
  ON fact_economic_event (importance)
  WHERE importance >= 1;   -- media + alta + muy alta

-- Índice útil ahora que viene ticker de la API
CREATE INDEX idx_fact_economic_event_ticker
  ON fact_economic_event (event_ticker);

-- Índice para el patrón "eventos por país + rango temporal"
CREATE INDEX idx_fact_economic_event_country_ts
  ON fact_economic_event (country, event_timestamp DESC);
```

Vista `vw_heatmap_event_impact` — actualizar el filtro:

```sql
-- ANTES: WHERE importance <= 2   (con escala 1=alta)
-- AHORA: WHERE importance >= 1   (con escala 0=baja … 3=muy alta)
```

### 3.4 Poblar `dim_country` (obligatorio antes del primer INSERT)

```sql
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
```

---

## 4. Series de mercado — ajustes al ETL (sin cambios de esquema)

Además del DDL de §2, el ETL debe:

1. **Convertir epoch → TIMESTAMPTZ al insertar:**

```python
timestamp_utc = datetime.fromtimestamp(row['timestamp_utc'], tz=timezone.utc)
```

2. **Derivar `asset_class` desde `config.py`** (el CSV no la trae):

| Prefijo del exchange | asset_class |
|---|---|
| `BINANCE:*`, `BITSTAMP:*` | `crypto` |
| `OANDA:*`, `FX_IDC:*`, `SAXO:*` | `forex` / `commodity` |
| `CME*:*`, `CBOT:*`, `NYMEX:*`, `ICEUS:*`, `CBOE:*` | `future` |
| `TVC:US02Y`, `TVC:US10Y` | `yield` |
| `TVC:VIX`, `NASDAQ:NDX` | `index` |
| `AMEX:*`, `NASDAQ:*`, `NYSE:*` | `etf` (si termina en ETF/SPY/VOO…) o `equity` |

3. **Descartar `fecha_iso`** (redundante, se recalcula desde `timestamp_utc`).
4. **Conservar `simbolo`** como clave natural → `dim_asset.symbol`.

---

## 5. Incompatibilidades que NO requieren cambio de esquema

| Aspecto | Estado | Nota |
|---|---|---|
| Clave natural `symbol` (`{EXCHANGE}:{TICKER}`) | ✅ idéntica | `dim_asset` compartible |
| Particionamiento mensual | ✅ coincide | V4 rota a `{SYMBOL}_{YYYYMM}` |
| Cadencia 180 s / 2.108 filas/símbolo/semana | ✅ soportada | ~232k filas LIVE + ~1,95M históricos |
| `audit_sync_run` | ✅ genérica | `script_name` separa los dos pipelines |
| `sync_checkpoint` | ✅ genérica | Sirve para ambos |
| `raw_vector` / `raw_metadata` (heatmap) | ✅ | Intacto, es del otro scraper |
| `raw_payload` de calendario | ✅ | Reconstruible desde V4 RAW |

---

## 6. Orden de ejecución recomendado

```sql
-- FASE 1 — Ajustes de tipos (no destructivos si hay backup)
BEGIN;
  -- Series
  ALTER TABLE fact_market_series
    ALTER COLUMN volume      TYPE NUMERIC(20,8),
    ALTER COLUMN close       TYPE NUMERIC(20,8),
    ALTER COLUMN perf_w      TYPE NUMERIC(12,8),
    ALTER COLUMN change_pct  TYPE NUMERIC(12,8);

  -- Calendario
  ALTER TABLE fact_economic_event
    ALTER COLUMN importance  TYPE SMALLINT,
    ALTER COLUMN event_id    TYPE BIGINT USING NULLIF(event_id,'')::bigint,
    ALTER COLUMN actual_raw  TYPE NUMERIC(30,8) USING actual_raw::numeric,
    ALTER COLUMN previous_raw TYPE NUMERIC(30,8) USING previous_raw::numeric,
    ALTER COLUMN forecast_raw TYPE NUMERIC(30,8) USING forecast_raw::numeric;
COMMIT;

-- FASE 2 — Columnas nuevas
BEGIN;
  ALTER TABLE dim_asset
    ADD COLUMN source_discovered_by VARCHAR(50),
    ADD COLUMN source_category VARCHAR(50);

  ALTER TABLE fact_economic_event
    ADD COLUMN indicator      TEXT,
    ADD COLUMN event_ticker   VARCHAR(50),
    ADD COLUMN period         VARCHAR(20),
    ADD COLUMN reference_date TIMESTAMPTZ,
    ADD COLUMN source         TEXT,
    ADD COLUMN source_url     TEXT,
    ADD COLUMN comment        TEXT,
    ADD COLUMN captured_at    TIMESTAMPTZ;
COMMIT;

-- FASE 3 — Índices + dim_country + vistas
BEGIN;
  DROP INDEX IF EXISTS idx_fact_economic_event_importance;
  CREATE INDEX idx_fact_economic_event_importance
    ON fact_economic_event (importance) WHERE importance >= 1;
  CREATE INDEX idx_fact_economic_event_ticker
    ON fact_economic_event (event_ticker);
  CREATE INDEX idx_fact_economic_event_country_ts
    ON fact_economic_event (country, event_timestamp DESC);
  CREATE INDEX idx_fact_market_series_ts_brin
    ON fact_market_series USING BRIN (timestamp_utc);

  INSERT INTO dim_country VALUES ( ... );  -- §3.4
COMMIT;

-- FASE 4 — Recrear vw_heatmap_event_impact con el filtro importance >= 1
```

---

## 7. DDL Final — Script único de migración

Con las decisiones confirmadas, este es el script completo. Pensado para ejecutarse **una sola vez, en transacción**, sobre una BD vacía o con datos migrables. Si hay datos previos en `fact_economic_event`, las cláusulas `USING` los castean de forma segura.

> **Archivo:** `migracion_v4_20260911.sql`

```sql
-- ============================================================================
-- Migración de esquema heatmap_stock para absorber el scraper V4
-- (series de mercado + calendario económico V4 RAW)
-- Fecha: 2026-09-11
-- Ejecutar como superusuario o dueño del schema public.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- FASE 1 — Verificación previa (falla ruidosamente si algo no cuadra)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- dim_country debe existir y estar vacía o poblada; no validamos aquí.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name='fact_economic_event'
    ) THEN
        RAISE EXCEPTION 'Falta la tabla fact_economic_event';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name='fact_market_series'
    ) THEN
        RAISE EXCEPTION 'Falta la tabla fact_market_series';
    END IF;
END$$;

-- ----------------------------------------------------------------------------
-- FASE 2 — fact_market_series: tipos alineados con V4
-- ----------------------------------------------------------------------------
ALTER TABLE fact_market_series
    ALTER COLUMN volume     TYPE NUMERIC(20,8) USING volume::numeric,
    ALTER COLUMN close      TYPE NUMERIC(20,8) USING close::numeric,
    ALTER COLUMN perf_w     TYPE NUMERIC(12,8) USING perf_w::numeric,
    ALTER COLUMN change_pct TYPE NUMERIC(12,8) USING change_pct::numeric;

COMMENT ON COLUMN fact_market_series.volume IS
    'Volumen. NUMERIC(20,8) porque cripto (BINANCE/BITSTAMP) llega fraccional; acciones/futuros con enteros caben igual.';
COMMENT ON COLUMN fact_market_series.perf_w IS
    'Performance semanal (%). 8 decimales preservan la serialización IEEE-754 del endpoint.';

-- raw_payload y source_checksum ya existen y son NULLABLE.
-- El ETL del radar los poblará: raw_payload con el JSON del endpoint,
-- source_checksum con SHA-256 del row canónico.
COMMENT ON COLUMN fact_market_series.raw_payload IS
    'JSON crudo de la respuesta del endpoint. NULL si el ETL no lo recupera.';
COMMENT ON COLUMN fact_market_series.source_checksum IS
    'SHA-256 hex del row canónico para detección de re-ingestas.';

-- ----------------------------------------------------------------------------
-- FASE 3 — dim_asset: trazabilidad multi-servicio
-- ----------------------------------------------------------------------------
ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS source_discovered_by VARCHAR(50),
    ADD COLUMN IF NOT EXISTS source_category      VARCHAR(50);

COMMENT ON COLUMN dim_asset.source_discovered_by IS
    'Scraper que dio de alta el símbolo: heatmap | radar_v4 | ...';
COMMENT ON COLUMN dim_asset.source_category IS
    'Categoría del config.py del radar (ej. SEMICONDUCTORES). NULL si no aplica.';
COMMENT ON COLUMN dim_asset.asset_class IS
    'Clase del activo: equity | etf | crypto | forex | future | yield | index | commodity.';

-- ----------------------------------------------------------------------------
-- FASE 4 — fact_economic_event: cambio estructural al esquema V4 RAW
-- ----------------------------------------------------------------------------

-- 4.1 event_id → BIGINT (usa el id de TradingView tal cual)
ALTER TABLE fact_economic_event
    ALTER COLUMN event_id TYPE BIGINT
    USING NULLIF(regexp_replace(event_id, '\D', '', 'g'), '')::bigint;

COMMENT ON COLUMN fact_economic_event.event_id IS
    'id int64 de la API economic-calendar.tradingview.com. Clave estable.';

-- 4.2 importance → SMALLINT con escala V4 (-1..3)
ALTER TABLE fact_economic_event
    ALTER COLUMN importance TYPE SMALLINT
    USING importance::smallint;

COMMENT ON COLUMN fact_economic_event.importance IS
    'Escala V4 RAW: -1=sin dato, 0=baja, 1=media, 2=alta, 3=muy alta. Filtro "relevante" → importance BETWEEN 1 AND 3.';

-- 4.3 actual_raw / previous_raw / forecast_raw → NUMERIC (V4 trae float64)
ALTER TABLE fact_economic_event
    ALTER COLUMN actual_raw   TYPE NUMERIC(30,8)
        USING NULLIF(actual_raw,   '')::numeric,
    ALTER COLUMN previous_raw TYPE NUMERIC(30,8)
        USING NULLIF(previous_raw, '')::numeric,
    ALTER COLUMN forecast_raw TYPE NUMERIC(30,8)
        USING NULLIF(forecast_raw, '')::numeric;

COMMENT ON COLUMN fact_economic_event.actual_raw IS
    'Valor "raw" del endpoint (unidad base, ej. 1207500000000.0).';
COMMENT ON COLUMN fact_economic_event.previous_raw IS
    'Valor previo en unidad base.';
COMMENT ON COLUMN fact_economic_event.forecast_raw IS
    'Valor forecast en unidad base.';

-- 4.4 Columnas display (texto formateado por el ETL)
ALTER TABLE fact_economic_event
    ADD COLUMN IF NOT EXISTS actual_display   TEXT,
    ADD COLUMN IF NOT EXISTS previous_display TEXT,
    ADD COLUMN IF NOT EXISTS forecast_display TEXT;

COMMENT ON COLUMN fact_economic_event.actual_display IS
    'Representación legible (ej. "$1.2B"). Formateada en ETL.';

-- 4.5 Columnas nuevas del esquema V4 RAW
ALTER TABLE fact_economic_event
    ADD COLUMN IF NOT EXISTS indicator      TEXT,
    ADD COLUMN IF NOT EXISTS event_ticker   VARCHAR(50),
    ADD COLUMN IF NOT EXISTS period         VARCHAR(20),
    ADD COLUMN IF NOT EXISTS reference_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS source         TEXT,
    ADD COLUMN IF NOT EXISTS source_url     TEXT,
    ADD COLUMN IF NOT EXISTS comment        TEXT,
    ADD COLUMN IF NOT EXISTS captured_at    TIMESTAMPTZ;

COMMENT ON COLUMN fact_economic_event.indicator      IS 'Nombre interno del indicador (V4 indicator).';
COMMENT ON COLUMN fact_economic_event.event_ticker   IS 'Ticker TradingView (ej. ECONOMICS:JPFER).';
COMMENT ON COLUMN fact_economic_event.period         IS 'Periodo de referencia (ej. Aug).';
COMMENT ON COLUMN fact_economic_event.reference_date IS 'Fecha de referencia del dato (V4 referenceDate).';
COMMENT ON COLUMN fact_economic_event.source         IS 'Institución emisora (ej. Ministry of Finance).';
COMMENT ON COLUMN fact_economic_event.source_url     IS 'URL de la fuente original.';
COMMENT ON COLUMN fact_economic_event.comment        IS 'Descripción de la fuente (V4 comment).';
COMMENT ON COLUMN fact_economic_event.captured_at    IS 'Momento de ingesta reportado por el scraper (V4 timestamp_captura).';

-- 4.6 first_seen_at / last_updated_at se derivan en ETL; siguen siendo NOT NULL.
--     captured_at queda como la marca puntual de cada snapshot.
-- 4.7 raw_payload y payload_checksum se pueblan en ETL (reconstruidos del JSON V4).
COMMENT ON COLUMN fact_economic_event.raw_payload IS
    'JSON crudo de la API. Reconstruido por el ETL del scraper calendario V4.';
COMMENT ON COLUMN fact_economic_event.payload_checksum IS
    'SHA-256 hex del raw_payload.';

-- ----------------------------------------------------------------------------
-- FASE 5 — Índices: reemplazar el filtro de importance y añadir los nuevos
-- ----------------------------------------------------------------------------

-- El índice anterior filtraba WHERE importance <= 2 (escala 1=alta).
-- Con la escala V4 el equivalente "media o superior" es importance >= 1.
DROP INDEX IF EXISTS idx_fact_economic_event_importance;
CREATE INDEX idx_fact_economic_event_importance
    ON fact_economic_event (importance)
    WHERE importance BETWEEN 1 AND 3;

CREATE INDEX IF NOT EXISTS idx_fact_economic_event_ticker
    ON fact_economic_event (event_ticker)
    WHERE event_ticker IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fact_economic_event_country_ts
    ON fact_economic_event (country, event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_fact_economic_event_captured
    ON fact_economic_event (captured_at DESC);

-- BRIN sobre timestamp_utc en la tabla particionada de series:
-- muy eficiente para tablas append-only con orden temporal natural.
CREATE INDEX IF NOT EXISTS idx_fact_market_series_ts_brin
    ON fact_market_series USING BRIN (timestamp_utc);

-- ----------------------------------------------------------------------------
-- FASE 6 — dim_country: seed de los 11 países del config.py
-- ----------------------------------------------------------------------------
INSERT INTO dim_country (country_code, country_name, region, currency_code)
VALUES
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
    ('AU','Australia','Oceania','AUD')
ON CONFLICT (country_code) DO UPDATE
    SET country_name  = EXCLUDED.country_name,
        region        = EXCLUDED.region,
        currency_code = EXCLUDED.currency_code;

-- ----------------------------------------------------------------------------
-- FASE 7 — Vistas: adaptar filtros de importance y aislar el heatmap
-- ----------------------------------------------------------------------------

-- 7.1 vw_heatmap_event_impact: nueva escala de importance
DROP VIEW IF EXISTS vw_heatmap_event_impact;
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
    ON e.currency = 'USD'                                  -- eventos USD afectan al heatmap US
   AND e.importance BETWEEN 1 AND 3                        -- media / alta / muy alta
   AND e.event_timestamp BETWEEN h.timestamp_utc - INTERVAL '6 hours'
                             AND h.timestamp_utc + INTERVAL '6 hours';

COMMENT ON VIEW vw_heatmap_event_impact IS
    'Cruce heatmap × eventos USD de importancia media+ en ventana ±6 h.';

-- 7.2 vw_heatmap_enriched: restringir a activos tipo equity/etf
--     (el radar V4 puebla otras clases que contaminarían el heatmap).
DROP VIEW IF EXISTS vw_heatmap_enriched;
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
WHERE a.asset_class IN ('equity', 'etf')   -- excluye crypto/forex/future/yield/index
  AND a.is_active = TRUE
  AND a.current_version = TRUE;

COMMENT ON VIEW vw_heatmap_enriched IS
    'Heatmap enriquecido. Restringido a equity/etf para no mezclar activos del radar V4.';

-- 7.3 vw_market_live: añadir filtro de clase y exponer categoría del radar
DROP VIEW IF EXISTS vw_market_live;
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

COMMENT ON VIEW vw_market_live IS
    'Series técnicas del radar V4 en ventana de 7 días, con señal derivada.';

-- ----------------------------------------------------------------------------
-- FASE 8 — Función upsert alineada con los nuevos tipos
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION upsert_market_series(
    p_asset_symbol         VARCHAR,
    p_timestamp_utc        TIMESTAMPTZ,
    p_close                NUMERIC,
    p_volume               NUMERIC,
    p_rsi                  NUMERIC,
    p_cci20                NUMERIC,
    p_bbpower              NUMERIC,
    p_adx                  NUMERIC,
    p_pivot_camarilla_r3   NUMERIC,
    p_perf_w               NUMERIC,
    p_change_pct           NUMERIC,
    p_raw_payload          JSONB DEFAULT NULL,
    p_source_checksum      VARCHAR DEFAULT NULL
) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_asset_id INTEGER;
BEGIN
    SELECT asset_id INTO v_asset_id
    FROM dim_asset
    WHERE symbol = p_asset_symbol
      AND is_active AND current_version
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

COMMENT ON FUNCTION upsert_market_series IS
    'UPSERT idempotente de un snapshot técnico. Requiere el activo ya presente en dim_asset.';

-- ----------------------------------------------------------------------------
-- FASE 9 — Actualizar sync_checkpoint.last_event_id a BIGINT
-- ----------------------------------------------------------------------------
ALTER TABLE sync_checkpoint
    ALTER COLUMN last_event_id TYPE BIGINT
    USING NULLIF(last_event_id, '')::bigint;

COMMIT;

-- ============================================================================
-- FIN
-- ============================================================================
```

---

## 8. Post-migración — checklist de validación

```sql
-- 1. Tipos alineados
\d+ fact_market_series
\d+ fact_economic_event

-- 2. Índices nuevos presentes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('fact_market_series','fact_economic_event','dim_asset')
ORDER BY tablename, indexname;

-- 3. dim_country poblada (11 filas)
SELECT COUNT(*) FROM dim_country;

-- 4. Vistas recompilables
SELECT 'vw_market_live'           AS v, COUNT(*) FROM vw_market_live
UNION ALL
SELECT 'vw_heatmap_enriched',            COUNT(*) FROM vw_heatmap_enriched
UNION ALL
SELECT 'vw_heatmap_event_impact',        COUNT(*) FROM vw_heatmap_event_impact;

-- 5. Función registrada con nueva firma
\df+ upsert_market_series
```

---

## 9. Pseudocódigo del ETL que debe acompañar esta migración

```python
# --- ETL series (radar V4) ---
def row_to_fact_market_series(row, asset_id):
    return {
        "asset_id":            asset_id,
        "timestamp_utc":       datetime.fromtimestamp(row["timestamp_utc"], tz=timezone.utc),
        "close":               row["close"],
        "volume":              row["volume"],        # NUMERIC, acepta fraccional
        "rsi":                 row["RSI"],
        "cci20":               row["CCI20"],
        "bbpower":             row["BBPower"],
        "adx":                 row["ADX"],
        "pivot_camarilla_r3":  row["Pivot.M.Camarilla.R3"],
        "perf_w":              row["Perf.W"],
        "change_pct":          row["change"],
        "raw_payload":         json.dumps(raw_endpoint_json),   # opcional
        "source_checksum":     sha256(row_canonical).hexdigest(),
    }

# --- ETL calendario (V4 RAW) ---
def row_to_fact_economic_event(row):
    return {
        "event_id":         int(row["id"]),
        "title":            row["title"],
        "country":          row["country"],
        "indicator":        row["indicator"],
        "event_ticker":     row["ticker"],
        "comment":          row["comment"],
        "category":         row["category"],
        "period":           row["period"],
        "reference_date":   parse_iso(row["referenceDate"]),
        "source":           row["source"],
        "source_url":       row["source_url"],
        "actual":           row["actual"],
        "previous":         row["previous"],
        "forecast":         row["forecast"],
        "actual_raw":       row["actualRaw"],       # NUMERIC
        "previous_raw":     row["previousRaw"],
        "forecast_raw":     row["forecastRaw"],
        "actual_display":   format_value(row["actual"],   row["unit"]),
        "previous_display": format_value(row["previous"], row["unit"]),
        "forecast_display": format_value(row["forecast"], row["unit"]),
        "currency":         row["currency"],
        "unit":             row["unit"],
        "importance":       int(row["importance"]),  # -1..3 directo
        "event_timestamp":  parse_iso(row["date"]),
        "captured_at":      parse_iso(row["timestamp_captura"]),
        "first_seen_at":    now_utc,                 # ON CONFLICT mantiene el mínimo
        "last_updated_at":  now_utc,
        "raw_payload":      json.dumps(row),         # reconstruido
        "payload_checksum": sha256(json_canonical(row)).hexdigest(),
    }

# Upsert con política first_seen inmutable:
#   INSERT ... ON CONFLICT (event_id) DO UPDATE SET
#       last_updated_at = EXCLUDED.last_updated_at,
#       ...campos mutables...,
#       first_seen_at   = fact_economic_event.first_seen_at  -- preservar
```

---

## 10. Notas operativas

1. **Fase 7.2 `vw_heatmap_enriched`**: le añadí `asset_class IN ('equity','etf')`. Sin ese filtro, los 110 símbolos del radar (que incluyen crypto, FX, futuros, yields) contaminarían el heatmap original. Si prefieres no tocar la vista y filtrar en la app, se revierte.

2. **`vw_heatmap_event_impact`**: cambié el JOIN a `currency = 'USD'` en lugar de la subquery por `dim_country`. Es más directo y no depende de que el evento tenga país mapeado. Si quieres mantener el filtro por país, se cambia en una línea.

3. **Histórico calendario 2026-08 mixto**: como acordamos "iniciar con datos nuevos", el ETL debe ignorar los ficheros V3 legacy (`2026-03/04/05` y el mixto `2026-08`). Conviene moverlos a `DATOS_LIVE/_legacy/` para que el unificador no los lea por accidente.

4. **`fact_economic_event.raw_payload` es NOT NULL** en el esquema original. Como el ETL lo reconstruye desde el JSON de la API, se puede mantener así. Si en algún momento el scraper no guarda el JSON, habría que relajar a NULL.

5. **BRIN en `fact_market_series`**: en una tabla particionada, PostgreSQL 15 **no permite** crear el índice BRIN sobre el padre cuando hay particiones hijas — hay que crearlo en cada partición. Si al ejecutar la Fase 5 da error `cannot create index on partitioned table`, cambia esa línea por:

```sql
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT inhrelid::regclass AS child
    FROM pg_inherits
    WHERE inhparent = 'fact_market_series'::regclass
  LOOP
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING BRIN (timestamp_utc)',
                   'idx_' || r.child::text || '_ts_brin', r.child);
  END LOOP;
END$$;
```

---

## 11. DDL completo — Base de datos `heatmap_stock` desde cero

Script único de inicialización. **Reemplaza al antiguo `02_init_database.sql`**; ya incorpora todos los ajustes del scraper V4 (series + calendario) y las decisiones confirmadas.

> **Archivo:** `02_init_database.sql` (versión 2026-09-11)

```sql
-- ============================================================================
-- Inicialización completa de heatmap_stock
-- Compatible con: heatmap scraper + radar V4 + calendario económico V4 RAW
-- Versión: 2026-09-11
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
```

---

## 12. Orden de arranque de los servicios

Con la BD vacía, el orden importa porque `fact_market_series` exige que el activo exista en `dim_asset` (FK lógica vía `upsert_market_series`):

1. **Ejecutar `02_init_database.sql`** — crea todo el esquema vacío + seed de países.
2. **Ejecutar `seed_dim_asset.py`** (ver §13) — puebla `dim_asset` **por defecto** con el catálogo base del heatmap desde `docs/dim_asset_202609112246.csv` (**1.005 símbolos**, ver §14) y lo fusiona con los 110 símbolos del `config.py` del radar. Debe correr **antes** de que arranque cualquier scraper. Sin esto, el primer ciclo del radar falla con `Activo no registrado en dim_asset`.
3. **Arrancar `scrapper_heatmap_v1.py`** — el heatmap auto-crea activos (`get_or_create_asset`) para los que falten, pero ya no debería hacerlo: la seed §14 cubre el universo completo exportado del heatmap. Así se evita la contención del primer ciclo.
4. **Arrancar `scraper_live_tradingview_v4.py`** — el radar.
5. **Arrancar `calendario_tradingview_live_v4.py`** — el calendario.

---

## 13. Script de seed para `dim_asset`

Esbozo para adaptarlo. Debe correr antes que el radar y **cargar primero el CSV por defecto** (`docs/dim_asset_202609112246.csv`, ver §14) y después derivar `asset_class` desde `config.py`. Los símbolos **no se incrustan** en este documento: el CSV es la fuente canónica y se lee con `COPY`/`csv.DictReader`; aquí solo se muestra el esquema del script.

```python
# seed_dim_asset.py
import psycopg2, json, hashlib, csv
from config import CONFIG_ACTIVOS
from scraper_live_tradingview_v4 import BASE_DIR  # opcional

DSN = "dbname=heatmap_stock user=... password=... host=... port=5432"

CSV_DEFAULT = "docs/dim_asset_202609112246.csv"   # catálogo base del heatmap (1.005 símbolos)

# Derivación de asset_class por prefijo del exchange
CLASS_MAP = {
    'BINANCE':  'crypto',
    'BITSTAMP': 'crypto',
    'OANDA':    'forex',
    'FX_IDC':   'forex',
    'SAXO':     'commodity',
    'CME':      'future',
    'CME_MINI': 'future',
    'CBOT':     'future',
    'NYMEX':    'future',
    'ICEUS':    'future',
    'CBOE':     'future',
    'TVC':      'index',      # se sobreescribe abajo para US02Y/US10Y
    'AMEX':     'etf',        # puede ser equity según ticker
    'NASDAQ':   'equity',
    'NYSE':     'equity',
}

def classify(symbol, category):
    ex, tk = symbol.split(':', 1)
    if ex == 'TVC' and tk.startswith('US') and tk.endswith('Y'):
        return 'yield'
    if ex == 'TVC' and tk == 'VIX':
        return 'index'
    if ex == 'TVC' and tk == 'SILVER':
        return 'commodity'
    if ex in ('NASDAQ', 'AMEX') and tk in ('QQQ','SPY','VOO','VGT','SHY','IEI','IEF','TLT','SLV','USO','XLE','XOP','UUP'):
        return 'etf'
    return CLASS_MAP.get(ex, 'equity')

def all_symbols():
    seen = set()
    for cat, data in CONFIG_ACTIVOS.items():
        for entry in data.values():
            for key in ('primario', 'respaldo'):
                s = entry.get(key)
                if s and s not in seen:
                    seen.add(s)
                    yield s, cat

def upsert_asset(cur, symbol, ticker, exchange, asset_class, source, category,
                 sector=None, company_name=None):
    cur.execute("""
        INSERT INTO dim_asset
            (symbol, ticker, exchange, asset_class, sector, company_name,
             source_discovered_by, source_category)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET
            exchange            = EXCLUDED.exchange,
            asset_class         = COALESCE(dim_asset.asset_class, EXCLUDED.asset_class),
            sector              = COALESCE(dim_asset.sector, EXCLUDED.sector),
            company_name        = COALESCE(dim_asset.company_name, EXCLUDED.company_name),
            source_category     = COALESCE(EXCLUDED.source_category, dim_asset.source_category),
            updated_at          = CURRENT_TIMESTAMP;
    """, (symbol, ticker, exchange, asset_class, sector, company_name, source, category))


with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
    # 1) Seed por defecto: catálogo completo del heatmap desde el CSV (no incrustado).
    with open(CSV_DEFAULT, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            symbol   = r['symbol']                        # 'NASDAQ:NVDA'
            exchange, ticker = symbol.split(':', 1)
            upsert_asset(
                cur, symbol, ticker, exchange,
                asset_class  = 'equity',                  # son acciones/ADR; ver §14 caveats
                source       = 'heatmap',
                category     = None,
                sector       = r['sector'] or None,
                company_name = r['company_name'] or None,
            )

    # 2) Merge con el radar: derivación de asset_class por configuración.
    for symbol, category in all_symbols():
        ex, tk = symbol.split(':', 1)
        upsert_asset(
            cur, symbol, tk, ex,
            asset_class = classify(symbol, category),
            source      = 'radar_v4',
            category    = category,
        )

    conn.commit()
    print("dim_asset sembrada: CSV(1.005) + radar(110, OK en solapamientos)")
```

---

## 14. Seed por defecto — `docs/dim_asset_202609112246.csv`

Catálogo base para cargar la BD por defecto. Es el export completo de `dim_asset` del heatmap con corte **2026-09-11 22:46** (**1.005 símbolos**). Los símbolos **no se incrustan** en este documento: el CSV es la fuente canónica y el seed lo lee directo (ver §13). Es la "información básica" que queremos en la BD en el arranque.

### 14.1 Caracterización del CSV

| Métrica | Valor |
|---|---|
| Filas | 1.005, todas `is_active = true` y `current_version = true` |
| Exchanges | `NASDAQ` 132 · `NYSE` 413 · `OTC` 459 · `AMEX` 1 |
| `asset_class` (CSV) | `common` 606 · `preferred` 127 · `unit` 4 · vacío 268 |
| Sectores (FT) | 20 (`Finance` 310 · `Electronic Technology` 104 · `Health Technology` 76 · `Producer Manufacturing` 69 · `Technology Services` 65 · resto 381) |
| `company_name` | = ticker (placeholder, no descriptivo) |
| `logo_id` | 0 filas con dato |
| `sector_es` | vacío |

> Los 459 tickers `OTC:*` (TCEHY, BABA, ASML…) son ADR/acciones foráneas del universo original del heatmap; `NASDAQ`/`NYSE`/`AMEX` incluyen además listados extranjeros (ASML, BABA en NYSE, etc.).

### 14.2 Mapeo CSV → `dim_asset`

| Columna CSV | Columna `dim_asset` | Acción |
|---|---|---|
| `symbol` | `symbol` (clave natural) | ✅ directo (`NASDAQ:NVDA`) |
| `ticker`, `exchange` | `ticker`, `exchange` | derivar con `split_part(symbol,':',1/2)` |
| `asset_class` | ⚠️ **no es la taxonomía nueva** | es *clase de acción* (`common/preferred/unit`), choca con `equity/etf/crypto/...`. → mapear a nueva columna `share_class VARCHAR(20)`; `asset_class = 'equity'` para el CSV |
| `sector` | `sector` | ✅ taxonomía FT Industry (20 sectores) |
| `company_name` | `company_name` | guardar como placeholder |
| `sector_es`, `logo_id` | `sector_es`, `logo_id` | ❌ vacíos en CSV → no cargar |
| — | `source_discovered_by` | fijar `'heatmap'` |
| — | `source_category` | ausente → NULL |
| `valid_from`/`created_at`/`updated_at` | idem | ✅ preservar con COPY para no perder el histórico de alta del heatmap |

Caveat ─ **colisión de nombres `asset_class`**: conviene añadir `share_class` (o `share_type`) para que la taxonomía del roadmap (equity|crypto|forex|…) quede sin ambigüedad:

```sql
ALTER TABLE dim_asset ADD COLUMN IF NOT EXISTS share_class VARCHAR(20); -- common | preferred | unit
```

### 14.3 Análisis — qué más se puede cargar por defecto

Además del catálogo de símbolos, hay otras cargas *default* baratas y con datos ya disponibles hoy:

| Dato | Fuente disponible hoy | Acción recomendada | DDL/script |
|---|---|---|---|
| `dim_asset` catálogo heatmap (1.005) | `docs/dim_asset_202609112246.csv` | ✅ **hacer ahora** (objetivo de esta sección) | §13 vía CSV |
| `dim_asset` catálogo radar (110) | `config.py` del radar | ✅ ya contemplado | §13 vía `CONFIG_ACTIVOS` |
| `dim_country` (11 países) | `config.py` | ✅ ya en seed | `02_init_database.sql` §8 |
| `dim_time` (2026–2027) | generación con `generate_series` | ➕ barato y puro SQL, habilita análisis temporal | script `seed_dim_time.py` o bloque CTE en init |
| `share_class` (common/preferred/unit) | CSV col. `asset_class` | ➕ nueva columna en `dim_asset`, poblada en el seed | `ALTER … ADD COLUMN` (§14.2) |
| `dim_country` extendido (ADR OTC) | países de domicilio inferibles del CSV (BABA→CN, LYG→GB, …) | ⚠️ requiere tabla de mapeo ADR→país; no existe hoy → **deferir** hasta tener datos del calendario V4 | — |
| Ctvo. de eventos histórico | ficheros `DATOS_LIVE` legacy | ⚠️ post-migración y aparte (§10 not. 3) | `calendario_tradingview_live_v4.py` |
| `dim_sector` normalizado (20 sectores FT) | CSV col. `sector` | 🔜 futuro: sin FK hoy, solo denormalizado | — |

**Recomendación de arranque** ─ cargar por defecto en este orden: (1) `dim_country` (11), (2) `dim_asset` CSV 1.005 + radar 110 (_seed_dim_asset_, §13), (3) `dim_time` 2026–2027, (4) `share_class` poblada desde el CSV. Lo demás (ADR→país, histórico de eventos) espera a los primeros ciclos V4.

---

## 15. Decisiones de diseño (resumen ejecutivo)

1. **`dim_asset.symbol` es UNIQUE global.** El heatmap y el radar comparten los activos coincidentes (NVDA, AAPL, etc.). Como `source_discovered_by` se actualiza con `ON CONFLICT DO UPDATE`, el primer scraper que llegue gana el crédito. Si quieres preservar ambos, cambia a un campo `sources_discovered JSONB` (array de strings).

2. **`vw_heatmap_enriched` filtra `asset_class IN ('equity','etf')`** — decisión de diseño para que el radar V4 (que puebla también crypto, FX, futuros) no contamine el heatmap original. Si prefieres filtrar en la app y no en la vista, quita el `WHERE`.

3. **`fact_economic_event` no está particionada** — el volumen es bajo (~500 filas/año). El particionado mensual solo vale la pena en las tablas de hechos técnicos.

---

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-09-11 | Creación del roadmap de migración basado en el corte de datos `2026-09-11`: calendario V4 RAW (22 cols), importancia −1..3, `event_id` int64, `actualRaw` float64, `dim_asset` multi-clase, DDL de migración `migracion_v4_20260911.sql`, rewrite de `02_init_database.sql`, seed de `dim_country` (11 países), orden de arranque y esbozo de `seed_dim_asset.py`. |
| 2026-09-12 | Seed por defecto del catálogo `docs/dim_asset_202609112246.csv` (1.005 símbolos del heatmap) incorporado al `seed_dim_asset.py` (§13, sin incrustarlos: el CSV es la fuente canónica); nuevo §14 con caracterización del CSV, mapeo a `dim_asset` y análisis de qué más se puede cargar por defecto (`dim_time`, `share_class`, `dim_country` extendido, etc.). Sección 14→15 (Decisiones de diseño). |

*Informe basado en datos reales del corte 2026-09-11 (`tipos_datos_obtenidos_2026-09-11.md`), verificado contra el esquema vigente (`SCHEMA_heatmap_stock.md`, `02_init_database.sql`) y el `config.py` del radar V4 (93 activos / 21 categorías / 110 símbolos).*