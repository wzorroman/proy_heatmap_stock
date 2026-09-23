# Informe Técnico de la Base de Datos `heatmap_stock`

> **Fecha del informe:** 2026-09-18
> **Base de datos:** `heatmap_stock` · PostgreSQL 17.10 (Debian 17.10-1.pgdg12+1) en localhost:5432
> **Usuario:** `postgres` · **Schema:** `public`
> **Generado a partir de:** consultas directas contra `information_schema`, `pg_catalog` y `pg_stat_*` vía `proy_scrapping_detail`.

---

## 1. Resumen Ejecutivo

| Concepto | Valor |
|---|---|
| Motor | PostgreSQL **17.10** (x86_64-pc-linux-gnu, Debian 12) |
| Tamaño total de la BD | **769 MB** |
| Tablas | **8** (3 dimensiones + 3 fact + 2 control) |
| Vistas analíticas | **3** (`vw_*`) |
| Particiones | `fact_market_series` (10 mensuales) + `fact_heatmap_snapshot` (4 mensuales) |
| Filas totales (fact) | **2.427.921** series · **3.000** snapshots · **579** eventos económicos |
| Activos en `dim_asset` | **1.083** (1.043 equity, 13 etf, 12 forex, 8 future, 2 yield, 2 commodity, 2 crypto, 1 index) |
| Rango temporal de series | `2026-03-17` → `2026-09-18` (radar/macro) · `2026-08-22` → hoy (equity) |
| Cadencia de captura | ~3 min por activo (radar 110 símbolos) |

**Consumidores:**
- `proy_heatmap/` — Streamlit (lectura heatmap, última hora).
- `proy_scrapping_detail/` — scrapers V5 radar + calendario (escritura upsert).
- `proy_dashboard/` — dashboard v2 planificado (lectura) según `docs/dashboard_radar_v2_Roadmap.md`.

---

## 2. Conexión y Credenciales

Variables de entorno usadas por `proy_scrapping_detail/config.py` y `proy_heatmap/config.py`:

```env
BD_HEATMAP_HOST=localhost
BD_HEATMAP_PORT=5432
BD_HEATMAP_DATABASE=heatmap_stock
BD_HEATMAP_USER=postgres
BD_HEATMAP_PASSWORD=postgres
```

Patrón de conexión (reutilizado por ambos proyectos):

```python
from db.postgresql_connection import PostgreSQLConnector
db = PostgreSQLConnector(PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD)
db.connect()          # psycopg2, autocommit=False
db.execute_query(...) # RealDictCursor, hace commit tras cada consulta
db.disconnect()
```

---

## 3. Inventario de Objetos

### 3.1 Tablas y filas exactas

| Tabla | Tipo | Filas | Tamaño total | Observación |
|---|---|---|---|---|
| `dim_asset` | dimensión | 1.083 | 656 kB | SCD Tipo 2 (versionado) |
| `dim_country` | dimensión | 11 | 24 kB | Catálogo de países |
| `dim_time` | dimensión | 730 | 104 kB | Calendario 2026–2027 |
| `fact_market_series` | fact (particionada) | **2.427.921** | ~758 MB | Series técnicas radar |
| `fact_heatmap_snapshot` | fact (particionada) | 3.000 | ~5,4 MB | Snapshots heatmap |
| `fact_economic_event` | fact | **579** | 1.272 kB | Calendario económico |
| `audit_sync_run` | control | 12 | 48 kB | Auditoría de scrapers |
| `sync_checkpoint` | control | 2 | 40 kB | Checkpoints de reanudación |

### 3.2 Vistas analíticas

| Vista | Volumen hoy | Descripción |
|---|---|---|
| `vw_market_live` | ~52.800/día | Series del radar V4 en ventana de 7 días + señal derivada (`signal_status`) |
| `vw_heatmap_enriched` | 1.000/ventana | Heatmap restringido a equity/etf + `last_rsi`, `market_direction`, `color_intensity` |
| `vw_heatmap_event_impact` | **0** | Cruce heatmap × eventos USD importancia 1–3 ±6 h (vacía por restricciones) |

### 3.3 Funciones PL/pgSQL y de extensión

| Función | Firma (resumida) | Propósito |
|---|---|---|
| `text_to_tsvector_english(text)` | → `tsvector` | Wrapper inmutable para GIN de búsqueda de títulos |
| `upsert_heatmap_snapshot(p_symbol, p_timestamp_utc, p_price_heatmap, p_daily_change_pct, p_market_cap, p_stream_status, p_raw_vector jsonb, p_raw_metadata jsonb)` | → `void` | Upsert del heatmap por símbolo |
| `upsert_market_series(p_asset_symbol, p_timestamp_utc, p_close, p_volume, p_rsi, p_cci20, p_bbpower, p_adx, p_pivot_camarilla_r3, p_perf_w, p_change_pct, p_raw_payload jsonb, p_source_checksum)` | → `void` | Upsert de series técnicas |
| `gtrgm_*`, `similarity_*`, `gin_trgm_*` | extensión `pg_trgm` | Búsqueda de similitud de texto |

### 3.4 Secuencias

| Secuencia | Asociada a |
|---|---|
| `audit_sync_run_run_id_seq` | `audit_sync_run.run_id` |
| `dim_asset_asset_id_seq` | `dim_asset.asset_id` |
| `sync_checkpoint_checkpoint_id_seq` | `sync_checkpoint.checkpoint_id` |

---

## 4. Particionamiento

Estrategia: **RANGE por mes** sobre `timestamp_utc`, con fronteras en hora local del servidor (`America/Lima`, `-05`).

### 4.1 `fact_market_series` → particiones `2026_03 … 2026_12`

| Partición | Filas | Tamaño | Rango (bound) |
|---|---|---|---|
| `fact_market_series_2026_03` | 147.248 | 45 MB | `['2026-03-01' , '2026-04-01')` |
| `fact_market_series_2026_04` | 301.298 | 92 MB | `['2026-04-01' , '2026-05-01')` |
| `fact_market_series_2026_05` | 262.776 | 81 MB | `['2026-05-01' , '2026-06-01')` |
| `fact_market_series_2026_06` | 284.427 | 87 MB | `['2026-06-01' , '2026-07-01')` |
| `fact_market_series_2026_07` | 310.968 | 95 MB | `['2026-07-01' , '2026-08-01')` |
| `fact_market_series_2026_08` | 452.767 | 141 MB | `['2026-08-01' , '2026-09-01')` |
| `fact_market_series_2026_09` | 668.437 | 211 MB | `['2026-09-01' , '2026-10-01')` |
| `fact_market_series_2026_10` | 0 | 96 kB | `['2026-10-01' , '2026-11-01')` |
| `fact_market_series_2026_11` | 0 | 96 kB | `['2026-11-01' , '2026-12-01')` |
| `fact_market_series_2026_12` | 0 | 96 kB | `['2026-12-01' , '2027-01-01')` |

### 4.2 `fact_heatmap_snapshot` → particiones `2026_09 … 2026_12`

| Partición | Filas | Tamaño | Rango (bound) |
|---|---|---|---|
| `fact_heatmap_snapshot_2026_09` | 3.000 | 5.456 kB | `['2026-09-01' , '2026-10-01')` |
| `fact_heatmap_snapshot_2026_10` | 0 | 56 kB | `['2026-10-01' , '2026-11-01')` |
| `fact_heatmap_snapshot_2026_11` | 0 | 56 kB | `['2026-11-01' , '2026-12-01')` |
| `fact_heatmap_snapshot_2026_12` | 0 | 56 kB | `['2026-12-01' , '2027-01-01')` |

> Las particiones vacías futuras se crean de forma preventiva (patrón `02_init_database.sql` y `db/partitions.py`).

## 5. Esquema Detallado de Tablas

### 5.1 `dim_asset` — Activos financieros (SCD Tipo 2)

> Comentario: "Activos financieros versionados (SCD Tipo 2). Compartida por heatmap y radar V4."

| # | Columna | Tipo | Null | Default | Notas |
|---|---|---|---|---|---|
| 1 | `asset_id` | `integer` | NO | `nextval('dim_asset_asset_id_seq')` | **PK** |
| 2 | `symbol` | `varchar(50)` | NO | — | **UNIQUE** (ej. `NASDAQ:NVDA`) |
| 3 | `ticker` | `text` | NO | — | Ej. `NVDA` |
| 4 | `exchange` | `text` | NO | — | Ej. `NASDAQ` |
| 5 | `asset_class` | `text` | SÍ | — | equity/etf/forex/future/yield/commodity/crypto/index |
| 6 | `share_class` | `varchar(20)` | SÍ | — | Ej. `common` |
| 7 | `sector` | `text` | SÍ | — | Ej. `Electronic Technology` |
| 8 | `sector_es` | `text` | SÍ | — | Traducción pendiente (null hoy) |
| 9 | `company_name` | `text` | SÍ | — | Ej. `NVDA` |
| 10 | `logo_id` | `text` | SÍ | — | Id slug de logo (ej. `nvidia`) |
| 11 | `source_discovered_by` | `varchar(50)` | SÍ | — | Scraper que descubrió el activo |
| 12 | `source_category` | `varchar(50)` | SÍ | — | Categoría del radar (ej. `SEMICONDUCTORES`) |
| 13 | `is_active` | `boolean` | NO | `true` | |
| 14 | `valid_from` | `timestamptz` | NO | `CURRENT_TIMESTAMP` | SCD T2 |
| 15 | `valid_to` | `timestamptz` | NO | `'infinity'` | SCD T2 |
| 16 | `current_version` | `boolean` | NO | `true` | SCD T2 |
| 17 | `created_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` | |
| 18 | `updated_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` | |
| 19 | `slug` | `text` | SÍ | — | Ej. `nasdaq_nvda` |
| 20 | `url_logo` | `text` | SÍ | — | URL CDN de logo |

**Ejemplo real (NVDA):**

```json
{
  "asset_id": 997, "symbol": "NASDAQ:NVDA", "ticker": "NVDA",
  "exchange": "NASDAQ", "asset_class": "equity", "sector": "Electronic Technology",
  "company_name": "NVDA", "slug": "nasdaq_nvda",
  "url_logo": "https://s3-symbol-logo.tradingview.com/nvidia.svg",
  "is_active": true, "current_version": true,
  "valid_from": "2026-09-10 12:13:38-05", "valid_to": "infinity"
}
```

**Distribución por clase de activo:**

| asset_class | N activos |
|---|---|
| equity | 1.043 |
| etf | 13 |
| forex | 12 |
| future | 8 |
| yield | 2 |
| commodity | 2 |
| crypto | 2 |
| index | 1 |

**Sectores con más activos:** Finance (324), Electronic Technology (109), Health Technology (79), Producer Manufacturing (71), Technology Services (67), Consumer Non-Durables (45), Utilities (39), Retail Trade (38).

---

### 5.2 `dim_country` — Catálogo de países

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `country_code` | `varchar(5)` | NO | **PK** (ej. `US`) |
| 2 | `country_name` | `varchar(100)` | SÍ | |
| 3 | `region` | `varchar(50)` | SÍ | |
| 4 | `currency_code` | `varchar(5)` | SÍ | |

**Datos (11 filas):** `AU` Australia/Oceania/AUD · `CA` Canada/Americas/CAD · `CH` Switzerland/Europe/CHF · `CN` China/Asia/CNY · `DE` Germany/Europe/EUR · `ES` Spain/Europe/EUR · `FR` France/Europe/EUR · `GB` United Kingdom/Europe/GBP · `IT` Italy/Europe/EUR · `JP` Japan/Asia/JPY · `US` United States/Americas/USD.

---

### 5.3 `dim_time` — Dimensión temporal

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `date_id` | `integer` | NO | **PK** (formato YYYYMMDD) |
| 2 | `full_date` | `date` | NO | |
| 3 | `year` | `smallint` | NO | |
| 4 | `quarter` | `smallint` | NO | |
| 5 | `month` | `smallint` | NO | |
| 6 | `month_name` | `varchar(20)` | SÍ | |
| 7 | `day_of_month` | `smallint` | NO | |
| 8 | `day_of_week` | `smallint` | NO | 1..7 (ISO) |
| 9 | `week_number` | `smallint` | NO | |
| 10 | `is_weekend` | `boolean` | NO | |
| 11 | `is_holiday` | `boolean` | NO | default `false` |
| 12 | `trading_session` | `varchar(20)` | SÍ | Ej. `US` (null en fin de semana) |

**Rango:** `2026-01-01` (date_id 20260101) → `2027-12-31` (730 filas).

---

### 5.4 `fact_market_series` — Series técnicas del radar (particionada)

> Series por activo con indicadores técnicos del radar V4.

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `asset_id` | `integer` | NO | **PK parcial** (`asset_id, timestamp_utc`) |
| 2 | `timestamp_utc` | `timestamptz` | NO | **PK parcial** · clave de partición |
| 3 | `close` | `numeric(20,8)` | SÍ | Precio de cierre del tick |
| 4 | `volume` | `numeric(20,8)` | SÍ | Volumen (null en índices/VIX) |
| 5 | `rsi` | `numeric(10,4)` | SÍ | RSI 14 |
| 6 | `cci20` | `numeric(10,4)` | SÍ | CCI período 20 |
| 7 | `bbpower` | `numeric(10,4)` | SÍ | Bandas de Bollinger %B |
| 8 | `adx` | `numeric(10,4)` | SÍ | ADX 14 |
| 9 | `pivot_camarilla_r3` | `numeric(18,6)` | SÍ | Nivel pivot Camarilla R3 |
| 10 | `perf_w` | `numeric(12,8)` | SÍ | Performance semanal % |
| 11 | `change_pct` | `numeric(12,8)` | SÍ | Cambio % del día |
| 12 | `raw_payload` | `jsonb` | SÍ | **null en backfill** (solo runtime) |
| 13 | `ingested_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` |
| 14 | `source_checksum` | `varchar(64)` | SÍ | SHA-256 canónico |

**Ejemplo real (NVDA, último tick):**

```json
{
  "asset_id": 997, "timestamp_utc": "2026-09-18 14:24:52-05:00",
  "close": 219.47000000, "volume": 73845021.00000000,
  "rsi": 51.8341, "cci20": 3.2136, "bbpower": 2.2237, "adx": 12.6935,
  "pivot_camarilla_r3": 230.025500, "perf_w": -0.79779420, "change_pct": 0.05926872,
  "raw_payload": null, "ingested_at": "2026-09-18 15:49:49-05:00",
  "source_checksum": "85eba1932d8af3be996dd286ebca8ad268ef35bbd7c7491e37ad9c10accb7d83"
}
```

**Ejemplo real (radar VIX, último tick):**

```json
{
  "asset_id": 1011, "timestamp_utc": "2026-09-18 14:23:01-05:00",
  "close": 15.00000000, "volume": null,
  "rsi": 45.9586, "cci20": -52.7602, "bbpower": -1.5270, "adx": 22.7889,
  "pivot_camarilla_r3": 16.112500, "perf_w": -14.33466591, "change_pct": -2.91262136
}
```

**Volumen por clase de activo (filas totales):**

| asset_class | Filas | Activos distintos |
|---|---|---|
| etf | 593.527 | 13 |
| equity | 590.831 | 70 |
| future | 455.029 | 8 |
| forex | 384.495 | 12 |
| crypto | 115.461 | 2 |
| yield | 115.439 | 2 |
| commodity | 115.423 | 2 |
| index | 57.716 | 1 |

**Calidad de datos:** `close` nulo solo en 4 filas (de 2,4 M); `rsi` nulo en 115.468 (4,8%); `raw_payload` 100% null (backfill desde CSV); `source_checksum` 100% poblado.

### 5.5 `fact_heatmap_snapshot` — Snapshots del heatmap (particionada)

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `asset_id` | `integer` | NO | **PK parcial** (`asset_id, timestamp_utc`) |
| 2 | `timestamp_utc` | `timestamptz` | NO | **PK parcial** · clave de partición |
| 3 | `price_heatmap` | `numeric(18,6)` | SÍ | Precio del heatmap |
| 4 | `daily_change_pct` | `numeric(12,6)` | SÍ | Cambio % diario |
| 5 | `market_cap` | `numeric(18,0)` | SÍ | Capitalización |
| 6 | `stream_status` | `varchar(30)` | SÍ | Ej. `delayed_streaming_900` |
| 7 | `raw_vector` | `jsonb` | SÍ | Vector crudo del scanner (28 elementos) |
| 8 | `raw_metadata` | `jsonb` | SÍ | Logo, sector, ticker, class |
| 9 | `ingested_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` |
| 10 | `source_checksum` | `varchar(64)` | SÍ | null hoy (ver nota §10) |

**Ventanas de snapshot existentes (3 totales, 1.000 activos c/u):**

| timestamp_utc | Filas | Activos |
|---|---|---|
| 2026-09-13 12:59:29 | 1.000 | 1.000 |
| 2026-09-18 12:48:42 | 1.000 | 1.000 |
| 2026-09-18 14:23:36 | 1.000 | 1.000 |

**Ejemplo real (NVDA):**

```json
{
  "asset_id": 997, "timestamp_utc": "2026-09-18 14:23:36-05:00",
  "price_heatmap": 219.405000, "daily_change_pct": 0.029600,
  "market_cap": 5287660411717, "stream_status": "delayed_streaming_900",
  "raw_metadata": {"logo": "nvidia", "sector": "Electronic Technology", "ticker": "NVDA", "asset_class": "equity", "share_class": "common"},
  "source_checksum": null
}
```

---

### 5.6 `fact_economic_event` — Calendario económico V4 RAW

> Comentario: "Calendario económico V4 RAW. Ingesta sin filtro de importancia."

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `event_id` | `bigint` | NO | **PK** (id int64 de TradingView) |
| 2 | `title` | `text` | SÍ | |
| 3 | `country` | `varchar(5)` | SÍ | **FK→`dim_country(country_code)`** |
| 4 | `indicator` | `text` | SÍ | |
| 5 | `event_ticker` | `varchar(50)` | SÍ | Ej. `ECONOMICS:USINTR` |
| 6 | `comment` | `text` | SÍ | Descripción |
| 7 | `category` | `varchar(100)` | SÍ | Ej. `mny`, `bsnss` |
| 8 | `period` | `varchar(20)` | SÍ | Ej. `Aug` |
| 9 | `reference_date` | `timestamptz` | SÍ | |
| 10 | `source` | `text` | SÍ | |
| 11 | `source_url` | `text` | SÍ | |
| 12 | `actual` | `numeric(18,6)` | SÍ | |
| 13 | `previous` | `numeric(18,6)` | SÍ | |
| 14 | `forecast` | `numeric(18,6)` | SÍ | |
| 15 | `actual_raw` | `numeric(30,8)` | SÍ | Unidad base |
| 16 | `previous_raw` | `numeric(30,8)` | SÍ | |
| 17 | `forecast_raw` | `numeric(30,8)` | SÍ | |
| 18 | `actual_display` | `text` | SÍ | Formato "4.0" |
| 19 | `previous_display` | `text` | SÍ | |
| 20 | `forecast_display` | `text` | SÍ | |
| 21 | `currency` | `varchar(5)` | SÍ | |
| 22 | `unit` | `varchar(20)` | SÍ | Ej. `%` |
| 23 | `importance` | `smallint` | SÍ | **-1=sin dato, 0=baja, 1=media, 2=alta, 3=muy alta** |
| 24 | `event_timestamp` | `timestamptz` | NO | |
| 25 | `captured_at` | `timestamptz` | SÍ | timestamp_captura del scraper |
| 26 | `first_seen_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` |
| 27 | `last_updated_at` | `timestamptz` | NO | `CURRENT_TIMESTAMP` |
| 28 | `raw_payload` | `jsonb` | SÍ | Payload JSON original |
| 29 | `payload_checksum` | `varchar(64)` | SÍ | SHA-256 |

**Ejemplo real (Fed Interest Rate Decision):**

```json
{
  "event_id": 390604, "title": "Fed Interest Rate Decision", "country": "US",
  "indicator": "Interest Rate", "event_ticker": "ECONOMICS:USINTR", "category": "mny",
  "actual_display": "4.0", "previous_display": "3.75", "forecast_display": "4.0",
  "currency": "USD", "unit": "%", "importance": 1,
  "event_timestamp": "2026-09-16 13:00:00-05:00", "captured_at": "2026-09-17 12:45:02-05:00"
}
```

**Distribución por país (579 eventos):** US 218 · GB 67 · JP 61 · CA 43 · AU 34 · DE 34 · FR 30 · IT 30 · ES 24 · CN 22 · CH 16.

**Distribución por importancia:** `-1` → 392 · `0` → 142 · `1` → 45 (sin eventos 2–3 por ahora).

**Rango temporal:** `2026-08-31 19:30` → `2026-09-18 12:00` UTC-5.

---

### 5.7 `audit_sync_run` — Auditoría de ejecuciones

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `run_id` | `integer` | NO | **PK** · serial |
| 2 | `script_name` | `varchar(100)` | NO | `calendario`, `radar_v4`, `backfill_*`, etc. |
| 3 | `run_start` | `timestamptz` | NO | |
| 4 | `run_end` | `timestamptz` | SÍ | |
| 5 | `records_fetched` | `integer` | NO | default 0 |
| 6 | `records_upserted` | `integer` | NO | default 0 |
| 7 | `records_failed` | `integer` | NO | default 0 |
| 8 | `status` | `varchar(20)` | NO | RUNNING/SUCCESS/PARTIAL_FAIL/FAILED |
| 9 | `error_message` | `text` | SÍ | |
| 10 | `source_params` | `jsonb` | SÍ | |
| 11 | `execution_mode` | `varchar(30)` | SÍ | cron/manual/backfill |

**Registros (12):** heatmap (3 SUCCESS), calendario (1 SUCCESS + 1 backfill SUCCESS), radar_v4 (2 SUCCESS), backfill_market_csv (3 SUCCESS + 3 FAILED históricos). Ejemplos de errores registrados: `relation "fact_market_series_2026_03" already exists` y `no partition of relation "fact_market_series" found for row (2026-08-31 19:00:02-05)`.

---

### 5.8 `sync_checkpoint` — Checkpoints de reanudación

| # | Columna | Tipo | Null | Notas |
|---|---|---|---|---|
| 1 | `checkpoint_id` | `integer` | NO | **PK** · serial |
| 2 | `script_name` | `varchar(100)` | NO | **UNIQUE** |
| 3 | `last_timestamp` | `timestamptz` | NO | |
| 4 | `last_event_id` | `bigint` | SÍ | |
| 5 | `records_processed` | `integer` | NO | default 0 |
| 6 | `last_run_at` | `timestamptz` | NO | |
| 7 | `status` | `varchar(20)` | NO | ACTIVE/PAUSED/COMPLETED |

**Datos actuales:**

```json
{"script_name": "radar_v4",   "last_timestamp": "2026-09-18 14:20:54-05:00", "last_event_id": null,  "records_processed": 110, "status": "ACTIVE"}
{"script_name": "calendario", "last_timestamp": "2026-09-18 20:15:28-05:00", "last_event_id": 421348, "records_processed": 579, "status": "ACTIVE"}
```

## 6. Restricciones y Relaciones

### 6.1 Claves primarias

| Tabla | PK |
|---|---|
| `dim_asset` | `(asset_id)` |
| `dim_country` | `(country_code)` |
| `dim_time` | `(date_id)` |
| `fact_market_series` | `(asset_id, timestamp_utc)` |
| `fact_heatmap_snapshot` | `(asset_id, timestamp_utc)` |
| `fact_economic_event` | `(event_id)` |
| `audit_sync_run` | `(run_id)` |
| `sync_checkpoint` | `(checkpoint_id)` |

### 6.2 Claves únicas

| Tabla | Columna(s) |
|---|---|
| `dim_asset` | `symbol` |
| `sync_checkpoint` | `script_name` |

### 6.3 Claves foráneas

| Origen | Destino | Columna FK |
|---|---|---|
| `fact_economic_event` | `dim_country` | `country` → `dim_country(country_code)` |

> Nota: `fact_market_series.asset_id` y `fact_heatmap_snapshot.asset_id` **no tienen FK declarada**; la integridad se mantiene en la capa de aplicación/seed.

### 6.4 Diagrama de relaciones

```
dim_asset (1) ──┐
                ├──(asset_id)── fact_market_series (N)      [no FK declarada]
                ├──(asset_id)── fact_heatmap_snapshot (N)   [no FK declarada]
dim_country (1) ┴──(country_code)── fact_economic_event (N) [FK declarada]
```

---

## 7. Índices

### 7.1 `fact_market_series` (padre `ONLY` + replicados por partición)

| Índice | Tipo | Columna(s) |
|---|---|---|
| `fact_market_series_pkey` | btree UNIQUE | `(asset_id, timestamp_utc)` |
| `idx_fact_market_series_ts_desc` | btree | `(timestamp_utc DESC)` |
| `idx_fact_market_series_rsi` | btree parcial | `(rsi) WHERE rsi IS NOT NULL` |
| `idx_fact_market_series_close` | btree parcial | `(close) WHERE close IS NOT NULL` |
| `idx_fact_market_series_date` | btree expresión | `((timestamp_utc AT TIME ZONE 'UTC')::date)` |
| `*_ts_brin` (por partición) | **BRIN** | `(timestamp_utc)` |

> Cada partición mensual replica: `_pkey`, `_timestamp_utc_idx`, `_rsi_idx`, `_close_idx`, `_timezone_idx`, `_ts_brin`.

### 7.2 `fact_heatmap_snapshot` (padre `ONLY` + replicados por partición)

| Índice | Tipo | Columna(s) |
|---|---|---|
| `fact_heatmap_snapshot_pkey` | btree UNIQUE | `(asset_id, timestamp_utc)` |
| `idx_fact_heatmap_ts_desc` | btree | `(timestamp_utc DESC)` |
| `idx_fact_heatmap_change` | btree parcial | `(daily_change_pct) WHERE ...` |
| `idx_fact_heatmap_mcap` | btree parcial | `(market_cap DESC) WHERE ...` |
| `idx_fact_heatmap_raw_vector` | **GIN** | `(raw_vector)` |

### 7.3 `fact_economic_event`

| Índice | Tipo | Columna(s) |
|---|---|---|
| `fact_economic_event_pkey` | btree UNIQUE | `(event_id)` |
| `idx_fact_economic_event_ts` | btree | `(event_timestamp DESC)` |
| `idx_fact_economic_event_country` | btree | `(country)` |
| `idx_fact_economic_event_country_ts` | btree | `(country, event_timestamp DESC)` |
| `idx_fact_economic_event_importance` | btree parcial | `(importance) WHERE importance BETWEEN 1 AND 3` |
| `idx_fact_economic_event_ticker` | btree parcial | `(event_ticker) WHERE event_ticker IS NOT NULL` |
| `idx_fact_economic_event_captured` | btree | `(captured_at DESC)` |
| `idx_fact_economic_event_title_gin` | **GIN** | `text_to_tsvector_english(title)` |

### 7.4 `dim_asset`

| Índice | Tipo | Columna(s) |
|---|---|---|
| `dim_asset_pkey` | btree UNIQUE | `(asset_id)` |
| `dim_asset_symbol_key` | btree UNIQUE | `(symbol)` |
| `idx_dim_asset_symbol` | btree | `(symbol)` |
| `idx_dim_asset_active` | btree parcial | `(is_active, current_version) WHERE is_active AND current_version` |
| `idx_dim_asset_class` | btree parcial | `(asset_class) WHERE is_active AND current_version` |
| `idx_dim_asset_slug` | btree | `(slug)` |

### 7.5 Control

| Tabla | Índice |
|---|---|
| `audit_sync_run` | `idx_audit_sync_run_script (script_name, run_start DESC)` |
| `sync_checkpoint` | `sync_checkpoint_script_name_key` (UNIQUE) |

## 8. Definición de las Vistas

### 8.1 `vw_market_live`

Series del radar en ventana de 7 días con señal derivada (`TRENDING`, `OVERSOLD_REVERSAL`, `OVERBOUGHT_REVERSAL`, `NEUTRAL`):

```sql
SELECT a.symbol, a.ticker, a.asset_class, a.source_category,
       ms.timestamp_utc, ms.close, ms.volume, ms.rsi, ms.cci20, ms.bbpower,
       ms.adx, ms.pivot_camarilla_r3, ms.perf_w, ms.change_pct,
       CASE
           WHEN (ms.rsi < 30 AND ms.change_pct > 0) THEN 'OVERSOLD_REVERSAL'
           WHEN (ms.rsi > 70 AND ms.change_pct < 0) THEN 'OVERBOUGHT_REVERSAL'
           WHEN (ms.adx > 25) THEN 'TRENDING'
           ELSE 'NEUTRAL'
       END AS signal_status
FROM fact_market_series ms
JOIN dim_asset a ON a.asset_id = ms.asset_id
WHERE ms.timestamp_utc >= now() - interval '7 days'
  AND a.is_active = true AND a.current_version = true;
```

### 8.2 `vw_heatmap_enriched`

Heatmap enriquecido restringido a `equity`/`etf`, con dirección de mercado, intensidad de color y último RSI previo al snapshot:

```sql
SELECT h.asset_id, a.symbol, a.ticker, a.company_name, a.sector, h.timestamp_utc,
       h.price_heatmap, h.daily_change_pct, h.market_cap,
       CASE WHEN h.daily_change_pct > 0 THEN 'BUY'
            WHEN h.daily_change_pct < 0 THEN 'SELL' ELSE 'NEUTRAL' END AS market_direction,
       abs(h.daily_change_pct) AS color_intensity,
       (SELECT ms.rsi FROM fact_market_series ms
        WHERE ms.asset_id = h.asset_id AND ms.timestamp_utc <= h.timestamp_utc
          AND ms.rsi IS NOT NULL ORDER BY ms.timestamp_utc DESC LIMIT 1) AS last_rsi
FROM fact_heatmap_snapshot h
JOIN dim_asset a ON a.asset_id = h.asset_id
WHERE a.asset_class IN ('equity','etf') AND a.is_active = true AND a.current_version = true;
```

### 8.3 `vw_heatmap_event_impact`

Cruce heatmap × eventos USD de importancia 1–3 en ventana ±6 h (hoy devuelve 0 filas por restricciones de datos):

```sql
SELECT h.*, e.event_id, e.title, e.country, e.importance, e.category,
       e.event_timestamp, e.actual, e.forecast, e.previous, e.currency, e.unit,
       EXTRACT(epoch FROM (h.timestamp_utc - e.event_timestamp)) / 3600.0 AS hours_since_event
FROM vw_heatmap_enriched h
JOIN fact_economic_event e
  ON e.currency = 'USD' AND e.importance BETWEEN 1 AND 3
 AND e.event_timestamp BETWEEN (h.timestamp_utc - interval '6 hours')
                           AND (h.timestamp_utc + interval '6 hours');
```

---

## 9. Detalle Técnico Adicional

### 9.1 Ruta de escritura (upserts)

Los scrapers V5 escriben con **UPSERT por PK** (`ON CONFLICT DO UPDATE`):

- **Series:** `insert_market_series_batch` en `db/market_repository.py` (por lotes con `execute_values`).
- **Heatmap:** `upsert_heatmap_snapshot` (función PL/pgSQL) + `db/heatmap_repository.py`.
- **Eventos:** `insert_events_batch` en `db/event_repository.py` (29 columnas, dedup por `event_id`, checksum SHA-256).

### 9.2 Pipeline de backfill (2026-09-18)

| Script | Registros | Modo |
|---|---|---|
| `scripts/load_market_csv_to_db.py` | 2.427.921 | manual (backfill histórico) |
| `scripts/load_calendar_csv_to_db.py` | 579 | manual (backfill calendario) |

### 9.3 Cadencia y volumen reciente

Últimos 7 días (ticks por día, 110 activos):

| Día | Ticks | Activos |
|---|---|---|
| 2026-09-14 | 52.799 | 110 |
| 2026-09-15 | 52.800 | 110 |
| 2026-09-16 | 52.799 | 110 |
| 2026-09-17 | 52.800 | 110 |
| 2026-09-18 | 31.759 | 110 |

Cadencia promedio NVDA: **3,00 min** entre ticks.

### 9.4 Formato de `raw_vector` (heatmap)

Vector JSON de 28 elementos del scanner TradingView (orden posicional):

```
[share_class, daily_change_pct, cambio5m?, ..., market_cap, ..., sector, logo_slug, precio, volumen_relativo, ticker, stream_status, currency]
```

Ejemplo (NVDA): `["common", 0.0296, 0.065, -1.0218, 5.824, 23.26, 26.10, 15.57, 1.31, 236.54, 164.27, 5287660411716.847, 118985082.07, 102083327.7, 73653038, 24100000000, 24100000000, 42000, 7.95, null, null, "Electronic Technology", "nvidia", 219.405, 100, "NVDA", "delayed_streaming_900", "USD"]`

### 9.5 Formato de `raw_payload` (eventos económicos)

Payload JSON crudo de la API de TradingView: `id`, `date`, `unit`, `title`, `actual`, `period`, `source`, `ticker` (ECONOMICS:*), `comment`, `country`, `category`, `currency`, `forecast`, `previous`, `actualRaw`, `previousRaw`, `forecastRaw`, `importance`, `timestamp_captura`.

## 10. Consideraciones de Diseño y Pendientes

1. **FK no declaradas** en `fact_market_series`/`fact_heatmap_snapshot` → `dim_asset`. La integridad se mantiene por capa de aplicación; opcional añadir FK (con coste en upsert).
2. **`raw_payload` en `fact_market_series` 100% null** tras el backfill desde CSV (el runtime V5 sí lo puebla).
3. **`vw_heatmap_event_impact` vacía**: requiere snapshots frecuentes y/o eventos de importancia 2–3. Ver deuda D6/D7/D8 en `docs/dashboard_radar_v2_Roadmap.md`.
4. **`dim_asset.sector_es` sin poblar** (traducción pendiente).
5. **Particiones futuras preventivas** ya creadas hasta 2026-12 (marzo–diciembre para series; septiembre–diciembre para snapshots).
6. **`source_checksum` en `fact_heatmap_snapshot` null** en los 3.000 registros actuales.
7. **Retro del momentum equity** limitado a `2026-08-22` (70 acciones); el radar/macro tiene historia desde `2026-03-17`.

---

## 11. Comandos de Verificación Útiles

```sql
-- Resumen de tamaños por tabla
SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY 2 DESC;

-- Filas exactas de una partición
SELECT count(*) FROM fact_market_series_2026_09;

-- Último tick por activo del radar
SELECT DISTINCT ON (a.symbol) a.symbol, s.close, s.change_pct, s.rsi, s.adx, s.timestamp_utc
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.is_active ORDER BY a.symbol, s.timestamp_utc DESC;

-- Eventos con sorpresa computable
SELECT count(*) FROM fact_economic_event
WHERE actual_raw IS NOT NULL AND forecast_raw IS NOT NULL;

-- Estado de checkpoints
SELECT script_name, last_event_id, records_processed, status FROM sync_checkpoint;

-- Últimos runs de auditoría
SELECT script_name, status, records_upserted, run_start, execution_mode
FROM audit_sync_run ORDER BY run_id DESC LIMIT 10;

-- Distribución por clase de activo en series
SELECT a.asset_class, count(*) FROM fact_market_series s JOIN dim_asset a USING (asset_id)
GROUP BY 1 ORDER BY 2 DESC;
```

---

*Fin del informe — 2026-09-18. Generado desde consultas a `information_schema`, `pg_catalog` y `pg_stat_*`.*