# **Roadmap Integral de Ejecución v2.2 — Ecosistema `heatmap_stock`**

**Versión:** 2.1 (consolidado tras tests D/E/F/G/H/C del 2026-09-22 · incorpora observaciones de auditoría 2026-09-22)

**Objetivo:** herramienta de apoyo a decisiones de trading en 15 min, operativa 09:00–16:00 ET.

**Estado:** 13 hipótesis cerradas · 10 dudas cerradas · 4 errores S1 activos · 2 errores nuevos · 1 decisión confirmada · 1 decisión nueva pendiente.

---

## **Estado de la evidencia**

Este roadmap consolida evidencia de cuatro fuentes con fechas distintas:

1. **Informe v3 (2026-09-20)** — análisis documental original.
2. **Anexo G (2026-09-21)** — primera revisión externa; Q18–Q21 clasificadas como dudas.
3. **Archivos compartidos (2026-09-22)** — `market_service.py`, `event_service.py`, `heatmap_service.py`, `heatmap_repository.py`. Promueven:
    - **Q18 → E-HM-13** (confirmado con código)
    - **Q19 → E-HM-14** (confirmado con código)
    - **Q20 → E-CAL-06** (confirmado con código)
    - **Q21 → E-CAL-07** (confirmado con código)
    - **E-RAD-12** (confirmado como nota de trazabilidad)
4. **Tests D/E/F/G/H/C (2026-09-22)** — cierran H1, H6, H7b, H19, H20, H21, H22, H24 y Q15, Q16, Q17, Q22, Q23, Q24. Añaden **E-RAD-14** y **E-RAD-15**.

Todo error confirmado en este roadmap cita su fuente en el campo **Origen**.

---

## **Sección 0 · Estado de partida**

### **0.1 Lo que ya sabemos con evidencia**

| **Área** | **Confirmado** | **Implicación** |
| --- | --- | --- |
| **Delay del feed** | equity/ETF: 15 min · futuros CME: 10 min · VIX spot, FX, cripto: 0 min | El banner `as_of` debe ser por activo |
| **Multi-TF** | sufijos `|5`, `|15`, `|30`, `|60` funcionan en `/symbol` | Vía confirmada para 15 min |
| **POST batch** | `/scan` **no existe** (404) | Replanificar F3.1: probar `/america/scan` o paralelizar GET |
| **Pre-market** | `premarket_close`, `premarket_change`, `premarket_volume`, `gap` existen y responden | Panel de pre-apertura viable |
| **Pivotes** | base=mes, `|5=|15`=día, `|30=|60`=semana | `Pivot.D.*`/`Pivot.W.*` no existen |
| **FX** | `FX_IDC:EURUSD` (primario actual) devuelve `volume=0` | Cambiar primario a `OANDA:EURUSD` |
| **Ventana ciega** | ±15 s alrededor de cada frontera de barra | Reformular regla de cierre (M-CAP-03) |
| **Refresco** | 15–40 s variable según momento del día | Cadencia de 3 min sigue bien dimensionada |

### **0.2 Hipótesis y dudas cerradas por los tests**

**Cerradas ✅ (evidencia directa):** H1, H6, H7b, H19, H20, H21, H22, H24, Q15, Q16, Q17, Q22, Q23, Q24, Q18, Q19, Q20, Q21.

**Pendientes (requieren semanas de datos):** H13 (score sin poder predictivo), H14 (reacción de eventos), H17 (cadencia vs barras).

### **0.3 Errores nuevos detectados**

| **ID** | **Sev** | **Descripción** | **Origen** | **Fase** |
| --- | --- | --- | --- | --- |
| **E-RAD-14** | S1 | `FX_IDC:EURUSD` devuelve `volume = 0` | Test F (2026-09-22) | F1.7 |
| **E-RAD-15** | S2 | Ventana ciega de ±15 s en cada frontera de barra | Test C (2026-09-22) | F4.1b |

### **0.4 Decisión nueva pendiente**

| **ID** | **Decisión** | **Recomendación** |
| --- | --- | --- |
| **D14** | Primario de EURUSD | `OANDA:EURUSD` (volume=14.911) sobre `FX_IDC:EURUSD` (0) y `FX:EURUSD` (22.504) |

### **0.5 Trazabilidad de la cobertura**

**El roadmap cubre 55 de 55 mejoras del informe v3 + E-RAD-14/15.** Estado por fase: F1 (8 quick-wins), F2 (5 subsecciones), F3 (12 subsecciones), F4 (9 subsecciones), F5 (6 subsecciones), F6 (9 subsecciones), F7 (10 subsecciones).

---

## **Sección 1 · Criterios de éxito globales**

| **KPI** | **Objetivo** | **Verificado en** |
| --- | --- | --- |
| Gate de sesión por clase de activo | 100% tests pasados | F2 |
| p95 duración del ciclo del radar | ≤ 15 s | F3 |
| `update_mode` poblado por tick | 100% | F3 |
| `premarket_*` poblados durante 09:00–09:30 ET | 100% de símbolos | F3 |
| Frescura de ingesta en ventana | p95 ≤ 60 s | F3 |
| Barras `definitive` (fuera de ventana ciega) | ≥ 95% | F4 |
| Barras con `n_ticks ≥ 3` | ≥ 95% | F4 |
| Snapshots heatmap por sesión | 28 | F3 |
| Latencia del `actual` de eventos | p95 ≤ 90 s | F3 |
| Streamlit sin ventana vacía | 100% de las consultas | F1 |
| Paneles MVP con datos reales en sesión | 4/4 | F5 |
| Informe walk-forward del score | con IC | F6 |
| Secretos en documentos | 0 | F2 |
| `dashboard_ro` no puede escribir | verificable | F2 |

---

## **FASE 0 · Verificación empírica**

**Estado:** F0.2 (protocolo T1–T11) **completado al 90%** el 2026-09-22.

**Pendiente:** T3.1 (semántica de `gap`), T12, T13, A1–A16 (SQL).

### **F0.1 · Ejecutar A1–A16 (SQL)**

| **Tarea** | **Duración** | **Criterio** |
| --- | --- | --- |
| A1–A16 contra `heatmap_stock` | 3 h | Planilla con resultados; H3, H4, H5, H8, H11, H15 cerradas |

### **F0.2 · Protocolo empírico**

| **Test** | **Estado** | **Cierra** |
| --- | --- | --- |
| T1 (update_mode) | ✅ Corrido | H1 |
| T2 (delay vs referencia) | ⏸ No corrido (requiere fuente externa) | H1 residual |
| T3 (pre-market) | ✅ Corrido | H6, H20 |
| T3.1 (semántica de `gap`) | ⏸ Mañana 09:29 ET | Q25 |
| T4 (repintado) | ✅ Corrido | H19, H21 |
| T5 (/scan) | ✅ Corrido (404) | Q16 |
| T6 (pivotes) | ✅ Corrido (parcial) | H22 |
| T7 (refresco acciones) | ✅ Corrido | H24 |
| T8 (fallos por exchange) | ⏸ Requiere logs de producción | Q6 |
| T9 (duración ciclo) | ⏸ Requiere logs de producción | H8 |
| T10 (FX equivalence) | ✅ Corrido | Q23, Q24 |
| T11 (gate por clase) | ✅ Corrido | Q22 |
| **T12 (nuevo)** · probar `/america/scan` | ⏸ 5 min | Desbloquea F3.1 |
| **T13 (nuevo)** · validar semántica `gap` | ⏸ Mañana | Cierra Q25 |

### **F0.3 · ADR (Architecture Decision Record)**

**Duración:** 2 h

**Entregable:** ADR 0001 con D1–D14 firmadas.

| **ID** | **Decisión** | **Estado** | **Recomendación** |
| --- | --- | --- | --- |
| D1 | Fuente de entrada | ✅ Confirmada (b) | TradingView contexto + fuente externa para entrada |
| D2 | VIX canónico | 🟡 | `TVC:VIX` spot para nivel, `CBOE:VX1!` para pre-apertura |
| D3 | DXY canónico | 🟡 | Validar `TVC:DXY`, si no `ICEUS:DX1!` |
| D4 | Indicadores 15 min | 🟡 | Híbrido: TV primario, cálculo propio en paralelo 5–10 sesiones |
| D5 | Cadencia heatmap | 🟡 | 15 min alineado a :00/:15/:30/:45 + 20s |
| D6 | Universo heatmap | 🟡 | NASDAQ/NYSE/AMEX, comunes, USD vol ≥ 20 M, N=600-800 |
| D7 | dim_asset SCD | 🟡 | Tipo 1 (quitar versionado) |
| D8 | Retención | 🟡 | Ticks 6 meses, barras indefinidas, `raw_payload` off |
| D9 | Streamlit existente | 🟡 | Absorber en dashboard v2 |
| D10 | Presentación del score | 🟡 | Solo contexto hasta rechazar H13 |
| D11 | Librería calendario | 🟡 | `exchange_calendars` (XNYS) |
| D12 | Ancho multi-TF | ✅ Confirmado | Tabla larga `fact_market_indicator_tf` |
| D13 | Gate por clase | ✅ Confirmado | Equity/ETF NYSE, FX 24/5, cripto 24/7 |
| **D14** | **Primario EURUSD** | ⏸ Nueva | **`OANDA:EURUSD`** |

---

## **FASE 1 · Bugs latentes + E-RAD-14 (quick wins)**

**Duración:** 1–2 días

**Objetivo:** cerrar bugs que romperán con el cron denso + corregir EURUSD.

**Criterio de salida:** Streamlit sin vacío, logs coherentes, EURUSD con volumen.

### **F1.1 · Arreglar `heatmap_service` / `heatmap_repository`**

**Cierra:** E-HM-13 (ventana muerta 1h), E-HM-14 (colisión `HH:MM`).

**Origen:** E-HM-13 y E-HM-14 confirmados con código el 2026-09-22 (`heatmap_service.py`, `heatmap_repository.py`); previamente clasificados como Q18 y Q19 en el Anexo G del informe v3.

**Duración:** 2 h

**Cambios:**

1. `get_heatmap_last_hour`: `WHERE timestamp_utc >= (SELECT MAX(timestamp_utc) - INTERVAL '15 minutes' FROM fact_heatmap_snapshot)`
2. `get_heatmap_stats`: mismo cambio
3. `get_price_evolution`: subir `lookback_hours: int = 24`
4. `fetch_price_evolution`: `label = snap['timestamp_utc'].strftime('%m-%d %H:%M')`

**Hecho cuando:**

- Con el último snapshot de hace 8 h, `fetch_heatmap_data()` retorna > 0 filas.
- Test unitario con dos snapshots sintéticos de días distintos no colisiona.

### **F1.2 · Arreglar `event_service`**

**Cierra:** E-CAL-06 (`max(safe_int)` TypeError), E-CAL-07 (doble `guardar_checkpoint`).

**Origen:** E-CAL-06 y E-CAL-07 confirmados con código el 2026-09-22 (`event_service.py`); previamente clasificados como Q20 y Q21 en el Anexo G. **El fix aplica sobre `event_service.py`, no sobre `calendario_tradingview_live_v5.py`** — el script solo contiene la definición de `guardar_checkpoint`, no la doble llamada.

**Duración:** 1 h

**Cambios:**

python

```
# Fix E-CAL-06
ids = [safe_int(e.get('id', 0)) for e in eventos_raw]
ids = [i for i in ids if i is not None]
max_event_id = max(ids) if ids else 0

# Fix E-CAL-07: eliminar del event_service
# from calendario_tradingview_live_v5 import guardar_checkpoint
# guardar_checkpoint(max_event_id, inserted, len(eventos_raw))
```

**Hecho cuando:**

- Evento con `id=""` no rompe el ciclo.
- `guardar_checkpoint` se llama una sola vez por ejecución.

### **F1.3 · Invertir orden en `scrapper_heatmap_v1.main()`**

**Cierra:** E-HM-16 (DDL antes de validar API).

**Origen:** Confirmado con código el 2026-09-22.

**Duración:** 30 min

**Cambio:** fetch → validar → DDL → procesar.

**Hecho cuando:** fuera de sesión se registra `SKIPPED`, no `FAILED`.

### **F1.4 · Contrato con estado en `market_service`**

**Cierra:** E-RAD-05 (triple silencio).

**Origen:** Confirmado con código el 2026-09-22 (`market_service.py` + `scraper_live_tradingview_v5.py`).

**Duración:** 3 h

**Cambios:**

- `process_radar_batch` retorna `{'inserted': int, 'status': str, 'error': str|None}`.
- `flush_radar_batch` propaga ese dict.
- `main()` solo limpia `batch_buffer` si `status == SUCCESS`.

**Hecho cuando:** con BD apagada 5 min, el log muestra `FAILED` y el buffer conserva filas.

### **F1.5 · Corregir `records_failed` en `log_sync_run`**

**Cierra:** E-HM-07.

**Origen:** Confirmado con código el 2026-09-22 (`scrapper_heatmap_v1.py`).

**Duración:** 15 min

**Cambio:** `records_failed = max((records_fetched or 0) - (records_upserted or 0), 0)`

**Hecho cuando:** `fetched=1000, upserted=0` registra `records_failed=1000`.

### **F1.6 · Documentar `source_checksum`**

**Cierra:** E-RAD-12.

**Duración:** 30 min

**Cambio:** comentario en `prepare_bd_row` con la ubicación exacta del cálculo.

**Hecho cuando:** un lector sabe dónde buscar.

### **F1.7 · Corregir primario de EURUSD**

**Cierra:** E-RAD-14.

**Origen:** Test F (2026-09-22).

**Duración:** 15 min + 1 ciclo de verificación

**⚠ Excepción al orden decisión → ADR → implementación:** F1.7 implementa D14 antes de la firma formal en F0.3. Justificación: la evidencia de Test F es concluyente (`FX_IDC:EURUSD` devuelve `volume=0`), el cambio es de una línea en `CONFIG_ACTIVOS`, y no bloquea ningún otro trabajo. **La decisión se firmará retroactivamente en el ADR 0001 el 2026-09-27.**

**Cambios:**

1. En `CONFIG_ACTIVOS`, cambiar:

python

```
"EURUSD": {
    "primario": "OANDA:EURUSD",   # antes FX_IDC:EURUSD
    "respaldo": "FX:EURUSD"        # antes OANDA:EURUSD
}
```

1. Opcional: en BD, marcar `FX_IDC:EURUSD` como `is_active = false`.
2. Validar en el siguiente ciclo que `fact_market_series.volume > 0` para EURUSD.

**Hecho cuando:** `SELECT volume FROM fact_market_series WHERE asset_id = <EURUSD> ORDER BY timestamp_utc DESC LIMIT 1` retorna > 0.

### **F1.8 · Refactorizar `main()` del heatmap: `create_partition` una sola vez**

**Cierra:** E-HM-11 (DDL duplicado).

**Duración:** 1 h

**Cambio:** decidir dónde vive el DDL (¿en `main()` o en `process_heatmap_data`?) y dejar una sola ruta.

---

## **FASE 2 · Tiempo y ventana**

**Duración:** 4–6 días

**Objetivo:** base temporal correcta antes del fin del DST (1-nov-2026).

**Criterio de salida:** gate probado con feriado, cierre anticipado y DST.

### **F2.1 · `dim_trading_session`**

**Cierra:** E-BD-01, E-BD-06, E-OPS-01.

**Duración:** 1 día

**Cambio:** crear tabla + poblar con `exchange_calendars` (XNYS) 2026–2027.

**Hecho cuando:** 2026-11-26 (Acción de Gracias) no es sesión; 2026-11-27 tiene `is_early_close=true`.

### **F2.2 · Gate por clase de activo**

**Cierra:** E-OPS-01, Q22.

**Duración:** 1 día

**Cambios:**

- Nuevo módulo `db/sessions.py` con `en_ventana(asset_class, ...)`.
- `GATE_POR_CLASE = {'equity': en_ventana_nyse, 'etf': en_ventana_nyse, 'fx': en_ventana_fx, 'crypto': en_ventana_cripto, 'future': en_ventana_nyse}`.
- Radar: filtrar símbolos, no abortar el ciclo.
- Heatmap: gate único NYSE.
- Calendario: gate NYSE con `pre_min=90`.

**Hecho cuando:** los 9 tests de B.1 pasan + FX captura fuera de NYSE + equity/ETF no.

### **F2.3 · Particiones UTC explícitas**

**Cierra:** E-BD-02, H11.

**Duración:** 4 h

**Cambios:**

- Verificar A5; si hay límites `05`, migrar.
- Crear hasta `2027_12`.
- Alerta si falta el mes+1.

**Hecho cuando:** A5 muestra límites contiguos a `00:00+00`.

### **F2.4 · Roles y credenciales**

**Cierra:** E-OPS-02.

**Duración:** 4 h

**Cambios:**

- `scraper_rw` (INSERT/UPDATE en `fact_*`, `audit_sync_run`, `sync_checkpoint`).
- `dashboard_ro` (SELECT).
- Rotar password `postgres`.
- Retirar credenciales del informe BD.

**Hecho cuando:** `psql -U dashboard_ro` no puede INSERT.

### **F2.5 · Mapeo canónico lógico → físico (NUEVO)**

**Cierra:** E-RAD-06, I7.

**Duración:** 1 día

**Depende de:** D2, D3 resueltas.

**Cambios:**

1. Añadir a `dim_asset`:

sql

```
ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS logical_key varchar(20),      -- VIX, DXY, TLT, US10Y, ORO, OIL
    ADD COLUMN IF NOT EXISTS is_canonical boolean DEFAULT false,
    ADD COLUMN IF NOT EXISTS role varchar(10)              -- 'primary' | 'fallback'
        CHECK (role IN ('primary','fallback')),
    ADD COLUMN IF NOT EXISTS feed_delay_s int;             -- 0/600/900
```

1. Poblar con el mapeo de `METADATOS_ACTIVOS` → símbolo físico canónico:
    - `VIX`: primario `TVC:VIX`, respaldo `CBOE:VX1!` (o al revés según D2).
    - `DXY`: primario `TVC:DXY`, respaldo `ICEUS:DX1!` (según D3).
    - `ORO`, `OIL`, `TLT`, `US10Y`: mapear según `METADATOS_ACTIVOS`.
2. Backfill del `feed_delay_s` para los activos existentes según `update_mode` observado:
    - Equity/ETF → 900
    - Futuros CME → 600
    - VIX/FX/cripto → 0
3. Corregir el docstring del radar que afirma "fallback automático entre primarios y respaldos" — no existe tal lógica.

**Hecho cuando:** `SELECT logical_key, symbol FROM dim_asset WHERE is_canonical AND logical_key IS NOT NULL` retorna una fila por clave lógica (VIX, DXY, TLT, US10Y, ORO, OIL) y cada una apunta al símbolo esperado.

---

## **FASE 3 · Captura fiable**

**Duración:** 8–11 días

**Objetivo:** ciclo corto, simultáneo, trazable, con pre-market.

**Criterio de salida:** p95 ciclo ≤ 15 s; `update_mode` 100%; `premarket_*` 100%.

### **F3.1 · Estrategia de captura batch (REESCRITA)**

**Cierra:** E-RAD-03.

**Duración:** 1 día (prueba) + 1 día (implementación)

**Estado:** `/scan` POST batch **no existe** (Test G → 404).

**Plan A** — probar `/america/scan` (T12):

json

```
{"symbols": {"tickers": ["NASDAQ:NVDA", "AMEX:SPY", ...]},
 "columns": [CAMPOS]}
```

- Si funciona: 1 round-trip, ciclo ~2 s.
- Si falla: Plan B.

**Plan B** — paralelizar GET con `ThreadPoolExecutor`:

python

```
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(fetch_from_scanner, s): s for s in lista_ordenada}
    for fut in as_completed(futures):
        sym = futures[fut]
        result = fut.result()
        # ... procesar
```

- 110 GET con 10 workers → ~15–20 s.
- Añadir jitter por worker para no disparar 429.

**Hecho cuando:** p95 ciclo ≤ 15 s; un timestamp de inicio por ciclo.

### **F3.2 · `CAMPOS` extendido (REESCRITO)**

**Cierra:** E-RAD-01, M-CAP-09, M-CAP-03.

**Origen:** Test H confirmó `Pivot.M.Camarilla.R3|15` como pivote diario (agrupación por pares en 3 símbolos).

**Duración:** 2 h

**Cambio:**

python

```
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
    "Pivot.M.Camarilla.R3|15",   # NUEVO: pivote diario confirmado en Test H
    "update_mode",
])
```

**Notas:**

- `close|TF` se omite: Test E confirmó que `close|5` y `close|15` son idénticos entre sí y distintos de `close` base; `premarket_close` cubre el caso de pre-apertura.
- `Pivot.M.Camarilla.R3|15` se incluye como pivote diario de TV. Si F6.3 (validación cruzada TV vs propio) decide usar cálculo propio, se puede retirar del `CAMPOS` sin romper nada.
- `Perf.W|TF` y `|1D` no existen (Test B).

**Hecho cuando:** una llamada a `/symbol` con `CAMPOS` devuelve todos los campos (sin `None` en los que deben tener valor).

### **F3.3 · Trazabilidad temporal**

**Cierra:** E-RAD-02, E-HM-10.

**Duración:** 1 día

**Cambios en `fact_market_series`:**

sql

```
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

`feed_delay_s` se deriva de `update_mode`:

- `streaming` → 0
- `delayed_streaming_600` → 600
- `delayed_streaming_900` → 900

**Hecho cuando:** 100% de filas nuevas tienen `update_mode` poblado.

### **F3.4 · Prioridad y circuit breaker por exchange**

**Cierra:** E-RAD-04.

**Duración:** 4 h

**Cambios:**

- Ordenar símbolos con prioridad (SPY, QQQ, VIX, US10Y, DXY, NQ1! primero).
- Breaker separado por exchange.

**Hecho cuando:** un fallo simulado de `CBOE` no afecta a `NASDAQ`.

### **F3.5 · Reintento + modo estricto + reconciliación**

**Cierra:** E-RAD-05 residual, E-CAL-05.

**Duración:** 2 días

**Cambios:**

- `DB_WRITE_ENABLED` obligatorio en prod.
- `load_dotenv(override=False)`.
- Job nocturno de reconciliación CSV → BD.

**Hecho cuando:** con BD caída 10 min, tras reiniciar no queda hueco.

### **F3.6 · Calendario: polling por evento + reintento (AMPLIADO)**

**Cierra:** E-CAL-01, E-CAL-03, E-CAL-04, M-CAP-15.

**Duración:** 1 día

**Cambios:**

1. **Polling por evento:** cron cada minuto entre `T−1` y `T+10 min` de eventos de alto impacto (importancia ≥ 1), ventana 08:00–16:00 ET.
2. **Reintento con backoff exponencial** en `fetch_calendar_events`: distinguir "sin eventos" (estado `PARTIAL_FAIL`, checkpoint intacto) de "error de API" (reintentar).
3. **`RotatingFileHandler`** en `setup_logging()`: `maxBytes=10MB, backupCount=7` (evita cientos de archivos de log por día con polling por minuto).
4. **`except` explícito** en el cálculo del checkpoint (reemplazar el `except:` desnudo actual).

**Hecho cuando:**

- p95 de latencia del `actual` ≤ 90 s.
- Un fallo de API queda auditado y reintentado.
- Un ciclo sin eventos queda como `PARTIAL_FAIL` sin sobrescribir el checkpoint.
- El directorio de logs no acumula más de 7 archivos.

### **F3.7 · Heatmap: filtros y parseo**

**Cierra:** E-HM-01, E-HM-02, E-HM-05, E-HM-06.

**Duración:** 1 día

**Cambio:** ver B.2 (parseo por nombre, filtro de exchange, filtro de liquidez).

**Hecho cuando:** test unitario falla si cambia el orden de columnas; 0 OTC en el último snapshot.

### **F3.8 · Heatmap: cache de asset_id**

**Cierra:** E-HM-04, E-HM-17.

**Duración:** 4 h

**Cambios:**

- Cache `symbol → asset_id` precargado.
- Alta masiva con `DO NOTHING`.
- Job de reconciliación de discrepancias `dim_asset` vs último snapshot.

**Hecho cuando:** ≤ 3 sentencias SQL de dimensión por snapshot.

### **F3.9 · Heatmap: cron con gate**

**Cierra:** E-HM-03.

**Duración:** 4 h

**Cambio:** cron cada 15 min alineado a :00/:15/:30/:45 + ~20 s.

**Hecho cuando:** 28 snapshots por sesión.

### **F3.10 · Auditoría por ciclo**

**Cierra:** E-RAD-05, E-OPS-03.

**Duración:** 1 día

**Cambio:** wrapper con `RUNNING → SUCCESS/PARTIAL_FAIL/SKIPPED` + duración + símbolos fallidos.

**Hecho cuando:** 1 fila de auditoría por ciclo, incluidos saltados.

### **F3.11 · Monitoreo y alertas**

**Cierra:** E-OPS-03.

**Duración:** 1 día

**Cambios:**

- Alerta si `now() - max(ingested_at) > 5 min` en ventana.
- Alerta si 429 recurrente.
- Alerta si `DB_WRITE=OFF`.

**Hecho cuando:** con el scraper apagado 5 min, llega alerta.

### **F3.12 · Ampliar universo del radar (NUEVO)**

**Cierra:** E-RAD-07, H16, M-CAP-08.

**Duración:** 4 h

**Cambios:**

1. Añadir a `CONFIG_ACTIVOS`:
    - `CME_MINI:ES1!` (futuro S&P 500 para pre-apertura).
    - ETF sectoriales SPDR: `AMEX:XLK`, `XLF`, `XLV`, `XLY`, `XLP`, `XLI`, `XLU`, `XLRE`, `XLB`, `XLC`.
    - `AMEX:IWM` (small caps).
    - `AMEX:RSP` (S&P equiponderado).
    - Validar `TVC:DXY` (según D3) o `ICEUS:DX1!`.
2. Verificar `update_mode` de cada símbolo nuevo:
    - ETF sectoriales → probablemente 15 min (equity-like).
    - `ES1!` → 600 s (futuros CME).
    - `TVC:DXY` → probablemente 0 s (índice TVC).
3. Recalcular el ciclo: 110 → 123 símbolos (+13).

**Hecho cuando:** los 13 símbolos nuevos se capturan con `update_mode` correcto; el ciclo sigue ≤ 15 s (con Plan A/B de F3.1).

---

## **FASE 4 · Modelo 15 min**

**Duración:** 8–11 días

**Objetivo:** barras y contexto consultables, con calidad medida.

**Criterio de salida:** 28 barras/día/activo; ≥95% `n_ticks ≥ 3`; ≥95% `definitive`.

### **F4.1 · `fact_market_bar_15m`**

**Cierra:** E-BD-01, H17.

**Duración:** 2 días

**Cambio:** tabla + job de agregación incremental.

**NUEVO — columnas adicionales:**

sql

```
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

**Hecho cuando:** las barras de NVDA del 2026-09-22 se materializan correctamente con `close_quality` calculado.

### **F4.1b · Regla de cierre de barra (REESCRITA por E-RAD-15)**

**Cierra:** H21, E-RAD-15.

**Origen:** Test C (2026-09-22), dos corridas independientes.

**Duración:** incluida en F4.1

**Regla:**

- Último tick en `[T_cierre − 20 s, T_cierre − 5 s]` → `close_quality = 'definitive'`.
- Último tick en `[T_cierre − 5 s, T_cierre + 15 s]` → `close_quality = 'provisional'`.
- Último tick fuera de ambos rangos → `close_quality = 'unknown'`.

**Hecho cuando:** 0% de barras `provisional` tras el siguiente ciclo completo.

### **F4.1c · Cron desfasado + muestreo T−10 s (NUEVO M-CAP-18)**

**Cierra:** E-RAD-15 mitigación.

**Duración:** 2 h

**Cambios:**

- Crontab: `/3 * * * *` → `1-59/3 * * * *` (minuto 1, 4, 7, 10...).
- Añadir un job secundario que capture a `T−10 s` de cada cuarto de hora (`:14:50`, `:29:50`, `:44:50`, `:59:50`).

**Hecho cuando:** el 95% de las barras quedan `definitive`.

### **F4.2 · `fact_market_indicator_tf` (formato largo)**

**Cierra:** E-RAD-01, D12.

**Duración:** 2 días

sql

```
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

**Hecho cuando:** `RSI|15` en la tabla coincide con `/symbol?fields=RSI|15`.

### **F4.3 · `latest_market_tick`**

**Cierra:** E-DSH-04.

**Duración:** 1 día

**Cambio:** una fila por activo, actualizada por upsert en cada ciclo.

**Hecho cuando:** el dashboard lee 110 filas en vez de escanear `fact_market_series`.

### **F4.4 · Snapshots con columnas explícitas**

**Cierra:** E-HM-08, E-HM-10.

**Duración:** 2 días

**Cambio:** migrar `raw_vector` a columnas (`volume`, `avg_vol_10d`, `volatility_d`, `high_52w`, `low_52w`, `update_mode`, `fetched_at`).

**Hecho cuando:** tamaño por fila < 1 kB.

### **F4.5 · Resolver SCD2 en `dim_asset`**

**Cierra:** E-BD-04, I4.

**Duración:** 1 día

**Cambio:** D7 → Tipo 1. Quitar `valid_from/valid_to/current_version` o dejar `UNIQUE (symbol) WHERE current_version`.

**Hecho cuando:** esquema coherente con D7.

### **F4.5b · `dim_asset`: logical_key + resolución SCD2 (NUEVO)**

**Cierra:** E-BD-04, E-RAD-06, I4, M-DAT-06.

**Depende de:** F2.5 (que ya añade las columnas).

**Duración:** incluida en F4.5

**Cambios:**

- Consolidar las columnas añadidas en F2.5 (`logical_key`, `is_canonical`, `role`, `feed_delay_s`).
- Aplicar la decisión D7 (Tipo 1 o SCD2 con unicidad parcial).
- Eliminar `idx_dim_asset_symbol` (duplicado del `dim_asset_symbol_key`).
- Documentar en `M-DOC-01` la semántica de cada columna nueva.

**Hecho cuando:** `dim_asset` tiene todas las columnas del mapeo canónico y solo un índice único sobre `symbol`.

### **F4.6 · Eventos: upsert condicional**

**Cierra:** E-CAL-02, E-BD-03.

**Duración:** 1 día

**Cambio:** B.3 + `captured_at = now()`.

**Hecho cuando:** `last_updated_at` solo cambia si cambia el payload.

### **F4.7 · Reempaquetado del histórico**

**Cierra:** E-RAD-01 histórico, H3 residual.

**Duración:** 3 días

**Cambio:** job offline que lee los CSV existentes y genera `fact_daily_context` + barras retroactivas.

**Salvedades a documentar:**

- `timestamp_utc` es hora de captura, no del dato.
- Posible retraso de 15 min.
- Captura 24 h (contaminada fuera de sesión).
- Equity solo desde 2026-08-22.

**Hecho cuando:** existen barras de 15 min desde 2026-08-22 para equity.

### **F4.8 · Suite nocturna de calidad**

**Cierra:** E-RAD-05 mitigación.

**Duración:** 2 días

**Cambios:**

- Duplicados.
- Huecos.
- Nulos.
- Ticks planos fuera de sesión.
- `n_ticks` por barra.
- `close_quality` por barra.
- Contigüidad de particiones.

**Hecho cuando:** corre a las 02:00 UTC y deja informe diario.

---

## **FASE 5 · MVP Dashboard**

**Duración:** 10–14 días

**Objetivo:** 4 paneles utilizables en sesión.

**Criterio de salida:** paneles con datos reales + banner de frescura por activo.

### **F5.1 · Esqueleto FastAPI**

**Duración:** 2 días

**Estructura:**

text

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

**Hecho cuando:** `uvicorn proy_dashboard:app` levanta en 8100; `/api/health` responde.

### **F5.2 · Modos PRE / LIVE / CLOSED**

**Cierra:** E-DSH-03.

**Duración:** 1 día

**Cambio:** `session_service` que lee `dim_trading_session`.

**Hecho cuando:** fuera de ventana muestra resumen del día y cuenta regresiva.

### **F5.3 · Banner de frescura por panel**

**Cierra:** E-RAD-02.

**Duración:** 1 día

**Cambio:** `as_of`, `feed_delay`, `ingest_lag` por panel — **por activo**, no global.

**Hecho cuando:** cada panel muestra su antigüedad real.

### **F5.4 · Los 4 paneles del MVP**

**Duración:** 4 días

**Panel 1 — Pre-apertura y régimen**

- VIX, DXY, US10Y, NQ/ES, BTC.
- **Nuevo:** `gap`, `premarket_change`, `premarket_volume` por activo.
- **Bloqueado parcialmente por D2/D3** (VIX y DXY canónicos) → depende de F2.5.

**Panel 2 — QQQ/SPY/ORO en 15 min**

- SMA20/50, VWAP, pivotes.
- Usa `Pivot.M.Camarilla.R3|15` (pivote diario, Test H).

**Panel 3 — Próximos eventos**

- Cuenta regresiva + sorpresa con polaridad.

**Panel 4 — Termómetro de riesgo**

- Percentil 60d de VIX, US10Y, TLT.
- Usa el mapeo canónico de F2.5.

**Hecho cuando:** los 4 con datos reales durante la sesión del lunes siguiente.

### **F5.5 · `session_service` con ET y Lima**

**Cierra:** E-DSH-03.

**Duración:** 4 h

**Hecho cuando:** antes y después del 1-nov muestra las horas correctas.

### **F5.6 · Panel de eventos**

**Cierra:** E-DSH-05.

**Duración:** 2 días

**Cambio:** cuenta regresiva, ventana de silencio, sorpresa con polaridad.

**Hecho cuando:** NFP y CPI con sorpresa correcta.

---

## **FASE 6 · Validación y score**

**Duración:** 15–20 días (en paralelo con F5)

**Objetivo:** saber si el score aporta.

**Criterio de salida:** informe walk-forward con IC.

### **F6.1 · Estudio forward-return**

**Cierra:** E-DSH-01, H13.

**Duración:** 5 días

**Cambio:** walk-forward del score y de cada componente, retornos a +15/+30/+60 min, con señal desplazada por el feed delay (**por clase de activo**: 0/600/900 s).

**Hecho cuando:** informe con IC; H13 rechazada o no.

### **F6.2 · Estudio de eventos**

**Cierra:** H14.

**Duración:** 5 días

**Cambio:** reacción media por importancia y sorpresa, ≥30 eventos con actual+forecast.

### **F6.3 · Validación cruzada TV vs propio**

**Cierra:** D4.

**Duración:** 3 días

**Cambio:** comparar `RSI|15`, `ADX|15`, `CCI20|15`, `Pivot.M.Camarilla.R3|15` de TV vs cálculo propio en 5–10 sesiones.

**Hecho cuando:** diferencias documentadas; decisión D4 cerrada (incluye si se mantiene o retira el pivote diario de TV del `CAMPOS`).

### **F6.4 · Score como contexto**

**Cierra:** E-DSH-01, D10.

**Duración:** 2 días

**Cambio:** valor + percentil + fase; sin zonas COMPRAR/VENDER hasta rechazar H13.

### **F6.5 · RVOL por hora del día**

**Cierra:** E-DSH-02.

**Duración:** 2 días

**Cambio:** solo equity/ETF (Q24 cerrada: FX no tiene volumen nocional).

**Hecho cuando:** mediana ≈ 1.0 a cualquier hora.

### **F6.6 · Amplitud sectorial**

**Cierra:** H16, E-RAD-07.

**Duración:** 3 días

**Cambio:** ETF sectoriales (F3.12) + heatmap filtrado.

### **F6.7 · `fact_symbol_score` / `fact_market_context`**

**Cierra:** E-BD-07.

**Duración:** 2 días

### **F6.8 · `fact_event_reaction`**

**Cierra:** E-BD-05.

**Duración:** 3 días

### **F6.9 · `fact_sector_snapshot`**

**Cierra:** H16.

**Duración:** 2 días

## **FASE 7 · Calidad, seguridad y retención**

**Duración:** 6–8 días

**Objetivo:** cerrar deuda.

**Criterio de salida:** retención aplicada, backups probados, docs alineadas.

### **F7.1 · Calendario: llamada semanal (M-CAP-16)**

### **F7.2 · Rotación CSV fuera del ciclo (M-CAP-17)**

### **F7.3 · Retención (M-DAT-12, D8)**

### **F7.4 · Limpieza de índices (M-DAT-13, A13)**

### **F7.5 · Backups (M-OPS-05)**

### **F7.6 · Unificar configs y versiones (M-OPS-06)**

### **F7.7 · Documentación de campos v3 (M-DOC-01)**

### **F7.7b · Correcciones al informe de BD (NUEVO M-DOC-02)**

**Cierra:** E-DOC-01, E-BD-03, M-DOC-02.

**Duración:** 2 h

**Cambios:**

- Corregir §9.4 del informe BD (índices `d[]` del layout v3: `d[1]`, `d[11]`, `d[23]`, no `d[3]`, `d[15]`, `d[25]`).
- Documentar la escala real de importancia (dependiente de A3).
- Fechar cada conteo de activos (1.060 vs 1.083 vs 1.005 vs 502).
- Actualizar los conteos tras F3.12 (110 → 123 símbolos).

**Hecho cuando:** el informe BD coincide con el código y con los conteos reales post-F3.12.

### **F7.8 · Separar auditoría del plan vivo (M-DOC-04)**

---

## **Sección 2 · Calendario consolidado**

| **Semana** | **Fase** | **Entregables** |
| --- | --- | --- |
| **22–27 sep** | F0 + F1 | Hipótesis cerradas; bugs latentes resueltos; EURUSD con volumen |
| **28 sep – 4 oct** | F2 | Gate por clase; particiones UTC; roles; mapeo canónico |
| **5–11 oct** | F3.1–F3.6 | Batch (Plan A o B); CAMPOS extendido; trazabilidad; calendario |
| **12–18 oct** | F3.7–F3.12 | Heatmap; auditoría; monitoreo; ampliar universo |
| **19–25 oct** | F4.1–F4.5b + F4.1b/c | Barras con `close_quality`; indicadores TF; snapshots; dim_asset |
| **26 oct – 1 nov** | F4.6–F4.8 + cierre F2 | Eventos; reempaquetado; calidad; **gate listo para DST** |
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
| R2 | Endpoint no oficial cambia sin aviso | Validar forma + alertas + plan B (Q13) |
| R3 | Sobreajuste del score | D10 (solo contexto) hasta rechazar H13 |
| R4 | Rate limit al aumentar peticiones | POST (si funciona) o thread pool con backoff |
| R5 | DST del 1-nov desalinea | F2 antes del 31-oct |
| R6 | Inserts sin partición | F2.3 + hitos 30-sep y 31-dic |
| R7 | Crecimiento del almacenamiento | Gate + retención D8 |
| R8 | Muestras pequeñas (20 sesiones equity, 45 eventos) | IC amplios; no calibrar zonas |
| R9 | Alcance excesivo del dashboard | MVP de 4 paneles |
| R10 | Exposición de credenciales | F2.4 |
| R11 | H/L muestreados subestiman extremos | Documentar; usar OHLC de TV `|15` para stops |
| R12 | Indicadores repintados dentro de vela | Regla de cierre M-CAP-03 (reformulada) |
| **R13** | **`FX_IDC:EURUSD` con volume=0 corrompe métricas** | **F1.7** |
| **R14** | **Ventana ciega de 15 s en cada frontera de barra** | **F4.1b + F4.1c** |
| **R15** | **`/scan` batch no existe; ciclo sigue secuencial** | **F3.1 Plan A/B** |
| **R16** | **Score sesgado por falta de ETF sectoriales** | **F3.12 + F6.6** |
| **R17** | **VIX/DXY sin mapeo canónico → score inconsistente** | **F2.5 + D2/D3** |

---

## **Sección 4 · Acción inmediata (orden de ejecución)**

**Hoy (2026-09-22 tarde):**

1. F1.1 (heatmap service) → 2 h
2. F1.2 (event service) → 1 h
3. F1.3 (orden heatmap main) → 30 min
4. F1.5 (`records_failed`) → 15 min
5. F1.7 (EURUSD primario) → 15 min
6. T12 (probar `/america/scan`) → 5 min

**Mañana (2026-09-23):**

1. F1.4 (contrato con estado) → 3 h
2. F1.6 (doc `source_checksum`) → 30 min
3. F1.8 (DDL único en heatmap) → 1 h
4. T3.1 (semántica de `gap`) a las 09:29 ET → 5 min
5. F0.1 (A1–A16) → 3 h

**Fin de semana (26–27 sep):**

1. F0.3 (ADR con D1–D14, incluye firma retroactiva de D14)
2. Arrancar F2.1 (`dim_trading_session`)

**Total día 1:** ~4 h de código + 5 min de tests.

**Total día 2:** ~8 h.

Con esto, **el lunes 2026-09-28 arranca F2** con F1 cerrado.

---

## **Sección 5 · Cobertura esperada al cierre**

| **Métrica** | **Real (2026-09-22)** | **Fin F0+F1 (2026-09-27)** | **Fin F3 (2026-10-18)** | **Fin F7 (2026-12-06)** |
| --- | --- | --- | --- | --- |
| Hipótesis cerradas | **13/24** | 13/24 (+0) | 16/24 | 20/24 |
| Dudas cerradas | **10/24** | 10/24 (+0) | 15/24 | 22/24 |
| Errores S1 activos | **4** | **3** (−1) | 1 | 0 |
| Errores S2 activos | 21 | 18 (−3) | 6 | 0 |
| Paneles operativos | 0 | 0 | 1 | 4 |
| Cobertura barras 15 min | 0% | 0% | 90% | 95% |
| Score validado | No | No | Parcial | Sí |
| Mejoras del informe v3 cubiertas | 55/55 (100%) | 55/55 | 55/55 | 55/55 |

**Nota metodológica:** la fila "Fin F0+F1" muestra +0 en hipótesis y dudas cerradas porque los tests D/E/F/G/H/C ya las cerraron hoy. F0+F1 cierra errores, no hipótesis. Los 4 S1 activos son E-RAD-01, E-RAD-02, E-BD-01, E-RAD-14; F1.7 solo cierra E-RAD-14, los otros 3 requieren F2–F5.

---

## **Changelog**
| **Versión** | **Fecha** | **Cambios** |
| --- | --- | --- |
| 2.0 | 2026-09-22 | Roadmap inicial consolidado tras tests D/E/F/G/H/C |
| 2.1 | 2026-09-22 | Incorpora observaciones de auditoría: **Estado de la evidencia** al inicio; trazabilidad explícita en F1.1 y F1.2 (Q18/Q19 → E-HM-13/14; Q20/Q21 → E-CAL-06/07); nota de excepción al orden en F1.7 (D14 pre-ADR); **F2.5 nueva** (M-CAP-07 mapeo canónico); **F3.12 nueva** (M-CAP-08 ampliar universo); **F3.2 ampliada** con `Pivot.M.Camarilla.R3|15`; **F3.6 ampliada** con M-CAP-15 (reintento, RotatingFileHandler, except explícito); **F4.5b nueva** (M-DAT-06 dim_asset); **F7.7b nueva** (M-DOC-02 correcciones informe BD); **Sección 5 recalculada** con baseline real (13 hipótesis, 10 dudas, 4 S1); riesgos R16 y R17 añadidos; F5.4 marca la dependencia de D2/D3. Cobertura de mejoras: 55/55. |
