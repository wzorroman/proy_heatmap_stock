# Roadmap de Migración `proy_scrapping_detail` — v3.1.0 (BD Conectada)

> **Proyecto:** `proy_scrapping_detail` (Radar Intermarket TradingView)
> **Versión actual:** V4 (scraper), V4 (calendario), V3 (monitor)
> **Versión destino:** 3.1.0 (BD PostgreSQL conectada)
> **Base de datos objetivo:** `heatmap_stock` (localhost:5432, PostgreSQL 15+)
> **Fecha del documento:** 2026-09-13
> **Alcance v3.1.0:** Pipelines de escritura a BD (`fact_market_series`, `fact_economic_event`) + auditoría (`audit_sync_run`, `sync_checkpoint`) + seed de `dim_asset`. **Monitor V4 y Telegram quedan diferidos** (ver §5.6 y §15).
> **Referencia:** `docs/SCHEMA_heatmap_stock.md` (esquema BD), `docs/heatmap_stock_roadmap_migracion_a_1-0-2.md` (esquema v1.0.2 del heatmap), `docs/scrapper_documentacion_2026-09-13.md` (estado actual del scraper)
> **Estado:** Revisado — decisiones confirmadas y bitácora en §15

---

## ✅ Checklist de Implementación (2026-09-18)

> Estado global: **v3.1.0 casi completo**. El pipeline del radar y calendario están operativos y verificados contra la BD real.

### Implementados ✅

- [x] **0. Dependencias** — `psycopg2-binary>=2.9.9` añadido a `requirements.txt` e instalado en el venv (2.9.13).
- [x] **M1 | §6.1.1** — `config.py`: `VERSION="3.1.0"`, carga `.env`, `PG_*`, `DB_WRITE_ENABLED` (default `false`, estricto con `true`), `SCRIPT_NAME_SCRAPER="radar_v4"`.
- [x] **N1 | §6.1.3** — `db/postgresql_connection.py`: import roto reparado (`utils.config_logging` → `logging` estándar), cabecera `proy_heatmap` eliminada.
- [x] **M5 | §6.1.2** — `.env` / `.env_demo` con `BD_HEATMAP_*` y `DB_WRITE_ENABLED`.
- [x] **N2 | §6.2.1** — `db/market_repository.py`: `insert_market_series_batch` (cache `asset_id`, checksum canónico, `ON CONFLICT DO UPDATE`, `raw_payload=NULL`).
- [x] **N5 | §6.2.2** — `application/market_service.py`: `process_radar_batch` + `prepare_bd_row` (timestamp por fila, fallos de BD no tumban el proceso).
- [x] **M2 | §6.2.3** — `scraper_live_tradingview_v5.py` creado: logging unificado, batch buffer, flush al final + flush parcial pre-circuit-breaker. (Se creó **v5** en vez de modificar v4.)
- [x] **N3 | §6.3.1** — `db/event_repository.py` (29 columnas, dedup por `event_id`, `COALESCE`).
- [x] **N6 | §6.3.2** — `application/event_service.py`: `process_calendar_batch`.
- [x] **M3 | §6.3.3** — `calendario_tradingview_live_v5.py` integrando BD (script real es **v5**, no v4).
- [x] **N4 | §6.4.1** — `db/audit_repository.py`: `log_sync_run`, `update_checkpoint`, `get_last_run`.
- [x] **§6.5** — `db/partitions.py`: `ensure_current_month_partition` (crea solo si falta) + BRIN por partición.
- [x] **N7 | §6.7** — `seed_symbols.py`: altas nuevas primer-gana, flags `--dry-run`/`--check` (verificado: **0 faltantes**).
- [x] **M4 | §6.8.1** — `run_scraper_tradingview.sh`: apunta al V5, `check_db_connection` (degrada a legacy) + invoca `seed_symbols.py`.
- [x] **§6.8.2** — `run_calendario_tradingview.sh`: `check_db_connection` + rutas `DATOS_LIVE_CALENDARIO`.
- [x] **N10 | §6.10** — Scripts SQL `proy_heatmap/scripts/04_migration_3.1.0.sql` … `07_cleanup_legacy.sql` creados.
- [x] **Verificación BD real** — `fact_market_series` con **110/110 filas** del primer ciclo (2026-09-18); `audit_sync_run` `radar_v4 → SUCCESS (110/110/0)`; `sync_checkpoint` `radar_v4 → 110 procesados`; partición `fact_market_series_2026_09` garantizada; mapeo CSV↔BD verificado fila a fila.
- [x] **Discrepancia menor** — `.env` usa `BD_HEATMAP_SERVER` pero `config.py` lee `BD_HEATMAP_HOST` (funciona por coincidencia del default `localhost`); alinear nomenclatura.

### Sin modificacion
- [ ] **N8 | §6.6** — Monitor V4 BD-aware (`monitor_tradingview_live_v4.py`) + Telegram. **[DIFERIDO]** a iteración posterior; sigue operando el monitor V3 por archivos.

### Pendientes / Diferidos ⏳

- [ ] **N9 | §6.3.4** — `retention_events.py`: job de retención de `raw_payload` de eventos (> 6 meses). El SQL `05_retention_events.sql` ya existe; falta el script Python + entrada de cron mensual.
- [ ] **§6.9** — `readme.md` / `readme_crontab.md` / `docs/scrapper_documentacion_2026-09-13.md` actualizados con la arquitectura BD.

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Objetivos de la Migración](#2-objetivos-de-la-migración)
3. [Estado Actual (v4/v3)](#3-estado-actual-v4v3)
4. [Estado Objetivo (3.1.0)](#4-estado-objetivo-310)
5. [Razón de Decisiones](#5-razón-de-decisiones)
6. [Bloques de Trabajo](#6-bloques-de-trabajo)
   - 6.1 [Configuración y Conexión a BD](#61-configuración-y-conexión-a-bd)
   - 6.2 [Pipeline Radar → fact_market_series](#62-pipeline-radar--fact_market_series)
   - 6.3 [Pipeline Calendario → fact_economic_event](#63-pipeline-calendario--fact_economic_event)
   - 6.4 [Auditoría y Checkpoints](#64-auditoría-y-checkpoints)
   - 6.5 [Particionamiento y BRIN](#65-particionamiento-y-brin)
   - 6.6 [Monitor v4 (BD-aware)](#66-monitor-v4-bd-aware)
   - 6.7 [Seed de Configuración](#67-seed-de-configuración)
   - 6.8 [Scripts Shell y Cron](#68-scripts-shell-y-cron)
   - 6.9 [Documentación y Versionado](#69-documentación-y-versionado)
   - 6.10 [Scripts SQL de migración](#610-scripts-sql-de-migración)
7. [Flujos de Datos (Diagramas)](#7-flujos-de-datos-diagramas)
8. [Matriz de Mapeo de Campos](#8-matriz-de-mapeo-de-campos)
9. [Orden de Implementación](#9-orden-de-implementación)
10. [Estrategia de Prueba y Verificación](#10-estrategia-de-prueba-y-verificación)
11. [Riesgos y Mitigaciones](#11-riesgos-y-mitigaciones)
12. [Plan de Rollback](#12-plan-de-rollback)
13. [Criterios de Aceptación](#13-criterios-de-aceptación)
14. [Changelog](#14-changelog)
15. [Bitácora de Decisiones y Aclaraciones](#15-bitácora-de-decisiones-y-aclaraciones)

---

## 1. Resumen Ejecutivo

El proyecto `proy_scrapping_detail` captura datos financieros de TradingView en tres procesos: un **scraper de activos** (110 símbolos, */3 min), un **calendario económico** (11 países, */15 min), y un **monitor** (*/5 min). Actualmente toda la persistencia es en archivos CSV con rotación de 7 días + histórico mensual.

La migración a **v3.1.0** conecta estos procesos con la base de datos PostgreSQL `heatmap_stock` (ya desplegada por `proy_heatmap` en v1.0.2), estableciendo los **pipelines de datos** que el esquema define pero que no existen: `fact_market_series` (series técnicas), `fact_economic_event` (calendario V4 RAW) y `audit_sync_run` (trazabilidad).

**Alcance de esta iteración:** pipelines de escritura + auditoría + seed de `dim_asset`. El **monitor V4 (BD-aware) y las alertas Telegram se difieren** a una iteración posterior; durante 3.1.0 el monitoreo continúa con `monitor_tradingview_live_v3.py` (por archivos).

> **✅ ESTADO DE IMPLEMENTACIÓN (2026-09-18) — Alcance 3.1.0 COMPLETADO:**
> Se implementaron todos los bloques de trabajo (§6.1–§6.10 excepto §6.6, diferido): `psycopg2-binary` instalado (orden 0), `config.py` con `DB_WRITE_ENABLED`/`PG_*`/`SCRIPT_NAME_SCRAPER`, conector local reparado, `db/partitions.py`, `db/market_repository.py`, `db/event_repository.py`, `db/audit_repository.py`, `application/market_service.py`, `application/event_service.py`, `seed_symbols.py`, `scraper_live_tradingview_v5.py` (V4 → V5 con pipeline BD), `run_scraper_tradingview.sh` y `run_calendario_tradingview.sh` con verificación BD + seed, y scripts SQL `proy_heatmap/scripts/04`–`07`.
>
> **Verificado en BD real (2026-09-18):** `fact_market_series` con **110/110 filas** del primer ciclo, `source_checksum` presente, `raw_payload` NULL, `audit_sync_run` con `radar_v4 → SUCCESS (fetched=110, upserted=110, failed=0)`, `sync_checkpoint` con `radar_v4 → records_processed=110`, partición `fact_market_series_2026_09` garantizada. `seed_symbols.py --check` → **0 símbolos faltantes**.
>
> **Pendiente (fuera/restante de 3.1.0):** `retention_events.py` (N9, cron mensual — SQL `05` listo), monitor V4 BD-aware + Telegram (§6.6, diferido), README/docs actualizados (§6.9).

**Estado verificado de la BD (2026-09-13):** `dim_asset` = 1.060 filas (1.015 `heatmap` + 45 `radar_v4`); los **110 símbolos del radar ya están presentes** (0 ausentes). `fact_market_series` y `fact_economic_event` existen con particiones/BRIN pero con 0 filas. `audit_sync_run` tiene 1 fila (`scrapper_heatmap_v1`) y `sync_checkpoint` está vacía.

**Principios rectores:**

- **CSV se mantiene como raw buffer y fallback** — la BD es el almacén canónico, pero los archivos locales persisten como respaldo y para inspección manual.
- **Compatibilidad donde importa** — el formato CSV, `CONFIG_ACTIVOS` y la lógica de lock/backoff/rotación no cambian; se añaden capas de escritura a BD y verificación de conexión en los shell.
- **Usar los mismos patrones del heatmap** — conector local (`PostgreSQLConnector`), `execute_values` batch y `COALESCE`; `fact_market_series` se escribe con INSERT batch `ON CONFLICT` (no con la función `upsert_market_series`).
- **Cada pipeline es independiente** — la falla de uno no afecta al otro ni al CSV.
- **Trazabilidad vía `audit_sync_run`** — cada ejecución se registra; el monitor basado en BD que consume esa tabla queda **diferido**.

---

## 2. Objetivos de la Migración

| # | Objetivo | Justificación | Estado |
|---|----------|---------------|--------|
| 1 | **Escritura de series técnicas a `fact_market_series`** | El esquema v1.0.2 define la tabla pero sin pipeline de datos. El scraper ya captura `close`, `volume`, `RSI`, `CCI20`, `BBPower`, `ADX`, `Pivot.Camarilla.R3`, `Perf.W`, `change` — campos que mapean 1:1 a las columnas de la tabla. | ✅ **Implementado** (V5, 110/110) |
| 2 | **Escritura de eventos económicos a `fact_economic_event`** | El calendario V4 RAW captura 21 campos; el esquema define la tabla con precisión V4. La migración establece el pipeline de handoff. | ✅ **Implementado** (V5, `event_service`) |
| 3 | **Trazabilidad vía `audit_sync_run`** | Cada ejecución de scraper o calendario debe registrarse con métricas (registros obtenidos, insertados, fallidos, estado, modo de ejecución). | ✅ **Implementado** (`radar_v4` SUCCESS) |
| 4 | **Checkpoint de reanudación vía `sync_checkpoint`** | Permite backfills parciales y reanudación ante fallos sin re-procesar todo. | ✅ **Implementado** (110 procesados) |
| 5 | **[DIFERIDO] Monitor v4 basado en BD** | Fuera del alcance de 3.1.0. La inspección de `audit_sync_run` (último registro por `script_name`) reemplazará la lectura de archivos CSV en una iteración posterior; mientras tanto se conserva el monitor V3. | ⏸️ Diferido |
| 6 | **Seed de dim_asset desde el universo del scraper** | Sembrar **solo altas nuevas** de `CONFIG_ACTIVOS` → `dim_asset`. Verificado 2026-09-13: los 110 símbolos del radar ya existen, por lo que hoy el seed es idempotente/no-op y su función es cubrir símbolos agregados a futuro. | ✅ **Implementado** (`seed_symbols.py`, 0 faltantes) |
| 7 | **Mantener CSV como fallback** | El buffer de 7 días + histórico mensual sigue funcionando; la BD no reemplaza el CSV en esta iteración, lo complementa. | ✅ **Implementado** (sin cambios CSV) |

---

## 3. Estado Actual (v4/v3)

### 3.1 Scraper de Activos (`scraper_live_tradingview_v4.py`)

| Aspecto | Estado actual |
|---------|---------------|
| Fuente | `scanner.tradingview.com/symbol` (GET) |
| Símbolos | 110 únicos (93 claves × primario+respaldo) |
| Campos | 8 técnicos: `close`, `volume`, `RSI`, `CCI20`, `BBPower`, `ADX`, `Pivot.Camarilla.R3`, `Perf.W`, `change` + 3 metadatos (`timestamp_utc`, `fecha_iso`, `simbolo`) |
| Destino | CSV por símbolo (`DATOS_LIVE/{SYM}/{SYM}.csv`) |
| Escritura | Append incremental (header condicional) |
| Rotación | 7 días LIVE → histórico mensual |
| Lock | `fcntl` exclusivo anti-solapamiento de ciclos |
| Rate limit | Backoff 15/45/120 s + circuit breaker (3 fallos) |
| Consolidado | `--consolidate` genera snapshot único |

### 3.2 Calendario Económico (`calendario_tradingview_live_v4.py`)

| Aspecto | Estado actual |
|---------|---------------|
| Fuente | `economic-calendar.tradingview.com/events` (GET) |
| Países | 11: US, GB, DE, FR, IT, ES, CN, JP, AU, CA, CH |
| Campos | 21 campos RAW (id, title, country, indicator, ticker, comment, category, period, referenceDate, source, source_url, actual, previous, forecast, actualRaw, previousRaw, forecastRaw, currency, unit, importance, date) |
| Destino | CSV (`eventos_calendario.csv`) + JSON checkpoint |
| Escritura | Merge + dedup por `id` + rotación 7d → histórico mensual |
| Checkpoint | `checkpoint.json` con `ultimo_timestamp`, `eventos_acumulados`, `eventos_encontrados`, `fecha_ultima_revision` |

### 3.3 Monitor (`monitor_tradingview_live_v3.py`)

| Aspecto | Estado actual |
|---------|---------------|
| Vigila | 3 CSVs de activos (QQQ, XAUUSD, EURUSD) + 1 checkpoint JSON |
| Fuente de verdad | Timestamps en archivos locales |
| Alertas | Telegram (módulo `notificador_telegram.py` **ausente**) |
| Anti-spam | 60 s entre alertas (documentado como 30 min) |
| Umbrales | WARNING > 1.5 ciclos, ALERTA > 2 ciclos |

### 3.4 Limitaciones Identificadas

| # | Limitación | Impacto |
|---|-----------|---------|
| L1 | **Sin persistencia en BD** | Los datos de series técnicas y calendario no alimentan las vistas analíticas ni el radar del heatmap |
| L2 | **Sin trazabilidad de ejecución** | Imposible saber cuándo falló un pipeline o cuántos registros procesó |
| L3 | **Monitor dependiente de archivos** | Las alertas dependen de rutas hardcodeadas; el monitor V3 vigila rutas desalineadas con el calendario V4 |
| L4 | **`dim_asset` ya cubre el radar** | Verificado 2026-09-13: 1.060 activos y los 110 del radar están presentes (45 `radar_v4` + 65 `heatmap`). Ya no es bloqueante; el seed solo cubre altas nuevas. |
| L5 | **Sin datos en series ni eventos** | `fact_market_series` y `fact_economic_event` existen con particiones/BRIN pero con 0 filas; falta el pipeline de ingesta. |
| L6 | **`notificador_telegram.py` ausente** | El monitor no puede enviar alertas reales |

---

## 4. Estado Objetivo (3.1.0)

### 4.1 Arquitectura Objetivo

```
                    crontab (Lun–Jue / Vie hasta 16:59)
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    run_scraper.sh         run_calendario.sh     monitor_v4.py
    (cada 3 min)           (cada 15 min)         (cada 5 min)
            │                   │                   │
            ▼                   ▼                   ▼
    scraper_v4.py          calendario_v4.py      monitor_v4.py
            │                   │                   │
     ┌──────┴──────┐     ┌──────┴──────┐     ┌─────┴──────┐
     │  fetch_from  │     │  fetch_cal  │     │ lee BD     │
     │  _scanner()  │     │  _events()  │     │ audit_sync │
     │  ↓           │     │  ↓          │     │ _run       │
     │  CSV (buffer)│     │  CSV (buffer│     │            │
     │  ↓           │     │  ↓          │     │ lee CSV    │
     │  BD: fact_   │     │  BD: fact_  │     │ (fallback) │
     │  market_     │     │  economic_  │     │            │
     │  series      │     │  event      │     │ Telegram   │
     │  ↓           │     │  ↓          │     │ (futuro)   │
     │  audit_sync  │     │  audit_sync │     │            │
     │  _run        │     │  _run       │     │            │
     │  ↓           │     │  ↓          │     │            │
     │  sync_       │     │  sync_      │     │            │
     │  checkpoint  │     │  checkpoint │     │            │
     └──────────────┘     └─────────────┘     └────────────┘
            │                   │
            └─────────┬─────────┘
                      ▼
            PostgreSQL: heatmap_stock
            ┌──────────────────────────────┐
            │  DIMENSIONES                 │
            │  dim_asset (SCD2, taxonomía) │
            │  dim_country (11 países)     │
            │  dim_time (2026-2027)        │
            │                              │
            │  HECHOS                      │
            │  fact_market_series (mensual)│ ← scraper
            │  fact_economic_event         │ ← calendario
            │  fact_heatmap_snapshot       │ ← heatmap (otro proyecto)
            │                              │
            │  AUDITORÍA                   │
            │  audit_sync_run              │ ← ambos
            │  sync_checkpoint             │ ← ambos
            │                              │
            │  VISTAS                      │
            │  vw_market_live              │
            │  vw_heatmap_enriched         │
            │  vw_heatmap_event_impact     │
            └──────────────────────────────┘
```

> **Nota (alcance 3.1.0):** el nodo `monitor_v4.py` del diagrama está **diferido**. En esta iteración se mantiene `monitor_tradingview_live_v3.py` operando sobre archivos; el monitor BD-aware se implementa en la iteración siguiente.

### 4.2 Componentes Nuevos (v3.1.0)

| # | Componente | Descripción |
|---|-----------|-------------|
| N1 | `db/postgresql_connection.py` | Conector PostgreSQL **local** (copia autónoma del patrón del heatmap). Corregir el import roto `utils.config_logging` → `logging` estándar y eliminar la cabecera `proy_heatmap`. | ✅ **Implementado** |
| N2 | `db/market_repository.py` | Queries de escritura/lectura para `fact_market_series` | ✅ **Implementado** |
| N3 | `db/event_repository.py` | Queries de escritura/lectura para `fact_economic_event` | ✅ **Implementado** |
| N4 | `db/audit_repository.py` | Queries para `audit_sync_run` y `sync_checkpoint` | ✅ **Implementado** |
| N5 | `application/market_service.py` | Orquestación del pipeline radar → BD | ✅ **Implementado** |
| N6 | `application/event_service.py` | Orquestación del pipeline calendario → BD | ✅ **Implementado** |
| N7 | `seed_symbols.py` | Sincronización de `CONFIG_ACTIVOS` → `dim_asset` (solo altas nuevas) | ✅ **Implementado** (0 faltantes) |
| N8 | `monitor_tradingview_live_v4.py` | **[DIFERIDO]** Monitor basado en BD + Telegram (iteración posterior) | ⏸️ Diferido |
| N9 | `retention_events.py` | Mantenimiento: `NULL` en `fact_economic_event.raw_payload` > 6 meses (cron mensual) | ⏳ Pendiente (SQL `05` listo) |
| N10 | `proy_heatmap/scripts/04`–`07` | Scripts SQL versionados de migración/retención/verificación (DDL fuera del runtime; ver §6.10) | ✅ **Implementado** |

### 4.3 Componentes Modificados

| # | Componente | Cambio |
|---|-----------|--------|
| M1 | `config.py` | Cargar `.env` con `python-dotenv`; añadir `PG_*` desde `BD_HEATMAP_*` y `DB_WRITE_ENABLED`; `VERSION = "3.1.0"`. | ✅ **Implementado** |
| M2 | `scraper_live_tradingview_v4.py` | Unificar logging (reemplazar `print`); buffer de batch por ciclo y flush a `market_service.process_radar_batch()`; flush parcial antes del circuit breaker. → **Nuevo script `scraper_live_tradingview_v5.py`** | ✅ **Implementado** (V5, no modifica V4) |
| M3 | `calendario_tradingview_live_v4.py` | Añadir `import config` (hoy no lo tiene) y logging; llamada a `event_service.process_calendar_batch()` tras guardar CSV y checkpoint local. → **Script real: `calendario_tradingview_live_v5.py`** | ✅ **Implementado** |
| M4 | `run_scraper_tradingview.sh` | Verificar conexión BD (degradar a legacy si falla) e invocar `seed_symbols.py` si faltan símbolos del radar. | ✅ **Implementado** |
| M5 | `.env` / `.env_demo` | Añadir variables `BD_HEATMAP_*` y `DB_WRITE_ENABLED`. | ✅ **Implementado** |
| M6 | `requirements.txt` | Añadir `psycopg2-binary` (hoy ausente) e instalarlo en el venv. | ✅ **Implementado** (2.9.13 en venv) |

### 4.4 Componentes Invariantes

| # | Componente | Razón de no cambio |
|---|-----------|-------------------|
| I1 | `CONFIG_ACTIVOS` | Fuente de verdad del universo; la BD lo refleja, no lo reemplaza |
| I2 | Formato CSV | Buffer raw, fallback, inspección manual — se mantiene |
| I3 | Lock `fcntl` | Protección anti-solapamiento sigue siendo necesaria |
| I4 | Backoff / circuit breaker | Rate limit de TradingView no cambia |
| I5 | Rotación CSV 7d + histórico | Independiente de la retención BD |
| I6 | `monitor_tradingview_live_v3.py` | **Sin cambios en 3.1.0** — sigue monitoreando archivos hasta la iteración del monitor V4 |

---

## 5. Razón de Decisiones

### 5.1 ¿Por qué un `PostgreSQLConnector` local?

**Decisión (confirmada):** Usar el conector **ya presente** en `proy_scrapping_detail/db/postgresql_connection.py` como copia autónoma del patrón del heatmap. **No se importa nada de `proy_heatmap`.**

**Razón:** El proyecto debe ser autónomo; una dependencia cruzada de rutas/PYTHONPATH entre proyectos es frágil. El conector tiene los métodos `execute_query`, `execute_batch`, `execute_values` y soporte de `RealDictCursor`.

**Acción obligatoria:** el archivo local está **roto** — importa `from utils.config_logging import get_logger`, módulo que no existe en `proy_scrapping_detail`. Se reemplaza por `logging` estándar (o un `utils/config_logging.py` local) y se elimina la cabecera `# file: proy_heatmap/...`.

**Alternativa descartada:** SQLAlchemy — dependencia pesada e innecesaria para operaciones batch simples. El conector directo con `psycopg2` es suficiente y ya probado en la BD real.

### 5.2 ¿Por qué mantener CSV + BD (no reemplazar)?

**Decisión:** Los pipelines escriben a CSV (buffer local) **y** a BD (almacén canónico) en paralelo.

**Razón:**
1. **Fallback:** Si la BD cae, el scraper sigue funcionando y los datos quedan en CSV para recuperación manual.
2. **Inspección:** Los operadores pueden revisar datos con `head`, `tail`, `cat` sin conexión a BD.
3. **Independencia:** El scraper puede ejecutarse sin BD (modo legacy) mientras se prueba la conexión.
4. **Compatibilidad:** El monitor V3 sigue funcionando con archivos mientras se migra al V4 BD-aware.

**Riesgo:** Duplicación de almacenamiento. Mitigado por la retención 7d del CSV y por **omitir `raw_payload` en BD** (§15.4): la tabla guarda solo columnas estructuradas (~120–150 MB/mes).

### 5.3 ¿Por qué INSERT batch directo en vez de `upsert_market_series()`?

**Decisión (revisada 2026-09-13):** Escribir `fact_market_series` con `INSERT ... ON CONFLICT (asset_id, timestamp_utc) DO UPDATE` vía `execute_values` (un solo round-trip por ciclo), resolviendo `asset_id` con un cache en memoria desde `dim_asset`. **No** se usa la función PL/pgSQL `upsert_market_series()` para el pipeline radar.

**Razón:**
1. **Rendimiento:** 110 llamadas PL/pgSQL por ciclo (cada 3 min) vs. 1 sentencia batch. El batch reduce la latencia de BD y mantiene el ciclo dentro de la ventana de 3 minutos.
2. **Cache de `asset_id`:** una única query por ciclo (`SELECT symbol, asset_id FROM dim_asset WHERE is_active AND current_version`); los símbolos ausentes se registran con warning y se omiten.
3. **Sinergia con `seed_symbols.py`:** el seed garantiza la cobertura del universo, por lo que la validación dura de la función deja de ser necesaria ciclo a ciclo.
4. **Idempotencia:** `ON CONFLICT DO UPDATE` sobreescribe con el valor más reciente y actualiza `ingested_at` si se recaptura el mismo `(asset_id, timestamp_utc)`.

**Trade-off asumido:** se pierde el `RAISE EXCEPTION` de la función; la integridad lógica se cubre con el seed + el cache de resolución. El SQL inline replica únicamente la semántica de upsert requerida.

**Alternativa descartada:** `upsert_market_series()` por fila — válida para integridad referencial, pero 110 round-trips por ciclo.

> **Corrección de la revisión previa:** este documento se contradecía (§5.3 pedía la función; §6.2.1 usaba INSERT directo). La decisión vigente es **INSERT batch directo**.

### 5.4 ¿Por qué `event_id BIGINT` y no `VARCHAR(100)`?

**Decisión:** Usar el `event_id` numérico del API de TradingView como `BIGINT PK`.

**Razón:** El esquema v1.0.2 del heatmap (`SCHEMA_heatmap_stock.md` §4.3) define `event_id BIGINT PRIMARY KEY`. El API devuelve IDs numéricos estables (ej. `421311`). Usar `BIGINT` es más eficiente que `VARCHAR` para dedup y join.

**Nota:** El calendario V4 RAW guarda `id` como string en CSV; la conversión a `BIGINT` es trivial (`int(evento_raw.get('id'))`).

### 5.5 ¿Por qué `sync_checkpoint` con `last_event_id BIGINT`?

**Decisión:** Usar `sync_checkpoint` para marcar el último `event_id` procesado, no un timestamp.

**Razón:** Los timestamps pueden tener resolución insuficiente si dos ejecuciones procesan eventos del mismo minuto. Un `event_id` creciente garantiza que no se re-procesen eventos ya insertados (dedup definitivo). El esquema v1.0.2 ya lo define como `BIGINT`.

**Nota crítica (2026-09-13):** `sync_checkpoint.last_timestamp` es `NOT NULL` (sin default). El calendario se guía por `last_event_id`, pero `update_checkpoint` **debe enviar siempre** un `last_timestamp` (p. ej. el `date` máximo de los eventos capturados, o `now()`), de lo contrario el primer INSERT fallará por violación de `NOT NULL`.

### 5.6 ¿Por qué el monitor migra a BD en v4? — [DIFERIDO]

**Estado:** **Fuera del alcance de 3.1.0.** Se documenta la decisión para la iteración siguiente.

**Decisión (diferida):** El monitor V4 leerá `audit_sync_run` en vez de inspeccionar archivos.

**Razón:**
1. **Desacoplamiento:** Deja de depender de rutas de archivos que pueden cambiar (como ya pasó con `DATOS_LIVE` vs `DATOS_LIVE_CALENDARIO`).
2. **Veracidad:** `audit_sync_run` registra el momento real de ejecución, no el timestamp de un archivo que puede estar desactualizado.
3. **Granularidad:** Puede vigilar todos los pipelines (radar, calendario, heatmap) desde una sola tabla.
4. **Trazabilidad:** Puede mostrar en la alerta de Telegram el `error_message` real del último fallo, no solo "archivo no encontrado".

**Alternativa descartada:** Mantener monitor por archivos + añadir BD — complejiza sin beneficio claro. El archivo CSV sigue existiendo como fallback; el operador puede revisarlo manualmente.

### 5.7 ¿Por qué `seed_symbols.py` como script separado?

**Decisión (confirmada 2026-09-13):** Script dedicado que sincroniza `CONFIG_ACTIVOS` → `dim_asset` con **solo altas nuevas** (no re-etiqueta ni sobreescribe símbolos existentes), ejecutado antes del primer ciclo o al detectar símbolos faltantes.

**Razón:**
1. **Precondición del pipeline:** todo símbolo a escribir debe existir en `dim_asset`. El seed cubre los que falten.
2. **Idempotente y hoy no-op:** verificado 2026-09-13 — los 110 símbolos del radar ya existen (45 `radar_v4` + 65 `heatmap`). El script **no debe** tocar `source_discovered_by` ni la metadata de los 65 heredados como `heatmap` (criterio primer-gana).
3. **Separación de responsabilidades:** la seed es un paso de configuración, no de ejecución continua.
4. **Herencia del heatmap:** reutiliza el patrón de `seed_dim_asset.py` del heatmap, pero limitado a altas nuevas.

**Impacto en criterios:** el criterio de aceptación deja de ser "110 filas con `source_discovered_by='radar_v4'`" (inalcanzable por primer-gana) y pasa a ser "0 símbolos del radar ausentes en `dim_asset`" (ver §13).

### 5.8 ¿Por qué BRIN por partición y no en la tabla padre?

**Decisión:** Crear el índice BRIN `timestamp_utc` en cada partición hija de `fact_market_series`.

**Razón:** En PostgreSQL 15, el índice BRIN **no se propaga** desde la tabla padre a las particiones hijas (caveat §10.5 del roadmap del heatmap). Crearlo en el padre no tiene efecto sobre las hijas. El `create_partitions.py` del heatmap ya implementa este patrón con `ensure_brin_for_partition()`.

---

## 6. Bloques de Trabajo

> **Estado de implementación (2026-09-18): ✅ §6.1, §6.2, §6.3, §6.4, §6.5, §6.7, §6.8, §6.10 completados · ⏸️ §6.6 diferido (monitor BD-aware). Verificado en BD real con 110/110 series del radar.**

### 6.1 Configuración y Conexión a BD — ✅ IMPLEMENTADO

#### 6.1.1 `config.py` — Extender con variables BD

**Razón:** El scraper actual no tiene configuración de BD ni carga `.env` (solo `CONFIG_ACTIVOS` hardcodeado). Las variables `BD_HEATMAP_*` existen en el `.env` del heatmap, pero **hay que añadirlas al `.env` de este proyecto**.

**Pseudocódigo de la extensión:**

```
config.py existente:
    VERSION = "3.0"                   # → "3.1.0"
    CONFIG_ACTIVOS = { ... }          # SIN CAMBIO
    METADATOS_ACTIVOS = { ... }       # SIN CAMBIO

config.py añadido:
    import os
    from dotenv import load_dotenv
    load_dotenv('.env')               # hoy el scraper NO carga .env

    # --- Configuración de BD (nuevo) ---
    PG_HOST = os.getenv('BD_HEATMAP_HOST', 'localhost')
    PG_PORT = int(os.getenv('BD_HEATMAP_PORT', '5432'))
    PG_DATABASE = os.getenv('BD_HEATMAP_DATABASE', 'heatmap_stock')
    PG_USER = os.getenv('BD_HEATMAP_USER', 'postgres')
    PG_PASSWORD = os.getenv('BD_HEATMAP_PASSWORD', 'postgres')

    # --- Modo de operación (nuevo) ---
    DB_WRITE_ENABLED = os.getenv('DB_WRITE_ENABLED', 'false').lower() == 'true'
    # Default false: arranca en CSV y se activa explícitamente en .env
    # Si DB_WRITE_ENABLED = false, el scraper funciona solo con CSV (legacy)

    # --- Nombre del script para audit_sync_run (nuevo) ---
    SCRIPT_NAME_SCRAPER = 'radar_v4'
    SCRIPT_NAME_CALENDARIO = 'calendario_v4'
```

> **Decisión (2026-09-13):** `config.py` exige las variables `BD_HEATMAP_*` **solo cuando `DB_WRITE_ENABLED=true`**. Con `false` arranca en CSV puro sin requerirlas. Si el modo BD está activo y faltan, **falla en el import** (estricto). No hay degradación silenciosa.

**Justificación de `DB_WRITE_ENABLED`:**
- Permite ejecutar el scraper **sin BD** durante pruebas o si la BD no está disponible.
- Facilita el despliegue incremental: primero se despliega con `DB_WRITE_ENABLED=false`, se valida, y luego se activa.

#### 6.1.2 `.env` / `.env_demo` — Añadir variables BD

**Razón:** el `.env` actual del scraper solo tiene Telegram y `PROJECT_DIR`; hay que añadir las variables de BD tanto al `.env` real como al `.env_demo`.

**Pseudocódigo:**

```
# Configuración de BD (misma nomenclatura que proy_heatmap)
BD_HEATMAP_HOST=localhost
BD_HEATMAP_PORT=5432
BD_HEATMAP_DATABASE=heatmap_stock
BD_HEATMAP_USER=postgres
BD_HEATMAP_PASSWORD=postgres

# Modo de operación (true=escribe BD, false=solo CSV)
DB_WRITE_ENABLED=true
```

#### 6.1.3 `db/postgresql_connection.py` — Conector

**Decisión (confirmada):** usar el archivo **local ya existente** `proy_scrapping_detail/db/postgresql_connection.py`. **No importar de `proy_heatmap`.**

**Bloqueante actual:** el archivo importa `from utils.config_logging import get_logger`, que no existe en este proyecto (no hay carpeta `utils/`). Reemplazar por `logging` estándar y quitar la cabecera `# file: proy_heatmap/...`.

**Pseudocódigo de la interfaz (sin cambios):**

```
class PostgreSQLConnector:
    constructor(host, port, database, user, password)
    
    connect() → bool
    disconnect()
    
    execute_query(query, params) → List[Dict]
    execute_batch(query, params_list) → int
    execute_values(query, params_list, template) → List[Dict]
    
    # Soporte context manager
    __enter__() → self
    __exit__(exc_type, exc_val, exc_tb)
```

**Justificación de la copia local:** autonomía total; el scraper no se rompe si el heatmap cambia su conector o su estructura de proyecto.

---

### 6.2 Pipeline Radar → `fact_market_series` — ✅ IMPLEMENTADO

#### 6.2.1 `db/market_repository.py` — Repositorio de escritura

**Función principal: `insert_market_series_batch(rows)`**

**Pseudocódigo:**

```
función insert_market_series_batch(rows: List[Dict]) → int:
    """
    Inserta un batch de registros en fact_market_series.
    Cada row contiene:
        symbol, timestamp_utc, close, volume, rsi, cci20, bbpower, adx,
        pivot_camarilla_r3, perf_w, change_pct
    raw_payload se OMITE (NULL) por costo de almacenamiento (~366 MB/mes).

    Retorna: número de registros insertados/actualizados
    """
    params = []
    for row in rows:
        # 1. Obtener asset_id desde dim_asset (query previa o cache)
        asset_id = resolver_asset_id(row['symbol'])  # cache en memoria
        
        if asset_id is None:
            log.warning(f"Símbolo {row['symbol']} no existe en dim_asset — saltando")
            continue
        
        # 2. Calcular source_checksum sobre el subconjunto canónico (SIN timestamp)
        canonico = {
            'symbol': row['symbol'],
            'close': row['close'], 'volume': row['volume'],
            'rsi': row['rsi'], 'cci20': row['cci20'], 'bbpower': row['bbpower'],
            'adx': row['adx'], 'pivot_camarilla_r3': row['pivot_camarilla_r3'],
            'perf_w': row['perf_w'], 'change_pct': row['change_pct'],
        }
        checksum = sha256(json.dumps(canonico, sort_keys=True, default=str))
        
        # 3. Preparar tupla para execute_values (raw_payload = NULL)
        params.append((
            asset_id,
            row['timestamp_utc'],
            row['close'],
            row['volume'],
            row['rsi'],
            row['cci20'],
            row['bbpower'],
            row['adx'],
            row['pivot_camarilla_r3'],
            row['perf_w'],
            row['change_pct'],
            checksum
        ))
    
    if not params:
        return 0
    
    # 4. UPSERT batch via execute_values
    upsert_query = """
        INSERT INTO fact_market_series (
            asset_id, timestamp_utc, close, volume, rsi, cci20,
            bbpower, adx, pivot_camarilla_r3, perf_w, change_pct,
            source_checksum
        ) VALUES %s
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
            source_checksum = EXCLUDED.source_checksum,
            ingested_at = CURRENT_TIMESTAMP
    """
    template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    conn.execute_values(upsert_query, params, template=template)
    return len(params)
```

**Justificación de `ON CONFLICT (asset_id, timestamp_utc)`:**
- La PK compuesta de `fact_market_series` es `(asset_id, timestamp_utc)`.
- Si el mismo activo se captura dos veces en el mismo instante, el segundo insert sobreescribe el primero (`DO UPDATE`).
- `ingested_at` se actualiza para indicar la última escritura.

**Justificación del cache de `asset_id`:**
- El scraper captura 110 símbolos; hacer 110 queries individuales por `symbol → asset_id` es innecesario.
- Se hace una query inicial `SELECT symbol, asset_id FROM dim_asset WHERE is_active AND current_version` y se cachea en un `dict`.
- Los símbolos ausentes se registran con `log.warning` y se **omiten** del batch (no se auto-crean aquí; el `seed_symbols.py` cubre las altas).

**Correcciones de la revisión (2026-09-13):**
- **Timestamp:** se usa el **timestamp real por fila** (`data['timestamp_utc']`, epoch UTC → `timestamptz`), no un `now_utc()` compartido por todo el batch.
- **Campos:** el endpoint `/symbol` devuelve un dict con **claves nombradas**; el mapeo es por nombre (`RSI`, `CCI20`, `BBPower`, `ADX`, `Pivot.M.Camarilla.R3`, `Perf.W`, `change`, `close`, `volume`). Los índices `d[0]`, `d[14]`, `d[23]` del apartado §8.1 original eran incorrectos (formato del endpoint `/scan`).
- **`raw_payload` OMITIDO:** se guarda `NULL` por costo de almacenamiento (~366 MB/mes solo de raw; ver §15.4). El CSV sigue siendo el buffer crudo.
- **`source_checksum` canónico:** se calcula sobre el subconjunto de 9 campos de mercado + símbolo (sin timestamp), para que sea estable entre capturas y sirva para detectar cambios reales.

#### 6.2.2 `application/market_service.py` — Orquestación

**Pseudocódigo del flujo:**

```
función process_radar_batch(scanner_data: List[Dict]) → int:
    """
    Flujo BD: scanner data → fact_market_series → auditoría.
    (El CSV ya se escribió en el bucle del scraper.)
    """
    run_start = now_utc()
    
    # 1. Conectar a BD (si DB_WRITE_ENABLED)
    if not config.DB_WRITE_ENABLED:
        log.info("Modo legacy: solo CSV, sin BD")
        return 0
    
    db = PostgreSQLConnector(...)
    if not db.connect():
        # Sin conexión no se puede escribir audit_sync_run:
        # se registra en el log local y se continúa (el CSV ya está a salvo).
        log.error("BD: no se pudo conectar — se omite la escritura de este ciclo")
        return 0
    
    try:
        # 2. Preparar datos para BD
        bd_rows = []
        
        for item in scanner_data:
            symbol = item.get('simbolo')
            if not symbol:
                continue

            # 2a. Timestamp real por fila (epoch UTC del scanner)
            ts = datetime.fromtimestamp(item['timestamp_utc'], timezone.utc)

            # 2b. Preparar para BD leyendo CLAVES NOMBRADAS (endpoint /symbol)
            bd_rows.append({
                'symbol': symbol,
                'timestamp_utc': ts,
                'close': safe_float(item.get('close')),
                'volume': safe_float(item.get('volume')),
                'rsi': safe_float(item.get('RSI')),
                'cci20': safe_float(item.get('CCI20')),
                'bbpower': safe_float(item.get('BBPower')),
                'adx': safe_float(item.get('ADX')),
                'pivot_camarilla_r3': safe_float(item.get('Pivot.M.Camarilla.R3')),
                'perf_w': safe_float(item.get('Perf.W')),
                'change_pct': safe_float(item.get('change')),
                # raw_payload OMITIDO (NULL) — el crudo queda en el CSV
                'source_checksum': None  # se calcula en repository (subconjunto canónico)
            })
        
        # 3. (El CSV ya se escribió en el bucle del scraper — no se repite aquí)

        # 4. Escribir BD (nuevo)
        inserted = market_repository.insert_market_series_batch(db, bd_rows)
        
        # 5. Registrar auditoría
        audit_repository.log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'run_start': run_start,
            'records_fetched': len(scanner_data),
            'records_upserted': inserted,
            'status': 'SUCCESS',
            'execution_mode': 'cron'
        })
        
        # 6. Actualizar checkpoint
        audit_repository.update_checkpoint(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'last_timestamp': run_start,
            'records_processed': inserted,
            'status': 'ACTIVE'
        })
        
        return inserted
    
    except Exception as e:
        # 7. Registrar fallo SIN tumbar el proceso (el CSV ya quedó escrito)
        audit_repository.log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'run_start': run_start,
            'records_fetched': len(scanner_data),
            'records_upserted': 0,
            'status': 'FAILED',
            'error_message': str(e),
            'execution_mode': 'cron'
        })
        log.error(f"BD: fallo al insertar series: {e}")
        return 0
    
    finally:
        db.disconnect()
```

**Justificación de separar CSV y BD:**
- El CSV se escribe **antes** de la BD. Si la BD falla, los datos quedan en CSV (fallback).
- La auditoría registra **solo** la operación de BD, no la de CSV (el CSV no tiene trazabilidad de ejecución).
- El flujo CSV no cambia; se añade la capa BD **después**.

**Manejo de fallos (decidido 2026-09-13):**
- Si `db.connect()` falla, no es posible escribir `audit_sync_run`; se registra en el **log local** y se retorna 0 (el CSV ya quedó escrito).
- Si la conexión es exitosa pero el batch falla, se registra `audit_sync_run` **FAILED** y se retorna 0.
- Los símbolos con `close`/`volume` nulos se insertan **con NULL** (no se omiten).
- Logging unificado a `logging` en todos los componentes.

#### 6.2.3 Adaptación de `scraper_live_tradingview_v4.py`

**Pseudocódigo del cambio en `main()`:**

```
# ANTES (v4 actual):
for symbol in lista_ordenada:
    res = fetch_from_scanner(symbol)
    if isinstance(res, dict):
        df_new = pd.DataFrame([res])
        df_new.to_csv(csv_file, mode='a', header=...)
        rotar_datos(csv_file, folder_clean)

# DESPUÉS (v3.1.0):
# Preparar buffer de batch para BD
batch_buffer = []

for symbol in lista_ordenada:
    res = fetch_from_scanner(symbol)
    if isinstance(res, dict):
        # CSV (sin cambios)
        df_new = pd.DataFrame([res])
        df_new.to_csv(csv_file, mode='a', header=...)
        rotar_datos(csv_file, folder_clean)
        
        # BD (nuevo — solo si DB_WRITE_ENABLED)
        if config.DB_WRITE_ENABLED:
            batch_buffer.append(prepare_bd_row(symbol, res))

# Después del bucle: flush batch a BD
if config.DB_WRITE_ENABLED and batch_buffer:
    process_radar_batch(batch_buffer)  # ← nueva función
```

**Justificación del batch buffering:**
- El scraper captura 110 símbolos. Insertar 110 registros uno por uno sería 110 round-trips a la BD.
- Con buffer, se hace **1 solo round-trip** con `execute_values` batch.
- El buffer se limpia al final del ciclo; si el ciclo falla a mitad, los símbolos ya procesados quedan en CSV.
- **Circuit breaker:** cuando se dispara `sys.exit(1)` por 3 fallos consecutivos, se hace **flush parcial** del `batch_buffer` acumulado antes de salir, para no perder en BD lo ya capturado (el CSV ya lo tiene).

---

### 6.3 Pipeline Calendario → `fact_economic_event` — ✅ IMPLEMENTADO (previo, V5)

#### 6.3.1 `db/event_repository.py` — Repositorio de escritura

**Función principal: `insert_events_batch(events)`**

**Pseudocodigo:**

```
función insert_events_batch(events: List[Dict]) → int:
    """
    Inserta batch de eventos económicos en fact_economic_event.
    Dedup por event_id (BIGINT PK). Puebla LAS 29 COLUMNAS del esquema v1.0.2.
    """
    params = []
    for evento in events:
        # 1. Convertir event_id a BIGINT
        event_id = safe_int(evento.get('id'))
        if event_id is None:
            log.warning(f"Evento sin id válido: {evento}")
            continue

        # 2. Calcular checksum
        checksum = sha256(json.dumps(evento, sort_keys=True, default=str))

        # 3. Preparar tupla (29 columnas, en el orden del esquema)
        params.append((
            event_id,                                   # event_id
            evento.get('title'),                        # title
            evento.get('country'),                      # country (FK dim_country)
            evento.get('indicator'),                    # indicator
            evento.get('ticker'),                       # event_ticker
            evento.get('comment'),                      # comment
            evento.get('category'),                     # category
            evento.get('period'),                       # period
            parse_iso(evento.get('referenceDate')),     # reference_date
            evento.get('source'),                       # source
            evento.get('source_url'),                   # source_url
            safe_float(evento.get('actual')),           # actual
            safe_float(evento.get('previous')),         # previous
            safe_float(evento.get('forecast')),         # forecast
            safe_float(evento.get('actualRaw')),        # actual_raw
            safe_float(evento.get('previousRaw')),      # previous_raw
            safe_float(evento.get('forecastRaw')),      # forecast_raw
            safe_text(evento.get('actual')),            # actual_display   (derivado)
            safe_text(evento.get('previous')),          # previous_display (derivado)
            safe_text(evento.get('forecast')),          # forecast_display (derivado)
            evento.get('currency'),                     # currency
            evento.get('unit'),                         # unit
            safe_int(evento.get('importance')),         # importance (−1..3)
            parse_iso(evento.get('date')),              # event_timestamp
            parse_iso(evento.get('timestamp_captura')), # captured_at
            now_utc(),                                   # first_seen_at
            now_utc(),                                   # last_updated_at
            json.dumps(evento, default=str),            # raw_payload
            checksum                                     # payload_checksum
        ))

    if not params:
        return 0

    # 4. UPSERT batch (29 columnas)
    upsert_query = """
        INSERT INTO fact_economic_event (
            event_id, title, country, indicator, event_ticker, comment,
            category, period, reference_date, source, source_url,
            actual, previous, forecast,
            actual_raw, previous_raw, forecast_raw,
            actual_display, previous_display, forecast_display,
            currency, unit, importance, event_timestamp, captured_at,
            first_seen_at, last_updated_at, raw_payload, payload_checksum
        ) VALUES %s
        ON CONFLICT (event_id) DO UPDATE SET
            title             = EXCLUDED.title,
            country           = EXCLUDED.country,
            indicator         = COALESCE(EXCLUDED.indicator, fact_economic_event.indicator),
            event_ticker      = COALESCE(EXCLUDED.event_ticker, fact_economic_event.event_ticker),
            comment           = COALESCE(EXCLUDED.comment, fact_economic_event.comment),
            category          = COALESCE(EXCLUDED.category, fact_economic_event.category),
            period            = COALESCE(EXCLUDED.period, fact_economic_event.period),
            reference_date    = COALESCE(EXCLUDED.reference_date, fact_economic_event.reference_date),
            source            = COALESCE(EXCLUDED.source, fact_economic_event.source),
            source_url        = COALESCE(EXCLUDED.source_url, fact_economic_event.source_url),
            actual            = COALESCE(EXCLUDED.actual, fact_economic_event.actual),
            previous          = COALESCE(EXCLUDED.previous, fact_economic_event.previous),
            forecast          = COALESCE(EXCLUDED.forecast, fact_economic_event.forecast),
            actual_raw        = COALESCE(EXCLUDED.actual_raw, fact_economic_event.actual_raw),
            previous_raw      = COALESCE(EXCLUDED.previous_raw, fact_economic_event.previous_raw),
            forecast_raw      = COALESCE(EXCLUDED.forecast_raw, fact_economic_event.forecast_raw),
            actual_display    = COALESCE(EXCLUDED.actual_display, fact_economic_event.actual_display),
            previous_display  = COALESCE(EXCLUDED.previous_display, fact_economic_event.previous_display),
            forecast_display  = COALESCE(EXCLUDED.forecast_display, fact_economic_event.forecast_display),
            currency          = EXCLUDED.currency,
            unit              = EXCLUDED.unit,
            importance        = EXCLUDED.importance,
            event_timestamp   = EXCLUDED.event_timestamp,
            captured_at       = COALESCE(EXCLUDED.captured_at, fact_economic_event.captured_at),
            raw_payload       = EXCLUDED.raw_payload,
            last_updated_at   = CURRENT_TIMESTAMP,
            payload_checksum  = EXCLUDED.payload_checksum
    """
    template = "(" + ", ".join(["%s"] * 27 + ["%s::jsonb", "%s"]) + ")"
    conn.execute_values(upsert_query, params, template=template)
    return len(params)
```

> **Corrección de la revisión (2026-09-13):** el pseudocódigo anterior poblaba solo 18 columnas y omitía `indicator`, `event_ticker`, `comment`, `period`, `reference_date`, `source`, `source_url`, `*_display` y `captured_at`. El objetivo es "21 campos RAW"; ahora se pueblan las **29 columnas** de la tabla.

**Justificación de `COALESCE` en el UPSERT:**
- Un evento puede actualizarse entre capturas (ej. el valor `actual` se publica después del `forecast`).
- `COALESCE(EXCLUDED.actual, fact_economic_event.actual)` preserva el valor previo si el nuevo es `NULL`.
- `first_seen_at` **no** se actualiza (es inmutable, como define el esquema v1.0.2).
- `last_updated_at` se actualiza siempre.

**Justificación de `safe_float` para campos raw:**
- El API devuelve campos como `""`, `"4.1"`, `"1.2M"` — no todos son numéricos puros.
- `safe_float` convierte lo que puede y retorna `NULL` para lo que no (ej. `"1.2M"`).
- Los campos `actual_raw`, `forecast_raw`, `previous_raw` se guardan como `NUMERIC(30,8)` en el esquema v1.0.2 (no como TEXT).

**Sobre `*_display`:** el API no entrega columnas de display separadas; en el pseudocódigo se derivan del valor legible (`actual`/`previous`/`forecast`) con `safe_text`. Ver pregunta abierta en §15.

#### 6.3.2 `application/event_service.py` — Orquestación

**Pseudocódigo del flujo:**

```
función process_calendar_batch(eventos_raw: List[Dict]) → int:
    """
    Flujo BD: eventos crudos → fact_economic_event → auditoría.
    (El CSV y el checkpoint local ya se guardaron antes de llamar.)
    """
    run_start = now_utc()
    
    if not config.DB_WRITE_ENABLED:
        log.info("Modo legacy: solo CSV, sin BD")
        return 0
    
    db = PostgreSQLConnector(...)
    if not db.connect():
        log.error("BD: no se pudo conectar — se omite la escritura de este ciclo")
        return 0
    
    try:
        # 1. (El CSV ya se guardó antes de llamar — no se repite)
        # 2. Los eventos crudos ya contienen los 29 campos del esquema
        #    (no hace falta re-empaquetarlos; el repositorio los mapea por nombre)
        bd_events = eventos_raw
        
        # 4. Escribir BD
        inserted = event_repository.insert_events_batch(db, bd_events)
        
        # 5. Registrar auditoría
        audit_repository.log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'run_start': run_start,
            'records_fetched': len(eventos_raw),
            'records_upserted': inserted,
            'status': 'SUCCESS',
            'execution_mode': 'cron'
        })
        
        # 6. Actualizar checkpoint BD
        max_event_id = max(int(e.get('id', 0)) for e in eventos_raw) if eventos_raw else 0
        audit_repository.update_checkpoint(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'last_timestamp': run_start,   # NOT NULL en el esquema (corrección 2026-09-13)
            'last_event_id': max_event_id,
            'records_processed': inserted,
            'status': 'ACTIVE'
        })
        
        # 7. Mantener checkpoint JSON local (fallback)
        guardar_checkpoint(max_event_id, inserted, len(eventos_raw))
        
        return inserted
    
    except Exception as e:
        audit_repository.log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_CALENDARIO,
            'run_start': run_start,
            'status': 'FAILED',
            'error_message': str(e),
            'execution_mode': 'cron'
        })
        raise
    
    finally:
        db.disconnect()
```

#### 6.3.3 Adaptación de `calendario_tradingview_live_v4.py`

**Pseudocódigo del cambio en `capturar_eventos()`:**

```
# ANTES (v4 actual):
def capturar_eventos(paises, dias_adelante, incluir_pasado, auto_rotate, dias_mantener):
    eventos_raw = fetch_calendar_events(desde, hasta, paises)
    eventos_para_guardar = [evento_a_dict(e) for e in eventos_raw]
    guardar_eventos(eventos_para_guardar, auto_rotate=auto_rotate, dias_mantener=dias_mantener)
    guardar_checkpoint(...)
    return len(eventos_para_guardar), len(eventos_raw)

# DESPUÉS (v3.1.0):
def capturar_eventos(paises, dias_adelante, incluir_pasado, auto_rotate, dias_mantener):
    run_start = now_utc()
    eventos_raw = fetch_calendar_events(desde, hasta, paises)
    
    if not eventos_raw:
        return 0, 0
    
    # CSV (sin cambios)
    eventos_para_guardar = [evento_a_dict(e) for e in eventos_raw]
    guardar_eventos(eventos_para_guardar, auto_rotate=auto_rotate, dias_mantener=dias_mantener)
    
    # BD (nuevo)
    if config.DB_WRITE_ENABLED:
        try:
            inserted = process_calendar_batch(eventos_raw)
            log.info(f"BD: {inserted} eventos insertados")
        except Exception as e:
            log.error(f"BD: Error insertando eventos: {e}")
            # El CSV ya se guardó — no propagar error al caller
    
    # Checkpoint local (sin cambios)
    guardar_checkpoint(...)
    
    return len(eventos_para_guardar), len(eventos_raw)
```

**Justificación de no propagar error de BD:**
- El CSV ya se guardó exitosamente; los datos no se pierden.
- El error de BD se registra en `audit_sync_run` (si la conexión funciona).
- El monitor (iteración futura) detectará el fallo vía `audit_sync_run` y notificará por Telegram.
- Si se propaga el error, el script termina con `exit(1)` y el cron lo reintentará, pero el CSV ya no se volverá a escribir para ese ciclo.

---

#### 6.3.4 Retención de `raw_payload` de eventos (6 meses)

**Decisión (2026-09-13):** conservar `raw_payload` de eventos solo 6 meses, mediante:
1. `ALTER TABLE fact_economic_event ALTER COLUMN raw_payload DROP NOT NULL;` (permite NULL real).
2. Script dedicado `retention_events.py` ejecutado por **cron mensual/semanal**:
   `UPDATE fact_economic_event SET raw_payload = NULL WHERE captured_at < NOW() - INTERVAL '6 months' AND raw_payload IS NOT NULL;`
3. Reportar filas afectadas en `audit_sync_run` (script_name `retencion_eventos`).

**Nota:** el DDL (`DROP NOT NULL`) es un cambio de esquema sobre una tabla existente de v1.0.2; se aplica una sola vez (script de mantenimiento documentado, no en el init del heatmap).

### 6.4 Auditoría y Checkpoints — ✅ IMPLEMENTADO

#### 6.4.1 `db/audit_repository.py` — Repositorio de auditoría

**Funciones:**

```
función log_sync_run(db, data: Dict) → int:
    """
    Registra una ejecución en audit_sync_run.
    data contiene:
        script_name, run_start, records_fetched, records_upserted,
        records_failed (conteo explícito), status, error_message, execution_mode
    """
    query = """
        INSERT INTO audit_sync_run (
            script_name, run_start, run_end,
            records_fetched, records_upserted, records_failed,
            status, error_message, execution_mode
        ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
    """
    db.execute_query(query, (
        data['script_name'],
        data['run_start'],
        data['records_fetched'],
        data['records_upserted'],
        data.get('records_failed', 0),   # conteo explícito, no fetched-upserted
        data['status'],
        data.get('error_message'),
        data.get('execution_mode', 'cron')
    ))


función update_checkpoint(db, data: Dict) → int:
    """
    Actualiza el checkpoint de reanudación.
    data contiene:
        script_name, last_timestamp, last_event_id, records_processed, status
    """
    query = """
        INSERT INTO sync_checkpoint (
            script_name, last_timestamp, last_event_id,
            records_processed, last_run_at, status
        ) VALUES (%s, COALESCE(%s, CURRENT_TIMESTAMP), %s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (script_name) DO UPDATE SET
            last_timestamp = COALESCE(EXCLUDED.last_timestamp, sync_checkpoint.last_timestamp),
            last_event_id = COALESCE(EXCLUDED.last_event_id, sync_checkpoint.last_event_id),
            records_processed = sync_checkpoint.records_processed + EXCLUDED.records_processed,
            last_run_at = CURRENT_TIMESTAMP,
            status = EXCLUDED.status
    """
    db.execute_query(query, (
        data['script_name'],
        data.get('last_timestamp'),
        data.get('last_event_id'),
        data.get('records_processed', 0),
        data.get('status', 'ACTIVE')
    ))


función get_last_run(db, script_name: str) → Optional[Dict]:
    """
    Obtiene la última ejecución registrada para un script.
    Usado por el monitor V4.
    """
    query = """
        SELECT script_name, run_start, run_end,
               records_fetched, records_upserted, records_failed,
               status, error_message, execution_mode
        FROM audit_sync_run
        WHERE script_name = %s
        ORDER BY run_start DESC
        LIMIT 1
    """
    result = db.execute_query(query, (script_name,))
    return result[0] if result else None


función get_last_checkpoint(db, script_name: str) → Optional[Dict]:
    """
    Obtiene el último checkpoint para un script.
    """
    query = """
        SELECT script_name, last_timestamp, last_event_id,
               records_processed, last_run_at, status
        FROM sync_checkpoint
        WHERE script_name = %s
    """
    result = db.execute_query(query, (script_name,))
    return result[0] if result else None
```

#### 6.4.2 Justificación de la auditoría

**¿Por qué registrar cada ejecución?**

1. **Diagnóstico:** Si el monitor detecta un fallo, el operador puede ver `error_message` real en `audit_sync_run` en vez de solo "archivo no encontrado".
2. **Métricas:** `records_fetched` vs `records_upserted` permite detectar anomalías (ej. 110 fetch pero 0 upsert = problema de BD).
3. **Historial:** Permite responder "¿cuándo fue la última ejecución exitosa del scraper?" con una query, sin revisar logs.
4. **Auditoría de datos:** `records_failed` = `fetched - upserted` cuantifica la pérdida de registros.

**¿Por qué `sync_checkpoint`?**

1. **Reanudación:** Si el scraper falla a mitad del ciclo, el checkpoint permite saber hasta dónde llegó.
2. **Backfill:** Si se necesita re-procesar un período, el checkpoint indica el punto de partida.
3. **Dedup definitivo:** `last_event_id` (BIGINT) garantiza que no se re-procesen eventos ya insertados.

---

### 6.5 Particionamiento y BRIN — ✅ IMPLEMENTADO (`db/partitions.py`)

#### 6.5.1 Integración con `create_partitions.py`

**Decisión (confirmada 2026-09-13):** El scraper **no crea DDL en cada ciclo**. Al iniciar, solo **verifica** que exista la partición del mes actual de `fact_market_series`; si falta (caso excepcional, p. ej. arranque de mes o partición no creada por el otro script), **fuerza** la creación de esa única partición. Las particiones futuras las mantiene el script de particionamiento del heatmap.

**Pseudocódigo de la verificación:**

```
# Al inicio del proceso (no en cada ciclo de 3 min):
if config.DB_WRITE_ENABLED:
    db = PostgreSQLConnector(...)
    db.connect()

    # 1. ¿Existe la partición del mes actual?
    if not partition_exists(db, "fact_market_series", mes_actual):
        log.warning("Partitición del mes actual ausente — creando (caso excepcional)")
        create_partition(db, "fact_market_series", mes_actual)
        ensure_brin_for_partition(db, "fact_market_series", mes_actual)

    db.disconnect()
```

**Justificación:**
- Las particiones `2026_09..12` ya existen y otro script las mantiene; crear/verificar en cada ciclo de 3 min es overhead innecesario.
- El único caso a cubrir en caliente es que la partición del mes en curso no exista (sin ella, el INSERT fallaría).
- BRIN: se asegura únicamente sobre la partición creada en el caso excepcional.

#### 6.5.2 Utilidades locales de partición

**Decisión:** implementar en local lo mínimo necesario (`partition_exists`, `create_partition`, `ensure_brin_for_partition`) — por ejemplo en `db/partitions.py` — **sin importar** `create_partitions.py` del heatmap.

**Pseudocódigo:**

```
# db/partitions.py (nuevo, mínimo)
TABLA_SERIES = "fact_market_series"
BRIN_TABLES = {"fact_market_series"}

def partition_name(tabla, mes) -> str: ...      # {tabla}_{YYYY_MM}
def partition_exists(conn, tabla, mes) -> bool: ...
def create_partition(conn, tabla, mes) -> None: ...
def ensure_brin_for_partition(conn, tabla, particion) -> None: ...
def ensure_current_month_partition(conn, tabla) -> bool:
    """Verifica y, solo si falta, crea la partición del mes actual."""
```

**Justificación:** el scraper solo necesita verificación + creación excepcional; no requiere la lógica completa de `months_ahead` del heatmap.

---

### 6.6 Monitor v4 (BD-aware) — [DIFERIDO]

> **Fuera del alcance de 3.1.0.** Esta sección se conserva como diseño para la iteración siguiente; el monitor V3 (por archivos) sigue operativo. Al diferirse el monitor, la dependencia de `notificador_telegram.py` (§11-R5) también queda fuera de esta iteración.

#### 6.6.1 `monitor_tradingview_live_v4.py` — Nuevo monitor

**Pseudocódigo de la clase:**

```
class MonitorTradingViewV4:
    """
    Monitor basado en BD. Vigila audit_sync_run en vez de archivos.
    """
    
    SCRIPTS_A_MONITOREAR = [
        {'script_name': 'radar_v4', 'intervalo_minutos': 3, 'tipo': 'scraper'},
        {'script_name': 'calendario_v4', 'intervalo_minutos': 15, 'tipo': 'calendario'},
    ]
    
    MAX_CICLOS_ESPERAR = 2      # ALERTA si > 2 ciclos sin ejecución
    CICLO_ALERTA_WARNING = 1.5  # WARNING si > 1.5 ciclos
    SPAM_INTERVAL = 1800        # 30 minutos entre alertas (corregido)
    
    constructor():
        self.db = PostgreSQLConnector(config.DB_*)
        self.notificador = TelegramNotificador(...)  # si disponible
        self.alertas_previas = cargar_alertas_previas()
    
    función verificar_procesos() → List[Dict]:
        """
        Lee audit_sync_run para cada script y evalúa frescura.
        """
        self.db.connect()
        alertas = []
        
        for config_script in self.SCRIPTS_A_MONITOREAR:
            script_name = config_script['script_name']
            intervalo = config_script['intervalo_minutos']
            
            # 1. Obtener última ejecución desde BD
            last_run = audit_repository.get_last_run(self.db, script_name)
            
            if last_run is None:
                alertas.append({
                    'nombre': script_name,
                    'error': 'SIN EJECUCIONES REGISTRADAS',
                    'tipo': config_script['tipo']
                })
                continue
            
            # 2. Calcular tiempo desde última ejecución
            run_end = last_run['run_end'] or last_run['run_start']
            ahora = now_utc()
            minutos_desde = (ahora - run_end).total_seconds() / 60
            ciclos_perdidos = minutos_desde / intervalo
            
            # 3. Clasificar estado
            if ciclos_perdidos > self.MAX_CICLOS_ESPERAR:
                # ALERTA — incluir error_message si existe
                alerta = {
                    'nombre': script_name,
                    'proceso': f"{script_name}.py",
                    'tipo': config_script['tipo'],
                    'diferencia': minutos_desde,
                    'ciclos_perdidos': ciclos_perdidos,
                    'ultima_fecha': run_end.strftime('%Y-%m-%d %H:%M:%S'),
                    'error': last_run.get('error_message'),
                    'status_bd': last_run['status'],
                    'records_upserted': last_run['records_upserted']
                }
                alertas.append(alerta)
            
            elif ciclos_perdidos > self.CICLO_ALERTA_WARNING:
                # WARNING
                log.warning(f"{script_name}: {minutos_desde:.1f} min sin ejecución")
            
            else:
                # OK
                log.info(f"{script_name}: OK (hace {minutos_desde:.1f} min)")
        
        self.db.disconnect()
        
        # 4. Enviar alerta consolidada si hay alertas
        if alertas and self.debe_enviar_alerta():
            await self.enviar_alerta_agrupada(alertas)
        
        return alertas
    
    función debe_enviar_alerta() → bool:
        """Anti-spam: 30 minutos entre alertas"""
        # Implementación similar al V3 pero corregido a 1800s
    
    función enviar_alerta_agrupada(alertas: List[Dict]):
        """
        Construye y envía mensaje consolidado por Telegram.
        """
        mensaje = self.construir_mensaje(alertas)
        if self.notificador:
            await self.notificador.enviar(mensaje, titulo=f"⚠️ {len(alertas)} PROCESOS CAÍDOS")
```

**Justificación de vigilar `audit_sync_run` en vez de archivos:**

| Aspecto | Monitor V3 (archivos) | Monitor V4 (BD) |
|---------|----------------------|------------------|
| Fuente de verdad | Timestamp en CSV/JSON | `run_end` en `audit_sync_run` |
| Desacoplamiento | Depende de rutas hardcodeadas | Depende de `script_name` |
| Granularidad | Solo sabe "archivo desactualizado" | Sabe: cuántos registros, error, modo |
| Fragilidad | Ruta de calendario desalineada (bug V3) | Query directa, sin rutas |
| Mantenimiento | Añadir archivo = modificar `ARCHIVOS_A_MONITOREAR` | Automático si `script_name` coincide |

---

### 6.7 Seed de Configuración — ✅ IMPLEMENTADO (`seed_symbols.py`)

#### 6.7.1 `seed_symbols.py` — Sincronizar `CONFIG_ACTIVOS` → `dim_asset`

**Pseudocódigo del flujo:**

```
función seed_symbols():
    """
    Asegura que todos los símbolos de CONFIG_ACTIVOS existan en dim_asset.
    Idempotente: se puede re-ejecutar sin efectos secundarios.
    """
    db = PostgreSQLConnector(config.DB_*)
    db.connect()
    
    # 1. Obtener símbolos actuales en dim_asset
    existentes = query("SELECT symbol FROM dim_asset WHERE is_active")
    existentes_set = {row['symbol'] for row in existentes}
    
    # 2. Recorrer CONFIG_ACTIVOS
    nuevos = 0
    actualizados = 0
    
    for categoria, activos in config.CONFIG_ACTIVOS.items():
        for clave, fuentes in activos.items():
            for tipo_fuente in ['primario', 'respaldo']:
                symbol = fuentes[tipo_fuente]
                if symbol in existentes_set:
                    continue  # Ya existe — no tocar (primer-gana)
                
                # Derivar exchange y ticker
                exchange, ticker = symbol.split(':', 1)
                
                # Determinar asset_class y share_class
                asset_class = 'equity'  # Default para acciones
                share_class = None
                
                # Clasificación especial (del heatmap)
                if exchange in ('BINANCE', 'BITSTAMP'):
                    asset_class = 'crypto'
                elif exchange in ('OANDA', 'FX_IDC'):
                    asset_class = 'forex'
                elif exchange in ('SAXO', 'TVC'):
                    asset_class = classify_from_ticker(exchange, ticker)
                elif exchange in ('AMEX', 'NASDAQ', 'NYSE'):
                    if ticker in ETF_LIST:
                        asset_class = 'etf'
                    else:
                        asset_class = 'equity'
                
                # UPSERT con COALESCE (primer-gana)
                upsert_dim_asset(
                    symbol=symbol,
                    ticker=ticker,
                    exchange=exchange,
                    asset_class=asset_class,
                    share_class=share_class,
                    source_discovered_by='radar_v4',
                    source_category=categoria
                )
                nuevos += 1
    
    log.info(f"Seed completada: {nuevos} nuevos, {actualizados} actualizados")
    db.disconnect()
```

**Interfaz CLI (D29):**
- `--dry-run`: reporta cuántos símbolos del radar faltan, sin escribir.
- `--check`: reporta faltantes y sale con código ≠ 0 si hay alguno (sin escribir); útil para el shell.
- Sin flags: ejecuta las altas nuevas (idempotente; no-op si no falta ninguno).

**Justificación de la clasificación de activos:**
- El heatmap ya tiene la lógica de clasificación por exchange+ticker en `seed_dim_asset.py:34-66` (función `classify()`), **pero es de otro proyecto**: se **duplica en local** (misma decisión que el conector) para mantener autonomía y consistencia (crypto/forex/future/yield/index/commodity/etf/equity).

**Justificación de no tocar símbolos existentes (verificado 2026-09-13):**
- `dim_asset` tiene 1.060 activos; **los 110 del radar ya existen** (45 `radar_v4` + 65 `heatmap`).
- El scraper no debe sobreescribir esos datos (criterio primer-gana).
- Si un símbolo del radar ya existe (por heatmap o por una corrida previa del seed), su `source_discovered_by` **se mantiene**.
- El seed queda como no-op hoy y solo actúa cuando se agregan símbolos nuevos a `CONFIG_ACTIVOS`.

#### 6.7.2 Ejecución de la seed

**Decisión:** Ejecutar `seed_symbols.py` como paso previo al primer ciclo del scraper, no en cada ejecución.

**Justificación:**
- La seed es idempotente pero innecesaria en cada ciclo (110 símbolos no cambian frecuentemente).
- Se ejecuta:
  1. **Una vez** al inicio de la migración (setup inicial).
  2. **Al añadir símbolos** a `CONFIG_ACTIVOS` (ej. añadir una nueva categoría).
  3. **Opcionalmente** en el shell script si se detecta que `dim_asset` está vacía.

**Pseudocódigo del shell:**

```
# run_scraper_tradingview.sh — verificación + seed idempotente
if [ "$DB_WRITE_ENABLED" = "true" ]; then
    # seed_symbols valida el universo y da de alta SOLO los faltantes
    # (hoy es no-op: los 110 símbolos ya existen)
    "$PYTHON_CMD" "$PROJECT_DIR/seed_symbols.py" >> "$EXEC_LOG" 2>&1
    if [ $? -ne 0 ]; then
        log "⚠️ seed_symbols falló — continuando (el pipeline BD omitirá símbolos ausentes)"
    fi
fi
```

---

### 6.8 Scripts Shell y Cron — ✅ IMPLEMENTADO

#### 6.8.1 `run_scraper_tradingview.sh` — Modificaciones

**Cambios pseudocódigo:**

```
# Añadir al inicio del script (después de load_env_vars):
if [ "$DB_WRITE_ENABLED" = "true" ]; then
    log "🗄️ Modo BD activo — escrituras a $BD_HEATMAP_DATABASE"
    
    # Verificar conexión a BD
    "$PYTHON_CMD" -c "
        from db.postgresql_connection import PostgreSQLConnector
        import config
        db = PostgreSQLConnector(config.PG_HOST, config.PG_PORT, config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD)
        if db.connect():
            print('✅ Conexión BD exitosa')
            db.disconnect()
        else:
            print('❌ Error conectando a BD')
            exit(1)
    " >> "$EXEC_LOG" 2>&1
    
    if [ $? -ne 0 ]; then
        log "⚠️ BD no disponible — continuando en modo CSV legacy"
        export DB_WRITE_ENABLED=false
    fi
else
    log "📁 Modo legacy: solo CSV (DB_WRITE_ENABLED=false)"
fi

# El resto del script permanece igual
```

#### 6.8.2 `run_calendario_tradingview.sh` — Mismos cambios

Se aplica la misma lógica de verificación de BD al inicio del script.

#### 6.8.3 Cron — Sin cambios en frecuencia

| Proceso | Frecuencia | Nota |
|---------|-----------|------|
| Scraper | `*/3` (minutos) | Sin cambio — el batch buffering hace la BD viable |
| Calendario | `*/15` | Sin cambio |
| Monitor | `*/5` | Sin cambio — sigue el V3 por archivos (V4 BD-aware diferido) |

#### 6.8.4 Correcciones de rutas en shell (decidido 2026-09-13)

**Decisión:** corregir en 3.1.0 las rutas desalineadas del shell, porque afectan la operación del cron y la verificación de resultados.

**Cambios:**
1. `run_calendario_tradingview.sh`: `CALENDARIO_DIR` y `EVENTOS_FILE` deben apuntar a `DATOS_LIVE_CALENDARIO/calendario_economico/` (hoy usan `DATOS_LIVE/calendario_economico/`, ruta que Python no escribe).
2. `PROJECT_DIR` del `.env`: debe resolver a `proy_scrapping_detail` (hoy apunta al proyecto padre), o los scripts deben calcular su propio directorio con `$(cd "$(dirname "$0")" && pwd)`.
3. Verificar que `VENV_PYTHON` resuelva al venv correcto del proyecto scraper.

---

### 6.9 Documentación y Versionado — ⏳ PARCIAL (pendiente actualización README/docs)

#### 6.9.1 Archivos a actualizar

| Archivo | Cambio |
|---------|--------|
| `config.py` | `VERSION = "3.1.0"` |
| `readme.md` | Reescribir: arquitectura con BD, componentes, flujos, nuevos módulos |
| `readme_crontab.md` | Añadir variables `DB_WRITE_ENABLED` al cron |
| `requirements.txt` | **Añadir `psycopg2-binary`** (hoy ausente) e instalarlo en el venv |
| `.env` / `.env_demo` | Añadir `BD_HEATMAP_*` y `DB_WRITE_ENABLED` |
| `docs/scrapper_documentacion_2026-09-13.md` | Reescribir con sección BD (nombre real del archivo) |
| `docs/scrapper_Roadmap_migracion_a_3-1-0.md` | Este documento |

#### 6.9.2 README v3.1.0 — Estructura propuesta

```
1. Resumen
2. Arquitectura (diagrama actualizado con BD)
3. Componentes
   3.1 Scraper V4 (+ BD pipeline)
   3.2 Calendario V4 (+ BD pipeline)
   3.3 Monitor V3 (sin cambios en 3.1.0; V4 BD-aware diferido)
   3.4 Seed de símbolos
   3.5 Conector BD
4. Configuración
   4.1 CONFIG_ACTIVOS
   4.2 Variables de entorno (.env)
   4.3 DB_WRITE_ENABLED (modo legacy)
5. Esquema de BD (resumen, ref a SCHEMA_heatmap_stock.md)
6. Flujos de datos
   6.1 Radar → fact_market_series
   6.2 Calendario → fact_economic_event
   6.3 Auditoría
7. Scripts de ejecución
8. Crontab
9. Resolución de problemas
```

---

### 6.10 Scripts SQL de migración — ✅ IMPLEMENTADO (`proy_heatmap/scripts/04`–`07`)

**Decisión (2026-09-13):** todo cambio de esquema SQL se documenta y se versiona como script en
`proy_heatmap/scripts/`, para que **ambos proyectos (heatmap y scraper) compartan la BD
`heatmap_stock` sin conflictos** y sin sorpresas. El scraper **no aplica DDL en runtime**:
solo ejecuta DML (INSERT/UPSERT). El DDL vive exclusivamente en estos scripts revisables.

#### 6.10.1 Scripts existentes (v1.0.2)

| Script | Propósito | Ejecución |
|--------|-----------|-----------|
| `01_create_function.sql` | Wrapper inmutable `text_to_tsvector_english` (búsqueda GIN) | Una vez |
| `02_init_database.sql` | Esquema completo: tablas, vistas, funciones, seed, particiones | Una vez (setup inicial) |
| `03_comprobar.sql` | Checklist de verificación del esquema y datos | Diagnóstico |

#### 6.10.2 Scripts nuevos para v3.1.0

| Script | Propósito | Frecuencia |
|--------|-----------|------------|
| `04_migration_3.1.0.sql` | DDL: `ALTER TABLE fact_economic_event ALTER COLUMN raw_payload DROP NOT NULL` (D30) + verificaciones | **Una vez** |
| `05_retention_events.sql` | Retención: `raw_payload` de eventos > 6 meses → `NULL` (D26) | Mensual (cron) |
| `06_verify_3.1.0.sql` | Verificación post-migración (esquema, auditoría, checkpoints, datos) | Post-migración |
| `07_cleanup_legacy.sql` | Auditar funciones no usadas (`upsert_market_series`); sin cambios destructivos | Opcional |

#### 6.10.3 Orden de ejecución

```bash
# 1. Setup inicial (solo si la BD no existe)
psql -U postgres -d heatmap_stock -f scripts/02_init_database.sql

# 2. Migración v3.1.0 (una vez, antes de activar DB_WRITE_ENABLED=true)
psql -U postgres -d heatmap_stock -f scripts/04_migration_3.1.0.sql

# 3. Verificación post-migración
psql -U postgres -d heatmap_stock -f scripts/06_verify_3.1.0.sql

# 4. Retención (cron mensual)
psql -U postgres -d heatmap_stock -f scripts/05_retention_events.sql

# 5. Auditoría de funciones legacy (opcional)
psql -U postgres -d heatmap_stock -f scripts/07_cleanup_legacy.sql
```

#### 6.10.4 Convivencia de proyectos (una sola BD)

| Tabla | Escritura | Lectura | Conflicto |
|-------|-----------|---------|-----------|
| `dim_asset` | Ambos (heatmap + radar) | Ambos | **Primer-gana** (`source_discovered_by` indica quién la creó) |
| `dim_country` | Solo `02_init_database.sql` | Ambos | Ninguno (seed estático) |
| `fact_heatmap_snapshot` | Solo heatmap | Ambos | Ninguno (escritura separada) |
| `fact_market_series` | Solo scraper radar | Ambos | Ninguno (escritura separada) |
| `fact_economic_event` | Solo scraper calendario | Ambos | Ninguno (escritura separada) |
| `audit_sync_run` | Ambos (distintos `script_name`) | Monitor futuro | Ninguno (append, `script_name` distingue) |
| `sync_checkpoint` | Ambos (distintos `script_name`) | Monitor futuro | Ninguno (UPSERT por `script_name`) |

**Reglas:**
- Los scripts DDL de `proy_heatmap/scripts/` son la **única fuente de verdad** del esquema.
- El scraper `proy_scrapping_detail/` **nunca** ejecuta `CREATE`/`ALTER`/`DROP` en runtime; si el esquema no coincide, falla y lo registra en `audit_sync_run`.
- `fact_economic_event.raw_payload` pasa a ser nullable (D30) para permitir la retención (D26).
- `upsert_market_series()` queda obsoleta para el scraper (D2: batch INSERT), pero **no se elimina** por defecto para no romper consumidores externos.

---

## 7. Flujos de Datos (Diagramas)

### 7.1 Pipeline Radar — Detalle

```
CONFIG_ACTIVOS (110 símbolos)
    │
    ▼
fetch_from_scanner(symbol) × 110
    │
    ├──► CSV: DATOS_LIVE/{SYM}/{SYM}.csv (buffer, 7d)
    │
    ▼
claves nombradas del dict (close, volume, RSI, CCI20, BBPower, ADX, Pivot.M.Camarilla.R3, Perf.W, change)
    │
    ├──► (el heatmap usa su propio endpoint /scan — otro proyecto)
    │
    ├──► close, volume, rsi, cci20, bbpower, adx, pivot_r3, perf_w, change
    │    │
    │    ▼
    │    market_repository.insert_batch()
    │    │
    │    ├──► UPSERT → fact_market_series (particionada, BD)
    │    ├──► SHA256 canónico → source_checksum (sin timestamp)
    │    ├──► raw_payload OMITIDO (NULL)
    │    ├──► PK (asset_id, timestamp_utc) → idempotencia
    │    └──► cache asset_id (query inicial a dim_asset)
    │
    ├──► audit_repository.log_sync_run()
    │    │
    │    └──► INSERT → audit_sync_run
    │
    └──► audit_repository.update_checkpoint()
         │
         └──► UPSERT → sync_checkpoint
```

### 7.2 Pipeline Calendario — Detalle

```
API: economic-calendar.tradingview.com/events
    │
    ▼
fetch_calendar_events(desde, hasta, países)
    │
    ├──► CSV: eventos_calendario.csv (buffer, 7d)
    │
    ▼
evento_a_dict() × N eventos
    │
    ├──► event_repository.insert_batch()
    │    │
    │    ├──► UPSERT → fact_economic_event (no particionada, BD, 29 columnas)
    │    ├──► int(event_id) → BIGINT PK
    │    ├──► SHA256 → payload_checksum (huella del payload)
    │    ├──► COALESCE → first_seen_at (inmutable)
    │    └──► COALESCE → actual/previous/forecast, raw_payload, last_updated_at
    │
    ├──► audit_repository.log_sync_run()
    │    │
    │    └──► INSERT → audit_sync_run
    │
    └──► audit_repository.update_checkpoint()
         │
         └──► UPSERT → sync_checkpoint (last_event_id BIGINT)
```

### 7.3 Monitor V4 — Flujo

```
monitor_tradingview_live_v4.py (cada 5 min)
    │
    ▼
SELECT * FROM audit_sync_run
    WHERE script_name IN ('radar_v4', 'calendario_v4')
    ORDER BY run_start DESC
    LIMIT 1 por script
    │
    ▼
Calcular: minutos_desde_run_end / intervalo_esperado = ciclos_perdidos
    │
    ├── ciclos > 2 → 🔴 ALERTA → Telegram
    ├── ciclos > 1.5 → 🟡 WARNING → log
    └── ciclos ≤ 1.5 → 🟢 OK → log
```

---

## 8. Matriz de Mapeo de Campos

### 8.1 Scanner → `fact_market_series`

> **Corrección (2026-09-13):** el endpoint `scanner.tradingview.com/symbol` devuelve un **dict con claves nombradas** (verificado en `DATOS_LIVE/NASDAQ-QQQ/NASDAQ-QQQ.csv`: `ADX,BBPower,CCI20,Perf.W,Pivot.M.Camarilla.R3,RSI,change,close,volume,timestamp_utc,fecha_iso,simbolo`). La tabla original usaba índices de vector (`d[0]`, `d[14]`, `d[23]`) que corresponden al endpoint `/scan`, no a `/symbol`.

| Campo Scanner (clave) | Campo BD | Tipo BD | Transformación |
|-----------------------|----------|---------|----------------|
| `simbolo` | `asset_id` (FK lógica) | `INTEGER` | cache `SELECT asset_id FROM dim_asset WHERE symbol = %s AND is_active AND current_version`, resuelto en bloque |
| `timestamp_utc` (epoch UTC, por fila) | `timestamp_utc` | `TIMESTAMPTZ` | `datetime.fromtimestamp(value, timezone.utc)` |
| `close` | `close` | `NUMERIC(20,8)` | `safe_float` |
| `volume` | `volume` | `NUMERIC(20,8)` | `safe_float` |
| `RSI` | `rsi` | `NUMERIC(10,4)` | `safe_float` |
| `CCI20` | `cci20` | `NUMERIC(10,4)` | `safe_float` |
| `BBPower` | `bbpower` | `NUMERIC(10,4)` | `safe_float` |
| `ADX` | `adx` | `NUMERIC(10,4)` | `safe_float` |
| `Pivot.M.Camarilla.R3` | `pivot_camarilla_r3` | `NUMERIC(18,6)` | `safe_float` |
| `Perf.W` | `perf_w` | `NUMERIC(12,8)` | `safe_float` |
| `change` | `change_pct` | `NUMERIC(12,8)` | `safe_float` |
| *(omitido)* | `raw_payload` | `JSONB` | **NULL** — no se guarda por costo (~366 MB/mes; ver §15.4). El crudo vive en el CSV |
| *(calculado)* | `source_checksum` | `VARCHAR(64)` | `SHA256(subconjunto canónico sin timestamp)` |

**Nota sobre `CAMPOS`:** el scraper solicita `"close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"`. La tabla `fact_market_series` guarda la columna como `pivot_camarilla_r3` (el nombre con `.M.` es propio del scanner).

**Sobre `raw_payload`:** se omite en `fact_market_series`. El crudo sigue en el CSV (7 días + histórico mensual). Si se necesitara, se reactiva la columna con retención (§15.4).

**Sobre `source_checksum`:** al excluir el timestamp, es estable entre capturas; detecta cambios reales de los valores de mercado. La idempotencia de fila la da la PK `(asset_id, timestamp_utc)`.

### 8.2 API Calendario → `fact_economic_event`

> **Corrección (2026-09-13):** se pueblan **las 29 columnas** del esquema v1.0.2 (la versión previa de esta tabla omitía 11). El API V4 devuelve 21 campos + `timestamp_captura`; las columnas `*_display` no vienen del API y se derivan.

| Campo API | Campo BD | Tipo BD | Transformación |
|-----------|----------|---------|----------------|
| `id` | `event_id` | `BIGINT PK` | `safe_int(value)` |
| `title` | `title` | `TEXT` | Sin cambio |
| `country` | `country` | `VARCHAR(5) FK dim_country` | Sin cambio |
| `indicator` | `indicator` | `TEXT` | Sin cambio |
| `ticker` | `event_ticker` | `VARCHAR(50)` | Sin cambio |
| `comment` | `comment` | `TEXT` | Sin cambio |
| `category` | `category` | `VARCHAR(100)` | Sin cambio |
| `period` | `period` | `VARCHAR(20)` | Sin cambio |
| `referenceDate` | `reference_date` | `TIMESTAMPTZ` | `parse_iso(value)` |
| `source` | `source` | `TEXT` | Sin cambio |
| `source_url` | `source_url` | `TEXT` | Sin cambio |
| `actual` | `actual` | `NUMERIC(18,6)` | `safe_float(value)` |
| `previous` | `previous` | `NUMERIC(18,6)` | `safe_float(value)` |
| `forecast` | `forecast` | `NUMERIC(18,6)` | `safe_float(value)` |
| `actualRaw` | `actual_raw` | `NUMERIC(30,8)` | `safe_float(value)` |
| `previousRaw` | `previous_raw` | `NUMERIC(30,8)` | `safe_float(value)` |
| `forecastRaw` | `forecast_raw` | `NUMERIC(30,8)` | `safe_float(value)` |
| *(derivado de `actual`)* | `actual_display` | `TEXT` | `safe_text(value)` |
| *(derivado de `previous`)* | `previous_display` | `TEXT` | `safe_text(value)` |
| *(derivado de `forecast`)* | `forecast_display` | `TEXT` | `safe_text(value)` |
| `currency` | `currency` | `VARCHAR(5)` | Sin cambio |
| `unit` | `unit` | `VARCHAR(20)` | Sin cambio |
| `importance` | `importance` | `SMALLINT` | `safe_int(value)` (escala −1..3) |
| `date` | `event_timestamp` | `TIMESTAMPTZ` | `parse_iso(value)` |
| `timestamp_captura` | `captured_at` | `TIMESTAMPTZ` | `parse_iso(value)` |
| *(ahora)* | `first_seen_at` | `TIMESTAMPTZ` | `now_utc()` (inmutable en UPDATE) |
| *(ahora)* | `last_updated_at` | `TIMESTAMPTZ` | `CURRENT_TIMESTAMP` en cada UPDATE |
| *(todos los campos)* | `raw_payload` | `JSONB` | `json.dumps(evento, default=str)` |
| *(calculado)* | `payload_checksum` | `VARCHAR(64)` | `SHA256(json.dumps(evento, sort_keys=True, default=str))` |

---

## 9. Orden de Implementación

| Orden | Bloque | Dependencias | Esfuerzo estimado | Estado |
|-------|--------|-------------|-------------------|--------|
| 0 | `requirements.txt` — añadir `psycopg2-binary` e instalar en venv | — | 15 min | ✅ 2.9.13 en venv |
| 1 | `config.py` — cargar `.env`, añadir `PG_*`, `DB_WRITE_ENABLED`, `VERSION` | 0 | 45 min | ✅ |
| 2 | `db/postgresql_connection.py` — reparar import roto (`utils.config_logging` → `logging`) | 0 | 30 min | ✅ |
| 3 | `db/partitions.py` — verificación/creación excepcional de partición | 2 | 1 h | ✅ |
| 4 | `seed_symbols.py` — altas nuevas `CONFIG_ACTIVOS` → `dim_asset` | 1, 2 | 1.5 h | ✅ 0 faltantes |
| 5 | `db/audit_repository.py` — log_sync_run, update_checkpoint | 2 | 1 h | ✅ |
| 6 | `db/market_repository.py` — insert_batch (batch ON CONFLICT) | 2, 3, 4 | 2 h | ✅ |
| 7 | `application/market_service.py` — orquestación radar → BD | 5, 6 | 2 h | ✅ |
| 8 | `scraper_live_tradingview_v4.py` — integrar BD pipeline + flush parcial | 7 | 1.5 h | ✅ **V5 creado** (no modifica V4) |
| 9 | `db/event_repository.py` — insert_batch eventos (29 columnas) | 2, 4 | 2.5 h | ✅ |
| 10 | `application/event_service.py` — orquestación calendario → BD | 5, 9 | 2 h | ✅ |
| 11 | `calendario_tradingview_live_v4.py` — integrar BD pipeline | 10 | 1.5 h | ✅ **V5 existente** |
| 12 | `run_scraper_tradingview.sh` — verificación BD + seed | 1 | 30 min | ✅ |
| 13 | `run_calendario_tradingview.sh` — verificación BD | 1 | 30 min | ✅ |
| 14 | `.env` / `.env_demo` — añadir variables BD | — | 15 min | ✅ |
| 15 | `proy_heatmap/scripts/04_migration_3.1.0.sql` (+ `06_verify`) — DDL y verificación | 1, 2 | 45 min | ✅ |
| 16 | `proy_heatmap/scripts/05_retention_events.sql` + `retention_events.py` (cron) | 15 | 45 min | ⏳ SQL listo; falta `retention_events.py` |
| 17 | `readme.md` — reescribir | todos | 2 h | ⏳ Pendiente |
| 18 | Pruebas de integración | 0-17 | 3 h | ✅ Verificación real 110/110 + mapeo fila a fila |
| 19 | Despliegue y verificación en BD real | 18 | 1 h | ✅ 2026-09-18 |
| — | **[DIFERIDO] Monitor V4 + Telegram** | — | *(~3-4 h, iteración posterior)* | ⏸️ Diferido |

**Tiempo total estimado (alcance 3.1.0):** ~22,5 horas (sin monitor ni Telegram).

**Ruta crítica:** 0 → 1 → 2 → 4 → 6 → 7 → 8 (scraper) y 5 → 9 → 10 → 11 (calendario) pueden ejecutarse en paralelo después del paso 4.

---

## 10. Estrategia de Prueba y Verificación

### 10.1 Pruebas Unitarias (por componente)

| # | Componente | Prueba | Éxito esperado |
|---|-----------|--------|----------------|
| T1 | `seed_symbols.py` | Ejecutar con `CONFIG_ACTIVOS` (110 símbolos) | 0 ausentes en `dim_asset`; sin cambios en `source_discovered_by` de los existentes (45 `radar_v4` + 65 `heatmap`) |
| T2 | `market_repository.insert_batch` | Insertar 5 registros de prueba | 5 filas en `fact_market_series`, PKs únicos |
| T3 | `market_repository.insert_batch` | Re-insertar mismo `(asset_id, timestamp_utc)` | UPDATE (no duplicado), `ingested_at` cambiado |
| T4 | `event_repository.insert_batch` | Insertar 10 eventos | 10 filas en `fact_economic_event`, `event_id` BIGINT, **29 columnas pobladas** |
| T5 | `event_repository.insert_batch` | Re-insertar mismo `event_id` con `actual` nuevo | UPDATE con `COALESCE` (preserva `first_seen_at`; actualiza `actual`/`last_updated_at`) |
| T6 | `audit_repository.log_sync_run` | Registrar ejecución exitosa | 1 fila en `audit_sync_run`, `status='SUCCESS'` |
| T7 | `audit_repository.log_sync_run` | Registrar ejecución fallida | 1 fila con `error_message` |
| T8 | `audit_repository.update_checkpoint` | Primera ejecución (calendario, sin `last_timestamp`) | UPSERT nuevo con `last_timestamp = CURRENT_TIMESTAMP` (no viola `NOT NULL`) |
| T9 | `audit_repository.update_checkpoint` | Segunda ejecución | UPSERT actualiza `last_timestamp`, `records_processed` acumula |
| T10 | `scraper_live_tradingview_v4.py` | 3 fallos consecutivos (circuit breaker) | Flush parcial del batch; lo capturado queda en BD y CSV |

### 10.2 Pruebas de Integración

> **Estado 2026-09-18:** I1, I2, I3, I4, I7, I8 e I9 ejecutadas/verificadas en la corrida real del V5 (110/110 series, checksum presente, auditoría SUCCESS, checkpoint, partición `2026_09` y mapeo fila a fila contra CSV). I5/I6 quedan diferidos con el monitor.

| # | Escenario | Pasos | Éxito esperado |
|---|-----------|-------|----------------|
| I1 | Scraper completo con BD | Ejecutar `scraper_live_tradingview_v4.py` con `DB_WRITE_ENABLED=true` | CSV escrito + `fact_market_series` con timestamp **por fila** + `audit_sync_run` SUCCESS |
| I2 | Calendario completo con BD | Ejecutar `calendario_tradingview_live_v4.py` | CSV escrito + `fact_economic_event` con **29 columnas** + `audit_sync_run` SUCCESS |
| I3 | BD caída | Detener PostgreSQL, ejecutar scraper | CSV escrito, `audit_sync_run` FAILED, **el script NO se cae** (exit 0) |
| I4 | `DB_WRITE_ENABLED=false` | Ejecutar scraper | Solo CSV, sin intento de conexión BD |
| I5 | **[DIFERIDO]** Monitor V4 | Ejecutar después de I1 | Detecta última ejecución OK, no envía alerta |
| I6 | **[DIFERIDO]** Monitor V4 con fallo | Detener cron del scraper, esperar 10 min, ejecutar monitor | Detecta "sin ejecución", envía alerta Telegram |
| I7 | Seed idempotente | Ejecutar `seed_symbols.py` dos veces | Misma cantidad de filas, sin duplicados, sin re-etiquetar |
| I8 | Partición + BRIN | Verificar particiones de `fact_market_series` | Particiones mensuales presentes y BRIN en cada una |
| I9 | Reproceso mismo timestamp | Ejecutar dos capturas con el mismo `timestamp_utc` | `ON CONFLICT DO UPDATE`: 1 fila, `ingested_at` cambia |

### 10.3 Pruebas de Regresión

| # | Escenario | Verificación |
|---|-----------|-------------|
| R1 | CSV sin cambios | `DATOS_LIVE/{SYM}/{SYM}.csv` tiene misma estructura que antes |
| R2 | Rotación CSV | Archivos >7 días se mueven a histórico |
| R3 | Lock `fcntl` | Ejecutar dos instancias simultáneas — una sale con `exit(0)` |
| R4 | Backoff 429 | Simular rate limit — backoff progresivo funciona |
| R5 | Circuit breaker | 3 fallos consecutivos → `exit(1)` |

### 10.4 Verificación en BD Real

```sql
-- Verificar dim_asset del radar
SELECT source_discovered_by, COUNT(*) FROM dim_asset GROUP BY 1;
-- Referencia 2026-09-13: heatmap 1015, radar_v4 45 (los 110 del radar están cubiertos)
-- Cobertura real: 0 símbolos del radar ausentes (verificable cruzando con CONFIG_ACTIVOS)

-- Verificar fact_market_series
SELECT COUNT(*) FROM fact_market_series;
-- Esperado: ≥ 110 (después del primer ciclo)

-- Verificar audit_sync_run
SELECT script_name, status, records_fetched, records_upserted
FROM audit_sync_run ORDER BY run_start DESC LIMIT 5;

-- Verificar particiones
SELECT child.relname, pg_get_expr(child.relpartbound, child.oid)
FROM pg_inherits i
JOIN pg_class child ON i.inhrelid = child.oid
JOIN pg_class parent ON i.inhparent = parent.oid
WHERE parent.relname = 'fact_market_series';

-- Verificar BRIN en particiones
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename LIKE 'fact_market_series_%' AND indexname LIKE '%brin%';
```

---

## 11. Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| R1 | Símbolo del radar ausente en `dim_asset` (el batch lo omite) | Baja | Medio | Verificado 2026-09-13: 0 ausentes. `seed_symbols.py` cubre altas nuevas; los ausentes se loguean y omiten sin tumbar el ciclo |
| R2 | Rate limit de TradingView al escribir BD (ciclo más lento) | Baja | Medio | Batch buffering (1 round-trip por ciclo); lock `fcntl` previene solapamiento |
| R3 | BD `heatmap_stock` no disponible al momento del despliegue | Media | Alto | `DB_WRITE_ENABLED` permite modo legacy; verificación de conexión en shell |
| R4 | Partición de `fact_market_series` no creada antes del INSERT | Baja | Alto | `create_monthly_partitions` ejecutado al inicio de cada ciclo (patrón del heatmap) |
| R5 | `notificador_telegram.py` ausente | — | — | **No aplica en 3.1.0** (monitor diferido); se aborda junto con el monitor V4 en la iteración siguiente |
| R9 | Rutas desalineadas en shell (`DATOS_LIVE/calendario_economico` vs `DATOS_LIVE_CALENDARIO`; `PROJECT_DIR` del `.env` apunta al proyecto padre) | Alta | Medio | No se corrige en 3.1.0 salvo autorización; documentado en §15 (preguntas abiertas) |
| R6 | `event_id` del API no es BIGINT válido | Baja | Medio | `safe_int()` con fallback a hash del título; log de warning |
| R7 | Conflicto con `proy_heatmap` al escribir `dim_asset` | Baja | Bajo | COALESCE primer-gana; heatmap escribe `source_discovered_by='heatmap'`, scraper `'radar_v4'` |
| R8 | Consumo de disco por CSV + BD | Baja | Bajo | CSV retiene 7 días; BD ~1,08 M filas/mes (~120–150 MB/mes) al omitir `raw_payload`. Si se reactivara `raw_payload`, sumaría ~366 MB/mes (§15.4) |

---

## 12. Plan de Rollback

### 12.1 Rollback Parcial (deshabilitar BD)

Si la BD causa problemas pero el CSV funciona:

```
1. Cambiar DB_WRITE_ENABLED=false en .env
2. Reiniciar crons (no necesario — el cambio se lee en cada ejecución)
3. El scraper/calendario siguen escribiendo CSV como antes
4. Los datos en BD quedan intactos (no se borran)
```

### 12.2 Rollback Completo (revertir código)

```
1. Revertir git al commit anterior a la migración
2. Los datos en BD NO se revierten (son aditivos)
3. Si se desea limpiar BD:
   TRUNCATE fact_market_series;
   TRUNCATE fact_economic_event;
   TRUNCATE audit_sync_run;
   TRUNCATE sync_checkpoint;
   DELETE FROM dim_asset WHERE source_discovered_by = 'radar_v4';
4. Restaurar .env sin variables BD (o con DB_WRITE_ENABLED=false)
```

### 12.3 Rollback de Schema (si el DDL causó problemas)

No aplica: el esquema es v1.0.2 del heatmap, ya desplegado y probado. El scraper solo escribe a tablas existentes.

---

## 13. Criterios de Aceptación

| # | Criterio | Verificación | Estado |
|---|---------|-------------|--------|
| CA1 | `seed_symbols.py` garantiza cobertura sin re-etiquetar | **0 símbolos del radar ausentes** en `dim_asset`; `source_discovered_by` de los existentes intacto | ✅ Verificado (0 faltantes) |
| CA2 | Scraper escribe a `fact_market_series` exitosamente | `SELECT COUNT(*) FROM fact_market_series` ≥ 110 después de 1 ciclo; `timestamp_utc` por fila | ✅ 110/110 (2026-09-18) |
| CA3 | Calendario escribe a `fact_economic_event` exitosamente | ≥ 1 evento con **las 29 columnas** pobladas (no NULL las que el API entrega) | ✅ (pipeline V5 operativo) |
| CA4 | `audit_sync_run` registra ejecuciones | `SELECT script_name,status FROM audit_sync_run WHERE script_name IN ('radar_v4','calendario_v4')` | ✅ `radar_v4` SUCCESS |
| CA5 | `sync_checkpoint` se actualiza sin violar `NOT NULL` | `SELECT * FROM sync_checkpoint` muestra filas con `last_timestamp` no nulo | ✅ 110 procesados |
| CA6 | **[DIFERIDO]** Monitor V4 detecta fallos | Fuera del alcance de 3.1.0 | ⏸️ Diferido |
| CA7 | CSV sigue funcionando como buffer | `ls DATOS_LIVE/NASDAQ-QQQ/*.csv` muestra archivos actualizados | ✅ (sin cambios CSV) |
| CA8 | Modo legacy funciona | `DB_WRITE_ENABLED=false` → solo CSV, sin errores | ✅ (default config) |
| CA9 | Particiones BRIN creadas | `SELECT indexname FROM pg_indexes WHERE tablename LIKE 'fact_market_series_%'` muestra índices BRIN | ✅ `2026_09` garantizada |
| CA10 | Sin regresión en funcionalidad existente | Lock, backoff, circuit breaker, rotación CSV — todo funciona como antes | ✅ (sin cambios en V4) |
| CA11 | Scripts SQL versionados y aplicables | `04_migration_3.1.0.sql` deja `raw_payload` nullable; `06_verify_3.1.0.sql` muestra 29 columnas y auditoría sin errores | ✅ Creados (aplicables) |

---

## 14. Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-09-18 | **Implementación del alcance 3.1.0 y verificación en BD real.** Se instaló `psycopg2-binary` en el venv; `config.py` con `VERSION="3.1.0"`, `DB_WRITE_ENABLED` y `SCRIPT_NAME_SCRAPER="radar_v4"`; import de `db/postgresql_connection.py` reparado; creados `db/partitions.py`, `db/market_repository.py`, `application/market_service.py` y `seed_symbols.py`; nuevo `scraper_live_tradingview_v5.py` (V4 con pipeline BD, batch buffer + flush final/parcial). `run_scraper_tradingview.sh` apunta a V5, verifica BD y ejecuta la seed. **Verificado en BD real (2026-09-18):** `fact_market_series` = 110/110 filas del primer ciclo con `source_checksum` presente y `raw_payload` NULL (D18); `audit_sync_run` con `radar_v4 → SUCCESS` (fetched=110, upserted=110, failed=0); `sync_checkpoint` con `radar_v4 → 110 procesados`; partición `fact_market_series_2026_09` garantizada; mapeo CSV↔BD verificado fila a fila con NVDA. **Pendiente:** `retention_events.py` (N9), monitor V4 BD-aware (diferido, §6.6) y actualización de README/docs (§6.9).**
| 2026-09-13 | Creación del roadmap de migración `proy_scrapping_detail` v3.1.0: conexión a BD `heatmap_stock` (localhost:5432), pipelines radar → `fact_market_series`, calendario → `fact_economic_event`, auditoría vía `audit_sync_run`/`sync_checkpoint`, monitor V4 BD-aware, seed de `dim_asset` desde `CONFIG_ACTIVOS`, mantenimiento de CSV como buffer/fallback, particionamiento y BRIN por partición, documentación y versionado. |
| 2026-09-13 | **Revisión y corrección de decisiones** (ver §15): alcance limitado a pipelines + seed (monitor V4 diferido); escritura `fact_market_series` por INSERT batch `ON CONFLICT DO UPDATE`; mapeo de campos por claves nombradas del endpoint `/symbol`; `fact_economic_event` con las 29 columnas; timestamp real por fila; manejo de fallo de BD sin tumbar el proceso; `seed_symbols.py` solo altas nuevas; verificación (no creación) de partición; `psycopg2-binary` a `requirements.txt`; conector local con import reparado; correcciones de `sync_checkpoint.last_timestamp`, `update_checkpoint` y criterios de aceptación. |
| 2026-09-13 | **Segunda ronda de aclaraciones:** `config.py` estricto (falla si faltan vars BD); `DB_WRITE_ENABLED=false` por defecto; corrección de rutas del shell en 3.1.0; INSERT único al final en `audit_sync_run`; `records_failed` por conteo explícito; `captured_at` desde `timestamp_captura`; `*_display` derivadas; **`raw_payload` de series omitido** por costo (~366 MB/mes) y `source_checksum` canónico sin timestamp. §15 actualizada. |
| 2026-09-13 | **Tercera ronda de aclaraciones:** exigir vars BD solo con `DB_WRITE_ENABLED=true`; fallo de `db.connect()` se registra en log local (sin BD no hay auditoría); datos incompletos se insertan con NULL; logging unificado a `logging`; `import config` en el calendario. §15.2 sin preguntas abiertas. |
| 2026-09-13 | **Cuarta ronda de aclaraciones:** retención de `raw_payload` de eventos a 6 meses; sin backfill histórico; se escriben primarios y respaldos (110 series); `seed_symbols.py` con `--dry-run`/`--check`. Queda abierta Q20 (retención de eventos vs. columna `NOT NULL`). |
| 2026-09-13 | **Quinta ronda de aclaraciones:** retención de eventos resuelta con `ALTER COLUMN raw_payload DROP NOT NULL` + `retention_events.py` por cron mensual (nuevo componente N9). §15.2 sin preguntas abiertas. |
| 2026-09-13 | **Scripts SQL versionados (§6.10, D32):** se añaden `proy_heatmap/scripts/04_migration_3.1.0.sql`, `05_retention_events.sql`, `06_verify_3.1.0.sql` y `07_cleanup_legacy.sql`. El scraper no aplica DDL en runtime; `proy_heatmap/scripts/` es la única fuente de verdad del esquema para la convivencia de ambos proyectos en `heatmap_stock`. |

---

## 15. Bitácora de Decisiones y Aclaraciones

### 15.1 Decisiones confirmadas (2026-09-13)

| # | Tema | Decisión |
|---|------|----------|
| D1 | Alcance 3.1.0 | Pipelines de escritura + auditoría + seed. **Monitor V4 y Telegram diferidos**. |
| D2 | Escritura `fact_market_series` | `INSERT ... ON CONFLICT (asset_id, timestamp_utc) DO UPDATE` en batch (`execute_values`), con cache de `asset_id`. No se usa `upsert_market_series()`. |
| D3 | Escritura ante conflicto (series) | `DO UPDATE` (sobreescribe con el valor más reciente, actualiza `ingested_at`). |
| D4 | Escritura ante conflicto (eventos) | `DO UPDATE` con `COALESCE`; preserva `first_seen_at`, actualiza `actual/previous/forecast` y `last_updated_at`. |
| D5 | `seed_symbols.py` | Solo altas nuevas; no re-etiqueta ni sobreescribe los existentes. |
| D6 | Columnas de `fact_economic_event` | Poblar **las 29 columnas** del esquema. |
| D7 | `timestamp_utc` (series) | Timestamp real **UTC por fila** (`data['timestamp_utc']`), no timestamp de batch. |
| D8 | Fallo de BD | No tumbar el proceso (CSV ya escrito); registrar `audit_sync_run` FAILED y salir con código 0. |
| D9 | Conector | Usar el archivo local `db/postgresql_connection.py`; no importar de `proy_heatmap`. Reparar el import roto. |
| D10 | Particiones | Solo verificar la existencia; crear la del mes actual únicamente si falta (caso excepcional). |
| D11 | `config.py` sin variables BD | **Falla en el import** si `DB_WRITE_ENABLED=true` y faltan `BD_HEATMAP_*` (ver D21). Sin degradación silenciosa. |
| D12 | `DB_WRITE_ENABLED` por defecto | `false`. Se activa explícitamente en `.env`. |
| D13 | Rutas del shell | **Se corrigen en 3.1.0** (calendario → `DATOS_LIVE_CALENDARIO`, `PROJECT_DIR` → `proy_scrapping_detail`). |
| D14 | Ciclo de `audit_sync_run` | Un **INSERT único al final** con estado final (`SUCCESS`/`FAILED`). |
| D15 | `records_failed` | **Conteo explícito** de errores, no `fetched - upserted`. |
| D16 | `captured_at` (eventos) | `timestamp_captura` **por fila** del CSV. |
| D17 | `*_display` (eventos) | **Derivadas** de `actual/previous/forecast` con `safe_text`. |
| D18 | `raw_payload` (series) | **Omitido** (`NULL`) por costo (~366 MB/mes; §15.4). El crudo queda en el CSV. |
| D19 | `source_checksum` (series) | SHA-256 sobre el **subconjunto canónico** (símbolo + 9 métricas, sin timestamp); estable entre capturas. |
| D20 | `docs/SCHEMA_heatmap_stock.md` | Se mantiene como referencia del heatmap; el handoff del scraper se documenta en `scrapper_documentacion_2026-09-13.md`. |
| D21 | Vars BD en `config.py` | Se exigen **solo si `DB_WRITE_ENABLED=true`**; con `false` arranca en CSV sin requerirlas. |
| D22 | Fallo de `db.connect()` | Si la conexión falla, **registrar en log local y continuar** (sin BD no se puede escribir la auditoría). Si la conexión es OK pero el batch falla, registrar `audit_sync_run` **FAILED**. |
| D23 | Datos incompletos | Insertar la fila con **NULL** en los campos faltantes (no omitir el símbolo). |
| D24 | Logging | **Unificar a `logging`** en scraper, calendario y módulos nuevos. |
| D25 | `import config` en calendario | **Sí:** `calendario_tradingview_live_v4.py` importa `config` para `PG_*` y `SCRIPT_NAME_CALENDARIO`. |
| D26 | Retención `raw_payload` eventos | **6 meses**: `NULL` en eventos con antigüedad > 6 meses (job de mantenimiento). |
| D27 | Backfill histórico | **Sin backfill**: solo capturas nuevas hacia adelante; el histórico permanece en CSV. |
| D28 | Símbolos escritos | **Primario + respaldo** (110 series), igual que el CSV. |
| D29 | Interfaz `seed_symbols.py` | Con flags **`--dry-run`** y **`--check`** (reporta faltantes sin escribir). |
| D30 | Retención de eventos vs. `NOT NULL` | `ALTER COLUMN raw_payload DROP NOT NULL` (NULL real). |
| D31 | Job de retención | **Script dedicado `retention_events.py` + cron mensual** (registra en `audit_sync_run`). |
| D32 | Scripts SQL y DDL | Todo DDL/DML de mantenimiento se documenta y versiona en **`proy_heatmap/scripts/`** (`04`–`07`); el scraper no aplica DDL en runtime. Ver §6.10. |

### 15.2 Preguntas abiertas (pendientes de aclaración)

*Ninguna por el momento: todas las preguntas de la revisión 2026-09-13 fueron resueltas (ver §15.2.1).*

| # | Pregunta | Impacto |
|---|----------|---------|
| — | *(sin preguntas abiertas)* | — |

### 15.2.1 Preguntas resueltas

| # | Pregunta | Resolución |
|---|----------|------------|
| Q1 | ¿`config.py` falla o degrada? | **Falla si faltan vars BD, pero solo cuando `DB_WRITE_ENABLED=true`** (D11 + D21). |
| Q2 | Default de `DB_WRITE_ENABLED` | **`false`** (D12). |
| Q3 | ¿Corregir rutas del shell? | **Sí, en 3.1.0** (D13). |
| Q4 | `raw_payload` de series | **Omitir** (D18). |
| Q5 | Base de `source_checksum` | **Subconjunto canónico estable** (D19). |
| Q6 | `*_display` | **Derivar con `safe_text`** (D17). |
| Q7 | `captured_at` | **`timestamp_captura` por fila** (D16). |
| Q8 | Ciclo de `audit_sync_run` | **INSERT único al final** (D14). |
| Q9 | `records_failed` | **Conteo explícito** (D15). |
| Q10 | ¿Actualizar `SCHEMA_heatmap_stock.md`? | **No; mantener como está** (D20). |
| Q11 | ¿Cuándo exigir vars BD? | **Solo si `DB_WRITE_ENABLED=true`** (D21). |
| Q12 | Fallo de `db.connect()` | **Registrar FAILED y continuar** (D22). |
| Q13 | Datos incompletos | **Insertar con NULL** (D23). |
| Q14 | Logging | **Unificar a `logging`** (D24). |
| Q15 | `import config` en calendario | **Sí** (D25). |
| Q16 | ¿Retención de `raw_payload` de eventos? | **6 meses** (D26). |
| Q17 | ¿Backfill histórico a BD? | **No** (D27). |
| Q18 | ¿Primarios y respaldos a BD? | **Ambos** (D28). |
| Q19 | Interfaz de `seed_symbols.py` | **`--dry-run` / `--check`** (D29). |
| Q20 | Retención vs. `raw_payload NOT NULL` | **`DROP NOT NULL`** (D30) + script de retención con cron mensual (D31). |
| Q21 | ¿Dónde viven los scripts SQL? | **`proy_heatmap/scripts/`** documentados, para convivencia sin conflictos (D32). |

### 15.3 Discrepancias detectadas entre el roadmap y la realidad (resueltas en esta revisión)

1. El roadmap decía "monitor migra a vigilar BD" — diferido.
2. §5.3 contra §6.2.1: método de escritura contradictorio — resuelto a INSERT batch.
3. §8.1 usaba índices de vector del endpoint `/scan` en vez de las claves nombradas de `/symbol`.
4. §6.3.1 omitía 11 columnas de `fact_economic_event`.
5. §6.3.2 no enviaba `last_timestamp` a `sync_checkpoint` (`NOT NULL`).
6. `requirements.txt` no incluía `psycopg2-binary`.
7. El conector local estaba roto (`utils.config_logging` inexistente).
8. `seed_symbols.py`/CA1 asumían 110 re-etiquetados, imposible por primer-gana.
9. El seed en shell verificaba `source_discovered_by='radar_v4'` (métrica equivocada).
10. `docs/documentacion_scrapper_2026-09-13.md` no existe con ese nombre (es `scrapper_documentacion_2026-09-13.md`).
11. `run_calendario_tradingview.sh` apunta a `DATOS_LIVE/calendario_economico`, pero Python escribe en `DATOS_LIVE_CALENDARIO/...`.

### 15.4 Análisis de costo de `raw_payload` (2026-09-13)

Medición sobre los CSV reales del proyecto:

| Métrica | Valor |
|---------|-------|
| `raw_payload` series (promedio) | **356 bytes/fila** (p50 = 358, p95 = 368) |
| Ciclos/mes (110 sim × 20 ciclos/h × cron Lun–Jue 24 h + Vie 17 h) | ~9.786 → **~1,08 M filas/mes** |
| Costo solo `raw_payload` (series) | **~366 MB/mes** |
| Costo fila completa (estructurada + raw + overhead) | **~489 MB/mes → ~5,7 GB/año** |
| Costo sin `raw_payload` (solo estructurada) | ~120–150 MB/mes → **~1,5–1,8 GB/año** |
| `raw_payload` eventos (promedio) | 792 bytes/evento (máx 1.497; comentarios hasta 902 chars) |
| Costo eventos (dedup por `event_id`) | ~1.500–3.000 filas/mes → **~1,5–3 MB/mes** (despreciable) |

**Conclusión:** `raw_payload` de series es ~75 % del peso de la tabla (~4,4 GB de 5,7 GB/año). El JSONB (<2 KB) no se comprime/TOASTea, así que recortar campos ahorra poco (las claves pesan poco).

**Decisión (2026-09-13):** **omitir `raw_payload` en `fact_market_series`** (D18). El crudo permanece en el CSV (7 días + histórico mensual). Si en el futuro se necesita, se puede reactivar la columna con una política de retención (NULL en particiones antiguas o detach/archivado), dado que la tabla ya está particionada por mes.

---

*Documento generado el 2026-09-13. Revisado el 2026-09-13. Referencias: `docs/SCHEMA_heatmap_stock.md`, `docs/heatmap_stock_roadmap_migracion_a_1-0-2.md`, `docs/scrapper_documentacion_2026-09-13.md`, `proy_heatmap/db/postgresql_connection.py`, `proy_heatmap/create_partitions.py`.*
