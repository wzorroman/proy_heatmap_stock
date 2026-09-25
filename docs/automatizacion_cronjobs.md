# Automatización de Cronjobs — Ecosistema heatmap_stock

> Informe de automatización operativa. Cada cronjob está justificado, con su fórmula
> crontab, ventana de ejecución, **ruta del venv** y salidas/logs.
>
> Fecha: 2026-09-24 · Convención horaria del documento: **hora ET del servidor**.
> Sustituye `<BASE>` por la carpeta raíz del monorepo en el servidor
> (véase §5 y §6).

---

## 1. Resumen ejecutivo

Hoy la captura se ejecuta **de forma manual**: radar v5 se disparó a demanda, el
calendario corrió por última vez a las 08:25 y el heatmap solo se ejecutó en
sesiones puntuales (`SKIPPED` fuera de ventana NYSE). Esto deja ventanas de datos
obsoletos (equity/ETF con ~153 min de antigüedad) y sin **certificación de cierre**
(`close_quality` 100% `unknown`).

Este informe registra los **7 cronjobs** que llevan el ecosistema a operación
autónoma 24/5:

| Job | What | Resultado operativo |
|---|---|---|
| A | Radar v5 | Series 3 min → `fact_market_series` + `indicator_tf` + `latest_market_tick` |
| B | Muestreo T−10 s (F4.1c) | Cierres de barra etiquetados `definitive` (~95%) |
| C | Heatmap v1 | Snapshots en sesión NYSE (28 por sesión objetivo) |
| D | Calendario económico | Eventos → `fact_economic_event` (checkpoint incremental) |
| E | Barras 15 min | Materialización `fact_market_bar_15m` (OHLCV) |
| F | Suite de calidad (F4.8) | Informe nocturno de salud de la BD |
| G | Monitor de alertas (F3.11) | Telegram si hay datos obsoletos / 429 / escritura off |

---

## 2. Tabla-resumen

| # | Entry point | Cadencia | Ventana (ET) | Venv |
|---|---|---|---|---|
| A | `<BASE>/proy_scrapping_detail/run_scraper_tradingview.sh` | `1-59/3 * * * *` | Lun–Jue 00–23, Vie 00–16 | `<BASE>/proy_scrapping_detail/venv/bin/python3` |
| B | `<BASE>/proy_scrapping_detail/scraper_live_tradingview_v5.py --at-close` | `14,29,44,59 * * * *` | idem A | idem A |
| C | `<BASE>/proy_heatmap/run_heatmap.sh` | `*/15 * * * *` | Lun–Jue 00–23, Vie 00–16 | `<BASE>/proy_heatmap/venv/bin/python3` |
| D | `<BASE>/proy_scrapping_detail/run_calendario_tradingview.sh` | `*/15 * * * *` | Lun–Jue 00–23, Vie 00–16 | `<BASE>/proy_scrapping_detail/venv/bin/python3` |
| E | `<BASE>/proy_scrapping_detail/scripts/build_market_bar_15m.py` | `1,16,31,46 * * * *` | 24/5 | idem A |
| F | `<BASE>/proy_bd_heatmap/scripts/suite_calidad_nocturna.py` | `5 4 * * *` | diario 04:05 | `<BASE>/proy_bd_heatmap/venv/bin/python3` |
| G | `<BASE>/proy_scrapping_detail/monitor_alertas.py` | `*/5 * * * *` | Lun–Jue 00–23, Vie 00–16 | idem A |

> Nota: con la convención ET del servidor, `04:05 ET` ≈ `08:05 UTC`.

---

## 3. Fichas por job

### A · Radar v5 (captura principal de mercado)

- **Entry point:** `run_scraper_tradingview.sh` → `scraper_live_tradingview_v5.py`
- **Venv:** `<BASE>/proy_scrapping_detail/venv/bin/python3` (el launcher lo detecta como `$PROJECT_DIR/venv/bin/python3`)
- **Cron:**
  ```
  1-59/3 0-23 * * 1-4 <BASE>/proy_scrapping_detail/run_scraper_tradingview.sh
  1-59/3 0-16 * * 5    <BASE>/proy_scrapping_detail/run_scraper_tradingview.sh
  ```
- **Justificación:**
  - Mantiene fresca `fact_market_series` (3 min), alimenta `indicator_tf` (bloques `|TF`) y `latest_market_tick` (fix E-RAD-16: `cycle_id` casteado a `str` en el upsert).
  - Los **gates son internos por clase** (equity solo en sesión NYSE vía `dim_trading_session`): el cron cubre 24/5 sin datos fuera de ventana.
  - **Desfase `1-59/3`** (F4.1c): ningún ciclo cae exactamente en la frontera de barra (`:00`), evitando la ventana ciega E-RAD-15 (muestras `provisional`).
  - **Anti-solapamiento:** `flock` no bloqueante en `/tmp/scraper_live_tradingview_v5.lock` (`scraper_live_tradingview_v5.py:482`) → si una corrida excede los 3 min, la siguiente se omite.
  - **Anti-429:** `REQUEST_DELAY_S` + reintentos internos entre símbolos.
  - El launcher ejecuta de forma idempotente `seed_symbols.py` (altas nuevas en `dim_asset`) y la verificación de conexión BD (degrada a CSV si la BD no responde).
- **Logs:** `<BASE>/proy_scrapping_detail/logs_ejecucion/scraper_*.log` — retención automática de 2 días por el launcher.
- **Exit:** 0 OK; ≠0 error (auditado en `audit_sync_run`).

### B · Muestreo T−10 s para cierre `definitive` (F4.1c)

> ⚠️ **Requiere implementación previa:** el flag `--at-close` aún **no existe** en el
> radar (paso F4.1c, ~2 h). Hasta implementarlo, esta entrada debe estar comentada.

- **Entry point:** `scraper_live_tradingview_v5.py --at-close`
- **Venv:** `<BASE>/proy_scrapping_detail/venv/bin/python3`
- **Cron:** el cron dispara en los minutos `14/29/44/59` y el job **se auto-alinea ~50 s**
  para capturar a `:14:50`, `:29:50`, `:44:50`, `:59:50` (10 s antes del cierre de barra):
  ```
  14,29,44,59 * * * 1-4 <BASE>/proy_scrapping_detail/venv/bin/python3 <BASE>/proy_scrapping_detail/scraper_live_tradingview_v5.py --at-close
  14,29,44,59 * * * 5    <BASE>/proy_scrapping_detail/venv/bin/python3 <BASE>/proy_scrapping_detail/scraper_live_tradingview_v5.py --at-close
  ```
- **Justificación:** con la regla F4.1b (`close_quality_para_offset`), un tick a 6–20 s
  de la frontera etiqueta el cierre como `definitive`. Hoy **0% `definitive`**: sin este
  muestreo, ningún ciclo cae en esa ventana y las 17.311 barras quedan `unknown`.
  Hecho cuando: ~95% de las barras `definitive`.
- **Logs / exit:** los mismos que A.

### C · Heatmap v1 (`scrapper_heatmap_v1.py`)

- **Entry point:** `run_heatmap.sh` (v1.2, F3.9)
- **Venv:** `<BASE>/proy_heatmap/venv/bin/python3` (el launcher lo detecta como `$PROJECT_DIR/venv/bin/python3`)
- **Cron:**
  ```
  */15 0-23 * * 1-4 <BASE>/proy_heatmap/run_heatmap.sh
  */15 0-16 * * 5    <BASE>/proy_heatmap/run_heatmap.sh
  ```
- **Justificación:**
  - Snapshots del heatmap en la sesión NYSE (F2.2/M-CAP-01). El launcher duerme **+20 s**
    para alinear el ciclo a `:00/:15/:30/:45` → objetivo de 28 snapshots por sesión.
  - **Autogate:** fuera de ventana NYSE registra un `SKIPPED` en `audit_sync_run` y sale
    `exit 0` (`scrapper_heatmap_v1.py:561-567`) — inofensivo si el cron cubre más horas,
    pero con la ventana arriba no malgasta requests.
  - Escribe `fact_heatmap_snapshot` (± escala 0–100) y con la migración `0005` el
    `fetched_at` queda poblado (verifica el gap E-HM-10).
  - **Anti-solapamiento / anti-429:** one-shot por invocación; con cadencia 15 min nunca
    hay concurrencia.
- **Logs:** `<BASE>/proy_heatmap/logs_ejecucion/heatmap_*.log` — retención de 7 archivos
  en el launcher.
- **Exit:** 0 OK / `SKIPPED`; 1 error de BD o gate no evaluable.

### D · Calendario económico TradingView

- **Entry point:** `run_calendario_tradingview.sh` → `calendario_tradingview_live_v5.py`
- **Venv:** `<BASE>/proy_scrapping_detail/venv/bin/python3`
- **Cron:**
  ```
  */15 0-23 * * 1-4 <BASE>/proy_scrapping_detail/run_calendario_tradingview.sh
  */15 0-16 * * 5    <BASE>/proy_scrapping_detail/run_calendario_tradingview.sh
  ```
- **Justificación:**
  - Captura periódica de eventos → `fact_economic_event`, con **checkpoint incremental**
    (`last_event_id`, hoy en 421.387) → evita duplicados y re-escaneos completos aunque
    falle una corrida.
  - **Gate interno `pre_min=90`** (arranque 08:00 ET, `calendario_tradingview_live_v5.py:622`):
    no pide datos fuera de la ventana relevante.
  - Cadencia 15 min (patrón heredado de `app_backup_nasdaq`): suficiente por el checkpoint
    y por copiar la granulidad de publicación de eventos.
  - Reintentos internos (E-CAL-05): tolera 429/tiempos de espera de TradingView.
- **Logs:** `<BASE>/proy_scrapping_detail/logs_ejecucion/calendario_*.log` y
  `DATOS_LIVE_CALENDARIO/calendario_economico/logs/` — retención de 2 días.
- **Exit:** 0 OK; ≠0 error (registrado en `audit_sync_run`).

### E · Materialización de barras 15 min

- **Entry point:** `scripts/build_market_bar_15m.py` (F4.1)
- **Venv:** `<BASE>/proy_scrapping_detail/venv/bin/python3`
- **Cron:**
  ```
  1,16,31,46 * * * 1-4 cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python scripts/build_market_bar_15m.py
  1,16,31,46 * * * 5    cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python scripts/build_market_bar_15m.py
  ```
- **Justificación:**
  - Agrega `fact_market_series` → `fact_market_bar_15m` (OHLCV, `volume_delta`, `n_ticks`,
    `is_regular` vía `dim_trading_session` XNYS para equity/ETF).
  - Dispara en **+1 min** de cada cierre de barra: con el job B (T−10 s) ya materializado,
    el último tick cae a 10 s de la frontera → cierre `definitive` por F4.1b.
  - **Idempotente:** upsert mensual `ON CONFLICT (asset_id, bar_start_utc)` → re-corridas
    (recuperación tras caída del servidor) no duplican. Flags útiles: `--dry-run`, `--since`,
    `--until`, `--days`.
- **Logs / exit:** stdout de cron → redirigir a archivo o `logger` del pipeline.

### F · Suite de calidad nocturna (F4.8)

- **Entry point:** `scripts/suite_calidad_nocturna.py` (13 cheques: ciclos, frescura,
  duplicados, nulos, ticks planos, calidad de cierre…)
- **Venv:** `<BASE>/proy_bd_heatmap/venv/bin/python3`
- **Cron:**
  ```
  5 4 * * * <BASE>/proy_bd_heatmap/venv/bin/python3 <BASE>/proy_bd_heatmap/scripts/suite_calidad_nocturna.py
  ```
- **Justificación:**
  - Detección temprana de degradación (radar parado, ticks planos, barras `unknown`, huecos
    de ciclo) — en la validación en vivo detectó 3 FAIL reales y 1 WARN.
  - Se ejecuta en la ventana ritual (04:05 ET ≈ 08:05 UTC), fuera de los carriles de captura,
    para no competir con el radar/heatmap; la BD queda con un día completo muestreado.
  - Credenciales leídas de `<BASE>/proy_bd_heatmap/.env` (auto-`load_dotenv`), sin depender
    del cwd. Flags útiles: `--check CHK-*`, `--hours`, `--quiet`, `--min-definitive`.
- **Reportes:** `<BASE>/proy_bd_heatmap/reports/suite_calidad_YYYYMMDD_HHMMSS.{md,json}` —
  limpiar manualmente con antelación (recomendado: retención 30 días).
- **Exit:** 0 OK; 1 FAIL; 3 (fallos + informativos). Sugerencia: `||` encolar aviso del
  monitor G.

### G · Monitor de alertas (F3.11) — recomendado

- **Entry point:** `monitor_alertas.py`
- **Venv:** `<BASE>/proy_scrapping_detail/venv/bin/python3`
- **Cron:**
  ```
  */5 0-23 * * 1-4 cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python monitor_alertas.py
  */5 0-16 * * 5    cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python monitor_alertas.py
  ```
- **Justificación:**
  - Emite **un único mensaje de Telegram** si se cumple cualquiera de (F3.11 / E-OPS-03):
    1. **A1 — Datos obsoletos:** en sesión NYSE abierta, `now() - max(ingested_at) > 5 min`
       en `fact_heatmap_snapshot`.
    2. **A2 — 429 recurrente:** más de `MAX_429` FAILED en `audit_sync_run` en la última hora.
    3. **A3 — Escritura off:** `DB_WRITE_ENABLED=false` con datos en ventana.
  - Cadencia 5 min dentro de la ventana del radar (si el radar cae, el monitor avisa en ≤5 min).
  - Requiere `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en `<BASE>/proy_scrapping_detail/.env`
    (sin token: solo loguea warning, no mata al proceso).
- **Exit:** 0 siempre (mejor esfuerzo).

---

## 4. Entradas crontab listas para copiar

```cron
# ============================================================
# ECOSISTEMA heatmap_stock · <BASE> = directorio raíz del monorepo
# TZ del servidor: ET (America/New_York)
# ============================================================

# --- A · RADAR V5 (captura principal, cada 3 min desfasado) ---
1-59/3 0-23 * * 1-4 <BASE>/proy_scrapping_detail/run_scraper_tradingview.sh
1-59/3 0-16 * * 5    <BASE>/proy_scrapping_detail/run_scraper_tradingview.sh

# --- B · MUESTREO T−10 s PARA CIERRE DEFINITIVE (F4.1c) ---
# PENDIENTE: requiere flag --at-close (paso F4.1c). Mantener comentado hasta implementarlo.
# 14,29,44,59 * * * 1-4 <BASE>/proy_scrapping_detail/venv/bin/python3 <BASE>/proy_scrapping_detail/scraper_live_tradingview_v5.py --at-close
# 14,29,44,59 * * * 5    <BASE>/proy_scrapping_detail/venv/bin/python3 <BASE>/proy_scrapping_detail/scraper_live_tradingview_v5.py --at-close

# --- C · HEATMAP V1 (cada 15 min, gate NYSE, +20 s internos) ---
*/15 0-23 * * 1-4 <BASE>/proy_heatmap/run_heatmap.sh
*/15 0-16 * * 5    <BASE>/proy_heatmap/run_heatmap.sh

# --- D · CALENDARIO ECONÓMICO (cada 15 min, checkpoint incremental) ---
*/15 0-23 * * 1-4 <BASE>/proy_scrapping_detail/run_calendario_tradingview.sh
*/15 0-16 * * 5    <BASE>/proy_scrapping_detail/run_calendario_tradingview.sh

# --- E · BARRAS 15 MIN (+1 min tras el cierre de cada barra) ---
1,16,31,46 * * * 1-4 cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python scripts/build_market_bar_15m.py
1,16,31,46 * * * 5    cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python scripts/build_market_bar_15m.py

# --- F · SUITE DE CALIDAD NOCTURNA (F4.8, diaria 04:05 ET) ---
5 4 * * * <BASE>/proy_bd_heatmap/venv/bin/python3 <BASE>/proy_bd_heatmap/scripts/suite_calidad_nocturna.py

# --- G · MONITOR DE ALERTAS (F3.11, cada 5 min en ventana) ---
*/5 0-23 * * 1-4 cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python monitor_alertas.py
*/5 0-16 * * 5    cd <BASE>/proy_scrapping_detail && set -a && . ./.env && set +a && ./venv/bin/python monitor_alertas.py
```

> Las entradas que usan `.sh` no necesitan `cd`: el launcher auto-detecta su `PROJECT_DIR`.
> Las de python directo (E, G) cargan `.env` explícitamente (`set -a && . ./.env && set +a`).

---

## 5. Notas de despliegue en el servidor

1. **Ruta base (`<BASE>`)**: carpeta que contiene `proy_scrapping_detail/`, `proy_heatmap/`
   y `proy_bd_heatmap/`. Ejemplo estilo legacy: `/home/wilson/BACKUP_DAILY/proy_heatmap_stock`.
2. **Venv por proyecto** (rutas absolutas a verificar tras el copiado):
   - `proy_scrapping_detail/venv/bin/python3`
   - `proy_heatmap/venv/bin/python3`
   - `proy_bd_heatmap/venv/bin/python3`
3. **`.env` por proyecto** con, al menos:
   - `proy_scrapping_detail/.env` y `proy_heatmap/.env`: `DB_WRITE_ENABLED=true` + `BD_HEATMAP_HOST/PORT/DATABASE/USER/PASSWORD`.
   - `proy_bd_heatmap/.env`: credenciales BD (la suite la carga sola).
   - `proy_scrapping_detail/.env`: además `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` para G.
4. **Zona horaria**: si el server no está en ET, añadir al CRONTAB `CRON_TZ=America/New_York`
   (o convertir los campos a la TZ local del server).
5. **Locks / concurrencia**: A usa `flock` en `/tmp`; B/C/D/E son one-shot; no programar dos
   jobs del mismo pipeline en el mismo minuto.
6. **Retención de logs**: ya gestionada por los launchers (2 días / 7 archivos). Limpiar
   `reports/` de la suite manualmente (sugerencia: 30 días).
7. **Activación progresiva**: activar primero A + D (captura base), verificar `audit_sync_run`
   con SUCCESS, luego C, E, F, G. Dejar B comentado hasta implementar `--at-close` (F4.1c).