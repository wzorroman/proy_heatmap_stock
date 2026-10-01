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

- Python **3.10+** (venv local) — o **Podman/Docker** para deploy contenedorizado (ver checklist de producción)
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

## Deploy en producción — pasos iniciales (checklist)

> **Regla de oro del despliegue actual:** el contenedor (o systemd) **solo corre la web**
> (lectura). La **escritura** la siguen haciendo los **crones del servidor** como `appuser`
> (`persist_score` cada 3 min, watchdog cada 10 min, scrapers, heatmap). No moverlos al contenedor.

### 1) Servidor y prerequisitos

- [ ] Acceso SSH al servidor de cronjobs (donde vive `/opt/proy_heatmap_stock`) con usuario `appuser`.
- [ ] Podman + podman-compose instalados (alternativa: Docker 24+):
  ```bash
  podman --version && podman-compose version
  ```
- [ ] Rootless funcionando (el deploy no requiere root): verificar subuids del usuario:
  ```bash
  grep appuser /etc/subuid /etc/subgid    # debe mostrar p. ej. 100000:65536
  ```
- [ ] Red abierta hacia la BD: `192.168.18.121:5432` (o el host de `BD_HEATMAP_HOST`):
  ```bash
  timeout 3 bash -c 'cat < /dev/null > /dev/tcp/192.168.18.121/5432' && echo OK
  ```
- [ ] Puerto `8100` libre en el host: `ss -ltnp | grep 8100` (si systemd/nohup lo tiene ocupado, detenerlo antes).

### 2) Código y configuración

- [ ] Actualizar el repo en `<BASE>/proy_heatmap_stock` (o clonar si es la primera vez):
  ```bash
  cd /opt/proy_heatmap_stock && git pull
  ```
- [ ] Crear el `.env` del dashboard desde el ejemplo (NUNCA versionar):
  ```bash
  cd <BASE>/proy_heatmap_stock/proy_dashboard
  cp .env.example .env
  ```
- [ ] Editar `.env`: `BD_HEATMAP_HOST/PORT/DATABASE/USER/PASSWORD` reales, `APP_ENV=prod`,
  `APP_PORT=8100`, `APP_TIMEZONE` de visualización, `FILE_PATH_LOG=./logs`.
- [ ] Permisos estrictos al `.env` (contiene la clave de BD): `chmod 600 .env`.
- [ ] Confirmar que `config_dashboard.json` trae los parámetros de negocio deseados
  (pesos del score, zonas, `history_hours_default`, umbrales del watchdog).

### 3) Base de datos

- [ ] Verificar migraciones aplicadas (tablas del score existentes):
  ```sql
  SELECT table_name FROM information_schema.tables
  WHERE table_schema='public' AND table_name LIKE 'fact_market_score%';
  -- esperado: fact_market_score, fact_market_score_agg (+ particiones mensuales)
  ```
- [ ] Si faltan (deploy virgen): aplicar desde `proy_bd_heatmap`:
  ```bash
  cd <BASE>/proy_heatmap_stock/proy_bd_heatmap
  ./venv/bin/alembic upgrade head       # aplica 0009 y restantes
  ```
- [ ] Confirmar que el usuario de `BD_HEATMAP_USER` puede SELECT/INSERT sobre las tablas del score.

### 4) Opción A (recomendada): contenedor con Podman

- [ ] Construir la imagen (usa `Containerfile`; excludes de `.dockerignore` evitan hornear `.env`/`venv`/`logs`):
  ```bash
  cd <BASE>/proy_heatmap_stock/proy_dashboard
  podman build -t localhost/proy_dashboard:latest -f Containerfile .
  ```
- [ ] Levantar con compose (una imagen, un servicio `dashboard`; `DB_WRITE_ENABLED=false` explícito):
  ```bash
  podman-compose up -d --build
  ```
- [ ] Arranque automático tras reboot del host (podman socket systemd/user o quadlet):
  ```bash
  systemctl --user enable --now podman.socket   # si usas `podman compose` v2
  ```
- [ ] Comprobar salud del contenedor (`healthy` tarda ~10 s):
  ```bash
  podman ps --filter name=proy_dashboard
  podman inspect --format '{{.State.Health.Status}}' proy_dashboard   # → healthy
  curl -s http://localhost:8100/api/health | python3 -m json.tool
  ```

### 5) Opción B (alternativa): venv directo + systemd

- [ ] Crear venv e instalar dependencias:
  ```bash
  cd <BASE>/proy_heatmap_stock/proy_dashboard
  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
  ```
- [ ] Instalar el unit `/etc/systemd/system/proy_dashboard.service` (ver al final de esta sección)
  con `User=appuser`, `EnvironmentFile=<BASE>/proy_heatmap_stock/proy_dashboard/.env`.
- [ ] `sudo systemctl daemon-reload && sudo systemctl enable --now proy_dashboard`.
- [ ] `systemctl status proy_dashboard --no-pager` → `active (running)`.

### 6) Cron en el SERVIDOR (sigue igual con A o B)

- [ ] Entradas del score ya instaladas en el crontab de `appuser` (verificar con `crontab -l`):
  ```cron
  CRON_TZ=America/New_York
  # --- H · SCORE DASHBOARD (cada 3 min, +2 min del radar) ---
  3-59/3 0-23 * * 1-4 <BASE>/proy_heatmap_stock/proy_dashboard/run_persist_score.sh --cycle >> <BASE>/proy_heatmap_stock/proy_dashboard/logs/cron_persist_score.log 2>&1
  3-59/3 0-16 * * 5    <BASE>/proy_heatmap_stock/proy_dashboard/run_persist_score.sh --cycle >> <BASE>/proy_heatmap_stock/proy_dashboard/logs/cron_persist_score.log 2>&1
  # --- watchdog de frescura (cada 10 min) ---
  */10 * * * * <BASE>/proy_heatmap_stock/proy_dashboard/run_check_score_freshness.sh >> <BASE>/proy_heatmap_stock/proy_dashboard/logs/cron_check_score_freshness.log 2>&1
  ```
- [ ] **Importante:** el launcher `run_persist_score.sh` carga el **mismo `.env`** del paso 2;
  ahí `DB_WRITE_ENABLED` debe quedar en **`true`** (los crones escriben; el contenedor web no).
- [ ] Los cron jobs **usan el venv del host**, no el contenedor: si solo vas a contenedor y
  no quieres el venv, cambia el launcher por `podman run --rm --env-file .env proy_dashboard python jobs/persist_score.py --cycle`.
- [ ] El radar arranca en `1-59/3`; `3-59/3` corre ~2 min después, con `latest_market_tick` ya escrito.
- [ ] El job usa `flock` (`/tmp/proy_dashboard_persist_score.lock`) para evitar solapamientos.
- [ ] **Redirigir siempre la salida** (`>> ... 2>&1`): sin `MAILTO` ni redirección, cron descarta
  la salida y un fallo queda invisible.
- [ ] Prueba manual como usuario de cron (**nunca como root**):
  ```bash
  sudo -u appuser <BASE>/proy_heatmap_stock/proy_dashboard/run_persist_score.sh --cycle --dry-run
  sudo -u appuser <BASE>/proy_heatmap_stock/proy_dashboard/run_check_score_freshness.sh; echo $?  # 0 fresco · 5 rancio · 4 precondición local
  ```

### 7) Verificación final del deploy

- [ ] Dashboard visible: `http://<servidor>:8100/` (sin errores de consola en el navegador).
- [ ] `/api/health` → `status: OK` y `data.edad_s` < 240 (score fresco alimentado por el cron).
- [ ] Panel *Evolución del score* creciendo punto a punto cada 3 min (confirmado mirando `max(timestamp_utc)`).
- [ ] Logs del cron con entradas `escrito detalle=… agg=1` cada 3 min:
  ```bash
  tail -f <BASE>/proy_heatmap_stock/proy_dashboard/logs/cron_persist_score.log
  ```

### 8) Actualizar / rollback (Opción A)

```bash
cd <BASE>/proy_heatmap_stock/proy_dashboard
git pull
podman-compose up -d --build          # nueva imagen; el anterior se reemplaza
# rollback:
podman tag localhost/proy_dashboard:<versión-anterior> localhost/proy_dashboard:latest
podman-compose up -d
```

> El **cron no se toca** al actualizar la imagen: usa el código del host (venv). Si algún día
> el cron debe usar el código contenerizado, cambiar el launcher (paso 6).

<details>
<summary>Unit systemd de referencia (Opción B)</summary>

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

</details>

> Puerto **8100** separado: no interrumpe scraper, calendario ni notificador.

### Watchdog de frescura del score (cada 10 min)

> Detecta un `persist_score` caído en ~10 min en lugar de en horas. Fue el fallo
> real de producción: el score quedó 16 h sin actualizarse sin que nadie se enterara.

```cron
*/10 * * * * <BASE>/proy_dashboard/run_check_score_freshness.sh >> <BASE>/proy_dashboard/logs/cron_check_score_freshness.log 2>&1
```

- Entry point: `run_check_score_freshness.sh` → `jobs/check_score_freshness.py`.
- Umbral: `panels.score_max_age_min` en `config_dashboard.json` (default **20 min**);
  se puede forzar con `--max-edad-min N`.
- La tabla vacía (sin ningún ciclo) cuenta como rancio.
- **Códigos de salida:** `0` fresco · `1` error · `2` argumentos · `3` BD no configurada ·
  `4` precondición local (falta `.env`, falta `venv` o `logs/` no escribible) · `5` rancio.

Prueba manual (siempre como el usuario de cron, **nunca como root**):

```bash
sudo -u appuser <BASE>/proy_dashboard/run_check_score_freshness.sh
echo $?   # 0 si el score está fresco; 5 si lleva más de 20 min parado
```

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
├── Containerfile  imagen de producción (Podman/Docker, rootless, no-root, healthcheck)
├── compose.yml    servicio `dashboard` (web; los cron jobs siguen en el host)
├── .dockerignore  excluye .env/venv/logs de la imagen
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
