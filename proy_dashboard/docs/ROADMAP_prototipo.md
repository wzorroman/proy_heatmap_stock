# ROADMAP — Prototipo Dashboard `proy_dashboard` (v1.2)

> **Proyecto:** `proy_heatmap_stock/proy_dashboard`
> **Propósito:** prototipo de dashboard general que lee **directo de PostgreSQL `heatmap_stock`**
> (sin CSV), inspirado en `app_backup_nasdaq/dashboard` pero con arquitectura desacoplada.
> **Stack:** FastAPI + Jinja2 + HTMX + **Apache ECharts** · PostgreSQL (psycopg2, sin ORM) · puerto **8100**.
> **Cambios de BD:** TODOS vía Alembic en `proy_heatmap_stock/proy_bd_heatmap` (revisión **`0009`**).
> **Librerías:** **todas vendorizadas en local** (`web/static/vendor/`), **sin CDN**, offline.
> **Logging / Versionado / Entorno:** patrón `proy_heatmap/utils/config_logging.py`, `VERSION` +
> `/api/version`, `venv` local y variables `.env` (ver §7).
> **Cron del score:** cada **3 min** (mismo carril que el radar V5).
> **Estado:** Fases 0–8 implementadas y verificadas (2026-09-30) — 74 tests verdes en
> `proy_dashboard` + 25 en `proy_bd_heatmap`; migración `0009` aplicada en la BD viva.
> **Referencias:** `docs/dashboard_radar_v2_Roadmap.md`, `proy_bd_heatmap/README.md`,
> `docs/automatizacion_cronjobs.md`, `proy_heatmap/utils/config_logging.py`,
> `/home/wilson/CODE_MAIN/app_backup_nasdaq/dashboard`.

---

## 0. Decisiones cerradas (fuente única de verdad)

| # | Decisión | Valor adoptado | Motivo |
|---|---|---|---|
| **D1** | Fuente de datos | PostgreSQL `heatmap_stock` vía `psycopg2` (sin CSV, sin ORM) | Datos vivos; particiones/BRIN |
| **D2** | Backend | **FastAPI + uvicorn** (:8100) | Roadmap v2; API JSON reutilizable |
| **D3** | Render | **Jinja2** (server-side) + **HTMX** (fragmentos) | Separación presentación; poco JS |
| **D4** | Librería de gráficos | **Apache ECharts 6.1.0** (Apache-2.0) | Código libre; Canvas aguanta el treemap ~1.009 celdas |
| **D5** | Librerías | **Vendorizadas en local**, sin CDN (offline) | Reproducible; "correr todo desde local" |
| **D6** | HTMX | **2.0.11** (0BSD), local | Refresco por fragmentos |
| **D7** | CSS/Fuentes | `app.css` propio + *system font stack* (sin Tailwind ni fuentes descargadas) | Sin build, 100% local |
| **D8** | Score | **Split**: `fact_market_score` (por activo) + `fact_market_score_agg` (mercado) | Sin redundancia; re-agregable |
| **D9** | Migraciones | **Alembic** en `proy_bd_heatmap`, revisión **`0009`** | Fuente única del esquema |
| **D10** | Cron score | cada **3 min**, offset `3-59/3` (≈+2 min del radar) | Alineado al radar V5 |
| **D11** | Alcance | Paneles **factibles + placeholders** honestos | Sin inventar datos |
| **D12** | Capas | `repositories`(SQL) → `services`(negocio) → `api`/`web`(presentación) | Clean code, sin fugas |
| **D13** | Config | `config_dashboard.json` + `.env`; **cero números mágicos** | Recalibración sin tocar código |
| **D14** | Python offline (opcional) | `wheelhouse/` con `pip download` | Instalación sin red |
| **D15** | Uso | Interno/estudiantil, no comercial | Sin riesgo de licencia |
| **D16** | Logging | `core/logging_config.py` **copia del patrón** `proy_heatmap/utils/config_logging.py`: logger `app`, rotación diaria (`TimedRotatingFileHandler`, 14 días), `namer` a `YYYY-MM-DD_app_history_{APP_NAME}_{RETRANSMISOR_ID}.log`, consola+archivo, `get_logger(name)` | Trazabilidad y continuidad con el ecosistema |
| **D17** | Versionamiento | `VERSION` en `core/settings.py` + `__version__` en `proy_dashboard/__init__.py`; `/api/version`; versión en log de arranque; bump por fase | Saber qué versión corre |
| **D18** | Entorno virtual | `venv/` propio en `proy_dashboard/` + launchers `run_dashboard.sh` / `run_persist_score.sh` con carga de `.env` | Reproducible, aislado |
| **D19** | Variables `.env` | Infra y secretos (BD, puerto, TZ, logs, retransmisor) en `.env`; negocio (pesos/zonas/umbrales) en `config_dashboard.json` | Sin hardcode, sin duplicar |

---

## 1. Resumen ejecutivo del entorno (2026-09-30)

| Hecho clave | Implicación |
|---|---|
| La BD se reinició con Alembic; `fact_market_series` tiene ~1.5 días | Sin SMA20/50, percentil 60d, performance semanal, backtest largo |
| `fact_heatmap_snapshot`: 30 ventanas, ~1.009 activos, con vol/volatilidad/52w | Treemap y sectorial son el panel más fuerte |
| `latest_market_tick`: 1 fila/activo con RSI 1D + bloque 15m | Motor de score y momentum sin escanear series |
| `fact_market_indicator_tf`: `tf`=5 y 15 | Multi-TF y score 15min |
| `fact_economic_event`: 235 eventos, 15 con sorpresa | Calendario con sorpresas reales |
| `dim_asset` es **Tipo 1** (sin `current_version`) | **NUNCA** filtrar por `current_version`/`valid_from`/`valid_to` |
| Símbolos canónicos de riesgo por `logical_key`: VIX, US10Y, DXY, TLT | Resolver con `is_canonical`; fallback `role='fallback'` (UUP→DXY) |

---

## 2. Objetivo y alcance

**Objetivo:** dashboard de **contexto de mercado** (no de ejecución) en `:8100`, con capas estrictas y
100% configurable, que **persista el score de mercado** para habilitar backtest futuro.

**Dentro (Fase de prototipo):** header/score, treemap sectorial, ranking/rotación sectorial, momentum
top/bottom, indicadores (RSI/ADX/CCI20/BBPower), anomalía de volumen, rango 52s, distribuciones,
termómetro de riesgo, calendario con sorpresas, multi-TF 5m/15m, health, evolución del score.

**Fuera (placeholders):** SMA20/50, percentil 60d, performance semanal, distribución histórica/backtest
largo, rotación multi-día.

---

## 3. Principios de diseño (clean code, sin sobre-ingeniería)

1. **Capas estrictas:** `repositories` solo SQL · `services` solo negocio (sin SQL/HTML/HTTP) ·
   `api` routers finos · `web` plantillas sin BD.
2. **Servicios reutilizables e inyectados por constructor** (DI manual en `core/container.py`).
   El mismo `score_service` lo usan el job y la API.
3. **Cero números mágicos:** todo en `config_dashboard.json` + `.env`.
4. **Sin ORM** (psycopg2 + SQL explícito).
5. **Degradación suave:** falta de datos → "sin datos", nunca crash.

> Regla de revisión: si una plantilla contiene una query, o un router una regla de negocio, es defecto.

---

## 4. Stack y dependencias

### 4.1 Backend (Python)
`fastapi`, `uvicorn[standard]`, `jinja2`, `psycopg2-binary`, `python-dotenv`, `pydantic`,
`pytest`, `httpx` (TestClient). Todas en `requirements.txt`; entorno en `proy_dashboard/venv`.

### 4.2 Frontend (vendorizado, local, sin CDN)

| Librería | Versión | Licencia | Archivo | Uso |
|---|---|---|---|---|
| **Apache ECharts** | 6.1.0 | Apache-2.0 | `dist/echarts.min.js` | Todos los gráficos |
| **HTMX** | 2.0.11 | 0BSD | `dist/htmx.min.js` | Refresco por fragmentos |
| CSS/fuentes | — | — | `app.css` + system fonts | Sin build, sin CDN |

> ECharts incluye el tema **`dark`** incorporado (`echarts.init(el, 'dark')`); no requiere archivo extra.
> **Plotly.js queda descartado** (reemplazado por ECharts).

### 4.3 Logging, versionamiento y entorno
- **Logging:** `core/logging_config.py` (réplica del patrón `proy_heatmap/utils/config_logging.py`).
- **Versionamiento:** `VERSION` (settings) + `__version__` (paquete) + `/api/version`.
- **Entorno:** `venv/` local + launchers `.sh` que cargan `.env`.
- **Configuración:** `.env` (infra/secretos) + `config_dashboard.json` (negocio). Ver §7.

---

## 5. Librerías locales (offline) — vendorizado

### 5.1 Estructura
```
proy_dashboard/web/static/
├── vendor/
│   ├── VERSIONS.md                          # lib, versión, URL, licencia, fecha, sha256
│   ├── echarts/6.1.0/{echarts.min.js, LICENSE, NOTICE}
│   └── htmx/2.0.11/{htmx.min.js, LICENSE}
├── app.css                                  # tema oscuro propio
└── app.js                                   # renderChart(el,data,theme) + re-init htmx:afterSwap
```

### 5.2 Pasos de descarga (una vez, Fase 0)
```bash
BASE=proy_dashboard/web/static/vendor
mkdir -p $BASE/echarts/6.1.0 $BASE/htmx/2.0.11

# ECharts 6.1.0 (Apache-2.0)
curl -L https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js \
  -o $BASE/echarts/6.1.0/echarts.min.js
curl -L https://raw.githubusercontent.com/apache/echarts/6.1.0/LICENSE -o $BASE/echarts/6.1.0/LICENSE
curl -L https://raw.githubusercontent.com/apache/echarts/6.1.0/NOTICE  -o $BASE/echarts/6.1.0/NOTICE

# HTMX 2.0.11 (0BSD)
curl -L https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/dist/htmx.min.js \
  -o $BASE/htmx/2.0.11/htmx.min.js
curl -L https://raw.githubusercontent.com/bigskysoftware/htmx/v2.0.11/LICENSE \
  -o $BASE/htmx/2.0.11/LICENSE

# Registrar versión + hash
sha256sum $BASE/echarts/6.1.0/echarts.min.js $BASE/htmx/2.0.11/htmx.min.js > $BASE/VERSIONS.md.sha
```

### 5.3 Verificación "cero CDN"
```bash
grep -rn "http[s]*://" proy_dashboard/web/templates proy_dashboard/web/static/app.* \
  || echo "OK: sin CDN en código propio"
```

### 5.4 (Opcional) Python offline
```bash
pip download -r proy_dashboard/requirements.txt -d proy_dashboard/wheelhouse/
pip install --no-index --find-links proy_dashboard/wheelhouse -r proy_dashboard/requirements.txt
```
> La BD sigue en `192.168.18.121` (LAN); no se cambia.

---

## 6. Estructura del proyecto

```
proy_dashboard/
├── __init__.py                  # __version__ = VERSION
├── config_dashboard.json        # ← ÚNICA fuente de parámetros de negocio
├── .env.example                 # plantilla de variables de entorno (ver §7)
├── .gitignore                   # venv/, .env, logs/, wheelhouse/, __pycache__/
├── requirements.txt
├── pyproject.toml               # [project] version = VERSION
├── run_dashboard.sh             # launcher: carga .env + venv + uvicorn :8100
├── run_persist_score.sh         # launcher del job (cron H)
├── README.md
├── ROADMAP_prototipo.md         # este documento
├── core/
│   ├── settings.py              # .env + config_dashboard.json → dataclass Settings (+ VERSION)
│   ├── container.py             # DI: repos+services+app
│   ├── timezone.py              # UTC ↔ America/New_York (fases)
│   └── logging_config.py        # patrón proy_heatmap/utils/config_logging.py (ver §7.3)
├── domain/                      # dataclasses puras
│   ├── score.py                 # ScoreActivo, ScoreMercado, ComponenteScore
│   ├── market.py                # ActivoTick, SectorSnapshot, RiesgoItem
│   └── event.py                 # EventoEconomico
├── db/
│   └── postgresql_connection.py # patrón copiado de proy_heatmap/db/
├── repositories/                # SOLO SQL
│   ├── base.py
│   ├── score_repo.py
│   ├── latest_tick_repo.py
│   ├── heatmap_repo.py
│   ├── events_repo.py
│   ├── series_repo.py
│   └── session_repo.py
├── services/                    # LÓGICA DE NEGOCIO
│   ├── score_service.py
│   ├── momentum_service.py
│   ├── heatmap_service.py
│   ├── indicator_service.py
│   ├── event_service.py
│   ├── session_service.py
│   └── health_service.py
├── jobs/
│   └── persist_score.py         # --cycle | --backfill | --since | --until | --dry-run
├── api/
│   ├── schemas.py               # Pydantic (borde)
│   └── routers/{health,score,heatmap,momentum,indicators,events,risk}.py
├── web/
│   ├── app.py                   # FastAPI: api/ + jinja2 + static + páginas/partials
│   ├── templates/{base.html, dashboard.html, partials/*.html}
│   └── static/{vendor/, app.css, app.js}
├── tests/
│   ├── conftest.py
│   ├── test_settings.py
│   ├── test_score_service.py
│   ├── test_repositories.py
│   ├── test_persist_score.py
│   └── test_api.py
├── logs/                        # gitignored
└── venv/                        # gitignored
```

---

## 7. Configuración: `.env`, `config_dashboard.json`, logging, versionado y venv

> **Precedencia (D19):** `.env` = infra/secretos; `config_dashboard.json` = negocio. La unión se
> expone en `core/settings.Settings`; el código **solo** lee de ahí.

### 7.1 Variables `.env` (infra/secretos) — plantilla `.env.example`
```dotenv
# --- PostgreSQL (heatmap_stock) ---
BD_HEATMAP_HOST=192.168.18.121
BD_HEATMAP_PORT=5432
BD_HEATMAP_DATABASE=heatmap_stock
BD_HEATMAP_USER=postgres
BD_HEATMAP_PASSWORD=cambiar

# --- Aplicación ---
APP_NAME=proy_dashboard
APP_ENV=dev
APP_PORT=8100
APP_TIMEZONE=America/New_York

# --- Logging (patrón proy_heatmap/utils/config_logging.py) ---
FILE_PATH_LOG=./logs
RETRANSMISOR_ID=101
LOG_LEVEL=INFO
LOG_BACKUP_DAYS=14

# --- Job / escritura ---
DB_WRITE_ENABLED=true

# --- (opcional) instalación offline ---
# WHEELHOUSE=./wheelhouse
```

| Variable | Default | Uso |
|---|---|---|
| `BD_HEATMAP_HOST` | — | Host PostgreSQL (`heatmap_stock`) |
| `BD_HEATMAP_PORT` | `5432` | Puerto |
| `BD_HEATMAP_DATABASE` | `heatmap_stock` | Base de datos |
| `BD_HEATMAP_USER` | `postgres` | Usuario |
| `BD_HEATMAP_PASSWORD` | — | Secreto (gitignored) |
| `APP_NAME` | `proy_dashboard` | Nombre en logs/versionado |
| `APP_ENV` | `dev` | `dev`/`prod` (controla `uvicorn --reload`) |
| `APP_PORT` | `8100` | Puerto uvicorn |
| `APP_TIMEZONE` | `America/New_York` | Fases/sesión |
| `FILE_PATH_LOG` | `./logs` | Carpeta de logs (patrón proy_heatmap) |
| `RETRANSMISOR_ID` | `101` | Sufijo de archivos de log |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `LOG_BACKUP_DAYS` | `14` | Retención de logs rotados |
| `DB_WRITE_ENABLED` | `true` | El job persiste score |
| `WHEELHOUSE` | `./wheelhouse` | (opcional) pip offline |

> El `.env` real está **gitignored**; se versiona solo `.env.example`.

### 7.2 `config_dashboard.json` (negocio)
```json
{
  "app": {
    "title": "Radar Intermarket — Prototipo BD",
    "htmx_refresh_ms": 30000,
    "stale_warn_min": 10
  },
  "data": {
    "min_history_days": 2,
    "placeholder_msg": "Histórico insuficiente (<2 días). Se habilitará al acumular la serie."
  },
  "panels": { "top_n": 15, "treemap_max": 1000, "sector_min_assets": 5, "history_hours_default": 24 },
  "score": {
    "weights": { "rsi": 20, "adx": 15, "cci20": 15, "bbpower": 15, "volume": 15, "change": 20 },
    "normalization": {
      "rsi":          { "min": 0,    "max": 100 },
      "adx":          { "min": 0,    "max": 50  },
      "cci20":        { "min": -200, "max": 200 },
      "bbpower":      { "min": -50,  "max": 50  },
      "volume_ratio": { "min": 0,    "max": 2   },
      "change_pct":   { "min": -5,   "max": 5   }
    },
    "clamp": { "min": 0, "max": 10 },
    "zones": { "comprar": 6.5, "vender": 4.5 },
    "momentum": { "asset_classes": ["equity", "etf"], "weight_mode": "equal" },
    "score_15min": { "tf": "15", "last_n": 5 },
    "radar": {
      "components": [
        { "logical_key": "VIX",   "weight": 30, "direction": "inverse" },
        { "logical_key": "US10Y", "weight": 25, "direction": "inverse" },
        { "logical_key": "DXY",   "weight": 25, "direction": "inverse" },
        { "logical_key": "TLT",   "weight": 20, "direction": "direct"  }
      ],
      "normalization": "rsi",
      "note": "direct: mayor valor => más alcista. inverse: mayor valor => más bajista."
    }
  },
  "events": { "importance_min": 0, "default_country": "ALL", "lookback_hours": 24, "lookahead_hours": 72 }
}
```

**`score.radar.normalization="rsi"`** (provisional): sin percentil 60d, `p = rsi/100`;
`norm_dir = p*10` si `direct`, `(1-p)*10` si `inverse`. Documentarlo en el panel.

### 7.3 Logging (`core/logging_config.py`) — réplica de `proy_heatmap/utils/config_logging.py`
Mismo comportamiento que el ecosistema; única adaptación: lee de `core.settings` en vez de `config`.

- **Directorio:** `FILE_PATH_LOG` (default `./logs`), `os.makedirs(exist_ok=True)`.
- **Logger raíz de app:** `logging.getLogger('app')`, nivel `LOG_LEVEL`, `propagate=False`, limpia handlers.
- **Formato:** `%(asctime)s - [%(name)s:%(lineno)s] - %(levelname)s - %(message)s`.
- **Archivo con rotación diaria:** `TimedRotatingFileHandler(when='midnight', interval=1,
  backupCount=LOG_BACKUP_DAYS, encoding='utf-8')` sobre `app_daily_{APP_NAME}_{RETRANSMISOR_ID}.log`.
- **`namer` personalizado** → los rotados pasan a `YYYY-MM-DD_app_history_{APP_NAME}_{RETRANSMISOR_ID}.log`.
- **Consola:** `StreamHandler(sys.stdout)`.
- **Arranque:** loguea `=== INICIO DE APLICACIÓN (v{VERSION}) ===` y la ruta del log.
- **API:** `get_logger(name) -> logging.getLogger(f'app.{name}')`.
- **Idempotencia:** `setup_global_logging()` limpia handlers antes de añadirlos (seguro ante re-import),
  idóneo para uvicorn de un solo proceso.

Esqueleto:
```python
# core/logging_config.py  (réplica de proy_heatmap/utils/config_logging.py)
import os, sys, logging
from logging.handlers import TimedRotatingFileHandler
from core.settings import FILE_PATH_LOG, RETRANSMISOR_ID, APP_NAME, LOG_LEVEL, LOG_BACKUP_DAYS, VERSION

def setup_global_logging():
    log_dir = FILE_PATH_LOG or os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "logs")
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False
    if logger.handlers: logger.handlers.clear()

    fmt = logging.Formatter('%(asctime)s - [%(name)s:%(lineno)s] - %(levelname)s - %(message)s')
    path = os.path.join(log_dir, f"app_daily_{APP_NAME}_{RETRANSMISOR_ID}.log")
    daily = TimedRotatingFileHandler(path, when='midnight', interval=1,
                                     backupCount=LOG_BACKUP_DAYS, encoding='utf-8')
    def history_namer(default_name):                      # -> YYYY-MM-DD_app_history_...log
        base = os.path.basename(default_name); d = os.path.dirname(default_name)
        if ".log." in base:
            _, date_part = base.split(".log.", 1)
            return os.path.join(d, f"{date_part}_app_history_{APP_NAME}_{RETRANSMISOR_ID}.log")
        return default_name
    daily.namer = history_namer
    daily.setFormatter(fmt)

    console = logging.StreamHandler(sys.stdout); console.setFormatter(fmt)
    logger.addHandler(daily); logger.addHandler(console)
    logger.info(f"=== INICIO DE APLICACIÓN (v{VERSION}) ===")
    logger.info(f"Logging configurado en: {path}")
    return logger, path

app_logger, LOG_FILE = setup_global_logging()

def get_logger(name):
    return logging.getLogger(f"app.{name}")
```

### 7.4 Versionado (D17)
- `VERSION = "0.1.0"` en `core/settings.py`; reexportado como `proy_dashboard.__version__`.
- `pyproject.toml` → `[project] version = "0.1.0"` (misma fuente conceptual).
- Endpoint `GET /api/version` → `{"app": APP_NAME, "version": VERSION, "env": APP_ENV}`.
- El log de arranque incluye la versión (heredado del patrón).
- **Regla:** subir `VERSION` al cerrar cada fase; registrar en el Changelog (§21).

### 7.5 Entorno virtual (`venv`) (D18)
```bash
cd proy_dashboard
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
# offline: ./venv/bin/pip install --no-index --find-links ./wheelhouse -r requirements.txt
```
Launchers (carga de `.env`, estilo `run_heatmap.sh`):
```bash
# run_dashboard.sh
set -a; . ./.env; set +a
exec ./venv/bin/uvicorn web.app:app --host 0.0.0.0 --port "${APP_PORT:-8100}"
```
`run_persist_score.sh` análogo, terminando en `./venv/bin/python jobs/persist_score.py --cycle`.
`.gitignore`: `venv/`, `.env`, `logs/`, `wheelhouse/`, `__pycache__/`, `*.pyc`.

---

## 8. Modelo de datos — Migración `0009` (en `proy_bd_heatmap`)

> Ruta: `proy_bd_heatmap/alembic/versions/0009_fact_market_score_2026_09_30.py`
> `revision="0009"`, `down_revision="0008"`. Estilo idéntico a `0003` (helper de particiones + BRIN).

```sql
-- Detalle por activo/ciclo (particionada mensual UTC 2026_09..2027_12 + BRIN)
CREATE TABLE public.fact_market_score (
    asset_id      integer      NOT NULL,
    timestamp_utc timestamptz  NOT NULL,
    score_general numeric(8,4),
    zona          text,
    componentes   jsonb,
    ingested_at   timestamptz  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fact_market_score_pkey PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

-- Mercado por ciclo (1 fila, no particionada, BRIN)
CREATE TABLE public.fact_market_score_agg (
    timestamp_utc   timestamptz  NOT NULL,
    score_momentum  numeric(8,4),
    score_15min     numeric(8,4),
    score_radar     numeric(8,4),
    score_market    numeric(8,4),
    zona            text,
    n_simbolos      smallint,
    source_checksum varchar(64),
    audit_id        bigint,
    ingested_at     timestamptz  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fact_market_score_agg_pkey PRIMARY KEY (timestamp_utc)
);
CREATE INDEX fact_market_score_agg_ts_brin ON public.fact_market_score_agg USING brin (timestamp_utc);

CREATE VIEW public.vw_market_score_history AS
  SELECT * FROM public.fact_market_score_agg ORDER BY timestamp_utc;
CREATE VIEW public.vw_market_score_latest AS
  SELECT * FROM public.fact_market_score_agg ORDER BY timestamp_utc DESC LIMIT 1;
```

`downgrade()`: `DROP VIEW ...` ×2, `DROP TABLE fact_market_score_agg CASCADE`,
`DROP TABLE fact_market_score CASCADE`. `COMMENT ON` en tablas/columnas. Helper `_particiones()` y
`_brin()` en loop (no escribir 16 bloques a mano).

### 8.1 Por qué `fact_market_score_agg` separada (decisión D8)
- **Sin redundancia:** la tabla única repetiría los 3 agregados en ~123 filas/ciclo (≈59k filas/día).
- **Integridad atómica:** el agregado no queda parcial si el ciclo muere.
- **Lectura O(1):** header/evolución leen 1 fila/ciclo.
- **Semántica:** el mercado deja de "ser" una fila de activo.
- **Recalibración:** el detalle por activo permite re-agregar con nuevos pesos sin re-scrapear.

---

## 9. Dominio (`domain/`) — dataclasses puras

```python
# score.py
ComponenteScore(nombre, valor, norm, peso)
ScoreActivo(asset_id, symbol, score_general, zona, componentes)
ScoreMercado(timestamp_utc, score_momentum, score_15min, score_radar, score_market,
             zona, n_simbolos, pesos, zonas)   # pesos/zonas = snapshot de config usada

# market.py
ActivoTick(asset_id, symbol, asset_class, close, change_pct, volume, rsi,
           rsi_15, cci20_15, bbpower_15, adx_15, pivot_r3_15, timestamp_utc)
SectorSnapshot(sector, n_activos, change_medio, market_cap_total, ganadores, perdedores)
RiesgoItem(logical_key, symbol, valor, change_pct, rsi, norm_dir, estado)

# event.py
EventoEconomico(event_id, title, country, categoria, importance, event_timestamp,
                actual, forecast, previous, sorpresa_pct, pasado)
```

---

## 10. Repositorios (`repositories/`) — solo SQL

`base.py`: helper `RealDictCursor` (`fetch_all`/`execute`). Todos reciben `PostgreSQLConnector`.
**Regla:** `dim_asset` es Tipo 1 → unir por `asset_id`, **no** filtrar `current_version`.
Canónicos por `logical_key` + `is_canonical` + `role`.

| Repo | Métodos | SQL clave |
|---|---|---|
| `latest_tick_repo` | `fetch_all()`, `fetch_by_asset_classes(classes)`, `fetch_by_logical_keys(keys)` | `... FROM latest_market_tick l JOIN dim_asset a USING(asset_id)` |
| `score_repo` | `upsert_detalle(rows)`, `upsert_agg(row)`, `fetch_agg_latest()`, `fetch_agg_history(since,until)`, `fetch_detalle(since)` | `INSERT ... ON CONFLICT ... DO UPDATE` con `execute_values` |
| `heatmap_repo` | `fetch_latest()`, `fetch_windows(n)`, `sectores()`, `rotacion()`, `rangos_52w()` | última ventana: `timestamp_utc = (SELECT max(...))` |
| `events_repo` | `fetch_eventos(country, importance_min, since, until)` | `event_timestamp BETWEEN` |
| `series_repo` | `fetch_serie(symbol, since)`, `distinct_timestamps(since,until)`, `fetch_tf(tf, since)` | ticks / backfill |
| `session_repo` | `estado_sesion(now)` | `dim_trading_session` |

**SQL de referencia:**
- Treemap: `price_heatmap, daily_change_pct, market_cap, sector, volatility_d, high_52w, low_52w`
  (última ventana, `ORDER BY market_cap DESC LIMIT panels.treemap_max`).
- Sectorial: `GROUP BY a.sector` → `n_activos, avg(daily_change_pct)`.
- Rotación: `avg(daily_change_pct)` por cada una de las `heatmap_windows` ventanas.
- Volumen: `h.volume / NULLIF(h.avg_vol_10d,0)`.
- Rango 52s: `(price_heatmap - low_52w) / NULLIF(high_52w - low_52w,0)`.

---

## 11. Servicios (`services/`) — negocio puro

Todos reciben repos + config por constructor. **No** SQL, **no** HTML.

### 11.1 `score_service`
```python
normalizar(nombre, valor, cfg) -> float | None
score_activo(tick, vol_ratio) -> ScoreActivo
score_momentum(scores) -> float | None
score_15min(tf, last_n) -> float | None
score_radar() -> (float | None, list[RiesgoItem])
calcular_ciclo(ts=None) -> (list[ScoreActivo], ScoreMercado)
zona(score) -> str
```
- **PASO 1**: `score = Σ(peso*norm)/Σ(peso)` (renorm NaN), clamp `[0,10]`.
  `rsi`←`tick.rsi`; `adx`←`adx_15`; `cci20`←`cci20_15`; `bbpower`←`bbpower_15`;
  `change`←`change_pct`; `volume`←`volume/avg_vol_10d` (si no, NaN).
- **PASO 2**: media de `score_general` sobre `asset_class in momentum.asset_classes` (`equal`).
- **PASO 2b**: por activo media de últimos `last_n` de `indicator_tf(tf)`, luego agregado.
- **PASO 3**: por componente resuelto por `logical_key` (preferir `is_canonical`, fallback
  `role='fallback'`), `p=rsi/100`, `norm_dir` según `direction`; media ponderada.
- `score_market` = media ponderada momentum/radar (default 50/50; documentar).
- Guardar `pesos`/`zonas` usados en `ScoreMercado` (recalibración futura).

### 11.2 Resto
- `momentum_service.top_bottom(n)` · `heatmap_service.{treemap,sectores,rotacion}()`
- `indicator_service.por_indicador(nombre, tf, n)` · `indicator_service.histograma(nombre, tf, bins)`
  (binning en servicio: ECharts no tiene tipo histograma nativo)
- `event_service.{proximos(filtros),sorpresas()}` (sorpresa = `(actual-forecast)/forecast*100`)
- `session_service.fase(now)` · `health_service.check()`

---

## 12. Job de persistencia y cron

`jobs/persist_score.py` (usa `core/container.py`, **sin** FastAPI/Jinja2):
- `--cycle` (default): `ts = último ciclo`; `calcular_ciclo(ts)`; `upsert_detalle` + `upsert_agg`;
  opcional `audit_sync_run` (`script_name='dashboard_score'`).
- `--backfill --since <ISO> [--until]`: recorre `distinct_timestamps`; idempotente (`ON CONFLICT`).
- `--dry-run`: no escribe.
- `fcntl.flock` no bloqueante en `/tmp/proy_dashboard_persist_score.lock`.
- Logs en `logs/persist_score_*.log`. Exit 0 OK / ≠0 error.

### 12.1 Cron (servidor TZ ET; `<BASE>` = raíz del monorepo)
```cron
# --- H · SCORE DASHBOARD (+2 min del radar, cada 3 min) ---
3-59/3 0-23 * * 1-4 cd <BASE>/proy_dashboard && set -a && . ./.env && set +a && ./venv/bin/python jobs/persist_score.py --cycle
3-59/3 0-16 * * 5    cd <BASE>/proy_dashboard && set -a && . ./.env && set +a && ./venv/bin/python jobs/persist_score.py --cycle
```
> Documentar esta entrada (sección H) en `docs/automatizacion_cronjobs.md`.

---

## 13. API JSON (`api/`) — routers finos

Salida con `api/schemas.py` (Pydantic). Degradación: 200 con `{"estado":"WARN","detalle":...}`.

| Método | Ruta | Servicio |
|---|---|---|
| GET | `/api/health` | `health_service.check` (nunca 500) |
| GET | `/api/version` | `{app, version, env}` desde `core.settings` |
| GET | `/api/score/latest` | `score_service.calcular_ciclo` |
| GET | `/api/score/history?hours=` | `score_repo.fetch_agg_history` |
| GET | `/api/momentum/top?n=` | `momentum_service` |
| GET | `/api/heatmap/treemap` | `heatmap_service` |
| GET | `/api/heatmap/sectors` | `heatmap_service` |
| GET | `/api/heatmap/rotation` | `heatmap_service` |
| GET | `/api/indicators?ind=&tf=&n=` | `indicator_service` |
| GET | `/api/risk` | `score_service.score_radar` |
| GET | `/api/events?country=&importance=&hours=` | `event_service` |
| GET | `/api/assets/{symbol}/series?hours=` | `series_repo` |

---

## 14. Web (`web/`) — Jinja2 + HTMX + ECharts

- `app.py`: `FastAPI()`; `Jinja2Templates("web/templates")`; `StaticFiles("/static", "web/static")`;
  monta routers; dependencias desde `core/container.py`.
- **Carga local (sin CDN)** en `base.html`:
  ```html
  <link rel="stylesheet" href="/static/app.css">
  <script src="/static/vendor/echarts/6.1.0/echarts.min.js"></script>
  <script src="/static/vendor/htmx/2.0.11/htmx.min.js"></script>
  <script src="/static/app.js"></script>
  ```
- **`app.js`**: helper `renderChart(elId, option, theme='dark')`; re-init en `htmx:afterSwap`
  (ECharts no se auto-monta tras un swap); destruir instancias previas para evitar fugas.
- Página `GET /` → `dashboard.html` (extends `base.html`) + partials iniciales.
- Fragmentos HTMX (`hx-trigger="every {htmx_refresh_ms}ms"`):
  `/partials/{header,treemap,sectors,momentum,indicators,volume,range52w,distributions,risk,calendar,multiframe,score_history}`.
- `partials/placeholder.html` recibe `{titulo, motivo}` con `data.placeholder_msg`.
- **Sin lógica de negocio en JS**: las plantillas inyectan `option` JSON; `app.js` solo dibuja.

---

## 15. Paneles

| # | Panel | Fuente | ECharts | Estado |
|---|---|---|---|---|
| 1 | Header/score/zona/cobertura/fase | score/session/latest_tick | `gauge` | ✅ real |
| 2 | Treemap sectorial | snapshot última ventana | `treemap` | ✅ real |
| 3 | Ranking + rotación sectorial | snapshot N ventanas | `bar`/`line` | ✅ real |
| 4 | Momentum top/bottom | `latest_market_tick` | `bar` | ✅ real |
| 5 | Indicadores RSI/ADX/CCI/BBPower | latest_tick / indicator_tf | `bar` | ✅ real |
| 6 | Anomalía de volumen | snapshot `volume/avg_vol_10d` | `bar` | ✅ real |
| 7 | Rango 52s | snapshot `high_52w/low_52w` | `bar` | ✅ real |
| 8 | Distribuciones (change/RSI/cap) | snapshot + latest_tick | `bar` (binning servicio) | ✅ real |
| 9 | Termómetro de riesgo | `score_radar` | `gauge`/`radar` | ✅ real (sin p60d) |
| 10 | Calendario con sorpresas | `fact_economic_event` | `heatmap`/tabla | ✅ real |
| 11 | Multi-TF 5m vs 15m | `fact_market_indicator_tf` | `heatmap` | ✅ real |
| 12 | Health/frescura | `audit_sync_run` | tabla | ✅ real |
| 13 | Evolución del score | `fact_market_score_agg` | `line` | ✅ real (crece con el job) |
| 14 | SMA20/50 de precio | `fact_market_series` | `line` | ⏳ placeholder |
| 15 | Percentil 60d riesgo | `fact_market_series` | `line` | ⏳ placeholder |
| 16 | Performance semanal | `fact_market_series` | `bar` | ⏳ placeholder |
| 17 | Distribución histórica/backtest | `fact_market_score` | `boxPlot` | ⏳ placeholder |

---

## 16. Tests

| Archivo | Tipo | Qué valida |
|---|---|---|
| `test_settings.py` | unit | `.env` + `config_dashboard.json`; defaults |
| `test_score_service.py` | unit (repos fake) | normalización, renorm NaN, clamp, zonas, momentum, radar direct/inverse |
| `test_repositories.py` | integración (marcado, read-only) | queries devuelven columnas/conteos |
| `test_persist_score.py` | integración | `--dry-run` no escribe; `--cycle` idempotente |
| `test_api.py` | TestClient | `/api/health` 200; endpoints degradan sin crash |
| `proy_bd_heatmap/tests/test_migraciones.py` | Alembic | `0009` upgrade/downgrade; tablas/particiones/BRIN/vistas |

---

## 17. FASES DE IMPLEMENTACIÓN

> Cada fase es autocontenida y verificable. Orden estricto: no avanzar sin cumplir el **DoD**.

### Estado de ejecución (2026-09-30)

| Fase | Estado | Nota |
|---|---|---|
| 0 — Esqueleto, librerías, logging, entorno | ✅ completada | 14 tests |
| 1 — Migración `0009` | ✅ completada | aplicada en BD viva; 25 tests de migraciones |
| 2 — Núcleo y dominio | ✅ completada | 15 tests |
| 3 — Repositorios | ✅ completada | 6 tests (degradación + integración) |
| 4 — Motor de score + job | ✅ completada | 18 tests; backfill por **bucket de 30 min** (ver §21) |
| 5 — Servicios restantes | ✅ completada | 12 tests |
| 6 — API JSON | ✅ completada | 8 tests |
| 7 — Web (Jinja2 + HTMX + ECharts) | ✅ completada | 5 tests; 13 paneles + 4 placeholders |
| 8 — Calidad, deploy y docs | ✅ completada | README con cron H; verificación sin CDN; suites verdes |

### FASE 0 — Preparación del proyecto, librerías locales, logging y entorno
**Objetivo:** esqueleto ejecutable con librerías vendorizadas, logging, versionado, venv y `/api/health`.
**Entregables:** estructura §6; `requirements.txt`; `.env.example` + `.gitignore`; `core/settings.py`; `core/logging_config.py`; `web/static/vendor/**`; `app.css`; `app.js`; `web/app.py`; `run_dashboard.sh`; `README.md`.
**Tareas:**
1. Crear carpetas + `__init__.py` con `__version__`.
2. Descargar y vendorizar ECharts 6.1.0 y HTMX 2.0.11 (§5.2); crear `vendor/VERSIONS.md` con
   versión, URL, licencia, fecha y `sha256`.
3. `.env.example` con todas las variables de §7.1 y `.gitignore` (`venv/`, `.env`, `logs/`, `wheelhouse/`).
4. `core/settings.py`: dataclass `Settings` desde `.env` + `config_dashboard.json`; `VERSION` (§7.4).
5. `core/logging_config.py`: réplica de `proy_heatmap/utils/config_logging.py` (§7.3) con
   `setup_global_logging()` y `get_logger(name)`.
6. Escribir `app.css` (tema oscuro) y `app.js` (`renderChart` + re-init `htmx:afterSwap`).
7. `db/postgresql_connection.py` (copiar/adaptar de `proy_heatmap/db/`).
8. `web/app.py`: FastAPI + `/api/health` + `/api/version` + plantilla mínima que carga las libs locales
   (inicializa el logging al arrancar).
9. `requirements.txt`; crear `venv` (o `wheelhouse/` si offline); launcher `run_dashboard.sh`; `README.md`.
**Comandos:**
```bash
cd proy_dashboard && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env      # editar BD_HEATMAP_*
./run_dashboard.sh        # o: ./venv/bin/uvicorn web.app:app --port 8100
```
**DoD:** `:8100` responde; `/api/health` y `/api/version` JSON; se crea `logs/app_daily_proy_dashboard_<ID>.log`
con la línea de inicio y versión; `grep` de §5.3 sin CDN; assets locales cargan (200); `venv` aislado.

### FASE 1 — Migración `0009` (en `proy_bd_heatmap`)
**Objetivo:** esquema del score creado y reversible.
**Entregables:** `alembic/versions/0009_fact_market_score_2026_09_30.py`; tests de migración.
**Tareas:**
1. Crear la revisión (helper `_particiones()`/`_brin()`, `2026_09…2027_12`).
2. DDL de `fact_market_score` + `fact_market_score_agg` + 2 vistas + comentarios; `downgrade()`.
3. Extender `tests/test_migraciones.py` (existencia de tablas/particiones/BRIN/vistas).
**Comandos:**
```bash
cd proy_bd_heatmap
./venv/bin/alembic upgrade head
./venv/bin/alembic downgrade 0008 && ./venv/bin/alembic upgrade head
./venv/bin/python -m pytest tests -q
```
**DoD:** `alembic current` = `0009`; upgrade/downgrade verdes; tablas y vistas visibles.

### FASE 2 — Núcleo y dominio
**Objetivo:** DI, config, timezone y dataclasses listos.
**Entregables:** `core/container.py`, `core/timezone.py`, `domain/*.py`.
**Tareas:** implementar `Settings`, `Container` (construye repos+services), utilidades TZ, dataclasses §9;
usar `get_logger(__name__)` en cada módulo (patrón §7.3).
**DoD:** `test_settings.py` verde; `Container` instancia sin error con BD accesible; los logs de cada
módulo salen por el logger `app`.

### FASE 3 — Repositorios
**Objetivo:** acceso a datos completo (solo SQL).
**Entregables:** `repositories/{base,score_repo,latest_tick_repo,heatmap_repo,events_repo,series_repo,session_repo}.py`.
**Tareas:** implementar métodos §10 y SQL de referencia; sin filtros por `current_version`.
**DoD:** `test_repositories.py` (read-only) devuelve datos reales de las tablas del §1.

### FASE 4 — Motor de score + job + cron
**Objetivo:** score calculado y persistido cada 3 min.
**Entregables:** `services/score_service.py`, `jobs/persist_score.py`, entrada cron H,
`tests/test_score_service.py`, `tests/test_persist_score.py`.
**Tareas:**
1. `score_service` (PASO 1/2/2b/3) con config inyectada (§11.1).
2. `persist_score.py` (`--cycle/--backfill/--dry-run`, lock, logs).
3. Backfill de los ~1.5 días disponibles; verificar idempotencia.
4. Añadir entrada cron H a `docs/automatizacion_cronjobs.md`.
**Comandos:**
```bash
./venv/bin/python jobs/persist_score.py --backfill --since 2026-09-29T00:00:00Z
./venv/bin/python jobs/persist_score.py --cycle
```
**DoD:** `fact_market_score(_agg)` pobladas; re-run no duplica; tests unit verdes.

### FASE 5 — Servicios restantes
**Objetivo:** servicios de momentum, heatmap, indicadores, eventos, sesión y health.
**Entregables:** `services/{momentum,heatmap,indicator,event,session,health}_service.py`.
**Tareas:** implementar §11.2 incl. `indicator_service.histograma` (binning).
**DoD:** cada servicio devuelve view models con datos reales; tests unit básicos.

### FASE 6 — API JSON
**Objetivo:** endpoints §13.
**Entregables:** `api/schemas.py`, `api/routers/*.py`, `tests/test_api.py`.
**Tareas:** routers finos que delegan en servicios; degradación sin crash.
**DoD:** todos los endpoints 200; `/api/health` OK; tests verdes.

### FASE 7 — Web (Jinja2 + HTMX + ECharts)
**Objetivo:** dashboard con los 17 paneles.
**Entregables:** `web/templates/{base,dashboard}.html`, `partials/*.html`, endpoints de partial, `app.js`.
**Tareas:**
1. `base.html` con carga local de libs + `app.css` + `htmx:afterSwap` handler.
2. Partials de los 13 paneles reales + 4 placeholders.
3. Endpoints de partial que construyen view models vía servicios (sin lógica en plantilla).
**DoD:** página carga, refresca por HTMX y muestra datos reales; placeholders honestos.

### FASE 8 — Calidad, deploy y docs
**Objetivo:** cierre del prototipo.
**Entregables:** suite completa verde (ambos proyectos), `README.md`, deploy :8100, cron instalado.
**Tareas:** tests por capa; verificación sin CDN; documentar operación (`uvicorn`, backfill, cron).
**DoD:** cumple §18.

---

## 18. Criterios de aceptación

1. `/api/health` OK con módulos independientes (degradación sin crash).
2. `0009` upgrade/downgrade verdes; ambas tablas pobladas por el job.
3. Paneles con datos reales; placeholders honestos donde falte histórico.
4. Score clamp `[0,10]`; **cero números mágicos** (todo en `config_dashboard.json`).
5. **Sin CDN**: todas las librerías servidas desde `web/static/vendor/` (§5.3).
6. Capas sin fugas: `services` sin SQL/HTTP, `repositories` sin negocio, templates sin BD.
7. Tests por capa verdes; sin ciclos de import.
8. Cron cada 3 min operativo; `latest_market_tick` fresco en el header.
9. **Logging** activo: archivo diario `logs/app_daily_{APP_NAME}_{RETRANSMISOR_ID}.log` con formato
   `asctime - [name:lineno] - level - message` y rotación a `YYYY-MM-DD_app_history_{APP_NAME}_{RETRANSMISOR_ID}.log`.
10. **Versionado:** `/api/version` responde y el log de arranque muestra la versión; `VERSION` sube por fase.
11. **venv** local funcional y `.env` fuera de control de versiones (solo `.env.example`).

---

## 19. Comandos de operación (referencia rápida)

```bash
# Setup
cd proy_dashboard && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env      # editar BD_HEATMAP_*

# Migración (una vez, en proy_bd_heatmap)
cd ../proy_bd_heatmap && ./venv/bin/alembic upgrade head

# Backfill inicial del score
cd ../proy_dashboard && ./venv/bin/python jobs/persist_score.py --backfill --since 2026-09-29T00:00:00Z

# Arranque
./run_dashboard.sh        # carga .env + venv + uvicorn :${APP_PORT:-8100}
#   Dashboard: http://localhost:8100
#   Health:    http://localhost:8100/api/health
#   Version:   http://localhost:8100/api/version
#   Logs:      ./logs/app_daily_proy_dashboard_${RETRANSMISOR_ID}.log
```

---

## 20. Riesgos y notas

| Riesgo | Mitigación |
|---|---|
| Historia <2 días (sin SMA/percentiles) | Placeholders honestos; el job acumula desde hoy |
| Zonas/pesos provisionales | Snapshot de config en cada fila (`pesos`/`zonas`) |
| `TVC:DXY` (canónico) puede no tener tick | Resolver por `logical_key` con fallback `role='fallback'` (UUP) |
| `asset_class` con `equity` y `common` | No asumir; filtrar por lo que declare config |
| ECharts no tiene histograma nativo | Binning en `indicator_service` |
| Treemap ~1.009 celdas | ECharts Canvas (elegido por esto) |
| `fact_market_score_agg` sin particionar | 1 fila/ciclo (~480/día); BRIN basta |
| Radar con dirección fija | Provisional hasta tener 60d para correlación real |
| HTMX swap rompe gráficos | `renderChart` re-inicializa en `htmx:afterSwap` |
| Logging duplicado con varios workers uvicorn | `setup_global_logging()` limpia handlers; dev con 1 worker |
| Crecimiento de logs | Rotación diaria + `LOG_BACKUP_DAYS` (14) |

---

## 21. Changelog

- **2026-09-30 (v1.3)** — **Implementación completa de Fases 0–8.** Migración `0009`
  aplicada en la BD viva. Job `persist_score` operativo (ciclo + backfill). Hallazgo: el
  radar escribe en **sub-lotes (~15 símbolos/ciclo)**, por lo que el backfill agrupa por
  **bucket de 30 min** (`data.backfill_bucket_min`) tomando el último valor por activo →
  universo completo por ciclo histórico. Cron documentado en `README.md` (entrada H), no
  instalado (sin acceso al servidor). Suites: 74 + 25 tests verdes; verificación sin CDN.
- **2026-09-30 (v1.2)** — Añadido **logging** réplica de `proy_heatmap/utils/config_logging.py`
  (rotación diaria, `namer`, consola+archivo, `get_logger`), **versionamiento** (`VERSION`,
  `__version__`, `/api/version`, bump por fase), **venv** local + launchers, y **variables `.env`**
  completas (§7.1). Decisiones D16–D19; §7 reestructurada (§7.1–7.5); Fase 0 y criterios actualizados.
- **2026-09-30 (v1.1)** — Decisión **Apache ECharts 6.1.0** (reemplaza Plotly.js); **todas las
  librerías vendorizadas en local** (sin CDN, offline); CSS propio (sin Tailwind). Añadida Fase 0 de
  vendorizado y §5; roadmap reorganizado por fases con todas las decisiones (D1–D15).
- **2026-09-30 (v1.0)** — Creación. Split `fact_market_score`/`_agg`; Jinja2+HTMX; cron 3 min;
  cambios de BD vía `proy_bd_heatmap` (migración `0009`).
