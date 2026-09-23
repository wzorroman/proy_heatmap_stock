# Evaluación del informe v2 y roadmap detallado

## **Parte 1 · Veredicto del informe v2**

El informe v2 es **excelente y honesto**. El Anexo G es la mejor pieza: en vez de aceptar como errores confirmados los 8 hallazgos de la revisión anterior sin poder verificarlos, los reclasifica como dudas (Q18–Q21) y explica exactamente por qué. Es metodológicamente correcto.

**Puntuación por dimensión:**

| **Dimensión** | **Nota** | **Comentario** |
| --- | --- | --- |
| Precisión de los hallazgos verificables | 9.5/10 | Los 30+ errores confirmables contra código se verifican línea a línea. |
| Trazabilidad H → D → E → M | 10/10 | La tabla del §12 cierra el círculo completo. |
| Disciplina de evidencia | 10/10 | Marca ✅/🟡/🔴 y Anexo G es un ejemplo de rigor. |
| Cobertura de mejoras | 9/10 | 54 mejoras; sin embargo, faltan dos acciones operativas (ver §4 abajo). |
| Riesgo de sobreajuste documental | 7/10 | El informe es tan completo que el coste de leerlo entero (48 errores + 54 mejoras + 16 incongruencias + 24 hipótesis) puede desincentivar la acción. |

**Ahora bien**, con los 7 archivos que me has pasado (`market_service.py`, `event_service.py`, `heatmap_service.py`, `heatmap_repository.py` + los 3 scrapers), **Q18–Q21 y E-RAD-12 dejan de ser dudas y pasan a ser errores confirmados**. Los abordo antes del roadmap.

---

## **Parte 2 · Confirmación con código de las dudas del Anexo G**

### **E-HM-13 · Ventana muerta de 1 h en `heatmap_service.py` → CONFIRMADO · S2 · P1**

python

```
# heatmap_repository.py, get_heatmap_last_hour:
WHERE h.timestamp_utc >= NOW() - INTERVAL '1 hour'
```

Y `get_price_evolution` (mismo archivo):

python

```
WHERE h.timestamp_utc >= NOW() - make_interval(hours => %s)
```

con `lookback_hours: int = 1` por defecto en `heatmap_service.fetch_price_evolution`.

**Consecuencia real:** con snapshots hoy espaciados >1 h, la Streamlit de `proy_heatmap` está **mostrando vacío sin causa aparente** ahora mismo. No es latente, es presente.

**Fix mínimo** (sin esperar D6):

python

```
# get_heatmap_last_hour
WHERE h.timestamp_utc >= (SELECT MAX(timestamp_utc) - INTERVAL '15 minutes'
                          FROM fact_heatmap_snapshot)
```

Y en `fetch_price_evolution`, subir `lookback_hours` default a 24.

### **E-HM-14 · Colisión de labels `HH:MM` → CONFIRMADO · S3 · P2**

python

```
# heatmap_service.fetch_price_evolution:
label = snap['timestamp_utc'].strftime('%H:%M')
row_data[label] = snap['price_heatmap']
```

Si dos snapshots del mismo activo en días distintos coinciden en `HH:MM`, uno sobreescribe al otro. Hoy con 3 snapshots manuales no se manifiesta; en cuanto D6 active el cron de 15 min, sí.

**Fix:** `label = snap['timestamp_utc'].strftime('%m-%d %H:%M')` o una clave `(fecha, hora)` explícita.

### **E-CAL-06 · `max(safe_int(...))` puede lanzar `TypeError` → CONFIRMADO · S3 · P2**

python

```
# event_service.py, process_calendar_batch:
max_event_id = max(safe_int(e.get('id', 0)) for e in eventos_raw) if eventos_raw else 0
```

`event_service.safe_int` retorna `None` si `val` es `""` o no numérico. `max()` con un `None` mezclado con `int` lanza `TypeError`. Está dentro del `try` que captura la excepción general, así que **no tumba el proceso**, pero **sí aborta el resto del flujo** (auditoría de éxito + checkpoint BD) y lo manda al `except` que registra `FAILED`. Un solo evento con `id` inválido deja el ciclo entero marcado como fallido.

**Fix:**

python

```
ids = [safe_int(e.get('id', 0)) for e in eventos_raw if safe_int(e.get('id', 0)) is not None]
max_event_id = max(ids) if ids else 0
```

### **E-CAL-07 · `guardar_checkpoint` doble por ciclo → CONFIRMADO · S3 · P2**

python

```
# calendario_tradingview_live_v5.py, capturar_eventos (cierre normal):
guardar_checkpoint(max_ts, len(eventos_para_guardar), len(eventos_raw))

# event_service.py, process_calendar_batch (al final del try):
from calendario_tradingview_live_v5 import guardar_checkpoint
guardar_checkpoint(max_event_id, inserted, len(eventos_raw))
```

**Dos escrituras al mismo JSON** con semántica distinta:

- `capturar_eventos` → `max_ts` = timestamp máximo de evento (ISO parseado)
- `event_service` → `max_event_id` = ID numérico máximo de evento

Los valores son de naturaleza distinta y **se pisan mutuamente** en cada ciclo. El checkpoint local pierde sentido. Reforzaría I15.

**Fix:** eliminar la llamada desde `event_service.py`. El checkpoint local es responsabilidad del script; el BD del servicio.

### **E-RAD-12 · `source_checksum` no está en `prepare_bd_row` → CONFIRMADO · S3 (nota de trazabilidad)**

python

```
# market_service.prepare_bd_row
return {
    'symbol': ..., 'timestamp_utc': ..., 'close': ..., 'volume': ...,
    'rsi': ..., 'cci20': ..., 'bbpower': ..., 'adx': ...,
    'pivot_camarilla_r3': ..., 'perf_w': ..., 'change_pct': ...,
}
```

El `source_checksum` no aparece. Debe calcularlo `insert_market_series_batch` (no tengo ese archivo). Pero el hecho de que `fact_market_series.source_checksum` esté 100% poblado indica que el cálculo existe en algún punto del pipeline; el riesgo es que esté **acoplado al repositorio** y no documentado. No es un bug, es una falta de trazabilidad del origen del checksum.

### **E-RAD-05 · Triple silencio confirmado con código → CONFIRMADO · S2 · P1**

Con `market_service.py` a la vista, la estructura es:

text

```
1. process_radar_batch      → try/except Exception, retorna 0 en fallo, NUNCA propaga
2. flush_radar_batch        → try/except Exception, retorna 0 (código muerto para fallos de BD)
3. main() (2 sitios)        → llama flush_radar_batch(...) → batch_buffer.clear() SIN leer el retorno
```

En `market_service.py` está el docstring explícito: *"No lanza excepciones hacia el caller: un fallo de BD no tumba el ciclo (D8)."* **Los tres niveles son intencionales**, así que no es un bug introducido: es una decisión de diseño que hoy hace invisible el fallo. El CSV se conserva, pero nada reconcilia.

**Consecuencia práctica:** si mañana `DB_WRITE_ENABLED=true` en producción y la BD tiene un lock momentáneo, el ciclo entero se pierde silenciosamente en BD. `audit_sync_run` no registra nada porque está dentro del mismo `try/except`.

**Fix mínimo:** que `process_radar_batch` **devuelva un estado**, no solo un int. Cambiar el contrato a `{'inserted': int, 'status': 'SUCCESS'|'FAILED', 'error': str|None}` y que `main()` decida si limpia o no `batch_buffer`.

### **E-RAD-05b · `log_sync_run` del fallo también puede fallar en silencio → NUEVO · S3**

python

```
# market_service.process_radar_batch, except:
try:
    log_sync_run(db, {... 'status': 'FAILED' ...})
except Exception as audit_error:
    logger.error(f"BD: No se pudo registrar auditoría de fallo:{audit_error}")
return 0
```

Si el fallo fue por pérdida de conexión, `log_sync_run` también falla → **no hay auditoría del fallo en BD**. Solo el log local. **Nuevo E-RAD-13 · S3 · P2.**

---

## **Parte 3 · Lo que aún queda sin verificar (y no bloquea)**

- `db/postgresql_connection.py`: si hace commit por llamada (afecta E-HM-04).
- `db/market_repository.py` / `db/event_repository.py`: cómo se calcula `source_checksum` (E-RAD-12), y si `execute_values` confirma por sentencia o por batch.
- `db/partitions.py` / `create_partitions.py`: la zona de los límites (H11, A5 lo confirma o desmiente).

No son bloqueantes para empezar el roadmap.

---

# **Parte 4 · Roadmap para resolver los problemas**

## **Principios de ejecución**

1. **Orden por riesgo, no por severidad nominal.** S1 con dependencia dura (E-RAD-01) va después de S2 sin dependencias (E-HM-13) porque desbloquea más rápido.
2. **Cada fase deja el sistema en un estado coherente y desplegable.** Nada de ramas que duran semanas.
3. **Cada tarea tiene un "hecho cuando" verificable.** Sin excepciones.
4. **Cada cambio toca un solo archivo cuando sea posible.** Si toca más, se hace como un commit único con mensaje descriptivo.
5. **Todo cambio en el scraper que escribe en BD entra con flag.** El `DB_WRITE_ENABLED` sigue siendo el interruptor.

---

## **FASE 0 · Verificación y cierre de hipótesis**

**Duración:** 1–2 días (hoy domingo + lunes en vivo)

**Objetivo:** cerrar H1–H24, Q15–Q21, confirmar decisiones D1–D4 con evidencia.

**Criterio de salida:** todas las hipótesis 🔴 pasan a ✅/🟡 con evidencia directa; `CAMPOS` definitivo firmado.

| **Tarea** | **Evidencia** | **Entregable** |
| --- | --- | --- |
| **F0.1** Ejecutar A1–A16 contra `heatmap_stock` | SQL | Planilla con resultados |
| **F0.2** Ejecutar T1–T9 el lunes (protocolo Anexo C) | CSV con muestras | `CAMPOS` definitivo |
| **F0.3** Decidir D1–D4 | Acta | ADR 0001 |
| **F0.4** Comparar premarket (`close|5` vs `premarket_close`) | T3 | Confirmar/descartar H6, H20 |

**Ninguna tarea de código en esta fase.** Todo es evidencia.

---

## **FASE 1 · Bugs latentes (quick wins, sin dependencias)**

**Duración:** 1 día (lunes en la mañana, antes de la apertura)

**Objetivo:** cerrar los bugs que hoy no hacen ruido pero romperán en cuanto se active el cron denso de D6.

**Criterio de salida:** Streamlit no vuelve a mostrar vacío; logs dejan de estar fragmentados; checkpoints coherentes.

Todas son **P0/P1, esfuerzo S**, sin dependencia entre sí. Se pueden hacer en paralelo.

### **F1.1 · Arreglar `heatmap_service` / `heatmap_repository` (cierra E-HM-13, E-HM-14)**

**Archivos:** `proy_heatmap/application/heatmap_service.py`, `proy_heatmap/db/heatmap_repository.py`

**Cambios:**

1. En `get_heatmap_last_hour`, reemplazar `WHERE h.timestamp_utc >= NOW() - INTERVAL '1 hour'` por:
    
    sql
    
    ```
    WHERE h.timestamp_utc >= (
        SELECT MAX(timestamp_utc) - INTERVAL '15 minutes'
        FROM fact_heatmap_snapshot
    )
    ```
    
2. En `get_heatmap_stats`, mismo cambio (misma ventana).
3. En `get_price_evolution`, subir default `lookback_hours: int = 24`.
4. En `fetch_price_evolution` (service), cambiar:
    
    python
    
    ```
    label = snap['timestamp_utc'].strftime('%m-%d %H:%M')
    ```
    

**Hecho cuando:**

- Con el último snapshot de hace 8 h, `fetch_heatmap_data()` retorna >0 filas.
- Un test unitario con dos snapshots sintéticos de días distintos a la misma hora no colisiona.

### **F1.2 · Arreglar `event_service` (cierra E-CAL-06, E-CAL-07)**

**Archivo:** `proy_scrapping_detail/application/event_service.py`

**Cambios:**

1. Reemplazar:
    
    python
    
    ```
    max_event_id = max(safe_int(e.get('id', 0)) for e in eventos_raw) if eventos_raw else 0
    ```
    
    por:
    
    python
    
    ```
    ids = [safe_int(e.get('id', 0)) for e in eventos_raw]
    ids = [i for i in ids if i is not None]
    max_event_id = max(ids) if ids else 0
    ```
    
2. **Eliminar** el bloque:
    
    python
    
    ```
    from calendario_tradingview_live_v5 import guardar_checkpoint
    guardar_checkpoint(max_event_id, inserted, len(eventos_raw))
    ```
    
    El checkpoint local es responsabilidad del script.
    

**Hecho cuando:**

- Un evento con `id=""` no rompe el ciclo.
- `guardar_checkpoint` se llama **una sola vez** por ejecución (verificado por log o por mock).

### **F1.3 · Invertir orden en `scrapper_heatmap_v1.main()` (cierra E-HM-16)**

**Archivo:** `proy_heatmap/scrapper_heatmap_v1.py`

**Cambio:**

python

```
def main():
    ...
    db = PostgreSQLConnector(...)
    if not db.connect(): ...

    try:
        # 1. Fetch PRIMERO
        heatmap_data = fetch_heatmap_data()
        if heatmap_data is None:
            log_sync_run(db, 'scrapper_heatmap_v1', run_start, 0, 0, 'SKIPPED', 'API sin datos')
            logger.warning("Sin datos del heatmap — ciclo SKIPPED")
            return   # ← ya no es FAILED ni exit(1)

        # 2. DDL de partición después
        create_monthly_partitions(db, "fact_heatmap_snapshot", 1)

        # 3. Procesar
        inserted = process_heatmap_data(db, heatmap_data)
        log_sync_run(db, 'scrapper_heatmap_v1', run_start, len(heatmap_data), inserted, 'SUCCESS')
    except Exception as e:
        ...
```

**Hecho cuando:** fuera de sesión, el script registra `SKIPPED` en `audit_sync_run`, no `FAILED`.

### **F1.4 · Convertir `process_radar_batch` a contrato con estado (cierra E-RAD-05)**

**Archivos:** `proy_scrapping_detail/application/market_service.py`, `proy_scrapping_detail/scraper_live_tradingview_v5.py`

**Cambios en `market_service.py`:**

python

```
def process_radar_batch(scanner_data: list) -> dict:
    """Retorna {'inserted': int, 'status': str, 'error': str|None}."""
    if not config.DB_WRITE_ENABLED:
        return {'inserted': 0, 'status': 'SKIPPED', 'error': 'DB_WRITE_ENABLED=false'}
    try:
        ...
        return {'inserted': inserted, 'status': 'SUCCESS', 'error': None}
    except Exception as e:
        logger.error(...)
        try:
            log_sync_run(db, {... 'status': 'FAILED' ...})
        except Exception as audit_error:
            logger.critical(f"Auditoría de fallo también falló:{audit_error}")
        return {'inserted': 0, 'status': 'FAILED', 'error': str(e)}
    finally:
        db.disconnect()
```

**Cambios en `scraper_live_tradingview_v5.py`, `flush_radar_batch`:**

python

```
def flush_radar_batch(batch_buffer):
    if not batch_buffer or not config.DB_WRITE_ENABLED:
        return {'inserted': 0, 'status': 'SKIPPED', 'error': None}
    ...
    result = process_radar_batch(bd_rows)
    if result['status'] == 'FAILED':
        logger.error(f"BD: fallo de escritura —{result['error']}")
    return result
```

**Cambios en `main()` (2 sitios):**

python

```
result = flush_radar_batch(batch_buffer)
if result['status'] in ('SUCCESS', 'SKIPPED'):
    batch_buffer.clear()
else:
    logger.warning(f"{len(batch_buffer)} filas quedan en buffer para el próximo ciclo")
    # NO limpiar; el CSV ya las tiene, pero al menos se ve la pérdida
```

**Hecho cuando:** con la BD apagada 5 min, el log muestra `FAILED` y el buffer conserva las filas; con la BD encendida, `SUCCESS` y limpia.

### **F1.5 · Corregir `records_failed` en `log_sync_run` (cierra E-HM-07)**

**Archivo:** `proy_heatmap/scrapper_heatmap_v1.py`

**Cambio:**

python

```
def log_sync_run(conn, script_name, run_start, records_fetched, records_upserted, status, error_message=None):
    records_failed = max((records_fetched or 0) - (records_upserted or 0), 0)
    ...
```

**Hecho cuando:** un ciclo con `fetched=1000, upserted=0` registra `records_failed=1000`.

### **F1.6 · Documentar E-RAD-12 (dónde se calcula `source_checksum`)**

**Acción:** buscar `source_checksum` en `db/market_repository.py` y `db/event_repository.py`. Añadir un comentario en `prepare_bd_row`:

python

```
# NOTE: source_checksum se calcula en <módulo>.<función>, no aquí.
```

**Hecho cuando:** un lector de `prepare_bd_row` sabe dónde buscar el checksum.

## **FASE 2 · Tiempo y ventana (P0, deadline 2026-10-31)**

**Duración:** 3–5 días

**Objetivo:** base temporal correcta antes del fin del DST (1-nov-2026).

**Criterio de salida:** gate probado con feriado, cierre anticipado y DST.

### **F2.1 · `dim_trading_session` (M-DAT-01)**

**Acción:** crear tabla y poblarla con `exchange_calendars` (XNYS) 2026–2027.

**Archivo nuevo:** `proy_scrapping_detail/db/sessions.py`

**Hecho cuando:** consulta de sesiones para 2026-11-26 devuelve 0 filas (Acción de Gracias); para 2026-11-27 devuelve `is_early_close=true`.

### **F2.2 · Gate de sesión en los 3 scrapers (M-CAP-01, M-OPS-04)**

**Archivos:** los 3 scripts + test suite.

**Cambio:** al inicio de `main()` de cada script:

python

```
from db.sessions import en_ventana
if not en_ventana(pre_min=30):   # 90 para calendario
    logger.info("Fuera de ventana — skip")
    sys.exit(0)
```

**Test suite:** los 9 casos de B.1.

**Hecho cuando:** los 9 tests pasan; con la fecha simulada 2026-11-02, el gate respeta el cambio de horario.

### **F2.3 · Particiones: límites UTC explícitos (M-DAT-07)**

**Acción:** verificar A5. Si los límites son `-05`, migrar a UTC. Crear hasta 2027-12. Añadir alerta si falta la partición del mes+1.

**Hecho cuando:** A5 muestra límites contiguos a `00:00+00`; existe `fact_market_series_2027_12`.

### **F2.4 · Roles y credenciales (M-OPS-03)**

**Acción:**

- Crear `scraper_rw` (INSERT/UPDATE en `fact_*`, `audit_sync_run`, `sync_checkpoint`) y `dashboard_ro` (SELECT en todo).
- Rotar password de `postgres`.
- Retirar credenciales del informe de BD.

**Hecho cuando:** `psql -U dashboard_ro` no puede hacer INSERT.

---

## **FASE 3 · Captura fiable (P0/P1)**

**Duración:** 5–8 días

**Objetivo:** ciclo corto, simultáneo, trazable.

**Criterio de salida:** p95 ciclo ≤ 15 s; `update_mode` en 100% de ticks; alertas de frescura.

### **F3.1 · `POST /scan` único (M-CAP-02)**

**Archivo:** `scraper_live_tradingview_v5.py`

**Cambio:** reemplazar el bucle de `GET /symbol` por un `POST /scan` con `symbols.tickers`.

**Dependencia:** validar Q16 en T5.

**Fallback:** si `/scan` no responde, caer al modo `GET` actual.

**Hecho cuando:** un ciclo completo tarda ≤ 15 s y trae los 110 símbolos.

### **F3.2 · `CAMPOS` multi-TF (M-CAP-03)**

**Archivo:** `scraper_live_tradingview_v5.py`

**Cambio:**

python

```
BASE = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"
def _bloque(tf):
    return ",".join(f"{c}|{tf}" for c in ("volume","RSI","CCI20","BBPower","ADX","change"))
CAMPOS = ",".join([BASE, _bloque("5"), _bloque("15")])
```

**Dependencia:** T4, T6 (confirma H19, H21, H22).

**Hecho cuando:** una llamada trae los campos base + sufijados.

### **F3.3 · Trazabilidad temporal (M-CAP-04)**

**Cambio:** añadir `update_mode`, `cycle_id`, `fetched_at` en cada tick.

**Hecho cuando:** `fact_market_series` (o su versión multi-TF) tiene `update_mode` poblado en 100% de filas.

### **F3.4 · Prioridad y circuit breaker por exchange (M-CAP-05)**

**Cambio:** ordenar símbolos por prioridad (SPY, QQQ, VIX, US10Y, DXY, NQ1! primero) y separar el breaker por exchange.

**Hecho cuando:** un fallo simulado de `CBOE` no afecta a `NASDAQ`.

### **F3.5 · Reintento + modo estricto + reconciliación (M-CAP-06)**

**Cambio:**

- `DB_WRITE_ENABLED` obligatorio en prod (falla arranque si falta).
- `load_dotenv(override=False)`.
- Job nocturno que compara CSV vs BD y reporta discrepancias.

**Hecho cuando:** con la BD caída 10 min, tras reiniciarla no queda hueco.

### **F3.6 · Calendario: polling por evento (M-CAP-14, M-CAP-15)**

**Cambio:** cron cada minuto entre T-1 y T+10 min de cada evento de alto impacto; reintento con backoff; `RotatingFileHandler`.

**Hecho cuando:** p95 de latencia del `actual` ≤ 90 s.

### **F3.7 · Heatmap: filtros y parseo (M-CAP-10, M-CAP-11)**

**Cambio:** ver B.2 (parseo por nombre, filtro de exchange común, filtro de liquidez).

**Hecho cuando:** un test unitario falla si cambia el orden de `HEATMAP_COLUMNS`; 0 OTC en el último snapshot.

### **F3.8 · Heatmap: cache de asset_id y alta masiva (M-CAP-12)**

**Cambio:** ver B.7.

**Hecho cuando:** ≤ 3 sentencias SQL de dimensión por snapshot.

### **F3.9 · Heatmap: cron con gate (M-CAP-13)**

**Cambio:** cron cada 15 min alineado (:00/:15/:30/:45 + 20 s).

**Hecho cuando:** 28 snapshots por sesión, 0 fuera de ella.

### **F3.10 · Auditoría por ciclo (M-OPS-01)**

**Cambio:** wrapper que registra `RUNNING → SUCCESS / PARTIAL_FAIL / SKIPPED` y duración.

**Hecho cuando:** 1 fila de auditoría por ciclo, incluyendo los saltados.

### **F3.11 · Monitoreo y alertas (M-OPS-02)**

**Cambio:** alerta si `now() - max(ingested_at) > 5 min` en ventana; alerta si 429 recurrente; alerta si `DB_WRITE=OFF`.

**Hecho cuando:** con el scraper apagado 5 min en ventana, llega alerta.

---

## **FASE 4 · Modelo 15 min (P0/P1)**

**Duración:** 5–7 días

**Objetivo:** barras y contexto diario consultables.

**Criterio de salida:** 28 barras/día/activo; ≥95% con `n_ticks ≥ 3`.

### **F4.1 · `fact_market_bar_15m` (M-DAT-02)**

**Cambio:** crear tabla + job de agregación incremental (ver B.5).

**Hecho cuando:** barras de NVDA del 2026-09-18 (viernes) se materializan correctamente.

### **F4.2 · `fact_market_indicator_tf` en formato largo (M-DAT-03)**

**Cambio:** crear tabla; el scraper escribe filas `(asset_id, timestamp_utc, tf, ...)`.

**Hecho cuando:** consultar `RSI|15` en la tabla nueva da el mismo valor que `/symbol?fields=RSI|15`.

### **F4.3 · `latest_market_tick` (M-DAT-04)**

**Cambio:** una fila por activo, actualizada por upsert.

**Hecho cuando:** el dashboard lee 110 filas en vez de escanear `fact_market_series`.

### **F4.4 · Snapshots con columnas explícitas (M-DAT-05)**

**Cambio:** migrar `raw_vector` a columnas (`volume`, `avg_vol_10d`, `volatility_d`, `high_52w`, `low_52w`, `update_mode`, `fetched_at`).

**Hecho cuando:** tamaño por fila < 1 kB; `raw_vector` se conserva pero deja de ser la fuente principal.

### **F4.5 · Resolver SCD2 en `dim_asset` (M-DAT-06, D7)**

**Decisión:** D7 → Tipo 1 (recomendado). Quitar `valid_from/valid_to/current_version` o dejarlos con `UNIQUE (symbol) WHERE current_version`.

**Hecho cuando:** el esquema es coherente con D7; `dim_asset_symbol_key` documentado.

### **F4.6 · Eventos: upsert condicional (M-DAT-08)**

**Cambio:** B.3 + `captured_at = now()` en el servicio.

**Hecho cuando:** `last_updated_at` solo cambia cuando cambia el payload.

### **F4.7 · Reempaquetado del histórico (M-VAL-05)**

**Cambio:** job offline que lee los CSV existentes, genera `fact_daily_context` y barras retroactivas.

**Hecho cuando:** existen barras de 15 min desde 2026-08-22 para equity.

### **F4.8 · Suite nocturna de calidad (M-VAL-01)**

**Cambio:** script que verifica duplicados, huecos, nulos, `n_ticks` por barra, contigüidad de particiones.

**Hecho cuando:** corre a las 02:00 UTC y deja un informe diario.

## **FASE 5 · MVP dashboard (P0, en paralelo con F4)**

**Duración:** 8–12 días

**Objetivo:** 4 paneles utilizables en sesión.

**Criterio de salida:** paneles con datos reales y banner de frescura.

### **F5.1 · Esqueleto FastAPI (M-DSH-07)**

**Acción:** estructura `proy_dashboard/` con `core/`, `db/`, `repositories/`, `services/`, `api/`, `web/`.

**Hecho cuando:** `uvicorn proy_dashboard:app` levanta en 8100; `/api/health` responde.

### **F5.2 · Modos PRE/LIVE/CLOSED (M-DSH-01)**

**Cambio:** `session_service` que lee `dim_trading_session`.

**Hecho cuando:** fuera de ventana muestra resumen del día y cuenta regresiva.

### **F5.3 · Banner de frescura (M-DSH-02)**

**Cambio:** `as_of`, `feed_delay`, `ingest_lag` por panel.

**Hecho cuando:** cada panel muestra su antigüedad.

### **F5.4 · Los 4 paneles del MVP (M-DSH-03)**

**Contenido:**

1. **Pre-apertura + régimen**: VIX, DXY, US10Y, NQ/ES, BTC.
2. **QQQ/SPY/ORO en 15 min**: SMA20/50, VWAP, pivotes.
3. **Próximos eventos**: cuenta regresiva + sorpresa.
4. **Termómetro de riesgo**: percentil 60d de VIX, US10Y, TLT.

**Hecho cuando:** los 4 con datos reales durante la sesión del lunes siguiente.

### **F5.5 · `session_service` (M-DSH-08)**

**Cambio:** mostrar ET y Lima.

**Hecho cuando:** antes y después del 1-nov muestra las horas correctas.

### **F5.6 · Panel de eventos (M-DSH-09)**

**Cambio:** cuenta regresiva, ventana de silencio, sorpresa con polaridad.

**Hecho cuando:** NFP y CPI con sorpresa correcta.

---

## **FASE 6 · Validación y score (P1, en paralelo con F5)**

**Duración:** 15–20 días

**Objetivo:** saber si el score aporta.

**Criterio de salida:** informe walk-forward con intervalos de confianza.

### **F6.1 · Estudio forward-return (M-VAL-02)**

**Acción:** walk-forward del score y de cada componente, retornos a +15/+30/+60 min, con la señal desplazada por el feed delay.

**Hecho cuando:** informe con IC; rechazar o no H13.

### **F6.2 · Estudio de eventos (M-VAL-03)**

**Hecho cuando:** reacción media por importancia y sorpresa, para ≥30 eventos con actual+forecast.

### **F6.3 · Validación cruzada TV vs propio (M-VAL-04)**

**Hecho cuando:** diferencias documentadas; decisión D4 cerrada.

### **F6.4 · Score como contexto (M-DSH-04)**

**Cambio:** valor + percentil + fase; **sin** zonas COMPRAR/VENDER hasta rechazar H13.

### **F6.5 · RVOL por hora (M-DSH-05)**

**Hecho cuando:** mediana ≈1.0 a cualquier hora.

### **F6.6 · Amplitud sectorial (M-DSH-06)**

**Cambio:** ETF sectoriales + heatmap filtrado.

### **F6.7 · `fact_symbol_score` / `fact_market_context` (M-DAT-09)**

**Cambio:** separar granularidad.

### **F6.8 · `fact_event_reaction` (M-DAT-10)**

**Cambio:** sustituye `vw_heatmap_event_impact`; `dim_indicator_polarity`.

### **F6.9 · `fact_sector_snapshot` (M-DAT-11)**

**Cambio:** amplitud y cambio ponderado por sector.

---

## **FASE 7 · Calidad, seguridad y retención (P2/P3)**

**Duración:** 5–7 días

**Objetivo:** cerrar deuda.

**Criterio de salida:** retención aplicada, backups probados, docs alineadas.

### **F7.1 · Calendario: llamada semanal (M-CAP-16)**

### **F7.2 · Rotación CSV fuera del ciclo (M-CAP-17)**

### **F7.3 · Retención (M-DAT-12)**

**Decisión:** D8. Implementar política.

### **F7.4 · Limpieza de índices (M-DAT-13)**

**Cambio:** dropear `idx_dim_asset_symbol` (duplicado); revisar A13.

### **F7.5 · Backups (M-OPS-05)**

**Cambio:** dump diario a NAS/S3; probar restauración.

### **F7.6 · Unificar configs y versiones (M-OPS-06)**

### **F7.7 · Documentación de campos v3 (M-DOC-01)**

### **F7.8 · Separar auditoría del plan vivo (M-DOC-04)**

---

## **Calendario consolidado**

| **Semana** | **Fase** | **Entregable semanal** |
| --- | --- | --- |
| **21–27 sep** | F0 + F1 | Hipótesis cerradas; bugs latentes resueltos |
| **28 sep – 4 oct** | F2 | Gate desplegado; particiones UTC; roles |
| **5–11 oct** | F3.1–F3.5 | POST único; CAMPOS multi-TF; trazabilidad |
| **12–18 oct** | F3.6–F3.11 | Calendario polling; heatmap; auditoría; monitoreo |
| **19–25 oct** | F4.1–F4.4 | Barras 15 min; indicadores por TF; snapshots columnas |
| **26 oct – 1 nov** | F4.5–F4.8 + cierre F2 | Eventos; reempaquetado; suite de calidad; **gate listo para DST** |
| **2–8 nov** | F5.1–F5.3 | Esqueleto FastAPI; modos; banner frescura |
| **9–15 nov** | F5.4–F5.6 | Los 4 paneles MVP |
| **16–22 nov** | F6.1–F6.4 | Validación forward-return; decisión D10 |
| **23–29 nov** | F6.5–F6.9 | RVOL; amplitud; event reaction; sector snapshot |
| **30 nov – 6 dic** | F7 | Calidad, seguridad, retención |

---

## **Criterios de éxito globales (KPIs)**

| **KPI** | **Objetivo** | **Fase** |
| --- | --- | --- |
| Gate probado con feriado, cierre anticipado, DST | 100% | F2 |
| p95 duración del ciclo del radar | ≤ 15 s | F3 |
| `update_mode` poblado | 100% | F3 |
| Frescura de ingesta en ventana | p95 ≤ 60 s | F3 |
| Barras válidas (`n_ticks ≥ 3`) | ≥ 95% | F4 |
| Snapshots heatmap por sesión | 28 | F3 |
| Latencia del `actual` de eventos de alto impacto | p95 ≤ 90 s | F3 |
| Streamlit no muestra vacío | siempre | F1 |
| Panel con datos reales en ventana | 4/4 | F5 |
| Informe walk-forward del score | con IC | F6 |
| Secretos en documentos | 0 | F2 |
| `dashboard_ro` no puede escribir | verificable | F2 |

---

## **Riesgos del plan**

| **Riesgo** | **Mitigación** |
| --- | --- |
| El gate no está listo antes del 1-nov | F2 tiene 5 días de colchón; el deadline duro es 31-oct |
| `/scan` (POST) no soporta sufijos TF (Q16) | Fallback a `GET` (110 requests sigue siendo válido) |
| El universe multi-TF multiplica filas ×5 | Decidir D12 → tabla larga; empeza con `|5` y `|15` |
| F4 + F5 en paralelo saturan el sprint | F4 no bloquea F5: el dashboard lee `fact_market_series` mientras F4 construye `fact_market_bar_15m` |
| El equipo es uno | Las fases se pueden serializar; el plan soporta eso |

---

## **Acción inmediata (hoy mismo)**

1. **F1.1** (heatmap service) → 2 h
2. **F1.2** (event service) → 1 h
3. **F1.3** (orden en heatmap main) → 30 min
4. **F1.4** (contrato con estado en market_service) → 3 h
5. **F1.5** (`records_failed`) → 15 min
6. Ejecutar A1–A16 → 2 h