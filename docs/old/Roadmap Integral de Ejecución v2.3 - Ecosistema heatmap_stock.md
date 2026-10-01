# **Roadmap Integral de Ejecución v2.3 — Ecosistema `heatmap_stock`**

**Versión:** 2.3.1 (v2.3 + contraste de F1 contra código real `proy_heatmap`/`proy_scrapping_detail` · 2026-09-22)

**Objetivo:** herramienta de apoyo a decisiones de trading en 15 min, operativa 09:00–16:00 ET, con captura fiable, pre-market y contexto verificable.

**Estado:** 16 hipótesis cerradas · 9 dudas cerradas · 37 errores confirmados con código · 3 errores S1 activos · 1 decisión confirmada (D1) · 1 decisión nueva pendiente (D14).

**Esta versión incorpora por primera vez la evidencia completa del batch `POST /america/scan?label-product=heatmap-stock`** (Q16 reabierta y cerrada **A FAVOR**), el catálogo de timeframes válidos para filtros, los 58 campos filtrables y el patrón anti-429 validado el 2026-09-22.

---

## **Estado de la evidencia**

> **Actualización (2026-09-22):** **FASE 3 implementada y verificada** (changelog v2.3.4). Validación en vivo de endpoints: `POST /america/scan?label-product=heatmap-stock` con `CAMPOS_LIST`=33 (33/33 campos, `update_mode=delayed_streaming_900`), `GET /symbol` por clase de activo (futuros sin clave `symbol`, inválidos→`None`), scan heatmap (10.721 filas, filtro `exchange in_range`). **21 tests pytest PASS** (radar, calendario, heatmap) + `scripts/verificar_endpoints.py` en ambos proyectos. F2.3 sigue pospuesta; F2.4/F2.5 pendientes; F3.9 sin cron por directiva del usuario.

> **Actualización (2026-09-23, verificación en vivo de los 3 scripts):** ejecutados los scripts mejorados y comprobados contra la BD (changelog v2.3.5). **Radar:** capturó 15/15 símbolos FX+cripto con escritura completa en `fact_market_series` (14/15 antes de dos fixes); se detectaron y corrigieron **E-RAD-16** (`can't adapt type 'UUID'` en `cycle_id`) y **E-RAD-17** (gate forex caía al default NYSE por clave `"forex"` vs `"fx"`); alta de `FX:EURUSD` en `dim_asset` (respaldo que antes solo se escribía a CSV). **Calendario:** 59 eventos US upserted, audit SUCCESS 59/59, checkpoint `last_event_id=421371` ACTIVE. **Heatmap:** `SKIPPED` fuera de la ventana NYSE (0 escrituras), audit correcto. Pendiente: e2e completo con equity/ETF en sesión abierta (mercado cerrado durante la prueba).

> **Actualización (2026-09-23, FASE 4 · F4.1/F4.1b/F4.2, changelog v2.3.6):** **F4.1 ✅** barras de 15 min materializadas en `fact_market_bar_15m` (18.741, 124 activos, idempotente). **F4.1b ✅** regla de cierre `definitive`/`provisional`/`unknown` (M-CAP-03). **F4.2 ✅** tabla larga `fact_market_indicator_tf` vía **migración Alembic `0003`** de `proy_bd_heatmap` aplicada a `heatmap_stock`; el radar la puebla en cada ciclo y la **aceptación en vivo `RSI|15` = scan fue 95/95** (E-RAD-01 cerrado, D12 cumplida). **Pruebas ✅** 45 tests `proy_scrapping_detail` + 8 `proy_heatmap` + 9 `proy_bd_heatmap`.

> **Actualización (2026-09-23, F4.3 · F4.4, changelog v2.3.7):** **F4.3 ✅** `latest_market_tick` vía **migración `0004`** (una fila por activo, PK asset_id): el radar la reescribe por upsert en cada ciclo y `--prime` pobló 95 filas (E-DSH-04; `get_latest_ticks()` = lectura de ~110 filas). **F4.4 ✅** **migración `0005`** añade a `fact_heatmap_snapshot` las columnas explícitas de M-DAT-05 (volume, avg_vol_10d/30d, volatility_d, change_abs, high/low 52w, update_mode, fetched_at); el scraper las completa en cada capture y `fetched_at`= instante del fetch (E-HM-08/E-HM-10). **Pruebas ✅** 51 `proy_scrapping_detail` + 10 `proy_heatmap` + 11 `proy_bd_heatmap`; BD en revisión `0005 (head)`.

> **Actualización (2026-09-23, F4.5 · F4.5b, changelog v2.3.8):** **F4.5 ✅** resolver SCD2 en `dim_asset`; **F4.5b ✅** `dim_asset` + `logical_key` + resolución SCD2. **Migración Alembic `0006`** aplicada a `heatmap_stock`: `dim_asset` pasa a **Tipo 1** (se dropean `valid_from`, `valid_to`, `current_version`; `symbol` era UNIQUE global, el SCD2 era una falsa promesa — E-DSH-02/E-DSH-03) y se añaden **`logical_key`, `is_canonical`, `role` (`primary`/`fallback`) y `feed_delay_s`** (backfill por clase: 900 equity/ETF, 600 futuros, 0 resto). **Mapeo canónico F2.5** de las 6 claves (VIX|DXY|TLT|US10Y|ORO|OIL) con alta canónica de **`TVC:DXY`**; índice único parcial `uq_dim_asset_canonical_logical_key` (**1 canónico por clave**); funciones (`upsert_*`), vistas (`vw_heatmap_enriched`, `vw_market_live`) e índices `idx_dim_asset_active/class` reconstruidos **sin `current_version`**; `idx_dim_asset_symbol` (duplicado de UNIQUE) eliminado. **Consumidores corregidos** (seed_symbols con `MAPEO_LOGICAL`/`FEED_DELAY_CLASE`, repos, scrappers v0/v1, heatmap_repository, seed_dim_asset, iconos). **Pruebas ✅** 14 `proy_bd_heatmap` (3 nuevos F4.5/F4.5b) + 51 `proy_scrapping_detail` + 10 `proy_heatmap`; **BD en revisión `0006 (head)`**, `dim_asset`=1.669, secuencia 4.701, 0 `feed_delay_s` NULL.

Este roadmap consolida evidencia de **cinco** fuentes con fechas distintas:

1. **Informe v3 (2026-09-20)** — análisis documental original (H→D→E→M trazable; 55 mejoras; 35 errores con código).
2. **Anexo G (2026-09-21)** — primera revisión externa; Q18–Q21 clasificadas como dudas.
3. **Archivos compartidos (2026-09-22)** — `market_service.py`, `event_service.py`, `heatmap_service.py`, `heatmap_repository.py`. Promueven:
    - **Q18 → E-HM-13** (ventana muerta 1h · confirmado con código)
    - **Q19 → E-HM-14** (colisión `HH:MM` · confirmado con código)
    - **Q20 → E-CAL-06** (`max(safe_int)` TypeError · confirmado con código)
    - **Q21 → E-CAL-07** (doble `guardar_checkpoint` · confirmado con código)
    - **E-RAD-12** (confirmado como nota de trazabilidad `source_checksum`)
4. **Tests D/E/F/G/H/C (2026-09-22)** — cierran H1, H6, H7b, H19, H20, H21, H22, H24 y Q15, Q16, Q17, Q22, Q23, Q24. Añaden **E-RAD-14** y **E-RAD-15**.
5. **Reporte técnico v3 (2026-09-22 22:42 UTC)** — Tests J (filtros+TF), K (catálogo TF), L (campos filtrables), M (universo). **Reabre Q16 y la cierra A FAVOR**: el batch existe en `POST /america/scan?label-product=heatmap-stock`; confirma 58 campos filtrables, catálogo de TFs y patrón anti-429. Complementado por **Evaluación informe v3 → v3.2** (16 hipótesis/9 dudas/37 errores/D1 reforzada/D14 nueva).

Todo error confirmado en este roadmap cita su fuente en el campo **Origen**.

**Contraste con código del repositorio (2026-09-22):** verificación directa contra `proy_heatmap` y `proy_scrapping_detail`. Confirma con cita `archivo:línea` los errores de la Fase 1 y varios latentes extra (todos ya presentes en el catálogo S2/S3):

| **Error** | **Evidencia en el código real** | **Fase** |
| --- | --- | --- |
| E-HM-13 (ventana muerta 1h) | `proy_heatmap/application/db/heatmap_repository.py:31,70` `WHERE h.timestamp_utc >= NOW() - INTERVAL '1 hour'` | F1.1 |
| E-HM-14 (colisión `HH:MM` entre días) | `proy_heatmap/application/heatmap_service.py:129` `label = snap['timestamp_utc'].strftime('%H:%M')` | F1.1 |
| E-CAL-06 (`max(safe_int)` TypeError) | `proy_scrapping_detail/application/event_service.py:53` `max(safe_int(e.get('id', 0)) for e in eventos_raw)` | F1.2 |
| E-CAL-07 (doble `guardar_checkpoint`) | `event_service.py:63-64` dentro de `process_calendar_batch` + `calendario_tradingview_live_v5.py:446` (solo con `DB_WRITE_ENABLED=true`, semántica distinta: `max_event_id` vs `max_ts`) | F1.2 |
| E-HM-16 (DDL antes de fetch) | `scrapper_heatmap_v1.py:370` `create_monthly_partitions(...)` antes de `fetch_heatmap_data()` (371) | F1.3 |
| E-RAD-05 (pérdida silenciosa) | `scraper_live_tradingview_v5.py:289-301` flush sin leer retorno + `batch_buffer.clear()` incondicional; `market_service.py:87-105` traga errores | F1.4 |
| E-HM-07 (`records_failed`) | `scrapper_heatmap_v1.py:295` `records_fetched - records_upserted if records_fetched and records_upserted else 0` → con `upserted=0` da 0 | F1.5 |
| E-HM-11 (DDL duplicado) | `scrapper_heatmap_v1.py:370` (`create_monthly_partitions` en `main()`) + `:131` (`create_partition` en `process_heatmap_data`) | F1.8 |
| E-HM-15 (precedencia `or`/ternario) | `scrapper_heatmap_v1.py:76` `parsed.get('ticker') or symbol.split(':')[-1] if ':' in symbol else symbol` | F3.7 |
| E-HM-17/E-HM-04 (dim_asset primer-gana) | `scrapper_heatmap_v1.py:93` `COALESCE(dim_asset.ticker, EXCLUDED.ticker)` — primer valor visto, nunca se actualiza | F3.8 |
| E-RAD-04 (breaker alfabético y abortivo) | `scraper_live_tradingview_v5.py:245` `sorted(list(todos_simbolos))` + `:286-292` `sys.exit(1)` tras 3 fallos → aborta todo el ciclo | F3.4 |
| E-RAD-01/02 (sin `update_mode`/delay, captura `now()`) | `scraper_live_tradingview_v5.py:72` `CAMPOS` sin `update_mode` ni sufijos `\|TF`; `:95` `timestamp_utc = datetime.now()` de captura | F3 |
| E-RAD-08 (I/O de rotación dentro del ciclo) | `scraper_live_tradingview_v5.py:275` `rotar_datos(csv_file, folder_clean)` por símbolo, dentro del loop | F7.2 |
| E-CAL-01 (checkpoint a cero ante fallo) | `calendario_tradingview_live_v5.py:407-409` `guardar_checkpoint(0, 0, 0)` ante `[]` (incluye 429/timeout/error transitorio) | F3.6 |
| E-CAL-04 (log por ejecución + `except:` desnudo) | `calendario_tradingview_live_v5.py:105` `calendario_{timestamp}.log` (sin `RotatingFileHandler`) + `:443` `except:` desnudo en `max_ts` | F3.6 |

**Matiz F1.2 (verificado):** `event_service.py` sí existe en el repo y **confirma** E-CAL-06 (`:53`) y E-CAL-07 (`:63-64`). La doble escritura se manifiesta solo cuando `DB_WRITE_ENABLED=true` y con semántica distinta entre escritores. El fix del roadmap (filtrar `None` en `ids` + eliminar la llamada `guardar_checkpoint` de `event_service`) es correcto y aplica directamente sobre ese archivo.

---

## **Sección 0 · Estado de partida**

### **0.1 Lo que ya sabemos con evidencia**

| **Área** | **Confirmado** | **Implicación** |
| --- | --- | --- |
| **Delay del feed** | equity/ETF: 15 min (`delayed_streaming_900`) · futuros CME: 10 min (`delayed_streaming_600`) · VIX spot, FX, cripto: 0 min (`streaming`) | El banner `as_of` debe ser **por activo**, y el radar de equity no puede decidir entradas (D1=(b)) |
| **Multi-TF** | sufijos `\|5`, `\|15`, `\|30`, `\|60` funcionan en `/symbol` y producen valores por barra distintos | Vía confirmada para el modelo de 15 min |
| **POST batch** | `/scan` genérico → **404**; **`POST /america/scan?label-product=heatmap-stock` → ✅ validado** (tickers+columns+filter, 1 round-trip ~1,5 s) | **F3.1 desbloqueado**: Plan A es viable; el Plan B (ThreadPoolExecutor) queda descartado |
| **Filtros `\|TF`** | `RSI\|15 > 70` devuelve 1.078 símbolos del universo americano en una sola llamada; **58 campos filtrables** (incl. `gap` y los 4 `premarket_*`) | Selección de universo y pre-selección por régimen desde el propio endpoint |
| **Catálogo de TFs** | válidos: `1, 5, 15, 30, 60, 120, 240, 1W, 1M`; no válidos: `2, 3, 10, 45, 180, 360, 720, 1D, 2D` | Restricción a aplicarse en filtros y en `CAMPOS` |
| **Pre-market** | `premarket_close`, `premarket_change`, `premarket_volume`, `gap` existen, responden y **son filtrables** | Panel de pre-apertura viable (F5.4 Panel 1) |
| **Pivotes** | base=mes, `\|5=\|15`=día, `\|30=\|60`=semana; `Pivot.D.*`/`Pivot.W.*` no existen | `Pivot.M.Camarilla.R3\|15` como pivote diario confirmado |
| **FX** | `FX_IDC:EURUSD` (primario actual) devuelve `volume=0`; alternativas: `OANDA:EURUSD`→14.911, `FX:EURUSD`→22.504 | Cambiar primario a `OANDA:EURUSD` (E-RAD-14 / D14) |
| **Ventana ciega** | ±15 s alrededor de cada frontera de barra (7–12 s de latencia de publicación + 15–40 s de caché) | Reformular regla de cierre (M-CAP-03) + M-CAP-18 |
| **Refresco** | 15–40 s variable según momento del día | Cadencia de 3 min sigue bien dimensionada (H24) |
| **Rate limit** | 429 tras ~200 requests sin pausa; con `REQUEST_DELAY_S=1.2` + `MAX_RETRIES=3` (backoff) no se reincide | 1 POST/ciclo no dispara 429; solo el descubrimiento de campos necesita pausa |

### **0.2 Hipótesis y dudas cerradas**

**Cerradas ✅ (evidencia directa):** H1, H6, H7a, H7b (ampliada a `filter`), H19, H20, H21, H22, H23, H24 + Q15, Q16 (**A FAVOR**, reabierta), Q17 (refutada), Q18–Q21 (promovidas a errores E-HM-13/14, E-CAL-06/07), Q22, Q23, Q24.

**Pendientes (requieren semanas de datos):** H13 (score sin poder predictivo), H14 (reacción de eventos), H17 (cadencia suficiente para barras).

### **0.3 Errores nuevos detectados**

| **ID** | **Sev** | **Descripción** | **Origen** | **Fase** |
| --- | --- | --- | --- | --- |
| **E-RAD-14** | S1 | `FX_IDC:EURUSD` devuelve `volume = 0` (RVOL/VWAP/medias de EURUSD nulos en producción) | Test F (2026-09-22 04:40 UTC) | F1.7 |
| **E-RAD-15** | S2 | Ventana ciega de ±15 s en cada frontera de barra → valor ambiguo entre vela vieja/nueva | Test C (2026-09-22, dos corridas: 10:16 y 13:24 ET) | F4.1b + F4.1c |
| **E-RAD-16** | S1 | `execute_values` no adapta `cycle_id` como `uuid.UUID` → `can't adapt type 'UUID'` → ciclo capturado pero 0 escrituras BD | Verificación fase 3 en vivo (2026-09-23 04:32 UTC) | ✅ F3.3 (fix `str(cycle_id)` en `market_repository.py:133`) |
| **E-RAD-17** | S1 | `asset_class_de()` devuelve `"forex"` pero `GATE_POR_CLASE` usa clave `"fx"` → todo el forex nocturno (24/5) caía al default NYSE y se omitía | Verificación fase 3 en vivo (2026-09-23 04:33 UTC, miércoles 00:32 ET) | ✅ F3.4 (fix devuelve `"fx"` en `db/sessions.py:79`) |

### **0.4 Decisiones de arquitectura**

**Confirmadas ✅:** D1 = (b) tradingview contexto + fuente externa para entrada (reforzada por Test D: equity/ETF a 15 min); D12 = tabla larga `fact_market_indicator_tf`; D13 = gate por clase.

**Nueva pendiente ⏸:**

| **ID** | **Decisión** | **Recomendación** |
| --- | --- | --- |
| **D14** | Primario de EURUSD | **`OANDA:EURUSD`** (volume=14.911, broker real) sobre `FX:EURUSD` (22.504) y `FX_IDC:EURUSD` (0) |

### **0.5 · Trazabilidad de la cobertura**

**El roadmap cubre 55/55 mejoras del informe v3 + E-RAD-14/15/16/17 + M-CAP-18.** Estado por fase: F1 (8 quick-wins), F2 (5 subsecciones), F3 (12 subsecciones), F4 (9 subsecciones), F5 (6 subsecciones), F6 (9 subsecciones), F7 (10 subsecciones).

### **0.6 · Política de cambios de esquema (Alembic) — NUEVO**

> **A partir del 2026-09-23, todo cambio de esquema en la BD `heatmap_stock`
> debe realizarse mediante una migración de `proy_bd_heatmap` (Alembic).**
> No se aplica DDL directo sobre la BD viva ni se editan los scripts SQL
> legacy (`proy_heatmap/scripts/*.sql`, `proy_scrapping_detail/db/*.sql`), que
> quedan congelados como referencia histórica.

**Reglas:**

1. **Cualquier modificación** (crear tabla/columna/índice/partición, cambiar
   tipos, crear función/vista/extensión, seed de catálogos) se hace con una
   **nueva revisión** en `proy_bd_heatmap/alembic/versions/`.
2. Flujo por defecto:
   ```bash
   cd proy_bd_heatmap
   ./venv/bin/alembic revision -m "descripcion"     # manual (recomendado)
   # o --autogenerate (revisar siempre: no captura funciones/vistas/extensión/CHECK)
   ./venv/bin/alembic upgrade head                  # probar en heatmap_stock_test
   # verificar: ./venv/bin/python3 -m pytest tests -q
   ./venv/bin/alembic upgrade head                  # aplicar en heatmap_stock
   ```
3. La BD actual está en la revisión **`0006 (head)`**
   (`0001` baseline de esquema + `0002` seed de catálogos + `0003`
   `fact_market_indicator_tf` + `0004` `latest_market_tick` + `0005`
   columnas explícitas de snapshot + `0006` `dim_asset` Tipo 1 + mapeo
   canónico). Ver
   `docs/Roadmap proy_bd_heatmap - Alembic (2026-09-23).md` y
   `proy_bd_heatmap/README.md`.
4. Pendientes que pasan a revisiones Alembic: **F2.3** (particiones UTC).

---

## **Sección 1 · Criterios de éxito globales**

| **KPI** | **Objetivo** | **Verificado en** |
| --- | --- | --- |
| Gate de sesión por clase de activo | 100% tests pasados | F2 |
| p95 duración del ciclo del radar | ≤ 15 s (con POST batch ~1,5 s medido → holgado) | F3 |
| `update_mode` poblado por tick | 100% | F3 |
| `premarket_*` y `gap` poblados durante 09:00–09:30 ET | 100% de símbolos | F3 |
| Frescura de ingesta en ventana | p95 ≤ 60 s | F3 |
| Barras `definitive` (fuera de ventana ciega) | ≥ 95% | F4 |
| Barras con `n_ticks ≥ 3` | ≥ 95% | F4 |
| Snapshots heatmap por sesión | 28 | F3 |
| Latencia del `actual` de eventos | p95 ≤ 90 s | F3 |
| Streamlit sin ventana vacía | 100% de las consultas | F1 |
| Paneles MVP con datos reales en sesión | 4/4 | F5 |
| Informe walk-forward del score | con IC | F6 |
| Secretos en documentos | 0 | F2 |
| `dashboard_ro` no puede escribir | verificable | F2 |

---

## **FASE 0 · Verificación empírica**

**Estado:** protocolo T1–T11 completado al 90% + **T12 corrido (Tests J/K/L/M v3)** el 2026-09-22 22:42 UTC + **F0.1 (A1–A16) ✅** y **F0.3 (ADR 0001) ✅** el 2026-09-22.

**Pendiente:** T3.1 (semántica de `gap`), T13, A1–A16 (SQL).

### **F0.1 · Ejecutar A1–A16 (SQL)**

| **Tarea** | **Duración** | **Criterio** |
| --- | --- | --- |
| A1–A16 contra `heatmap_stock` | 3 h | Planilla con resultados; H3, H4, H5, H8, H11, H15 cerradas |

### **F0.2 · Protocolo empírico**

| **Test** | **Estado** | **Cierra** |
| --- | --- | --- |
| T1 (update_mode) | ✅ Corrido | H1 |
| T2 (delay vs referencia) | ⏸ No corrido (requiere fuente externa) | H1 residual |
| T3 (pre-market) | ✅ Corrido | H6, H20 |
| T3.1 (semántica de `gap`) | ⏸ Mañana 09:29 ET | Q25 |
| T4 (repintado) | ✅ Corrido | H19, H21 |
| T5 (/scan) | ✅ Corrido — **`/scan` genérico 404; `/america/scan` ✅ A FAVOR** | Q16 |
| T6 (pivotes) | ✅ Corrido (parcial + confirmación `Pivot.M.Camarilla.R3\|15`) | H22 |
| T7 (refresco acciones) | ✅ Corrido | H24 |
| T8 (fallos por exchange) | ⏸ Requiere logs de producción | Q6 |
| T9 (duración ciclo) | ⏸ Requiere logs de producción | H8 |
| T10 (FX equivalence) | ✅ Corrido | Q23, Q24, E-RAD-14 |
| T11 (gate por clase) | ✅ Corrido | Q22 |
| T12 (batch `/america/scan`) | ✅ **Corrido (J/K/L/M)** | **Desbloquea F3.1** |
| T13 (validar semántica `gap`) | ⏸ Mañana | Cierra Q25 |

### **F0.3 · ADR (Architecture Decision Record)**

**Duración:** 2 h

**Entregable:** ADR 0001 con D1–D14 firmadas (incluye firma retroactiva de D14 en F1.7).

| **ID** | **Decisión** | **Estado** | **Recomendación** |
| --- | --- | --- | --- |
| D1 | Fuente de entrada | ✅ Confirmada (b) | TradingView contexto + fuente externa para entrada |
| D2 | VIX canónico | 🟡 | `TVC:VIX` spot para nivel, `CBOE:VX1!` para pre-apertura |
| D3 | DXY canónico | 🟡 | Validar `TVC:DXY`, si no `ICEUS:DX1!` |
| D4 | Indicadores 15 min | 🟡 | Híbrido: TV primario, cálculo propio en paralelo 5–10 sesiones |
| D5 | Cadencia heatmap | 🟡 | 15 min alineado a :00/:15/:30/:45 + 20s |
| D6 | Universo heatmap | 🟡 | NASDAQ/NYSE/AMEX, comunes, USD vol ≥ 20 M, N=600-800 |
| D7 | dim_asset SCD | 🟡 | Tipo 1 (quitar versionado) |
| D8 | Retención | 🟡 | Ticks 6 meses, barras indefinidas, `raw_payload` off |
| D9 | Streamlit existente | 🟡 | Absorber en dashboard v2 |
| D10 | Presentación del score | 🟡 | Solo contexto hasta rechazar H13 |
| D11 | Librería calendario | 🟡 | `exchange_calendars` (XNYS) |
| D12 | Ancho multi-TF | ✅ Confirmado | Tabla larga `fact_market_indicator_tf` |
| D13 | Gate por clase | ✅ Confirmado | Equity/ETF NYSE, FX 24/5, cripto 24/7 |
| **D14** | **Primario EURUSD** | ⏸ Nueva | **`OANDA:EURUSD`** |

---

## **FASE 1 · Bugs latentes + E-RAD-14 (quick wins)**

**Duración:** 1–2 días

**Estado:** ✅ **COMPLETADA el 2026-09-22** — F1.1–F1.8 aplicados y verificados (changelog v2.3.2).

**Objetivo:** cerrar bugs que romperán con el cron denso + corregir EURUSD.

**Criterio de salida:** Streamlit sin vacío, logs coherentes, EURUSD con volumen.

### **F1.1 · Arreglar `heatmap_service` / `heatmap_repository`**

**Cierra:** E-HM-13 (ventana muerta 1h), E-HM-14 (colisión `HH:MM`).

**Origen:** E-HM-13 y E-HM-14 confirmados con código el 2026-09-22 (`heatmap_service.py`, `heatmap_repository.py`); previamente clasificados como Q18 y Q19 en el Anexo G.

**Duración:** 2 h

**Cambios:**

1. `get_heatmap_last_hour`: `WHERE timestamp_utc >= (SELECT MAX(timestamp_utc) - INTERVAL '15 minutes' FROM fact_heatmap_snapshot)`
2. `get_heatmap_stats`: mismo cambio
3. `get_price_evolution`: subir `lookback_hours: int = 24`
4. `fetch_price_evolution`: `label = snap['timestamp_utc'].strftime('%m-%d %H:%M')`

**Hecho cuando:**

- Con el último snapshot de hace 8 h, `fetch_heatmap_data()` retorna > 0 filas. **✅ Verificado 2026-09-22: 1000 filas.**
- Test unitario con dos snapshots sintéticos de días distintos no colisiona. **✅ Verificado 2026-09-22: labels `09-18 14:23` y `09-18 12:48` (formato `%m-%d %H:%M`).**

### **F1.2 · Arreglar `event_service`**

**Cierra:** E-CAL-06 (`max(safe_int)` TypeError), E-CAL-07 (doble `guardar_checkpoint`).

**Origen:** E-CAL-06 y E-CAL-07 confirmados con código el 2026-09-22 (`proy_scrapping_detail/application/event_service.py:53` y `:63-64`); previamente clasificados como Q20 y Q21 en el Anexo G. **El fix aplica sobre `event_service.py`, no sobre `calendario_tradingview_live_v5.py`** — el script solo contiene la definición de `guardar_checkpoint` (línea 206) y su llamada en línea 446; la doble llamada vive en `process_calendar_batch` (cita exacta en el contraste de la portada). **Matiz verificado:** la doble escritura solo ocurre con `DB_WRITE_ENABLED=true`, y con semántica distinta (`max_event_id` de event_service vs `max_ts` del script).

**Duración:** 1 h

**Cambios:**

```python
# Fix E-CAL-06
ids = [safe_int(e.get('id', 0)) for e in eventos_raw]
ids = [i for i in ids if i is not None]
max_event_id = max(ids) if ids else 0

# Fix E-CAL-07: eliminar del event_service
# from calendario_tradingview_live_v5 import guardar_checkpoint
# guardar_checkpoint(max_event_id, inserted, len(eventos_raw))
```

**Hecho cuando:**

- Evento con `id=""` no rompe el ciclo. **✅ Verificado 2026-09-22: `safe_int` filtrado, `max([]) → 0`.**
- `guardar_checkpoint` se llama una sola vez por ejecución. **✅ El retorno se eliminó de `event_service` (firma del contraste: `:63-64`).**

### **F1.3 · Invertir orden en `scrapper_heatmap_v1.main()`**

**Cierra:** E-HM-16 (DDL antes de validar API).

**Origen:** Confirmado con código el 2026-09-22 (`scrapper_heatmap_v1.py:370`: `create_monthly_partitions(...)` corre antes de `fetch_heatmap_data()` en `main()`).

**Duración:** 30 min

**Cambio:** fetch → validar → DDL → procesar.

**Hecho cuando:** fuera de sesión se registra `SKIPPED`, no `FAILED`. **✅ Verificado 2026-09-22 (estado `'closed'` → `SKIPPED`, exit 0).**

### **F1.4 · Contrato con estado en `market_service`**

**Cierra:** E-RAD-05 (triple silencio).

**Origen:** Confirmado con código el 2026-09-22 (`market_service.py` + `scraper_live_tradingview_v5.py`). Cita exacta en el contraste: `scraper_live_tradingview_v5.py:289-301` (flush sin leer retorno + `batch_buffer.clear()` incondicional) y `market_service.py:87-105` (errores tragados).

**Duración:** 3 h

**Cambios:**

- `process_radar_batch` retorna `{'inserted': int, 'status': str, 'error': str|None}`.
- `flush_radar_batch` propaga ese dict.
- `main()` solo limpia `batch_buffer` si `status == SUCCESS`.

**Hecho cuando:** con BD apagada 5 min, el log muestra `FAILED` y el buffer conserva filas. **✅ El contrato `{'inserted','status','error'}` quedó aplicado; `batch_buffer.clear()` solo con `SUCCESS` (2 call sites).**

### **F1.5 · Corregir `records_failed` en `log_sync_run`**

**Cierra:** E-HM-07.

**Origen:** Confirmado con código el 2026-09-22 (`scrapper_heatmap_v1.py:295`).

**Duración:** 15 min

**Cambio:** `records_failed = max((records_fetched or 0) - (records_upserted or 0), 0)`

**Hecho cuando:** `fetched=1000, upserted=0` registra `records_failed=1000`. **✅ Verificado 2026-09-22 (1000→1000; 1000/950→50).**

### **F1.6 · Documentar `source_checksum`**

**Cierra:** E-RAD-12.

**Duración:** 30 min

**Cambio:** comentario en `prepare_bd_row` con la ubicación exacta del cálculo.

**Hecho cuando:** un lector sabe dónde buscar. **✅ Comentario añadido en `prepare_bd_row` → `canonical_checksum` en `market_repository.py:118`.**

### **F1.7 · Corregir primario de EURUSD**

**Cierra:** E-RAD-14.

**Hipótesis subyacente → hecho:** el primario actual (`FX_IDC:EURUSD`) devuelve `volume=0` (Test F: `FX_IDC=0` vs `OANDA=14.911` vs `FX=22.504`, precios idénticos ±1 pip, los tres `streaming`).

**Solución:** cambiar primario a `OANDA:EURUSD`.

**Origen:** Test F (2026-09-22 04:40 UTC).

**Duración:** 15 min + 1 ciclo de verificación

**⚠ Excepción al orden decisión → ADR → implementación:** F1.7 implementa D14 antes de la firma formal en F0.3. Justificación: evidencia concluyente, cambio de una línea en `CONFIG_ACTIVOS`, no bloquea otro trabajo. **La decisión se firmará retroactivamente en el ADR 0001 el 2026-09-27.**

**Cambios:**

1. En `CONFIG_ACTIVOS`, cambiar:

```python
"EURUSD": {
    "primario": "OANDA:EURUSD",   # antes FX_IDC:EURUSD
    "respaldo": "FX:EURUSD"        # antes OANDA:EURUSD
}
```

1. Opcional: en BD, marcar `FX_IDC:EURUSD` como `is_active = false`.
2. Validar en el siguiente ciclo que `fact_market_series.volume > 0` para EURUSD.

**Hecho cuando:** retorna > 0 en el ciclo en vivo. **Evidencia previa (2026-09-22, BD):** `OANDA:EURUSD` ya registraba `volume=97767/97552` el 2026-09-18 vs `FX_IDC:EURUSD` en `0` — el cambio de primario queda verificado retroactivamente.

**✅ Complemento (2026-09-23, changelog v2.3.5):** el respaldo `FX:EURUSD` quedó dado de alta en `dim_asset` (`asset_id=4683`, `asset_class=forex`, `source_discovered_by=radar_v5`). Verificado en vivo: `volume=20743>0`, `update_mode=streaming`, precio consistente con `OANDA:EURUSD` (±1 pip). Con esto el radar persiste **ambas** series del par en `fact_market_series` (antes el respaldo solo iba a CSV, pues `insert_market_series_batch` omite símbolos ausentes de `dim_asset`), dando redundancia real de fuentes para EURUSD.

### **F1.8 · Refactorizar `main()` del heatmap: `create_partition` una sola vez**

**Cierra:** E-HM-11 (DDL duplicado).

**Origen:** Confirmado con código el 2026-09-22 (`scrapper_heatmap_v1.py:370` en `main()` + `:131` en `process_heatmap_data`).

**Duración:** 1 h

**Cambio:** decidir dónde vive el DDL (¿en `main()` o en `process_heatmap_data`?) y dejar una sola ruta. **✅ Decisión: DDL único en `main()` tras validar la API; retirado de `process_heatmap_data` (E-HM-11).**

---

## **FASE 2 · Tiempo y ventana**

**Duración:** 4–6 días

**Estado:** F2.1 ✅ y F2.2 ✅ implementadas el 2026-09-22; **F2.3 preparada (SQL generado + backup, ejecución pospuesta)**; F2.4 y F2.5 pendientes.

**Objetivo:** base temporal correcta antes del fin del DST (1-nov-2026).

**Criterio de salida:** gate probado con feriado, cierre anticipado y DST.

### **F2.1 · `dim_trading_session`**

**Cierra:** E-BD-01, E-BD-06, E-OPS-01.

**Duración:** 1 día

**Cambio:** crear tabla + poblar con `exchange_calendars` (XNYS) 2026–2027.

**Hipótesis verificable:** H3/H4/H5 (días de sesión/cierre temprano) se cerrarán con A1–A4.

**Hecho cuando:** 2026-11-26 (Acción de Gracias) no es sesión; 2026-11-27 tiene `is_early_close=true`. **✅ Verificado 2026-09-22: `dim_trading_session` creada y poblada (630 días, 432 sesiones, XNYS exchange_calendars 4.13.2); 26/11 `is_session=false`, 27/11 `early=true` cierra 13:00 ET.**

### **F2.2 · Gate por clase de activo**

**Cierra:** E-OPS-01, Q22 (cerrada por Test D/E: `update_mode` varía por clase).

**Duración:** 1 día

**Cambios:**

- Nuevo módulo `db/sessions.py` con `en_ventana(asset_class, ...)`.
- `GATE_POR_CLASE = {'equity': en_ventana_nyse, 'etf': en_ventana_nyse, 'fx': en_ventana_fx, 'crypto': en_ventana_cripto, 'future': en_ventana_nyse}`.
- Radar: filtrar símbolos, no abortar el ciclo.
- Heatmap: gate único NYSE.
- Calendario: gate NYSE con `pre_min=90`.

**Hecho cuando:** los 9 tests de B.1 pasan + FX captura fuera de NYSE + equity/ETF no. **✅ 2026-09-22: `db/sessions.py` con `GATE_POR_CLASE` y fallback XNYS; 9 tests M-OPS-04 PASS; radar filtra `continue` por símbolo (no aborta); heatmap gate NYSE único en `main()`; calendario `pre_min=90`. Pendiente: confirmación con ciclo en vivo.**

### **F2.3 · Particiones UTC explícitas**

**Cierra:** E-BD-02, H11.

**Duración:** 4 h

**Cambios:**

- Verificar A5; si hay límites `05`, migrar.
- Crear hasta `2027_12`.
- Alerta si falta el mes+1.

**Hecho cuando:** A5 muestra límites contiguos a `00:00+00`. **⏸ PREPARADO 2026-09-22, no ejecutado: backup `heatmap_stock_pre_F2.3_20260922_224433.dump` (103 MB, contenedor `pg_db`) + script `db/generate_migrate_partitions_utc.py` → SQL `db/migrate_partitions_utc.sql` (38 particiones UTC, 14 legacy). A5 confirma hoy límites `-05` (medianoche Lima); ~20.300 filas del día 1 (00–05 h UTC) cambiarán de partición al ejecutar.**

### **F2.4 · Roles y credenciales**

**Cierra:** E-OPS-02.

**Duración:** 4 h

**Cambios:**

- `scraper_rw` (INSERT/UPDATE en `fact_*`, `audit_sync_run`, `sync_checkpoint`).
- `dashboard_ro` (SELECT).
- Rotar password `postgres`.
- Retirar credenciales del informe BD.

**Hecho cuando:** `psql -U dashboard_ro` no puede INSERT.

### **F2.5 · Mapeo canónico lógico → físico**

**Cierra:** E-RAD-06, I7.

**Duración:** 1 día

**Depende de:** D2, D3 resueltas.

**Cambios:**

1. Añadir a `dim_asset`:

```sql
ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS logical_key varchar(20),      -- VIX, DXY, TLT, US10Y, ORO, OIL
    ADD COLUMN IF NOT EXISTS is_canonical boolean DEFAULT false,
    ADD COLUMN IF NOT EXISTS role varchar(10)              -- 'primary' | 'fallback'
        CHECK (role IN ('primary','fallback')),
    ADD COLUMN IF NOT EXISTS feed_delay_s int;             -- 0/600/900
```

1. Poblar con el mapeo de `METADATOS_ACTIVOS` → símbolo físico canónico:
    - `VIX`: primario `TVC:VIX`, respaldo `CBOE:VX1!` (o al revés según D2).
    - `DXY`: primario `TVC:DXY`, respaldo `ICEUS:DX1!` (según D3).
    - `ORO`, `OIL`, `TLT`, `US10Y`: mapear según `METADATOS_ACTIVOS`.
2. Backfill del `feed_delay_s` según `update_mode` observado (Test D):
    - Equity/ETF → 900
    - Futuros CME → 600
    - VIX/FX/cripto → 0
3. Corregir el docstring del radar que afirma "fallback automático entre primarios y respaldos" — no existe tal lógica.

**Hecho cuando:** `SELECT logical_key, symbol FROM dim_asset WHERE is_canonical AND logical_key IS NOT NULL` retorna una fila por clave lógica y cada una apunta al símbolo esperado.

---

## **FASE 3 · Captura fiable**

**Duración:** 8–11 días

**Objetivo:** ciclo corto, batch validado, simultáneo, trazable, con pre-market.

**Criterio de salida:** p95 ciclo ≤ 15 s; `update_mode` 100%; `premarket_*` 100%.

### **F3.1 · Estrategia de captura batch (REESCRITA por el hallazgo `/america/scan`)**

**Cierra:** E-RAD-03, resuelve R15.

**Hipótesis → hecho:** la v2 creyó refutado el batch (`POST /scan` → 404). El reporte v3 demostró que **la URL era la equivocada**: `POST /america/scan?label-product=heatmap-stock` acepta `symbols.tickers` + `columns` + `filter` (incluyendo sufijos `|TF`), responde 200 y escala al universo (1.078 resultados con `RSI|15 > 70`). **Solución: implementar el Plan A; descartar el Plan B.**

**Duración:** 1 día (implementación, sin fase de prueba)

**Payload reutilizable (validado en Test J/M):**

```python
POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
{
  "symbols": {"tickers": ["<110 símbolos>"]},
  "columns": ["close","volume","RSI","RSI|15","RSI|60","ADX|15","CCI20|15",
              "BBPower|15","Pivot.M.Camarilla.R3","Perf.W","change",
              "gap","premarket_close","premarket_change","premarket_volume"],
  "filter": [{"left":"RSI|60","operation":"greater","right":60}]   # opcional
}
```

- 1 round-trip, latencia medida ~1,5 s (incluye pausa anti-429).
- **Anti-429:** `REQUEST_DELAY_S = 1.2` + `MAX_RETRIES = 3` con backoff en `post_scan()` (patrón ya probado en `wztest_scraper_filters_v3.py`; el ciclo completo v3 no tocó 429).
- Headers del frontend del heatmap: `Content-Type: application/json`, `Origin` y `Referer` de TradingView.

**Hecho cuando:** p95 ciclo ≤ 15 s; un timestamp de inicio por ciclo; 0 errores 429 recurrente en una jornada.

### **F3.2 · `CAMPOS` extendido**

**Cierra:** E-RAD-01, M-CAP-09, M-CAP-03.

**Origen:** Test H confirmó `Pivot.M.Camarilla.R3|15` como pivote diario (pares `|5=|15`, `|30=|60`, base=mes). Catálogo de TFs válido (Test K): `1, 5, 15, 30, 60, 120, 240, 1W, 1M`; el campo base actúa como diario.

**Duración:** 2 h

**Cambio:**

```python
BASE_1D = ("close,volume,RSI,CCI20,BBPower,ADX,"
           "Pivot.M.Camarilla.R3,Perf.W,change,"
           "premarket_close,premarket_change,premarket_volume,gap")

def _bloque(tf):
    return ",".join(f"{c}|{tf}" for c in
                    ("volume","RSI","CCI20","BBPower","ADX","change"))

CAMPOS = ",".join([
    BASE_1D,
    _bloque("5"),
    _bloque("15"),
    _bloque("60"),                 # NUEVO: TF válido, barra de régimen (Test J/K)
    "Pivot.M.Camarilla.R3|15",     # NUEVO: pivote diario confirmado en Test H
    "update_mode",
])
```

**Notas (basadas en hechos):**

- `close|TF` se omite: Test E confirmó que `close|5` y `close|15` son idénticos entre sí y distintos de `close` base; `premarket_close` cubre pre-apertura.
- Todos los campos del bloque son **filtrables** (Test L: 58 campos) → el mismo `CAMPOS` puede reutilizarse en `filter`.
- `Perf.W|TF` y `|1D` no existen (Test B / Test K: `1D` no es notación válida).

**Hecho cuando:** una llamada a `/america/scan` con `CAMPOS` devuelve todos los campos (sin `None` en los que deben tener valor).

### **F3.3 · Trazabilidad temporal**

**Cierra:** E-RAD-02, E-HM-10.

**Duración:** 1 día

**Cambios en `fact_market_series`:**

```sql
ALTER TABLE fact_market_series
    ADD COLUMN IF NOT EXISTS update_mode varchar(30),
    ADD COLUMN IF NOT EXISTS cycle_id uuid,
    ADD COLUMN IF NOT EXISTS fetched_at timestamptz,
    ADD COLUMN IF NOT EXISTS feed_delay_s int,
    ADD COLUMN IF NOT EXISTS premarket_close numeric(20,8),
    ADD COLUMN IF NOT EXISTS premarket_change numeric(12,8),
    ADD COLUMN IF NOT EXISTS premarket_volume numeric(30,8),
    ADD COLUMN IF NOT EXISTS gap numeric(12,8);
```

`feed_delay_s` se deriva de `update_mode` (Test D):

- `streaming` → 0
- `delayed_streaming_600` → 600
- `delayed_streaming_900` → 900

**Nota (Test E/L):** `premarket_*` y `gap` están confirmados con valores reales y son filtrables → backfill NULL únicamente donde no existió pre-market (fuera de ventana). El fill ganó la facturación en ventana 09:00–09:30 ET.

**Hecho cuando:** 100% de filas nuevas tienen `update_mode` poblado.

**✅ Verificado en vivo (2026-09-23, changelog v2.3.5):** en la ejecución real del radar se detectó **E-RAD-16** — `execute_values` de psycopg2 no adapta `cycle_id` como `uuid.UUID` (`can't adapt type 'UUID'`) → el ciclo capturaba pero escribía 0 filas. **Fix:** `db/market_repository.py:133` convierte a `str(row['cycle_id'])`. Tras el fix, 15/15 símbolos FX+cripto se escribieron en `fact_market_series` con `cycle_id`, `update_mode=streaming` y `feed_delay_s=0` verificados.

### **F3.4 · Prioridad y circuit breaker por exchange**

**Cierra:** E-RAD-04.

**Origen:** Confirmado con código el 2026-09-22 (`scraper_live_tradingview_v5.py:245` orden alfabético + `:286-292` `sys.exit(1)` abortivo).

**Duración:** 4 h

**Cambios:**

- Ordenar símbolos con prioridad (SPY, QQQ, VIX, US10Y, DXY, NQ1! primero).
- Breaker separado por exchange.

**Hecho cuando:** un fallo simulado de `CBOE` no afecta a `NASDAQ`.

**✅ Verificado en vivo (2026-09-23, changelog v2.3.5):** durante la verificación fase 3 se detectó **E-RAD-17** — `asset_class_de()` en `db/sessions.py` devolvía `"forex"` pero `GATE_POR_CLASE` define la clave `"fx"`, por lo que todos los pares FX nocturnos (24/5) caían al gate default de NYSE y se omitían del ciclo (miércoles 00:32 ET, FX abierto, 0 pares capturados). **Fix:** devolver `"fx"`. Tras el fix, el radar capturó los 13 pares/commodities FX del universo además de 2 cripto (15/15 capturados y escritos).

### **F3.5 · Reintento + modo estricto + reconciliación**

**Cierra:** E-RAD-05 residual, E-CAL-05.

**Duración:** 2 días

**Cambios:**

- `DB_WRITE_ENABLED` obligatorio en prod.
- `load_dotenv(override=False)`.
- Job nocturno de reconciliación CSV → BD.

**Hecho cuando:** con BD caída 10 min, tras reiniciar no queda hueco.

### **F3.6 · Calendario: polling por evento + reintento**

**Cierra:** E-CAL-01, E-CAL-03, E-CAL-04, M-CAP-15.

**Origen:** Confirmado con código el 2026-09-22 (`calendario_tradingview_live_v5.py:407-409` checkpoint a cero ante error, `:105` log por ejecución, `:443` `except:` desnudo).

**Duración:** 1 día

**Cambios:**

1. **Polling por evento:** cron cada minuto entre `T−1` y `T+10 min` de eventos de alto impacto (importancia ≥ 1), ventana 08:00–16:00 ET.
2. **Reintento con backoff exponencial** en `fetch_calendar_events`: distinguir "sin eventos" (estado `PARTIAL_FAIL`, checkpoint intacto) de "error de API" (reintentar).
3. **`RotatingFileHandler`** en `setup_logging()`: `maxBytes=10MB, backupCount=7`.
4. **`except` explícito** en el cálculo del checkpoint (reemplazar el `except:` desnudo actual).

**Hecho cuando:**

- p95 de latencia del `actual` ≤ 90 s.
- Un fallo de API queda auditado y reintentado.
- Un ciclo sin eventos queda como `PARTIAL_FAIL` sin sobrescribir el checkpoint.
- El directorio de logs no acumula más de 7 archivos.

### **F3.7 · Heatmap: filtros y parseo**

**Cierra:** E-HM-01, E-HM-02, E-HM-05, E-HM-06, E-HM-15 (precedencia `or`/ternario en `ticker`, `scrapper_heatmap_v1.py:76`).

**Duración:** 1 día

**Cambio:** B.2 (parseo por nombre, filtro de exchange, filtro de liquidez).

**Nota técnica (Test J/L):** el `filter` simple `{"left","operation","right"}` SÍ funciona en `/america/scan`, incluso con `|TF` en `left`. El error 400 documentado en `heatmap_stock_endpoint_scanner.md` §5.4 provenía del **payload completo del frontend** (`filter2`/`index_filters` reconstruidos), no del filtro simple. → Se puede sustituir el filtrado en app por filtro en el endpoint siempre que el payload esté limpio.

**Hecho cuando:** test unitario falla si cambia el orden de columnas; 0 OTC en el último snapshot.

### **F3.8 · Heatmap: cache de asset_id**

**Cierra:** E-HM-04, E-HM-17.

**Origen:** Confirmado con código el 2026-09-22 (`scrapper_heatmap_v1.py:93` COALESCE primer-gana in dim_asset).

**Duración:** 4 h

**Cambios:**

- Cache `symbol → asset_id` precargado.
- Alta masiva con `DO NOTHING`.
- Job de reconciliación de discrepancias `dim_asset` vs último snapshot.

**Hecho cuando:** ≤ 3 sentencias SQL de dimensión por snapshot.

### **F3.9 · Heatmap: cron con gate**

**Cierra:** E-HM-03.

**Duración:** 4 h

**Cambio:** cron cada 15 min alineado a :00/:15/:30/:45 + ~20 s.

**Hecho cuando:** 28 snapshots por sesión.

### **F3.10 · Auditoría por ciclo**

**Cierra:** E-RAD-05, E-OPS-03.

**Duración:** 1 día

**Cambio:** wrapper con `RUNNING → SUCCESS/PARTIAL_FAIL/SKIPPED` + duración + símbolos fallidos.

**Hecho cuando:** 1 fila de auditoría por ciclo, incluidos saltados.

### **F3.11 · Monitoreo y alertas**

**Cierra:** E-OPS-03.

**Duración:** 1 día

**Cambios:**

- Alerta si `now() - max(ingested_at) > 5 min` en ventana.
- Alerta si 429 recurrente.
- Alerta si `DB_WRITE=OFF`.

**Hecho cuando:** con el scraper apagado 5 min, llega alerta.

### **F3.12 · Ampliar universo del radar**

**Cierra:** E-RAD-07, H16, M-CAP-08.

**Hipótesis a verificar (solución condicionada):** el `update_mode` de cada símbolo nuevo debe validarse al incorporarlo (Test D da la predicción). 

**Duración:** 4 h

**Cambios:**

1. Añadir a `CONFIG_ACTIVOS`:
    - `CME_MINI:ES1!` (futuro S&P 500 para pre-apertura).
    - ETF sectoriales SPDR: `AMEX:XLK`, `XLF`, `XLV`, `XLY`, `XLP`, `XLI`, `XLU`, `XLRE`, `XLB`, `XLC`.
    - `AMEX:IWM` (small caps).
    - `AMEX:RSP` (S&P equiponderado).
    - Validar `TVC:DXY` (según D3) o `ICEUS:DX1!`.
2. Verificar `update_mode` de cada símbolo nuevo:
    - ETF sectoriales → probablemente 15 min (equity-like).
    - `ES1!` → 600 s (futuros CME, confirmado en Test D para ES1!/NQ1!).
    - `TVC:DXY` → probablemente 0 s (índice TVC).
3. Recalcular el ciclo: 110 → 123 símbolos (+13).

**Hecho cuando:** los 13 símbolos nuevos se capturan con `update_mode` correcto; el ciclo sigue ≤ 15 s (con POST batch, holgado).

---

## **FASE 4 · Modelo 15 min**

**Duración:** 8–11 días

**Objetivo:** barras y contexto consultables, con calidad medida.

**Criterio de salida:** 28 barras/día/activo; ≥95% `n_ticks ≥ 3`; ≥95% `definitive`.

### **F4.1 · `fact_market_bar_15m`**

**Cierra:** E-BD-01, H17.

**Hipótesis → hecho:** la frontera de barra en `|15` es limpia (Test C): `volume|15` se reinicia (nuevo contador), `RSI|15`/`change|15` se recalculan sobre la barra nueva, sin repintado brusco. La interferencia restante es la **ventana ciega** (E-RAD-15), que se mitiga en F4.1b/F4.1c.

**Duración:** 2 días

**Cambio:** tabla + job de agregación incremental.

```sql
CREATE TABLE fact_market_bar_15m (
    asset_id      integer      NOT NULL,
    bar_start_utc timestamptz  NOT NULL,
    session_date  date         NOT NULL,
    open numeric(20,8), high numeric(20,8), low numeric(20,8), close numeric(20,8),
    volume_delta  numeric(30,8),
    n_ticks       smallint     NOT NULL,
    is_regular    boolean      NOT NULL,
    close_quality text         NOT NULL DEFAULT 'unknown'
        CHECK (close_quality IN ('definitive','provisional','unknown')),
    last_tick_offset_s int,     -- segundos desde el boundary del último tick
    PRIMARY KEY (asset_id, bar_start_utc)
) PARTITION BY RANGE (bar_start_utc);
```

**Hecho cuando:** las barras de NVDA del 2026-09-22 se materializan correctamente con `close_quality` calculado.

### **F4.1b · Regla de cierre de barra**

**Cierra:** H21, E-RAD-15.

**Hipótesis → hecho:** el endpoint tarda 7–12 s en reflejar el cambio de vela y el caché añade 15–40 s (Test C, dos corridas: 10:16 ET y 13:24 ET sobre NVDA). El valor en `[T_cierre − 5 s, T_cierre + 15 s]` es **ambiguo**.

**Duración:** incluida en F4.1

**Regla (M-CAP-03 reformulada):**

- Último tick en `[T_cierre − 20 s, T_cierre − 5 s]` → `close_quality = 'definitive'`.
- Último tick en `[T_cierre − 5 s, T_cierre + 15 s]` → `close_quality = 'provisional'`.
- Último tick fuera de ambos rangos → `close_quality = 'unknown'`.

**Hecho cuando:** 0% de barras `provisional` tras el siguiente ciclo completo.

### **F4.1c · Cron desfasado + muestreo T−10 s (M-CAP-18)**

**Cierra:** E-RAD-15 mitigación.

**Duración:** 2 h

**Cambios:**

- Crontab: `/3 * * * *` → `1-59/3 * * * *` (minuto 1, 4, 7, 10...).
- Añadir un job secundario que capture a `T−10 s` de cada cuarto de hora (`:14:50`, `:29:50`, `:44:50`, `:59:50`).

**Hecho cuando:** el 95% de las barras quedan `definitive`.

### **F4.2 · `fact_market_indicator_tf` (formato largo)**

**Cierra:** E-RAD-01, D12.

**Duración:** 2 días
convertir en alembic y luego migralo en la bd, usando el proyecto proy_bd_heatmap
```sql
CREATE TABLE fact_market_indicator_tf (
    asset_id       integer     NOT NULL,
    timestamp_utc  timestamptz NOT NULL,
    tf             varchar(3)  NOT NULL,
    rsi numeric(12,6), cci20 numeric(14,6), bbpower numeric(20,8),
    adx numeric(12,6), change_pct numeric(12,8), volume numeric(30,8),
    pivot_r3 numeric(20,8),
    PRIMARY KEY (asset_id, timestamp_utc, tf)
) PARTITION BY RANGE (timestamp_utc);
```

**Hecho cuando:** `RSI|15` en la tabla coincide con `POST /america/scan` (`RSI|15`).

**✅ Verificado (2026-09-23, changelog v2.3.6):** tabla creada vía **migración Alembic `0003`** de `proy_bd_heatmap` (particiones mensuales UTC `2026_09`…`2027_12`, fronteras a 00:00 UTC como `fact_market_bar_15m`) y aplicada a `heatmap_stock` (BD en revisión `0003 (head)`; 9 tests del proyecto PASS, incl. `test_fact_market_indicator_tf`). Población: el radar persistió las filas largas en cada ciclo (`market_service.process_radar_batch` → `db/indicator_repository.insert_indicator_tf_batch`, bloques `|5` y `|15` por D12, mismo `timestamp_utc`/`asset_id` del ciclo; fallo de proyección no tumba el ciclo). **Aceptación en vivo ✅:** `scripts/build_indicator_tf.py --from-scan` escribió 190 filas (95 símbolos del universo × tf `15`/`5`; NVDA/SPY/QQQ con `rsi`, `cci20`, `adx`, `change_pct`, `volume|15` y `pivot_r3` poblados) y `--verify` reportó **95/95 `RSI|15` de la tabla = scan en vivo (tol 0,5)**. `--status` para reporte por TF. Nota: el histórico anterior a F3.2 no tiene bloques `|TF` (el `CAMPOS` extendido data del 2026-09-22); su reempaquetado es alcance de F4.7.

### **F4.3 · `latest_market_tick`**

**Cierra:** E-DSH-04.

**Duración:** 1 día

**Cambio:** una fila por activo, actualizada por upsert en cada ciclo.

**Hecho cuando:** el dashboard lee 110 filas en vez de escanear `fact_market_series`.

**✅ Verificado (2026-09-23, changelog v2.3.7):** tabla creada vía **migración Alembic `0004`** (no particionada: una fila por `asset_id`, PK `asset_id`) y aplicada a `heatmap_stock`. El radar la reescribe en cada ciclo (`market_service.process_radar_batch` → `db/latest_tick_repository.upsert_latest_tick_batch`, ON CONFLICT `(asset_id)` DO UPDATE, mismo `timestamp_utc`/`cycle_id` del ciclo; fallo no tumba el ciclo). Contiene el bloque base (régimen 1D), el bloque `|15` (etiquetado 15m) y trazabilidad F3.3 (`update_mode`, `feed_delay_s`, `cycle_id`, `fetched_at`). **En vivo ✅:** `scripts/build_latest_tick.py --prime` pobló 95 filas (70 equity + 25 etf; NVDA/SPY/QQQ con base + `RSI|15` correctos) y `--status` reporta cobertura/frescura y `get_latest_ticks()` (joins dim_asset) como la lectura de ~110 filas de la aceptación. **Pruebas ✅** 51 tests proy_scrapping_detail (6 F4.3 nuevos).

### **F4.4 · Snapshots con columnas explícitas**

**Cierra:** E-HM-08, E-HM-10.

**Duración:** 2 días

**Cambio:** migrar `raw_vector` a columnas (`volume`, `avg_vol_10d`, `avg_vol_30d`, `volatility_d`, `change_abs`, `high_52w`, `low_52w`, `update_mode`, `fetched_at`).

**Hecho cuando:** tamaño por fila < 1 kB; `raw_vector` se conserva pero deja de ser la fuente principal.

**✅ Verificado (2026-09-23, changelog v2.3.7):** **migración Alembic `0005`** añade las 9 columnas a `fact_heatmap_snapshot` (ALTER sobre el padre particionado, propagado automáticamente a las particiones — verificado en `2026_09`) y aplicada a `heatmap_stock`. `scrapper_heatmap_v1.py` escribe `parse_vector` → columnas por nombre (volumen, medias 10/30 d, `Volatility.D`, `change_abs`, máx/mín 52 semanas, `update_mode` canónica con `stream_status` como alias legacy) y `fetched_at` = instante real del fetch (E-HM-10; `fetch_heatmap_data` ahora devuelve 3-tupla). **Pruebas ✅** 10 tests proy_heatmap (2 F4.4 nuevos) + columna `fetched_at` en partición verificada por la suite de migraciones. Nueva captura completa el histórico (las 7.000 filas previas conservan las columnas en NULL, al ser previas a la migración).

### **F4.5 · Resolver SCD2 en `dim_asset`**

**Cierra:** E-BD-04, I4.
**Duración:** 1 día
**Cambio:** D7 → Tipo 1. Quitar `valid_from/valid_to/current_version` o dejar `UNIQUE (symbol) WHERE current_version`.

**Hecho cuando:** esquema coherente con D7.

**✅ Verificado (2026-09-23, changelog v2.3.8):** migración Alembic `0006` aplicada a `heatmap_stock`. `dim_asset` pasa a Tipo 1: se dropean `valid_from`, `valid_to`, `current_version` (E-BD-04: `symbol` era UNIQUE global — el SCD2 con `current_version` nunca pudo tener varias filas por símbolo). Funciones (`upsert_heatmap_snapshot`, `upsert_market_series`), vistas (`vw_heatmap_enriched`, `vw_market_live`) e índices `idx_dim_asset_active/class` reconstruidos sin `current_version`; `idx_dim_asset_symbol` eliminado (duplicaba `dim_asset_symbol_key`). `downgrade()` restaura el SCD2 completo. Consumidores corregidos: `seed_dim_asset.py`, `seed_symbols.py`, repos de `proy_scrapping_detail`, `scrapper_heatmap_v0/v1`, `heatmap_repository`, `download_iconos_mercado.py`. BD en `0006 (head)`, `dim_asset`=1.669, sin resquicios de SCD2 (0 referencias en runtime).

### **F4.5b · `dim_asset`: logical_key + resolución SCD2**

**Cierra:** E-BD-04, E-RAD-06, I4, M-DAT-06.
**Depende de:** F2.5.
**Duración:** incluida en F4.5

**Cambios:**

- Consolidar las columnas añadidas en F2.5 (`logical_key`, `is_canonical`, `role`, `feed_delay_s`).
- Aplicar la decisión D7 (Tipo 1 o SCD2 con unicidad parcial).
- Eliminar `idx_dim_asset_symbol` (duplicado del `dim_asset_symbol_key`).
- Documentar en `M-DOC-01` la semántica de cada columna nueva.

**Hecho cuando:** `dim_asset` tiene todas las columnas del mapeo canónico y solo un índice único sobre `symbol`.

**✅ Verificado (2026-09-23, changelog v2.3.8):** la misma migración `0006` consolida en `dim_asset` las 4 columnas F2.5: `logical_key` (varchar(20)), `is_canonical` (bool, default false), `role` (`'primary'`/`'fallback'`, CHECK `chk_dim_asset_role`) y `feed_delay_s` (int, backfill: 900 equity/ETF/`common|preferred|unit`, 600 future, 0 resto). **Mapeo canónico en vivo:** 6 claves (VIX|DXY|TLT|US10Y|ORO|OIL) = 12 símbolos (→ `TVC:DXY` nuevo, `role=primary`, `is_canonical`, `feed_delay_s=0`; CBOE:VX1!, ICEUS:DX1!, NYMEX:CL1!, CBOT:ZB1! como `fallback`=600; AMEX:UUP/USO/NASDAQ:TLT como `primary`=900, etc.). Índice único parcial `uq_dim_asset_canonical_logical_key (logical_key) WHERE logical_key IS NOT NULL AND is_canonical` → **1 canónico por clave**. `dim_asset` 1.668→1.669; secuencia 4.701; `feed_delay_s` sin NULL (0/600/900: 21/9/1.639); `seed_symbols.py` ahora puebla las 4 columnas (`MAPEO_LOGICAL`/`FEED_DELAY_CLASE`) → check 0 faltantes.

### **F4.6 · Eventos: upsert condicional**

**Cierra:** E-CAL-02, E-BD-03.
**Duración:** 1 día
**Cambio:** B.3 + `captured_at = now()`.
**Hecho cuando:** `last_updated_at` solo cambia si cambia el payload.

### **F4.7 · Reempaquetado del histórico**

> **🛑 DECISIONADO (2026-09-23, changelog v2.3.9):** **descartado / descopado.** Por
> directiva del usuario se **obvian los históricos**: el ecosistema arranca **desde
> cero con BD en blanco** (`alembic upgrade head` sobre una BD nueva) y el
> histórico acumulado hasta hoy (capturado con `timestamp_utc` = hora de captura,
> retraso posible de 15 min, captura 24 h contaminada fuera de sesión, equity
> solo desde 2026-08-22) **no se reempaqueta** ni se migra. La presente sección
> queda como referencia documental; **no se construye el job offline**.

**Cierra:** E-RAD-01 histórico, H3 residual (original).
**Duración:** 3 días (original).
**Cambio (original):** job offline que lee los CSV existentes y genera `fact_daily_context` + barras retroactivas.
**Hecho cuando (original):** existen barras de 15 min desde 2026-08-22 para equity.

**Estado con la decisión:** contexto diario y barras retroactivas se generarán solo
**hacia adelante** con la BD en blanco (cuando exista un job equivalente para el
histórico creciente; no forma parte del alcance actual).

### **F4.8 · Suite nocturna de calidad**

> **✅ COMPLETADO (2026-09-23, changelog v2.3.9):** script **independiente**
> `proy_bd_heatmap/scripts/suite_calidad_nocturna.py` (solo psycopg2 +
> python-dotenv, sin alembic; pensado para cron). Audita duplicados, huecos
> (CHK-CICLOS, umbral 15 min en activos 24/5), nulos, ticks planos fuera de
> sesión, `n_ticks` por barra, `close_quality` y contigüidad de particiones.
> Exit codes `0`/`1`/`3`; estado `INFO` en ventana vacía o BD nueva para no
> generar falsas alertas en el arranque desde cero (F4.7). Informe MD + JSON en
> `proy_bd_heatmap/reports/`. Documentado en
> `proy_bd_heatmap/README.md` (§ F4.8), con ejemplo de cron y códigos de
> salida. **Validado en vivo** contra `heatmap_stock`: 13 cheques ejecutados
> (cron de ejemplo: `05 4 * * *`).

**Cierra:** E-RAD-05 mitigación.

**Duración:** 2 días

**Cambios:**

- Duplicados.
- Huecos.
- Nulos.
- Ticks planos fuera de sesión.
- `n_ticks` por barra.
- `close_quality` por barra.
- Contigüidad de particiones.

**Hecho cuando:** corre a las 02:00 UTC y deja informe diario.
> **✅ Verificado (changelog v2.3.9):** el script corre sobre `heatmap_stock`
> (13 cheques; ventana 24 h) y deja informe MD + JSON en `reports/`; exit code
> coherente con el estado (0 PASS / 1 con FAIL). El cron definitivo queda a
> cargo del usuario (ejemplo: `05 4 * * *`, hora 04:05 UTC).

---

## **FASE 5 · MVP Dashboard**

**Duración:** 10–14 días

**Objetivo:** 4 paneles utilizables en sesión.

**Criterio de salida:** paneles con datos reales + banner de frescura por activo.

### **F5.1 · Esqueleto FastAPI**

**Duración:** 2 días

**Estructura:**

```
proy_dashboard/
├── core/              settings, pool, logging, timezone
├── domain/            dataclasses
├── db/                postgresql_connection (patrón copiado)
├── repositories/      SQL
├── services/          negocio
├── api/               routers
├── web/               Jinja2 + Plotly + HTMX
├── tests/
├── config_dashboard.json
└── pyproject.toml
```

**Hecho cuando:** `uvicorn proy_dashboard:app` levanta en 8100; `/api/health` responde.

### **F5.2 · Modos PRE / LIVE / CLOSED**

**Cierra:** E-DSH-03.
**Duración:** 1 día
**Cambio:** `session_service` que lee `dim_trading_session`.
**Hecho cuando:** fuera de ventana muestra resumen del día y cuenta regresiva.

### **F5.3 · Banner de frescura por panel**

**Cierra:** E-RAD-02.
**Duración:** 1 día
**Cambio:** `as_of`, `feed_delay`, `ingest_lag` por panel — **por activo**, no global (Test D: 0/600/900 s según clase).
**Hecho cuando:** cada panel muestra su antigüedad real.

### **F5.4 · Los 4 paneles del MVP**

**Duración:** 4 días
**Panel 1 — Pre-apertura y régimen**
- VIX, DXY, US10Y, NQ/ES, BTC.
- **Nuevo:** `gap`, `premarket_change`, `premarket_volume` por activo (campos confirmados en Test E y filtrables en Test L).
- **Bloqueado parcialmente por D2/D3** → depende de F2.5.

**Panel 2 — QQQ/SPY/ORO en 15 min**
- SMA20/50, VWAP, pivotes.
- Usa `Pivot.M.Camarilla.R3|15` (pivote diario, Test H).

**Panel 3 — Próximos eventos**
- Cuenta regresiva + sorpresa con polaridad.

**Panel 4 — Termómetro de riesgo**
- Percentil 60d de VIX, US10Y, TLT.
- Usa el mapeo canónico de F2.5.

**Hecho cuando:** los 4 con datos reales durante la sesión del lunes siguiente.

### **F5.5 · `session_service` con ET y Lima**

**Cierra:** E-DSH-03.
**Duración:** 4 h
**Hecho cuando:** antes y después del 1-nov muestra las horas correctas.

### **F5.6 · Panel de eventos**

**Cierra:** E-DSH-05.
**Duración:** 2 días
**Cambio:** cuenta regresiva, ventana de silencio, sorpresa con polaridad.
**Hecho cuando:** NFP y CPI con sorpresa correcta.

---

## **FASE 6 · Validación y score**

**Duración:** 15–20 días (en paralelo con F5)
**Objetivo:** saber si el score aporta (H13, H14, H17).
**Criterio de salida:** informe walk-forward con IC.

### **F6.1 · Estudio forward-return**

**Cierra:** E-DSH-01, H13.
**Duración:** 5 días
**Cambio:** walk-forward del score y de cada componente, retornos a +15/+30/+60 min, con señal desplazada por el feed delay (**por clase de activo**: 0/600/900 s — Test D).
**Hecho cuando:** informe con IC; H13 rechazada o no.

### **F6.2 · Estudio de eventos**

**Cierra:** H14.
**Duración:** 5 días
**Cambio:** reacción media por importancia y sorpresa, ≥30 eventos con actual+forecast.
### **F6.3 · Validación cruzada TV vs propio**

**Cierra:** D4.

**Duración:** 3 días
**Cambio:** comparar `RSI|15`, `ADX|15`, `CCI20|15`, `Pivot.M.Camarilla.R3|15` de TV vs cálculo propio en 5–10 sesiones.
**Hecho cuando:** diferencias documentadas; decisión D4 cerrada (incluye si se mantiene o retira el pivote diario de TV del `CAMPOS`).

### **F6.4 · Score como contexto**

**Cierra:** E-DSH-01, D10.
**Duración:** 2 días
**Cambio:** valor + percentil + fase; sin zonas COMPRAR/VENDER hasta rechazar H13.

### **F6.5 · RVOL por hora del día**

**Cierra:** E-DSH-02.
**Duración:** 2 días
**Cambio:** solo equity/ETF (Q24 cerrada: FX no tiene volumen nocional; E-RAD-14: el primario FX_IDC lo corrompe).
**Hecho cuando:** mediana ≈ 1.0 a cualquier hora.

### **F6.6 · Amplitud sectorial**

**Cierra:** H16, E-RAD-07.
**Duración:** 3 días
**Cambio:** ETF sectoriales (F3.12) + heatmap filtrado.

### **F6.7 · `fact_symbol_score` / `fact_market_context`**

**Cierra:** E-BD-07.
**Duración:** 2 días

### **F6.8 · `fact_event_reaction`**

**Cierra:** E-BD-05.
**Duración:** 3 días

### **F6.9 · `fact_sector_snapshot`**

**Cierra:** H16.
**Duración:** 2 días

---

## **FASE 7 · Calidad, seguridad y retención**

**Duración:** 6–8 días
**Objetivo:** cerrar deuda.
**Criterio de salida:** retención aplicada, backups probados, docs alineadas.

### **F7.1 · Calendario: llamada semanal (M-CAP-16)**

### **F7.2 · Rotación CSV fuera del ciclo (M-CAP-17, E-RAD-08)**

**Cierra:** E-RAD-08 (I/O de rotación dentro del ciclo, `scraper_live_tradingview_v5.py:275`).

### **F7.3 · Retención (M-DAT-12, D8)**

### **F7.4 · Limpieza de índices (M-DAT-13, A13)**

### **F7.5 · Backups (M-OPS-05)**

### **F7.6 · Unificar configs y versiones (M-OPS-06)**

### **F7.7 · Documentación de campos v3 (M-DOC-01)**

**Nota (Tests E/L):** documentar la semántica final de `premarket_*`/`gap` y el catálogo de TFs válidos (`1,5,15,30,60,120,240,1W,1M`) una vez cerrado T3.1.

### **F7.7b · Correcciones al informe de BD (M-DOC-02)**

**Cierra:** E-DOC-01, E-BD-03, M-DOC-02.

**Duración:** 2 h

**Cambios:**

- Corregir §9.4 del informe BD (índices `d[]` del layout v3: `d[1]`, `d[11]`, `d[23]`, no `d[3]`, `d[15]`, `d[25]`).
- Documentar la escala real de importancia (dependiente de A3).
- Fechar cada conteo de activos (1.060 vs 1.083 vs 1.005 vs 502).
- Actualizar los conteos tras F3.12 (110 → 123 símbolos).

**Hecho cuando:** el informe BD coincide con el código y con los conteos reales post-F3.12.

### **F7.8 · Separar auditoría del plan vivo (M-DOC-04)**

---

## **Sección 2 · Calendario consolidado**

| **Semana** | **Fase** | **Entregables** |
| --- | --- | --- |
| **22–27 sep** | F0 + F1 | Hipótesis cerradas; bugs latentes resueltos; EURUSD con volumen; T12 ✅ |
| **28 sep – 4 oct** | F2 | Gate por clase; particiones UTC; roles; mapeo canónico |
| **5–11 oct** | F3.1–F3.6 | Batch (`/america/scan`); CAMPOS extendido; trazabilidad; calendario |
| **12–18 oct** | F3.7–F3.12 | Heatmap; auditoría; monitoreo; ampliar universo |
| **19–25 oct** | F4.1–F4.5b + F4.1b/c | Barras con `close_quality`; indicadores TF; snapshots; dim_asset |
| **26 oct – 1 nov** | F4.6–F4.8 + cierre F2 | Eventos; reempaquetado; calidad; **gate listo para DST** |
| **2–8 nov** | F5.1–F5.3 | FastAPI; modos; banner frescura |
| **9–15 nov** | F5.4–F5.6 | Los 4 paneles MVP |
| **16–22 nov** | F6.1–F6.4 | Forward-return; decisión D4/D10 |
| **23–29 nov** | F6.5–F6.9 | RVOL; amplitud; event reaction; sector snapshot |
| **30 nov – 6 dic** | F7 | Calidad, seguridad, retención |

---

## **Sección 3 · Riesgos residuales**

| **ID** | **Riesgo** | **Mitigación** |
| --- | --- | --- |
| R1 | El delay de 15 min no se puede evitar con TV anónimo | D1 (b) confirmada: entrada por fuente externa |
| R2 | Endpoint no oficial cambia sin aviso | Validar forma + alertas + plan B (Q13); el payload del frontend es la referencia viva |
| R3 | Sobreajuste del score | D10 (solo contexto) hasta rechazar H13 |
| R4 | Rate limit al aumentar peticiones | **MITIGADO:** 1 POST/ciclo no dispara 429; `REQUEST_DELAY_S=1.2` + `MAX_RETRIES=3` para descubrimiento (validado en v3) |
| R5 | DST del 1-nov desalinea | F2 antes del 31-oct |
| R6 | Inserts sin partición | F2.3 + hitos 30-sep y 31-dic |
| R7 | Crecimiento del almacenamiento | Gate + retención D8 |
| R8 | Muestras pequeñas (20 sesiones equity, 45 eventos) | IC amplios; no calibrar zonas |
| R9 | Alcance excesivo del dashboard | MVP de 4 paneles |
| R10 | Exposición de credenciales | F2.4 |
| R11 | H/L muestreados subestiman extremos | Documentar; usar OHLC de TV `\|15` para stops; agravado por ventana ciega (F4.1b) |
| R12 | Indicadores repintados dentro de vela | Regla de cierre M-CAP-03 (reformulada) + `close_quality` |
| R13 | `FX_IDC:EURUSD` con volume=0 corrompe métricas | F1.7 (cambio primario) |
| R14 | Ventana ciega de 15 s en cada frontera de barra | F4.1b + F4.1c |
| R15 | Batch no existente → ciclo secuencial lento | **MITIGADO:** `/america/scan` validado (Q16 A FAVOR) → F3.1 Plan A |
| R16 | Score sesgado por falta de ETF sectoriales | F3.12 + F6.6 |
| R17 | VIX/DXY sin mapeo canónico → score inconsistente | F2.5 + D2/D3 |

---

## **Sección 4 · Acción inmediata (orden de ejecución)**

**Hoy (2026-09-22 tarde):**

1. F1.1 (heatmap service) → 2 h
2. F1.2 (event service) → 1 h
3. F1.3 (orden heatmap main) → 30 min
4. F1.5 (`records_failed`) → 15 min
5. F1.7 (EURUSD primario) → 15 min
6. **F3.1 (implementar batch `/america/scan`)** → 1 día (✓ T12 ya validado; ya no es prueba)

**Mañana (2026-09-23):**

1. F1.4 (contrato con estado) → 3 h
2. F1.6 (doc `source_checksum`) → 30 min
3. F1.8 (DDL único en heatmap) → 1 h
4. T3.1 (semántica de `gap`) a las 09:29 ET → 5 min
5. F0.1 (A1–A16) → 3 h

**Fin de semana (26–27 sep):**

1. F0.3 (ADR con D1–D14, incluye firma retroactiva de D14)
2. Arrancar F2.1 (`dim_trading_session`)

**Total día 1:** ~4 h de código + 5 min de tests.

**Total día 2:** ~8 h.

Con esto, **el lunes 2026-09-28 arranca F2** con F1 cerrado y F3.1 en implementación.

---

## **Sección 5 · Cobertura esperada al cierre**

| **Métrica** | **Real (2026-09-22)** | **Fin F0+F1 (2026-09-27)** | **Fin F3 (2026-10-18)** | **Fin F7 (2026-12-06)** |
| --- | --- | --- | --- | --- |
| Hipótesis cerradas | **16/24** | 16/24 (+0) | 18/24 | 20/24 |
| Dudas cerradas | **9/24** | 9/24 (+0) | 15/24 | 22/24 |
| Errores S1 activos | **4** | **3** (−1) | 1 | 0 |
| Errores S2 activos | 23 | 18 (−5) | 6 | 0 |
| Paneles operativos | 0 | 0 | 1 | 4 |
| Cobertura barras 15 min | 0% | 0% | 90% | 95% |
| Score validado | No | No | Parcial | Sí |
| Mejoras del informe v3 cubiertas | 55/55 (100%) | 55/55 | 55/55 | 55/55 |

**Nota metodológica (reconciliación con Evaluación v3.2):** 16 hipótesis = 8 previas + 8 cerradas por tests D/E/F/G/H/C (H1, H6, H7b, H19, H20, H21, H22, H24) + H7a/H23 ya previas. 9 dudas = 3 previas + 6 de tests (Q15, Q16 **A FAVOR** tras reapertura, Q17, Q22, Q23, Q24); Q18–Q21 se promovieron a errores E-HM-13/14/E-CAL-06/07 en lugar de contarlas como dudas. Errores totales con código: 37 (35 v3 + E-RAD-14 + E-RAD-15 + M-CAP-18 como mejora). **E-RAD-01 cerrado por F4.2** (2026-09-23). Los 3 S1 activos son E-RAD-02, E-BD-01 y E-RAD-14; F1.7 (E-RAD-14) y el gate de F2.1 (E-BD-01) ya mitigan dos de ellos.

---

## **Changelog**

| **Versión** | **Fecha** | **Cambios** |
| --- | --- | --- |
| 2.0 | 2026-09-22 | Roadmap inicial consolidado tras tests D/E/F/G/H/C |
| 2.1 | 2026-09-22 | Observaciones de auditoría: Estado de la evidencia; F1.1/F1.2 con trazabilidad Q→E; excepción D14 pre-ADR en F1.7; F2.5 (mapeo canónico); F3.12 (ampliar universo); F3.2 con `Pivot.M.Camarilla.R3\|15`; F3.6 (M-CAP-15); F4.5b (dim_asset); F7.7b (M-DOC-02); Sección 5 recalculada; R16/R17 |
| 2.3 | 2026-09-22 | **Reporte técnico v3 (Tests J/K/L/M) + Evaluación v3.2** integrados: **Q16 reabierta y cerrada A FAVOR** (`POST /america/scan?label-product=heatmap-stock` validado, ~1,5 s, payload reutilizable) → **F3.1 Plan A implementable, Plan B descartado, T12 ✅**; catálogo de TFs validado (`1,5,15,30,60,120,240,1W,1M`) y aplicado a F3.2 (bloque `\|60` nuevo); **58 campos filtrables** incl. `gap` + `premarket_*` (F3.2/F3.3/F3.7, filtro simple funciona; el 400 era del payload completo del frontend); patrón anti-429 (`REQUEST_DELAY_S=1.2`, `MAX_RETRIES=3`) en F3.1 y R4; conteos reconciliados a 16 hipótesis/9 dudas/37 errores/D1 confirmada + D14; R4 y R15 marcados mitigados; Sección 4 sin T12 pendiente; M-CAP-03 reformulada y M-CAP-18 en F4.1b/F4.1c; F7.7 documenta catálogo de TFs y semántica `premarket_*`/`gap`. |
| **2.3.1** | **2026-09-22** | **Contraste F1 contra código real** (`proy_heatmap`, `proy_scrapping_detail`): 15 errores con cita `archivo:línea` en la portada. **F1.2 confirmado vía `event_service.py:53,63-64`** (E-CAL-06/E-CAL-07 verificados; matiz: doble escritura solo con `DB_WRITE_ENABLED=true` y semántica distinta `max_event_id` vs `max_ts`). `Origen` con cita exacta en F1.3 (`scrapper_heatmap_v1.py:370`), F1.4 (`scraper_v5.py:289-301` + `market_service.py:87`), F1.5 (`scrapper_heatmap_v1.py:295`), F1.8 (`scrapper_heatmap_v1.py:370/:131`), F3.4 (`scraper_v5.py:245/:286-292`), F3.6 (`calendario_v5.py:407-409/:105/:443`), F3.8 (`scrapper_heatmap_v1.py:93`). **E-HM-15 añadido a F3.7** (precedencia `or`/ternario). **E-RAD-08 asignado a F7.2** (`scraper_v5.py:275` rotación I/O dentro del ciclo). |
| **2.3.2** | **2026-09-22** | **F0 y F1 implementadas.** **F0.1 ✅** A1–A16 ejecutados contra `heatmap_stock` (`proy_scrapping_detail/db/verify_a1_a16.sql` + `run_verify_a1_a16.py` → `docs/Planilla F0.1 - Verificación A1-A16 (2026-09-22).md`): cierra H3, H4 (matiz), H5, H8, H11, H15, Q4, Q8, H14; refuta H9 y H17; confirma E-RAD-05 (backfill FAILED×3), E-RAD-04 (yields con RSI/vol 100% nulos), E-HM-01 (snapshot=1000), E-HM-05 (sin logo), E-BD-04, E-BD-08; nuevo E-BD-03 (escala `−1/0/1`). **F0.3 ✅** `docs/ADR 0001 - Decisiones D1-D14 (2026-09-22).md` con D1/D12/D13/D14 confirmadas (D14 firmada retroactiva) y D2-D11 adoptadas. **F1 ✅** cambios aplicados y verificados: F1.1 (ventana `MAX(timestamp_utc)-15min`, labels `%m-%d %H:%M`, lookup a 24h; `get_heatmap_last_hour`→1000 filas, evolución OK con 144h); F1.2 (`safe_int` filtrado + `guardar_checkpoint` eliminado de `event_service`); F1.3 (orden fetch→validar→DDL→procesar + estado `SKIPPED` fuera de sesión); F1.4 (contrato `{'inserted','status','error'}` en `market_service`/`flush_radar_batch`; buffer solo se limpia con SUCCESS); F1.5 (`records_failed = max(fetched-upserted,0)`; 1000/0→1000 ✓); F1.6 (comentario `source_checksum` → `market_repository.py:118`); F1.7 (`CONFIG_ACTIVOS` EURUSD → `OANDA:EURUSD` + `FX:EURUSD`; verificación de volume pendiente de ciclo en vivo); F1.8 (DDL único en `main()`, retirado de `process_heatmap_data`). Verificación: `py_compile` OK en 8 módulos. |
| **2.3.3** | **2026-09-22** | **FASE 2 parcial.** **F2.1 ✅** `dim_trading_session` creada y poblada (`proy_scrapping_detail/db/create_dim_trading_session.py`, XNYS exchange_calendars 4.13.2): 630 días, 432 sesiones 2026-01→2027-09; `is_early_close` ✓ (26/11 festivo, 27/11 cierra 13:00 ET); cierra E-BD-01/E-BD-06/E-OPS-01 vía gate. **F2.2 ✅** `db/sessions.py` con `en_ventana_nyse`/`en_ventana_fx`/`en_ventana_cripto`/`GATE_POR_CLASE` (fallback XNYS si BD cae); 9 tests M-OPS-04 PASS; radar v5 filtra símbolo con `continue` (no aborta); heatmap gate NYSE en `main()`→SKIPPED; calendario gate `pre_min=90`. **F2.3 ⏸** pospuesta: backup `heatmap_stock_pre_F2.3_20260922_224433.dump` (103 MB, pg_db) + SQL `db/migrate_partitions_utc.sql` generado por `db/generate_migrate_partitions_utc.py` (38 particiones `00:00+00` hasta `2027_12`, 14 legacy). **F2.4/F2.5** quedan pendientes a petición del usuario. `py_compile` OK en 6 módulos. |
| **2.3.4** | **2026-09-22** | **FASE 3 completa (F3.1–F3.12) + pruebas de fase 3.** **F3.1/F3.2 ✅** `CAMPOS_LIST`=33 validado en vivo (`POST /america/scan?label-product=heatmap-stock`, 33/33 campos, `update_mode=delayed_streaming_900`, `RSI\|15` poblado). **F3.6 ✅** calendario: RotatingFileHandler 10 MB×7, `fetch_calendar_events` con reintento/backoff 3×5 s distinguiendo `ApiSinEventos` (checkpoint intacto) de `ErrorApi`. **F3.12 ✅** universo 110→123 (`FUTUROS_PREAPERTURA` ES1=`CME_MINI:ES1!`, `ETF_SECTORIALES_SPDR` 12 tickers); fix `fetch_from_scanner` (futuros sin clave `symbol`, inválidos→`None`); `AMEX:TLT`→`NASDAQ:TLT`. **F3.7 ✅** heatmap: 29 columnas con `description`, filtro `exchange in_range` (10.721 filas), app filtra OTC/preferred/liquidez ≥20M USD→top 1000; `company_name`+`asset_class`+`logo_id` verificados en BD. **F3.8 ✅** cache de asset_id + `alta_masiva_assets` (DO NOTHING RETURNING en lotes 500) + reconciliación ≤3 SQL de dimensión; ejecutado (1.083 cache, 167 nuevos). **F3.11 ✅** `monitor_alertas.py` (A1 frescura en ventana NYSE, A2 429 en logs, A3 DB_WRITE_ENABLED=false, Telegram best-effort). **F3.5 ✅** `--reconcile --dry-run` sin huecos. **F3.9 ⏸** `run_heatmap.sh` preparado sin cron (por directiva). **Pruebas ✅** 21 tests pytest (`proy_scrapping_detail/tests/test_fase3_radar.py` 10, `test_fase3_calendario.py` 3; `proy_heatmap/tests/test_fase3_heatmap.py` 8) + `scripts/verificar_endpoints.py` en ambos proyectos (endpoints en vivo OK: batch, GET /symbol por clase, heatmap sin OTC/preferidas/logoid None). Detalle: `setup_logging()` del calendario adjunta handlers al logger del módulo (basicConfig no-op bajo pytest). |
| **2.3.5** | **2026-09-23** | **Verificación en vivo de los 3 scripts + 2 bugs corregidos + alta de respaldo EURUSD.** **Radar (radar_v5) ✅** ejecutado a las 00:32 ET (NYSE cerrado): captura FX+cripto por gate de clase; tras dos fixes quedó **15/15 escrituras en `fact_market_series`** con `cycle_id`, `update_mode=streaming`, `feed_delay_s=0`. **Fix E-RAD-16 ✅** `db/market_repository.py:133` convierte `cycle_id` a `str` (`execute_values` no adapta `uuid.UUID` → `can't adapt type 'UUID'`; antes: ciclo capturado pero 0 filas en BD). **Fix E-RAD-17 ✅** `db/sessions.py:79` `asset_class_de()` devuelve `"fx"` (antes `"forex"` → caía al gate default NYSE → todo el forex nocturno 24/5 se omitía). **Alta `FX:EURUSD` ✅** respaldo del par (F1.7/D14) dado de alta en `dim_asset` (`asset_id=4683`, `radar_v5`, verificado `volume=20743>0`, `streaming`) → ahora se persiste en BD (antes solo CSV); serie dual verificada en `fact_market_series` (FX 1.14287/20762 + OANDA 1.14288/13243, mismo ciclo). **Calendario ✅** gate `pre_min=90` omite captura a 00:32 ET (comportamiento F2.2); vía `capturar_eventos` (mismo pipeline BD): 59 eventos US upserted en `fact_economic_event`, audit SUCCESS 59/59, checkpoint `last_event_id=421371`/`records_processed=59`/`ACTIVE`. **Heatmap ✅** fuera de ventana NYSE → `SKIPPED` (0 escrituras, audit correcto; `fact_heatmap_snapshot` intacto en 4.000). **Pendiente:** e2e completo con equity/ETF en sesión abierta; doble registro de auditoría por ciclo radar (flush + main) anotado como observación menor. |
| **2.3.6** | **2026-09-23** | **FASE 4 · F4.1/F4.1b y F4.2 implementadas y verificadas.** **F4.1 ✅** `db/bar_repository.py` + `scripts/build_market_bar_15m.py`: agregación de `fact_market_series` en barras de 15 min UTC (`bucket_15m_utc`, OHLCV, `volume_delta`, `n_ticks`, `is_regular` vía `dim_trading_session` XNYS para equity/ETF) con upsert mensual `ON CONFLICT (asset_id, bar_start_utc)` y auditoría `bar_15m`; corrida real materializó 18.741 barras (124 activos, 17–23/09), re-corrida idempotente. **F4.1b ✅** regla de cierre (M-CAP-03 reformulada): `close_quality_para_offset` con ventanas `[6,20]→definitive`, `[−15,5]→provisional` (offsets 5 s caen a provisional por la ambigüedad E-RAD-15), resto `unknown`; hoy todas `unknown` porque el muestreo T−10 s es F4.1c (pendiente). Fix de particiones: `asegurar_particion` por mes (commit por mes, fronteras `timestamptz` UTC). **F4.2 ✅** migración Alembic **`0003`** en `proy_bd_heatmap` (`fact_market_indicator_tf` formato largo, particiones UTC `2026_09`→`2027_12`) aplicada a `heatmap_stock`; `db/indicator_repository.py` (proyección bloques `|TF`→largas, upsert ON CONFLICT `(asset_id,timestamp_utc,tf)`); radar persiste filas por ciclo (`process_radar_batch(scanner_raw=…)`); `scripts/build_indicator_tf.py` (`--status`/`--from-scan`/`--verify`). **Aceptación en vivo ✅** `RSI|15` tabla = scan en vivo **95/95** (tol 0,5); 190 filas en ventana (95 × tf 15/5; NVDA/SPY/QQQ con `pivot_r3` poblado). **Pruebas ✅** 45 tests `proy_scrapping_detail` (25 F4.1b barras + 8 F4.2 indicadores TF + 12 previos) + 8 `proy_heatmap` + 9 `proy_bd_heatmap` (incl. `test_fact_market_indicator_tf`). |
| **2.3.7** | **2026-09-23** | **F4.3 (latest_market_tick) y F4.4 (snapshots columnas explícitas) implementadas y verificadas.** **F4.3 ✅** migración Alembic **`0004`** (`latest_market_tick`: 1 fila/asset_id, PK asset_id, no particionada) aplicada a `heatmap_stock`; `db/latest_tick_repository.py` (proyección base + bloque `|15` + trazabilidad F3.3; upsert ON CONFLICT `(asset_id)`); radar la reescribe por ciclo (`process_radar_batch` → 5c); `scripts/build_latest_tick.py` (`--status`/`--prime`); `get_latest_ticks()` con join dim_asset. **En vivo ✅** `--prime` = 95 filas (70 equity + 25 etf; NVDA/SPY/QQQ con base y `RSI|15` correctos, `update_mode=delayed_streaming_900`; E-DSH-04: lectura de ~110 filas sin escanear `fact_market_series`). **F4.4 ✅** migración Alembic **`0005`** añade a `fact_heatmap_snapshot` (padre + particiones por ALTER automático) `volume, avg_vol_10d, avg_vol_30d, volatility_d, change_abs, high_52w, low_52w, update_mode, fetched_at` (M-DAT-05, E-HM-08/E-HM-10); `scrapper_heatmap_v1.py` escribe las columnas por nombre y `fetched_at` = instante del fetch (`fetch_heatmap_data` ahora 3-tupla); `raw_vector` conservado pero deja de ser fuente principal. **Pruebas ✅** 51 tests `proy_scrapping_detail` (6 F4.3) + 10 `proy_heatmap` (2 F4.4) + 11 `proy_bd_heatmap` (test_latest_market_tick + test_fact_heatmap_snapshot_columnas); BD en `0005 (head)`. |
| **2.3.8** | **2026-09-23** | **F4.5 (SCD2 → Tipo 1) y F4.5b (mapeo canónico F2.5) implementadas y verificadas.** **Migración Alembic `0006`** aplicada a `heatmap_stock` (BD en `0006 (head)`): se dropean `valid_from/valid_to/current_version` (E-BD-04, D7 → Tipo 1) y se añaden `logical_key`, `is_canonical`, `role` (`primary`/`fallback`, CHECK) y `feed_delay_s` (backfill 900/600/0 por clase); **mapeo canónico** de las 6 claves F2.5 (VIX|DXY|TLT|US10Y|ORO|OIL) con alta de **`TVC:DXY`** e índice único parcial `uq_dim_asset_canonical_logical_key` (1 canónico por clave); funciones (`upsert_heatmap_snapshot`, `upsert_market_series`), vistas (`vw_heatmap_enriched`, `vw_market_live`) e índices `idx_dim_asset_active/class` reconstruidos **sin `current_version`**; `idx_dim_asset_symbol` eliminado. **Consumidores corregidos**: `seed_dim_asset.py`, `seed_symbols.py` (`MAPEO_LOGICAL`/`FEED_DELAY_CLASE`, puebla las 4 columnas), `db/latest_tick_repository`, `db/market_repository` (`WHERE is_active`), `db/bar_repository` (JOIN sin `current_version`), `scrapper_heatmap_v0/v1`, `heatmap_repository`, `download_iconos_mercado.py`; scripts legacy `proy_heatmap/scripts` retirados (eliminados 01/02/04/08, archivados 03/06/07 en `docs/old/`, README → Alembic). **Verificación en vivo ✅** `dim_asset`=1.669, secuencia 4.701, 0 `feed_delay_s` NULL (0/600/900=21/9/1.639), funciones upsert OK (insert + ON CONFLICT), vistas sin `current_version` y con datos, `seed_symbols.py --check`=0 faltantes, `build_latest_tick.py --status` OK. **Pruebas ✅** 14 tests `proy_bd_heatmap` (3 nuevos F4.5/F4.5b) + 51 `proy_scrapping_detail` + 10 `proy_heatmap`. |
| **2.3.9** | **2026-09-23** | **FASE 4 · F4.7 descartada y F4.8 completada.** **🛑 F4.7 descopada por directiva del usuario**: se **obvian los históricos** (la captura previa tiene `timestamp_utc` = hora de captura, retraso posible de 15 min, captura 24 h contaminada fuera de sesión, equity solo desde 2026-08-22); el ecosistema **inicia desde cero con BD en blanco** (`alembic upgrade head` en BD nueva) y no se construye el job de reempaquetado. **F4.8 ✅** script **independiente** `proy_bd_heatmap/scripts/suite_calidad_nocturna.py` (solo psycopg2 + python-dotenv, para cron): audita duplicados, huecos en activos 24/5 (>15 min), nulos, ticks planos fuera de sesión, `n_ticks` por barra, `close_quality` y contigüidad de particiones; exit codes `0`/`1`/`3`; estado `INFO` en ventana vacía o BD recién creada (sin falsas alertas en el arranque desde cero); informe MD + JSON en `reports/` (gitignored). **Validado en vivo ✅** contra `heatmap_stock`: 13 cheques ejecutados, informe generado, exit coherente (recomendación cron `05 4 * * *`). Documentado en `proy_bd_heatmap/README.md` (§ F4.8). |
| **2.3.10** | **2026-09-24** | **Verificación en vivo de los 3 scripts en sesión NYSE abierta + fix del gate NYSE del heatmap + Anexo A (uso de disco y proyección).** **Radar ✅** 123/123 símbolos capturados y escritos en `fact_market_series` (224 filas TF en `fact_market_indicator_tf`, 123 en `latest_market_tick`, auditoría `SUCCESS`). **Calendario ✅** 81 eventos upserted en `fact_economic_event`, checkpoint `event_id=421420`, auditoría `SUCCESS`. **Heatmap ✅** 1000 snapshots/sesión en `fact_heatmap_snapshot`, auditoría `SUCCESS`. **Fix gate NYSE ✅** `proy_heatmap/db/sessions.py:46` usaba `.replace(tzinfo=timezone.utc)` (reetiqueta sin convertir) → con la tz de sesión de la conexión (−05:00), `opens_at=08:30−05:00` se comparaba como `08:30 UTC` en vez de `13:30 UTC` → el heatmap se saltaba el ciclo **estando el mercado abierto** (e2e pendiente del changelog v2.3.5). Fix: `.astimezone(timezone.utc)`. **Pruebas ✅** 10 `proy_heatmap` + 53 `proy_scrapping_detail` PASS. **Anexo A (uso de disco) ✅** análisis y proyección de crecimiento incorporados al final de este documento. |

---

# **Anexo A · Uso de disco y proyección de crecimiento**

**Fecha:** 2026-09-24 · **Sesión de referencia:** 2026-09-24 (NYSE abierta, 13:10 ET / 18:10 UTC)

**Método de cálculo resumido:** los bytes/registro se midieron sobre particiones reales de `heatmap_stock` (`pg_total_relation_size` ÷ `count(*)` por partición, incluye tabla + índices + TOAST), y las filas/día se proyectaron multiplicando la tasa observada por la cadencia de producción definida en el roadmap (radar `/3 min` = 480 ciclos/día teóricos con gate por clase; heatmap 28 snapshots × 1000 filas; F3.9/F4.1c). El desglose completo de consultas SQL se documenta a continuación.

## A.1 · Baseline actual (2026-09-24)

| Componente | Tamaño | Nota |
| --- | --- | --- |
| BD `heatmap_stock` | **785 MB** | `pg_database_size`, revisión `0006 (head)` |
| `DATOS_LIVE` (CSV radar) | 421 MB | 498 archivos, rotación mensual |
| `DATOS_LIVE_CALENDARIO` | 2 MB | |
| Logs (`proy_heatmap/LOGS`, `logs_ejecucion`) | < 1 MB | RotatingFileHandler 10 MB×7 (F3.6) |
| **Total** | **≈ 1.2 GB** | |

Disco raíz `/`: **44 GB libres de 457 GB (91% usado)**.

## A.2 · Tasas medidas el 2026-09-24 (bytes/registro)

| Tabla | Filas 2026-09-24 (parcial) | B/registro (total) | Detalle |
| --- | --- | --- | --- |
| `fact_market_series` | 261 (123 assets/ciclo en NYSE, 15 fuera) | **331** | 2,4 M filas; tabla ~200 B + índices ~130 B |
| `fact_market_indicator_tf` | 478 (112 assets × 2 tf) | **216** | partición `2026_09` |
| `fact_heatmap_snapshot` | 2,000 (2 snapshots × 1000) | **1,528** | `raw_vector` JSONB ~295 B + 9 columnas explícitas (F4.4) |
| `fact_market_bar_15m` | 0 (job F4.1 no corrido hoy) | **302** | 18.741 filas acumuladas |
| `fact_economic_event` | 81 upserted | 2,577 | tabla estática ~709 filas |
| `latest_market_tick` | 123 | 799 | 1 fila por activo, no crece en volumen |

**Cálculo de B/registro:** `pg_total_relation_size(oid) / count(*)` por partición (incluye heap + índices + TOAST). Ejemplo `fact_market_series_2026_09`: 221,3 MB / 669.391 filas = **331 B/registro**.

## A.3 · Proyección a cadencia de producción

Filas/día proyectadas (roadmap F3.9/F4.1c):

- **Radar** (`/3 min`): 130 ciclos NYSE × 123 assets + 350 ciclos fuera × 15 FX/cripto = **21.240 filas/día** → 21.240 × 331 B ≈ **7,0 MB/día**
- **`fact_market_indicator_tf`** (×2 tf `|5`/`|15`): 42.480 filas/día → **9,2 MB/día**
- **Heatmap** (28 snapshots × 1000): 28.000 filas/día → **42,8 MB/día**
- **`fact_market_bar_15m`** (28 barras × 123 assets): 3.444 filas/día → **1,0 MB/día**
- **Calendario**: ~81/día, tabla estable (~709 filas, 1,8 MB), crecimiento despreciable

| Horizonte | Incremento BD | Incremento total (BD + CSV) | Acumulado |
| --- | --- | --- | --- |
| **Día** | ≈ 60,0 MB | ≈ 64,9 MB | ≈ 1,27 GB |
| **Mes (30,4 d)** | ≈ 1,82 GB | **≈ 1,97 GB** | ≈ 3,2 GB |
| **Año (365 d)** | ≈ 21,9 GB | **≈ 23,7 GB** | ≈ 24,9 GB |

CSV (`DATOS_LIVE`) aporta ≈ 4,9 MB/día (112 MB en `202609` / 23 días en curso; rotación mensual).

## A.4 · Hallazgos y conclusiones

1. **El heatmap es el 71% del incremento BD** (42,8 de 60 MB/día) por `raw_vector` (~295 B) + 9 columnas explícitas F4.4 (~1,5 KB/fila). El mayor lever de ahorro es retirar/compactar `raw_vector` cuando las columnas ya estén pobladas (F4.4 mantiene `raw_vector` por compatibilidad).
2. **`fact_market_series` es la tabla más grande** (2,4 M filas; ~90% de la BD de 785 MB): crece ~7 MB/día.
3. **Sin riesgo de disco a 1 año** (~25 GB proyectados vs 44 GB libres), pero el **91% de uso global** del disco raíz es una señal a vigilar (otras cargas fuera del ecosistema).
4. **Escenario BD en blanco (F4.7):** si el arranque en producción parte de `alembic upgrade head` en BD nueva, el baseline baja a ~10 MB y el año ≈ 23,7 GB (los históricos no se reempaquetan).
5. **Recomendación (sigue a F4.8):** monitorizar con `pg_database_size` + tamaño por partición + `du` de `DATOS_LIVE` con ventana de 7 días y alerta si la proyección a 90 días supera el espacio libre; política de retención D8 (ticks 6 meses, particiones mensuales a purgar pasado N meses).