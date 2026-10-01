# Roadmap de Migración `proy_heatmap` — v1.0.1 → v1.0.2

> **Sistema:** proyecto `proy_heatmap` (heatmap de TradingView + Streamlit + PostgreSQL `heatmap_stock`)
> **Versión origen:** `VERSION = "1.0.1"` (`proy_heatmap/config.py:11`)
> **Versión destino:** `VERSION = "1.0.2"`
> **Referencia normativa:** `docs/Roadmap_bd_heatmap_stock_2026-09-11.md` (roadmap del corte de datos 2026-09-11)
> **Fecha del documento:** 2026-09-12

> **Estrategia de migración (decidida):** se **arranca desde una BD en blanco**. El artefacto principal es la **reescritura de `scripts/02_init_database.sql`** según el DDL completo del roadmap fuente (§11). El script one-shot `migracion_v4_20260911.sql` (§7) **no es necesario** y no forma parte de v1.0.2; se documenta solo como referencia para una eventual migración de una BD existente (§3.2).

---

## 1. Objetivo y alcance

Elevar `proy_heatmap` de **1.0.1** a **1.0.2** implementando el esquema completo del corte 2026-09-11 (roadmap fuente §11) sobre una **base de datos nueva**, más las adaptaciones de código: seed de `dim_asset`, scraper del heatmap y filtro de taxonomía en la capa de aplicación.

**Lo que ENTRA en 1.0.2:**

| # | Bloque | Artefacto |
|---|---|---|
| 1 | Esquema de BD desde cero | `scripts/02_init_database.sql` (rewrite → §11 + `share_class`) |
| 2 | Checklist de validación | `scripts/03_comprobar.sql` (actualizado) |
| 3 | Seed de `dim_asset` | `seed_dim_asset.py` + `config/radar_activos.json` (volcado de `CONFIG_ACTIVOS`) |
| 4 | Seed de `dim_time` (2026–2027) | dentro de `seed_dim_asset.py` o script `seed_dim_time.py` (roadmap §14.3) |
| 5 | Scraper del heatmap | `scrapper_heatmap_v0.py`, `scrapper_heatmap_v1.py` |
| 6 | Capa de aplicación | `application/db/heatmap_repository.py`, `application/heatmap_service.py` |
| 7 | Versionado y bitácora | `config.py` (`1.0.2`), `README.md`, este documento |

**Lo que NO entra (vive en otro proyecto):**

- **ETL / ingesta de series del radar** (`scraper_live_tradingview_v4.py`) y del **calendario V4 RAW** (`calendario_tradingview_live_v4.py`). Se capturan y escriben en `heatmap_stock` **desde el otro proyecto** (`app_backup_nasdaq`). Este proyecto **solo provee el esquema base** (§3.9 fija el contrato de handoff).
- **Migración one-shot §7** (§3.2): innecesaria al partir de BD en blanco.
- **Actualización de `docs/SCHEMA_heatmap_stock.md` y `docs/documentacion_campos_heatmap.md`**: fuera de alcance; las mejoras de documentación de esta iteración se concentran en **este roadmap**.

**Decisiones de diseño confirmadas:**

1. **`dim_asset.symbol` UNIQUE global, primer-gana.** El primer scraper que llegue deja su `source_discovered_by`; el resto usa `COALESCE` y no lo pisa (roadmap fuente §15.1).
2. **`source_discovered_by` = `'heatmap'` para el CSV de 1.005 símbolos**, `'radar_v4'` para el merge de 110.
3. **`asset_class` con la taxonomía del roadmap** (`equity | etf | crypto | forex | future | yield | index | commodity`). La columna `asset_class` del CSV es *clase de acción* → se mapea a la nueva columna **`share_class`**; para el CSV `asset_class = 'equity'`.
4. **`vw_heatmap_enriched` filtra `asset_class IN ('equity','etf')`** (roadmap fuente §15.2); la app replica este criterio.
5. **Sin FK físicas de los hechos hacia `dim_asset`** (el DDL §11 define `asset_id INTEGER NOT NULL` sin `REFERENCES`; la integridad es "lógica" vía `upsert_market_series`, roadmap fuente §12).
6. **Sin incrustar símbolos en el documento**: la fuente canónica del catálogo heatmap es `docs/dim_asset_202609112246.csv` (1.005 símbolos); el volcado radar es `config/radar_activos.json`.

---

## 2. Estado de partida (verificado)

| Ítem | Valor |
|---|---|
| `config.py` | `VERSION = "1.0.1"` (`proy_heatmap/config.py:11`), `HEATMAP_*` y conn a `heatmap_stock` ya definidos |
| Esquema vigente | `scripts/02_init_database.sql` (409 líneas): `text_to_tsvector_english`, `dim_asset/dim_country/dim_time`, `fact_market_series/fact_heatmap_snapshot/fact_economic_event`, `audit_sync_run/sync_checkpoint`, 3 vistas, 2 funciones `upsert_*` |
| `dim_asset.asset_class` hoy | `TEXT` con `"common"/"etf"` (clase de acción, para el scraper del heatmap) |
| FKs físicas hoy | `fact_market_series.asset_id → dim_asset(asset_id)` y `fact_heatmap_snapshot.asset_id → dim_asset(asset_id)` (`02_init_database.sql:77,116`) — **el DDL destino §11 las elimina** |
| `fact_market_series` | `volume BIGINT`, `close NUMERIC(18,6)`, `perf_w/change_pct NUMERIC(10,4)` |
| `fact_economic_event` | `event_id VARCHAR(100)`, `importance INT 1..3`, `actual_raw TEXT`; `raw_payload JSONB NOT NULL` |
| `sync_checkpoint.last_event_id` hoy | `VARCHAR(100)` — el DDL destino §11 lo define `BIGINT` |
| Scrapers | `scrapper_heatmap_v0.py` y `v1.py` con `get_or_create_asset` escribiendo `asset_class` (clase de acción); ambos crean la partición del mes (`v1.py:123-141`) y llaman `create_monthly_partitions(..., 1)` |
| App | `heatmap_repository.py`: `get_heatmap_last_hour`, `get_sectors`, `get_heatmap_stats`, `get_price_evolution` consultan `fact_heatmap_snapshot`, **sin** filtrar por `asset_class` |
| CSV seed | `docs/dim_asset_202609112246.csv`: 1.005 filas; exchanges `NASDAQ` 132 / `NYSE` 413 / `OTC` 459 / `AMEX` 1; col. `asset_class`: `common` 606 · `preferred` 127 · `unit` 4 · vacío 268 |
| Radar | `CONFIG_ACTIVOS` en `app_backup_nasdaq/config.py` (93 configs / 21 categorías / 110 símbolos) |
| Postgres local | ⚠️ no instalado/activo en esta máquina; verificación vía revisión SQL + `--dry-run` |

> Nota: hay cambios sin commitear en git (renombrado `price` → `price_heatmap` en README, app.py, repositorio, servicio, scrapers y scripts SQL). Se recomienda confirmar el commit de ese renombrado **antes** de iniciar la migración (o incluirlo en la rama v1.0.2).

---

## 3. Bloques de trabajo

### 3.1 Esquema desde cero — `scripts/02_init_database.sql` (rewrite)

Fuente: roadmap fuente §11 (DDL completo) **+** §14.2 (`share_class`). Al partir de BD en blanco, este script es la **única fuente de esquema**.

Elementos que debe contener (checklist de fidelidad con §11):

1. **Extensiones/preámbulo**: `CREATE EXTENSION IF NOT EXISTS pg_trgm;` y `SET search_path = public;` (§11).
2. **`dim_asset`** (SCD Tipo 2):
   - `symbol VARCHAR(50) NOT NULL` + `CONSTRAINT dim_asset_symbol_key UNIQUE (symbol)`.
   - `ticker TEXT NOT NULL`, `exchange TEXT NOT NULL` (hoy eran nullables → el seed siempre los provee).
   - `asset_class TEXT` con taxonomía (`equity|etf|crypto|forex|future|yield|index|commodity`).
   - **Nuevas**: `source_discovered_by VARCHAR(50)` (`'heatmap'|'radar_v4'`), `source_category VARCHAR(50)` (categoría del radar), **`share_class VARCHAR(20)`** (`common|preferred|unit`, propuesta §14.2).
   - Comentarios de tabla/columna.
   - Índices: `idx_dim_asset_active`, `idx_dim_asset_symbol` y **`idx_dim_asset_class`** (`(asset_class) WHERE is_active AND current_version`, §11).
3. **`dim_country`** y **`dim_time`** (sin cambios de estructura respecto a §11).
4. **`fact_heatmap_snapshot`** (particionada mensual):
   - `price_heatmap NUMERIC(18,6)`, `daily_change_pct NUMERIC(12,6)`, `market_cap NUMERIC(18,0)`, `stream_status`, `raw_vector JSONB`, `raw_metadata JSONB`, `ingested_at`, `source_checksum`.
   - **Sin `REFERENCES dim_asset`** (FK lógica).
   - Índices: `idx_fact_heatmap_ts_desc`, `idx_fact_heatmap_mcap`, `idx_fact_heatmap_change`, `idx_fact_heatmap_raw_vector` (GIN).
5. **`fact_market_series`** (particionada mensual):
   - `close NUMERIC(20,8)`, `volume NUMERIC(20,8)`, `rsi/cci20/bbpower/adx NUMERIC(10,4)`, `pivot_camarilla_r3 NUMERIC(18,6)`, `perf_w NUMERIC(12,8)`, `change_pct NUMERIC(12,8)`, `raw_payload JSONB`, `source_checksum VARCHAR(64)`.
   - **Sin `REFERENCES dim_asset`** (FK lógica).
   - Índices: `idx_fact_market_series_ts_desc`, `_rsi`, `_close`, `_date`, más **BRIN por partición** (§6, caveat §10.5).
6. **`fact_economic_event`** (V4 RAW, no particionada):
   - `event_id BIGINT PRIMARY KEY`, `title`, `country VARCHAR(5) REFERENCES dim_country(country_code)`, `indicator`, `event_ticker VARCHAR(50)`, `comment`, `category VARCHAR(100)`, `period VARCHAR(20)`, `reference_date TIMESTAMPTZ`, `source`, `source_url`.
   - `actual/previous/forecast NUMERIC(18,6)`; `actual_raw/previous_raw/forecast_raw NUMERIC(30,8)` (float64 unidad base); `actual_display/previous_display/forecast_display TEXT`.
   - `currency`, `unit`, `importance SMALLINT` (**escala −1..3**), `event_timestamp TIMESTAMPTZ NOT NULL`, `captured_at`, `first_seen_at`/`last_updated_at NOT NULL DEFAULT CURRENT_TIMESTAMP`, `raw_payload JSONB NOT NULL`, `payload_checksum VARCHAR(64)`.
   - Índices: `idx_fact_economic_event_ts`, `_country`, `_country_ts`, **`_importance` con `WHERE importance BETWEEN 1 AND 3`**, `_ticker`, `_captured`, y **`_title_gin`** (`text_to_tsvector_english(title)`).
7. **`audit_sync_run`** (sin cambios).
8. **`sync_checkpoint`**: `last_event_id BIGINT` (hoy `VARCHAR(100)`), `UNIQUE (script_name)`.
9. **Funciones**:
   - `text_to_tsvector_english(input_text TEXT)` con `IMMUTABLE PARALLEL SAFE` (hoy solo `IMMUTABLE`); el índice GIN de título se crea después.
   - `upsert_heatmap_snapshot(...)`: auto-crea `dim_asset` con `ticker`/`exchange` (`split_part`) y `source_discovered_by='heatmap'`. *(Nota: no setea `asset_class`/`share_class`; es un fallback PL/pgSQL que los scrapers no usan — escriben inline.)*
   - `upsert_market_series(...)`: firma con `p_raw_payload JSONB DEFAULT NULL` y **`p_source_checksum VARCHAR DEFAULT NULL`**, `RAISE EXCEPTION` si el activo no existe (la seed es responsable del universo), `ON CONFLICT` con `COALESCE` para `raw_payload`/`source_checksum`.
10. **Vistas** (§11.6):
    - `vw_market_live`: expone `symbol, ticker, asset_class, source_category` (ya **no** `exchange`/`sector`) y `signal_status` (OVERSOLD/OVERBOUGHT/TRENDING si `adx>25`/NEUTRAL).
    - `vw_heatmap_enriched`: filtro `asset_class IN ('equity','etf')`, añade `asset_id` y `company_name`, y `last_rsi` con `m.rsi IS NOT NULL`.
    - `vw_heatmap_event_impact`: JOIN por `e.currency='USD'`, `importance BETWEEN 1 AND 3`, ventana `±6 h`.
11. **Particiones iniciales** `2026_09..2026_12` para `fact_heatmap_snapshot` y `fact_market_series` (§11.7).
12. **BRIN por partición**: bloque `DO` que crea el índice BRIN `timestamp_utc` sobre **cada partición hija** de `fact_market_series` (Postgres 15 no lo propaga desde el padre; §10.5).
13. **Seed `dim_country`** (11 países del `config.py` del radar) con `ON CONFLICT (country_code) DO UPDATE` (§11.8).

### 3.2 Migración one-shot §7 — **NO aplica (referencia)**

Al arrancar desde BD en blanco, `scripts/migracion_v4_20260911.sql` **no se crea** en v1.0.2. Se conserva documentado aquí para una eventual migración de una BD existente, anotando los dos puntos que el §7 **no** cubre y que serían obligatorios entonces:

- **Backfill de clase**: mover `dim_asset.asset_class` (`common|preferred|unit|''`) a `share_class` y fijar `asset_class='equity'`; sin esto, `vw_heatmap_enriched` (filtro `equity/etf`) devolvería 0 filas sobre datos existentes.
- **Drop de FK físicas** de `fact_market_series` y `fact_heatmap_snapshot` hacia `dim_asset` para igualar el DDL §11.
- `sync_checkpoint.last_event_id` → `BIGINT` y `event_id` legacy (`slug` → BIGINT) requieren `USING` cuidadoso.

### 3.3 Checklist — `scripts/03_comprobar.sql`

- Actualizar tipos/columnas esperados: `dim_asset` (taxonomía + `share_class` + `source_discovered_by/source_category` + `ticker/exchange NOT NULL`), `fact_market_series` (precisión ampliada), `fact_economic_event` (V4 RAW), `sync_checkpoint.last_event_id BIGINT`.
- Verificar firmas de `upsert_market_series` (con `p_source_checksum`, `RAISE EXCEPTION`) y `upsert_heatmap_snapshot`.
- Verificar índices (incluido `<partición>_ts_brin` **en cada partición** de `fact_market_series`, y `idx_dim_asset_class`) y vistas.
- Mantener la sección de limpieza/truncate para pruebas.

### 3.4 Seed de `dim_asset`

Fuente: roadmap fuente §13 (esbozo) y §14 (CSV por defecto).

1. **`config/radar_activos.json`** (nuevo): volcado JSON de `CONFIG_ACTIVOS` del radar (`app_backup_nasdaq/config.py`, 93 configs / 21 categorías / 110 símbolos), estructura:

   ```json
   {
     "SENTIMIENTO": { "1": { "primario": "CBOE:VIX", "respaldo": "TVC:VIX", "indicadores": ["RSI", "CCI20"] } },
     "FOREX_CENTINELA": { "2": { "primario": "OANDA:EURUSD", "respaldo": "FX_IDC:EURUSD", "indicadores": ["ADX"] } }
   }
   ```

   El volcado se genera durante la implementación con un one-liner de import (`python -c "import config as c, json; json.dump(c.CONFIG_ACTIVOS, open('config/radar_activos.json','w'))"`) desde el directorio del radar.

2. **`seed_dim_asset.py`** (nuevo, raíz `proy_heatmap/`):
   - Paso 1 — catálogo heatmap: leer `docs/dim_asset_202609112246.csv` (relativo a la raíz del repo) con `csv.DictReader`. Por fila:
     - `symbol` → `symbol`; `ticker/exchange` derivados con `split(':')`.
     - `asset_class = 'equity'` (fijo; son acciones/ADR).
     - `share_class` = valor de la col. `asset_class` del CSV (`common|preferred|unit|''`).
     - `sector`, `company_name` con `or None`.
     - `source_discovered_by = 'heatmap'`, `source_category = NULL`.
     - **Preservar `valid_from`/`created_at`/`updated_at`** del CSV (§14.2): usar `COPY` a una staging table (o incluir las columnas en el INSERT) para no perder el histórico de alta del heatmap.
     - Upsert con `ON CONFLICT (symbol)` y `COALESCE` (primer-gana): no pisa `asset_class/share_class/source_*` ni los timestamps ya existentes.
   - Paso 2 — merge radar: leer `config/radar_activos.json`, reutilizar `classify()` y `all_symbols()` del §13 (`classify()` resuelve `yield/index/commodity/etf/future/forex/crypto` por exchange+ticker), `source='radar_v4'`, `source_category` = categoría; `source_discovered_by`/`share_class` con `COALESCE` (si el símbolo ya existía por el heatmap, gana `'heatmap'`).
   - Idempotente: se puede re-ejecutar sin efectos secundarios.
   - Flags útiles: `--csv-only` (omite el merge radar), `--dry-run` (muestra cuentas sin tocar la BD), `--config path`.
   - Salida final del estilo: `dim_asset sembrada: CSV(1.005) + radar(110, OK en solapamientos)`.

### 3.5 Seed de `dim_time` (roadmap §14.3)

Generar el calendario `2026–2027` con `generate_series` (bloque SQL en el seed o en `seed_dim_asset.py --with-dim-time`), poblando `date_id`, `full_date`, `year/quarter/month`, `month_name`, `day_of_month`, `day_of_week`, `week_number`, `is_weekend`, `is_holiday`, `trading_session`. Barato y habilita análisis temporal.

### 3.6 Scraper del heatmap — `scrapper_heatmap_v0.py` / `scrapper_heatmap_v1.py`

- En `parse_vector`: el `typespecs` (`d[0]`, ej. `["common"]`) pasa a ser la **clase de acción** → se mapea a `share_class`; `asset_class = 'equity'`.
- En `get_or_create_asset`: el INSERT/ON CONFLICT de `dim_asset` incluye `share_class`, `asset_class='equity'`, `source_discovered_by='heatmap'`, `ticker`/`exchange` (ahora `NOT NULL`), con `COALESCE` para no pisotear datos previos (primer-gana).
- **Particiones + BRIN**: ambos scrapers crean la partición del mes actual (`v1.py:123-141`) y llaman `create_monthly_partitions(..., 1)`; deben crear el **BRIN** en cada partición nueva (helper compartido).
- El resto del flujo (insert en `fact_heatmap_snapshot` con `price_heatmap` y `audit_sync_run`) queda intacto.
- `create_partitions.py`: además de crear `fact_heatmap_snapshot_*` / `fact_market_series_*`, crear el BRIN de cada partición nueva de series.

### 3.7 Capa de aplicación

- `application/db/heatmap_repository.py`: añadir `AND a.asset_class IN ('equity','etf')` al JOIN con `dim_asset` en:
  - `get_heatmap_last_hour`, `get_heatmap_stats`, `get_price_evolution`, **y `get_sectors`** (4º método con query a `dim_asset`, `heatmap_repository.py:37`).
  - Alternativa: basar las consultas en `vw_heatmap_enriched` si el rendimiento lo permite.
- `application/heatmap_service.py`: exponer el filtro como constante compartida (`ASSET_CLASSES_HEATMAP = ('equity', 'etf')`) usada por el repositorio; docstring actualizado.
- Sin cambios en `app.py` salvo que se desee loguear el criterio.

### 3.8 Versionado y documentación

- `config.py:11` → `VERSION = "1.0.2"`.
- `README.md`: nueva sección de arquitectura v1.0.2 (esquema con taxonomía, seed, arranque desde BD en blanco, flujo con el proyecto externo), tabla de componentes y nota de que la ingesta radar/calendario es externa.
- **Fuera de alcance**: `docs/SCHEMA_heatmap_stock.md` y `docs/documentacion_campos_heatmap.md` no se actualizan en v1.0.2; las mejoras documentales se centralizan en este roadmap. (Quedan pendientes para una iteración futura: semántica de `asset_class`/`share_class`, FK, índices y mapeo `d[0]`.)

### 3.9 Contrato de handoff con el proyecto externo

El esquema de v1.0.2 debe satisfacer estas expectativas de los ETL externos (roadmap fuente §5, §9, §10):

- `audit_sync_run.script_name` separa pipelines (`heatmap` / `radar_v4` / `calendario_v4`); `sync_checkpoint` es compartido y su `last_event_id` es `BIGINT`.
- `upsert_market_series(symbol, ts, close, volume, rsi, cci20, bbpower, adx, pivot_r3, perf_w, change_pct, raw_payload, source_checksum)`; **lanza excepción** si el símbolo no está en `dim_asset`.
- Calendario: `event_id` int64 estable, `importance` −1..3 directo, `actual_raw/previous_raw/forecast_raw` numéricos, `raw_payload`/`payload_checksum` reconstruidos, y `first_seen_at` inmutable en el `ON CONFLICT`.
- Los ficheros de calendario legacy V3 (`2026-03/04/05` y el mixto `2026-08`) deben quedar en `DATOS_LIVE/_legacy/` para que el ETL no los lea (roadmap §10.3).

---

## 4. Orden de implementación

| Orden | Tarea | Depende de |
|---|---|---|
| 0 | (recomendado) commit del renombrado `price→price_heatmap` actualmente sin commitear | — |
| 1 | `scripts/02_init_database.sql` (rewrite desde cero → §11 + `share_class`) | 0 |
| 2 | `scripts/03_comprobar.sql` (actualizar) | 1 |
| 3 | `config/radar_activos.json` (volcado del radar) | radar disponible |
| 4 | `seed_dim_asset.py` (nuevo, CSV + radar + `dim_time`) | 1, 3 |
| 5 | `scrapper_heatmap_v1.py` (adaptar; luego `v0.py`) + BRIN en particiones | 1 |
| 6 | `application/db/heatmap_repository.py` + `application/heatmap_service.py` | 1 |
| 7 | `config.py` → `1.0.2`, `README.md`, este changelog | 1–6 |
| 8 | Verificación (sección 5) | 1–7 |

## 5. Verificación

Sin Postgres local disponible, la validación es:

1. **Revisión SQL estática** de `02_init_database.sql` contra el roadmap fuente §11 (dimensiones, hechos, índices, vistas, funciones, particiones, BRIN, seed `dim_country`).
2. **`seed_dim_asset.py --dry-run`**: confirma conteos (CSV 1.005 → `asset_class='equity'`, `share_class` 606/127/4/268; radar 110, categorías 21; solapamientos NVDA/AAPL etc. conservan fuente de la seed del heatmap por primer-gana).
3. **Los ingestores externos** devuelven éxito: `upsert_market_series` no lanza `Activo no registrado en dim_asset` y `fact_economic_event` inserta eventos V4 RAW sin colisiones de `event_id`.
4. **`03_comprobar.sql`** pasa con el esquema objetivo.
5. Checklist post-migración del roadmap fuente §8.

---

## 6. Riesgos y notas

- **`BRIN` y particionado**: en Postgres 15 el índice BRIN **no** se crea sobre el padre con particiones hijas; debe crearse **en cada partición** (bloque `DO` en el init, y en `create_partitions.py` + scrapers para particiones nuevas). Caveat §10.5.
- **Ausencia de FK físicas**: la integridad es lógica (`upsert_market_series`). Un insert directo de series/calendario con `asset_id` inexistente **no** fallará por FK; debe validarse en los ETL externos.
- **`ticker`/`exchange` NOT NULL en `dim_asset`**: el seed del CSV y el `get_or_create_asset` deben proveerlos siempre; cualquier insert directo con solo `symbol` fallará.
- **`asset_class='equity'` fijo para las 1.005 filas del CSV**: ETFs reales presentes en el heatmap quedarán como `equity` (no afecta a `vw_heatmap_enriched`, que admite ambos; la lista de ETFs de `classify()` solo aplica al radar). Caveat §14.
- **Cambios de columnas en las vistas**: `vw_market_live` deja de exponer `exchange`/`sector` y `vw_heatmap_enriched` añade `asset_id`/`company_name`; revisar consumidores si se conectan directamente a las vistas.
- **Primer-gana vs `ON CONFLICT DO UPDATE`**: el `COALESCE` en `upsert_asset`/`get_or_create_asset` materializa el criterio; migrar a `sources_discovered JSONB` sería un cambio de esquema + vistas (fuera de alcance v1.0.2).
- **`text_to_tsvector_english`**: pasa a `PARALLEL SAFE`; si se conserva `scripts/01_create_function.sql`, sincronizar ambas definiciones.
- **BD en blanco**: al no migrar datos previos, quedan obvios los riesgos de backfill y de `event_id` legacy (documentados en §3.2 por si se reutilizara la BD actual).

---

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-09-12 | Creación del roadmap de migración `proy_heatmap` 1.0.1 → 1.0.2: implementación del esquema del corte 2026-09-11 (DDL §11 + `share_class` + BRIN), seed de `dim_asset` (CSV 1.005 + radar 110 vía `config/radar_activos.json`), adaptación de scrapers del heatmap al nuevo `asset_class`/`share_class`/`source_discovered_by`, filtro `equity/etf` en la capa de aplicación, y bump de versión a 1.0.2. La ingesta de series/calendario queda delegada al proyecto externo (esquema base únicamente). |
| 2026-09-12 | Revisión de fidelidad contra roadmap §7/§9/§11/§14, `SCHEMA_heatmap_stock.md` y `endpoint_scanner_heatmap.md`. **Estrategia cambiada a arranque desde BD en blanco** (el §7 deja de ser necesario; §3.2 lo conserva como referencia con el backfill de `share_class` y el drop de FK que faltaban). Se incorporan: `pg_trgm`/`search_path`, `idx_dim_asset_class`, `sync_checkpoint.last_event_id BIGINT`, `text_to_tsvector_english PARALLEL SAFE`, índice GIN de título, seed de `dim_time` 2026–2027, preservación de `valid_from/created_at` del CSV, BRIN en particiones creadas por scrapers, `get_sectors()` en el filtro de la app, cambio de columnas de `vw_market_live`/`vw_heatmap_enriched`, y el contrato de handoff con el proyecto externo (§3.9). Se deja fuera la actualización de `SCHEMA_heatmap_stock.md`/`documentacion_campos_heatmap.md` (mejoras centralizadas en este documento). |

*Referencias: `docs/Roadmap_bd_heatmap_stock_2026-09-11.md` (§5, §7, §9, §10, §11, §13, §14), `docs/SCHEMA_heatmap_stock.md`, `docs/endpoint_scanner_heatmap.md`, `docs/dim_asset_202609112246.csv`, `app_backup_nasdaq/config.py` (CONFIG_ACTIVOS), `proy_heatmap/scripts/02_init_database.sql` y `proy_heatmap/application/db/heatmap_repository.py` vigentes.*