# proy_dashboard

Prototipo de **dashboard de contexto de mercado** que lee directamente de PostgreSQL
`heatmap_stock` (sin CSV). Stack: **FastAPI + Jinja2 + HTMX + Apache ECharts**, con
todas las librerías servidas **desde local (sin CDN)**.

> Roadmap completo y decisiones de diseño: [`ROADMAP_prototipo.md`](ROADMAP_prototipo.md).
> Migraciones de BD: proyecto hermano [`../proy_bd_heatmap`](../proy_bd_heatmap).

---

## Estado

| Fase | Entregable | Estado |
|---|---|---|
| 0 | Esqueleto, config, logging, librerías locales, `/api/health`, `/api/version` | ✅ |
| 1 | Migración `0009` (`fact_market_score` + `fact_market_score_agg`) en `proy_bd_heatmap` | ✅ **aplicada en BD viva** |
| 2 | Núcleo (settings, timezone, container) y dominio | ✅ |
| 3 | Repositorios SQL (degradan sin conector) | ✅ |
| 4 | Motor de score + job `persist_score` + cron | ✅ |
| 5 | Servicios: momentum, heatmap, indicadores, eventos, sesión, health | ✅ |
| 6 | API JSON (`/api/*`) | ✅ |
| 7 | Web Jinja2 + HTMX + ECharts (13 paneles + 4 placeholders) | ✅ |
| 8 | Calidad, deploy y documentación (este README) | ✅ |

**Paneles reales:** header/score, evolución del score, sectorial, Sector Risk Gauge, momentum,
Momentum Confirmado (Change vs RSI), Alcistas/Bajistas del Día, RSI top, riesgo intermarket,
Termómetro de Riesgo, Riesgo e Interpretación + FX/Macro, volumen, rango 52s,
RSI top-cap (dot-plot), multi-TF, calendario, health.
**Layout:** grid CSS de **12 columnas** (paneles a 6 = mitad; calendario y header a 12 = ancho completo).
**Placeholders honestos:** SMA20/50, percentil 60d, performance semanal, distribución histórica/backtest.
**Deshabilitado:** mapa sectorial (treemap) — puede reactivarse descomentando el bloque en
`web/views.py` y `web/templates/dashboard.html`.

Colores semánticos: **verde** = positivo/alcista, **rojo** = negativo/bajista, **amarillo** = neutro
(score, momentum, RSI, sorpresas, health y rango 52s).

---

## Requisitos

- Python **3.10+** (venv local)
- Acceso a PostgreSQL `heatmap_stock` (por defecto `192.168.18.121:5432`)
- Librerías frontend ya **vendorizadas** en `web/static/vendor/` (ECharts 6.1.0, HTMX 2.0.11)

---

## Instalación

```bash
cd proy_dashboard
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env          # editar BD_HEATMAP_* (ver abajo)
```

### Variables `.env`

| Variable | Default | Uso |
|---|---|---|
| `BD_HEATMAP_HOST` / `_PORT` / `_DATABASE` / `_USER` / `_PASSWORD` | — | Conexión PostgreSQL |
| `APP_NAME` | `proy_dashboard` | Nombre en logs/versionado |
| `APP_ENV` | `dev` | `dev`/`prod` (controla `uvicorn --reload`) |
| `APP_PORT` | `8100` | Puerto |
| `APP_TIMEZONE` | `America/New_York` | Fases de sesión |
| `FILE_PATH_LOG` | `./logs` | Carpeta de logs |
| `RETRANSMISOR_ID` | `101` | Sufijo de archivos de log |
| `LOG_LEVEL` / `LOG_BACKUP_DAYS` | `INFO` / `14` | Logging |
| `DB_WRITE_ENABLED` | `true` | El job persiste score |

Los parámetros de negocio (pesos, zonas, umbrales) viven en `config_dashboard.json`.

### Migración de BD (una vez)

```bash
cd ../proy_bd_heatmap
./venv/bin/alembic upgrade head       # aplica 0009 (fact_market_score + _agg)
```

---

## Ejecución

```bash
./run_dashboard.sh                     # carga .env + venv + uvicorn :${APP_PORT:-8100}
# o bien:
./venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 8100
```

| URL | Descripción |
|---|---|
| `http://localhost:8100/` | Dashboard |
| `http://localhost:8100/api/health` | Salud por módulo (degrada sin crash) |
| `http://localhost:8100/api/version` | Versión y entorno |
| `http://localhost:8100/docs` | OpenAPI (Swagger) |

### Poblado del score

```bash
# ciclo actual (una vez)
./venv/bin/python jobs/persist_score.py --cycle

# backfill histórico desde fact_market_series (buckets de 30 min)
./venv/bin/python jobs/persist_score.py --backfill --since 2026-09-29T00:00:00Z

# sin escribir
./venv/bin/python jobs/persist_score.py --cycle --dry-run
```

---

## Deploy

### Arranque persistente (`nohup`)

```bash
cd /opt/proy_heatmap_stock/proy_dashboard
nohup ./run_dashboard.sh > logs/uvicorn.out 2>&1 &
```

### Servicio systemd (recomendado)

`/etc/systemd/system/proy_dashboard.service`:

```ini
[Unit]
Description=proy_dashboard (FastAPI :8100)
After=network.target

[Service]
User=appuser
WorkingDirectory=/opt/proy_heatmap_stock/proy_dashboard
ExecStart=/opt/proy_heatmap_stock/proy_dashboard/venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 8100
Restart=unless-stopped
EnvironmentFile=/opt/proy_heatmap_stock/proy_dashboard/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now proy_dashboard
```

> Puerto **8100** separado: no interrumpe scraper, calendario ni notificador.

### Cron del score (cada 3 min, offset +2 del radar)

> Esta es la **entrada H** a agregar en el crontab del servidor
> (TZ del servidor = ET). No se instala desde este README; requiere acceso al servidor.

```cron
# ============================================================
# proy_dashboard · score de mercado (cada 3 min)
# <BASE> = directorio raíz del monorepo (ej. /opt/proy_heatmap_stock)
# ============================================================

# --- H · SCORE DASHBOARD (+2 min del radar, cada 3 min) ---
3-59/3 0-23 * * 1-4 cd <BASE>/proy_dashboard && set -a && . ./.env && set +a && ./venv/bin/python jobs/persist_score.py --cycle
3-59/3 0-16 * * 5    cd <BASE>/proy_dashboard && set -a && . ./.env && set +a && ./venv/bin/python jobs/persist_score.py --cycle
```

Equivalente usando el launcher:

```cron
3-59/3 0-23 * * 1-4 <BASE>/proy_dashboard/run_persist_score.sh --cycle
3-59/3 0-16 * * 5    <BASE>/proy_dashboard/run_persist_score.sh --cycle
```

- El radar arranca en `1-59/3`; `3-59/3` corre ~2 min después, con `latest_market_tick` ya escrito.
- El job usa `flock` (`/tmp/proy_dashboard_persist_score.lock`) para evitar solapamientos.

---

## Tests

```bash
cd proy_dashboard
./venv/bin/python -m pytest tests -q          # 74 tests

cd ../proy_bd_heatmap
./venv/bin/python -m pytest tests -q          # 25 tests (migraciones, incl. 0009)
```

> Los tests de migración crean una BD scratch `heatmap_stock_test` en el docker local;
> si el `.env` apunta a otro host, ejecutarlos con
> `BD_HEATMAP_HOST=localhost BD_HEATMAP_PASSWORD=postgres ./venv/bin/python -m pytest tests -q`.

### Verificación "cero CDN"

```bash
grep -rn "http[s]*://" web/templates web/static/app.* || echo "OK: sin CDN en código propio"
```

---

## Estructura

```
proy_dashboard/
├── core/          settings, logging_config, timezone, container (DI)
├── domain/        dataclasses puras (score, market, event)
├── db/            conector PostgreSQL (psycopg2)
├── repositories/  SOLO SQL (latest_tick, score, heatmap, events, series, indicator, session)
├── services/      LÓGICA DE NEGOCIO (score, momentum, heatmap, indicator, event, session, health)
├── api/           routers JSON + schemas Pydantic
├── web/           FastAPI + Jinja2 + static/vendor (ECharts, HTMX) + views (partials)
├── jobs/          persist_score (--cycle/--backfill/--dry-run)
├── tests/         pytest por capa
├── config_dashboard.json   parámetros de negocio (única fuente)
└── ROADMAP_prototipo.md
```

## Arquitectura

```
PostgreSQL heatmap_stock
        │
        ▼
repositories/ (solo SQL)  →  services/ (negocio)  →  api/ (JSON) ─┐
        ▲                        │                                 │
        │                        └──────────────►  web/ (Jinja2+HTMX+ECharts)
        └── jobs/persist_score ──► fact_market_score(_agg)
```

- **Capas sin fugas:** `services` no contiene SQL/HTTP; `repositories` no contiene negocio;
  las plantillas no tocan la BD.
- **Cero números mágicos:** pesos/zonas/umbrales en `config_dashboard.json`.
- **Degradación suave:** sin BD o sin datos, los paneles muestran "sin datos", nunca crash.

---

## Operación y mantenimiento

- **Logs:** `logs/app_daily_proy_dashboard_<ID>.log` con rotación diaria (retención 14 días);
  los rotados pasan a `YYYY-MM-DD_app_history_proy_dashboard_<ID>.log`.
- **Frescura:** `/api/health` reporta `db`, `data`, `heatmap` y `events`; el panel Health lo muestra.
- **Backfill:** usar `--backfill --since` si se requiere reconstruir el score histórico.
- **Retención del score:** `fact_market_score` está particionada por mes (2026-09 … 2027-12).
