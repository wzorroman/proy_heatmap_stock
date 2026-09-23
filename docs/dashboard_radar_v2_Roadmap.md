# Roadmap Proyecto — Dashboard Radar Intermarket v2 (PostgreSQL)

> **Proyecto:** `proy_dashboard` — Dashboard de Contexto Intermarket (score 0–10, termómetro de riesgo, momentum, mapa sectorial, calendario con sorpresas, historial).
> **Versión destino:** 1.0.0
> **Base de datos fuente:** `heatmap_stock` (localhost:5432, PostgreSQL 15+)
> **Fecha del documento:** 2026-09-18
> **Stack propuesto:** Python 3.13 / FastAPI (monolítico moderno) + Jinja2 + HTMX + Plotly.js, repositorios PostgreSQL sin ORM.
> **Referencias:** `docs/scrapper_Roadmap_migracion_a_3-1-0.md` (radar/calendario v3.1.0), `docs/heatmap_stock_Roadmap_bd_2026-09-11.md` (esquema BD), `/home/wilson/CODE_MAIN/app_backup_nasdaq/dashboard/README.md` (proyecto a superar).
> **Estado:** Análisis validado contra BD (revisión 2026-09-18) — sin código aún.

---

## ✅ Resumen del análisis (datos reales verificados en BD, 2026-09-18)

| Métrica | Valor en `heatmap_stock` |
|---|---|
| Filas en `fact_market_series` | **2.427.921** (particionadas `2026_03`…`2026_12` + BRIN) |
| Rango temporal | **2026-03-17 → 2026-09-18** (radar/macro) · **2026-08-22 → hoy** (equity) |
| Activos (`dim_asset`) | **1.083** (equity 1.043, etf 13, forex 12, future 8, yield 2, commodity 2, crypto 2, index 1) |
| Activos con series (`fact_market_series`) | **110** (70 equity + 40 macro/etf/fx/fut) |
| Cadencia de ticks | ~**3 min** (NVDA; 8.441 ticks desde 22-ago) |
| `fact_heatmap_snapshot` | **3.000 en 3 ventanas** (13-sep, 2× 18-sep; ~1.000 activos c/u, cap, sector, logo) |
| `fact_economic_event` | **579 eventos YA cargados** (sorpresa computable en 253; importancia ≤1) |
| Vistas analíticas listas | `vw_market_live`, `vw_heatmap_enriched` · `vw_heatmap_event_impact` = **0 filas hoy** |

**Ejemplos reales extraídos (último tick por activo):**
- TOP momentum: `MSTR +15.06% (RSI 65.4, ADX 38.3)`, `MARA +12.93%`, `BTCUSD +6.19%`
- BOTTOM: `CL1! −6.28%`, `QCOM −5.16%`, `NFLX −4.38%`
- Radar riesgo: `VIX 15.00 (perf_w −14.3%)`, `US10Y 5.00 (+0.87%)`, `TLT 81.27 (−0.04%)`
- Heatmap última ventana: `MSTR +15.18% cap $58.5B`, `COIN +11.72%`, `OVCHF +11.32%`
- Sectores con más activos: Finance (324), Electronic Technology (109), Health Technology (79)

> ⚠️ **Hallazgo clave de esta revisión:** el universo **equity solo tiene series desde 2026-08-22**
> (~1 mes), mientras el **radar/macro tiene 6 meses** (2026-03-17). El retro-cómputo del score
> momentum queda limitado a 1 mes; solo el score radar es retro-computable completo.

---

## Tabla de Contenidos

1. [Propósito y Justificación](#1-propósito-y-justificación)
2. [Objetivos](#2-objetivos)
3. [Comparativa vs Proyecto de Referencia](#3-comparativa-vs-proyecto-de-referencia)
4. [Prerrequisitos / Deuda a Corregir](#4-prerrequisitos--deuda-a-corregir)
5. [Arquitectura (Monolítico Moderno en FastAPI)](#5-arquitectura-monolítico-moderno-en-fastapi)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [Diagramas ASCII de los Paneles](#7-diagramas-ascii-de-los-paneles)
8. [Motor de Score: Fórmulas y Calibración](#8-motor-de-score-fórmulas-y-calibración)
9. [Fases de Implementación](#9-fases-de-implementación)
10. [Riesgos y Mitigaciones](#10-riesgos-y-mitigaciones)
11. [Criterios de Aceptación](#11-criterios-de-aceptación)
12. [Decisión de Arquitectura (por qué FastAPI y no Django/Flask/Streamlit)](#12-decisión-de-arquitectura-por-qué-fastapi-y-no-django)
13. [Changelog](#13-changelog)

---

## 1. Propósito y Justificación

**Propósito:** construir el reemplazo del dashboard de contexto `app_backup_nasdaq/dashboard/` (puerto 8004, fuente CSV + SQLite) por un sistema que **lea directamente de PostgreSQL** y aproveche los **2.4 M de filas** ya capturadas por los scrapers V5 (radar 110 activos + calendario V4), elevando el score de mercado de "contexto en vivo" a "contexto **vivo + histórico retro-computado**".

**Justificación (por qué importa):**
1. **La referencia lee CSVs** (re-parseo con caché de 6 min) y guarda el score en **SQLite con retención de 48 h**. Nosotros ya tenemos la serie histórica en BD: podemos **calcular el radar desde 2026-03-17** y el **momentum desde 2026-08-22**, y calibrar umbrales con datos reales — no con parámetros ad-hoc.
2. **El calendario de la referencia usa placeholder "≈"** para preliminares; nuestro esquema `fact_economic_event` ya prevé `actual`/`forecast`/`previous` + unidad + importancia −1..3 → sorpresas **reales** (253 eventos con sorpresa computable ya en BD).
3. **El mapa sectorial** puede usar `fact_heatmap_snapshot` (1.005+ activos con cap/logo) en vez de derivarlo de 110 series. **Limitación:** solo existen 3 ventanas de snapshot (13-sep, 18-sep) → mapa solo "estado actual", sin rotación histórica por ahora.
4. Permite **backtestear** el score contra forward-return y decidir con evidencia las zonas COMPRAR/VENDER (hoy la referencia producía zona radar "siempre VENDER" por sesgo del blend).

**Relevancia:** es el panel de inteligencia de mercado del sistema. Alimenta a TradingView como "contexto", y su historial será la base para futuras señales/estrategias (no solo contexto).

---

## 2. Objetivos

| # | Objetivo | Medible |
|---|----------|---------|
| O1 | Dashboard en FastAPI puerto **8100**, independiente, sin interrumpir scraper/calendario | `curl /health` → JSON OK (data, score, events, heatmap) |
| O2 | Score 0–10 (momentum + 15-min + radar) retro-computado: **radar desde 2026-03-17, momentum desde 2026-08-22** | tabla `fact_market_score` particionada poblada con fechas reales de partida |
| O3 | Campos `fact_economic_event` poblados | **PARCIALMENTE CUMPLIDO**: 579 eventos cargados; 253 con sorpresa `actual` vs `forecast` |
| O4 | Paneles: header, mapa sectorial, termómetro riesgo, momentum, calendario, historial + **precio/indicadores por activo, distribución del score** | renders Plotly reales desde `/api/*` |
| O5 | Capas separadas: negocio en `services/`, datos en `repositories/`, UI en `web/` | tests por capa + import-cycle limpios |

---

## 3. Comparativa vs Proyecto de Referencia

| Aspecto | `app_backup_nasdaq/dashboard` (ref) | **v2 propuesto** | Ventaja |
|---|---|---|---|
| Fuente de datos | CSV re-parseados (caché 6 min) | PostgreSQL + vistas `vw_*` + BRIN | consultas SQL directas, sin cacheo manual |
| Histórico score | SQLite 48 h | `fact_market_score` particionado; radar 6 meses, momentum ~1 mes | backtest + calibración (con limitación equity) |
| Config | copia manual en `config.py` | única (BD + JSON en repo) | sin drift |
| Señal | sin clamp (>100 posible) | clamp + zonas calibradas | determinismo |
| Sesgo radar | zona siempre VENDER | recalibración con datos 6 meses | señales reales |
| Mapas sectoriales | derivado de 110 | `fact_heatmap_snapshot` + `vw_heatmap_enriched` | 1.005+ activos, cap/logo (solo última ventana) |
| Calendario | "≈" preliminares | actual/forecast/previous reales (579 eventos) | sorpresas reales |
| Precio/indicadores | RSI/ADX/CCI/BBPower/pivot + precio QQQ/SPY/ORO (SMA20/50) | **se incorporan como paneles extra** | mismo valor, sin re-parseo CSV |
| UI | Dash (Python render) | FastAPI + Plotly.js en navegador | gráficos vectoriales, endpoints reutilizables |

---

## 4. Prerrequisitos / Deuda a Corregir

Sin esto el dashboard muestra datos incompletos. **Fase 0 del proyecto.**

| # | Deuda | Estado hoy | Acción |
|---|-------|------------|--------|
| D1 | `fact_economic_event` vacía | ✅ **RESUELTA** (579 eventos cargados via `scripts/load_calendar_csv_to_db.py`) | mantener pipeline en vivo (`DB_WRITE_ENABLED=true`) |
| D2 | Cron apunta al repo viejo | `app_backup_nasdaq/` | apuntar jobs a `proy_scrapping_detail/` (V5) |
| D3 | Monitor V3 con path roto | alerta falsa del calendario | Monitor V4 BD-aware (diferido en v3.1.0) |
| D4 | `DB_WRITE_ENABLED` del calendario | ✅ **RESUELTA** (repositorio + configuración V5 OK) | verificar que el cron escriba en vivo |
| D5 | Partes del doc desactualizadas | `SCHEMA_heatmap_stock.md` etc. | actualizar tras deploy |
| **D6** | `fact_heatmap_snapshot` sin histórico | solo 3 ventanas (13-sep, 18-sep) | programar snapshot periódico del heatmap (cada 15 min) para acumular rotación sectorial |
| **D7** | `vw_heatmap_event_impact` vacía (0 filas) | exige USD + importancia 1–3 dentro de ±6h de un snapshot | crear `vw_heatmap_event_impact_relaxed` (sin filtro duro) o alimentar con D6 + eventos 2–3 |
| **D8** | Sin eventos importancia 2–3 | solo −1/0/1 en BD | filtrar calendario con importancia ≥1; documentar gap hasta que TradingView publique alto impacto |

> **Nota D1/D4:** la deuda original del roadmap quedó resuelta en la misma jornada (2026-09-18)
> al cargar los 579 eventos desde `DATOS_LIVE_CALENDARIO/calendario_economico`. La Fase 0 ahora
> se enfoca en D2/D3 (cron/monitor) y en las nuevas deudas D6–D8.

---

## 5. Arquitectura (Monolítico Moderno en FastAPI)

**Principio:** monolito en una sola app, pero con **capas estrictas** y **lógica de negocio sin HTML**:

> **Ubicación:** nuevo directorio `proy_dashboard/` dentro de `proy_heatmap_stock` (raíz del repo).
> Reutiliza el **patrón de conexión de `proy_heatmap`** (`db/postgresql_connection.py` +
> `config.py` leyendo env `BD_HEATMAP_*`), copiado/adaptado a su propia carpeta. Así hereda
> las mismas credenciales y convenciones sin acoplarse a los scrapers.

```
proy_dashboard/
├── core/                 settings, pool PostgreSQL (psycopg2), logging, timezone
├── domain/               dataclasses puras: Snapshot, Score, EventoEconomico, Activo
├── db/                   postgresql_connection.py (patrón copiado de proy_heatmap) + repos
├── repositories/         ÚNICA capa con SQL: series, assets, events, score, heatmap
├── services/             LÓGICA DE NEGOCIO:
│   ├── score_service.py        PASO 1/2/3 (momentum, 15min, radar)
│   ├── backfill_score_service.py  retro-cómputo radar(mar)/momentum(ago) vectorizado
│   ├── event_service.py        sorpresas actual/forecast, impacto ±6h
│   ├── heatmap_service.py      sectorial, ranking, termómetro
│   ├── indicator_service.py    RSI/ADX/CCI/BBPower/pivot por activo + precio SMA20/50
│   └── session_service.py      fases ADR-2, comparación sesiones
├── api/                  routers FastAPI: /api/score, /api/series, /api/heatmap,
│                         /api/events, /api/indicators, /api/health → JSON (Pydantic en borde)
├── web/                  Jinja2 templates + static/ (Plotly.js, Tailwind, HTMX)
├── tests/                pytest por capa + integración contra heatmap_stock
├── config_dashboard.json pesos/zonas/universe (fuente única)
└── pyproject.toml
```

```
  ┌────────────┐   ┌────────────────┐   ┌───────────────┐   ┌───────────────┐
  │ PostgreSQL │──▶│ repositories/  │──▶│ services/     │──▶│ api/(JSON)    │
  │ heatmap_   │   │ (solo SQL)     │   │ (negocio)     │   │ routers       │
  │ stock      │◀──│                │◀──│ (score engine)│   └──────┬────────┘
  └────────────┘   └────────────────┘   └───────────────┘          │
                                                            ┌──────▼────────┐
                                                            │ web/ Jinja2 + │
                                                            │ Plotly.js (UI)│
                                                            └───────────────┘
```

**Decisiones:**
- **Sin ORM**: repositorios con SQL directo sobre `psycopg2` (particiones, BRIN, `execute_values`, JSONB). Pydantic solo valida el borde API.
- **Frontend**: páginas Jinja2 que piden datos a `/api/*`; los paneles se dibujan con Plotly.js en el navegador. **El navegador jamás se entera de la lógica.**
- **Auto-refresh**: HTMX poll (15–30 s) o Server-Sent Events para cards vivas.

---

## 6. Modelo de Datos

### 6.1 Nueva tabla `fact_market_score` (particionada, mensual + BRIN)

```sql
CREATE TABLE fact_market_score (
    asset_id           INTEGER NOT NULL REFERENCES dim_asset(asset_id),
    timestamp_utc      TIMESTAMPTZ NOT NULL,
    score_general      NUMERIC(8,4),   -- PASO 1 por símbolo, [0,10]
    score_momentum     NUMERIC(8,4),   -- PASO 2 agregado equity
    score_15min        NUMERIC(8,4),   -- promedio últimos 5
    score_radar        NUMERIC(8,4),   -- PASO 3 blend intermarket
    zona               TEXT,           -- COMPRAR|NEUTRAL|VENDER
    n_simbolos         SMALLINT,
    source_checksum    CHAR(64),
    audit_id           BIGINT,
    PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);
-- + partición por mes y BRIN (mismo patrón que fact_market_series)
```

**Justificación:** persistir score por símbolo (no solo agregado) permite drill-down y backtest por activo. El agregado se deriva por vista.

> ⚠️ **Partida real del retro-backfill:** la serie equity empieza en **2026-08-22**, así que
> `fact_market_score` solo puede poblarse de esa fecha en adelante para el score por símbolo/momentum.
> El **radar** (componentes macro/etf/fx/fut) sí puede retro-computarse desde **2026-03-17**.
> El backfill debe procesar ambos rangos por separado.

### 6.2 Tablas existentes aprovechadas

| Tabla | Uso en dashboard |
|---|---|
| `fact_market_series` | series por activo (momentum, rsi, adx, cci20, bbpower, perf_w, change) |
| `fact_heatmap_snapshot` | mapa sectorial + ranking por capitalización (última ventana; histórico pendiente D6) |
| `fact_economic_event` | calendario + sorpresas (579 eventos cargados) |
| `dim_asset` | universo 1.083 + sector + logo |
| `vw_market_live`, `vw_heatmap_enriched` | consultas de presentación |
| `audit_sync_run` | salud del pipeline |

### 6.3 Nueva vista corregida `vw_heatmap_event_impact_relaxed`

La vista original `vw_heatmap_event_impact` exige `currency='USD'` + importancia 1–3 + evento a ±6h
de un snapshot → devuelve **0 filas** con los datos actuales. Se crea una versión relajada:

```sql
CREATE OR REPLACE VIEW vw_heatmap_event_impact_relaxed AS
SELECT h.asset_id, h.symbol, h.ticker, h.company_name, h.sector,
       h.timestamp_utc, h.price_heatmap, h.daily_change_pct, h.market_cap,
       h.market_direction, h.color_intensity, h.last_rsi,
       e.event_id, e.title, e.country, e.importance, e.category,
       e.event_timestamp, e.actual, e.forecast, e.previous, e.currency, e.unit,
       EXTRACT(EPOCH FROM (h.timestamp_utc - e.event_timestamp)) / 3600.0 AS hours_since_event
FROM vw_heatmap_enriched h
JOIN fact_economic_event e
  ON e.importance BETWEEN 1 AND 3
 AND e.event_timestamp BETWEEN (h.timestamp_utc - INTERVAL '6 hours')
                          AND (h.timestamp_utc + INTERVAL '6 hours');
-- sin filtro de moneda: el cruce de series con eventos es por ventana temporal.
```

> Aun así, seguirá vacía hasta que haya snapshots frecuentes (D6) y/o eventos de importancia 2–3 (D8).
> El panel de calendario funciona **directo desde `fact_economic_event`** sin depender de esta vista.

---

## 7. Diagramas ASCII de los Paneles

Cada panel incluye: figura ASCII, ejemplo con datos reales, propósito, importancia.

### 7.1 Header — Score de Mercado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ▶ MERCADO   Score Momentum 8.7 ▌▌▌▌▌▌▌▌▌   Zona: COMPRAR   Badge: ⚠️       │
│  ▶ 15 min     7.2  ▌▌▌▌▌▌▌▌     Radar: 5.1 ▌▌▌▌▌▌                          │
│  ▶ Aceleración +0.4   Fase: Sesión Madura (14:00–16:00 UTC)  Cobertura 96%  │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo esperado (con datos actuales):** los 110 activos con 8.441 ticks NVDA; score derivado de RSI/ADX/CCI20/BBPower/vol/change.
- **Propósito:** sentencia ejecutiva de "¿comprar/vender exposición?".
- **Importancia:** es la pieza que el trader consulta cada 15 min antes de operar. El badge ✅/⚠️/🔄 alerta divergencia entre momentum y 15-min.

### 7.2 Mapa Sectorial (heatmap)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Technology ████████████░░░░░░░░░░░░░░ (+)  Retail ██████░░░░░░░░░░░░ (+)   │
│  Financials ████████████░░░░░░░░░░░░░░ (+)  Health ████░░░░░░░░░░░░░░ (0)    │
│  Energy     ██░░░░░░░░░░░░░░░░░░░░░░░ (−)  Utility █░░░░░░░░░░░░░░░░ (−)    │
│  cada celda = activo, tamaño ∝ market_cap, color ∝ daily_change_pct         │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real tomado de BD:** `MSTR +15.18% cap $58.5B`, `COIN +11.72%`, `OVCHF +11.32%` (última ventana `fact_heatmap_snapshot`).
- **Propósito:** rotación sectorial de un vistazo.
- **Importancia:** los 1.005+ activos con sector y cap ya están en BD (Finance 324, Electronic Technology 109, Health Technology 79…).

### 7.3 Termómetro de Riesgo

```
┌────────────────────────────────────────────────────────────────────────────┐
│  VIX  █████████████████████░░░░░░░░░░ 15.00  (perf_w −14.3%, ⬇ riesgo)      │
│  US10Y ████████████████████████████░░ 5.00   (perf_w +0.87%, ⬈ presión)     │
│  DXY  ████████████████████████░░░░░░  xx.xx (—)                            │
│  TLT  ███████████████████░░░░░░░░░░░ 81.27  (perf_w −0.04%)                │
│  escala = percentil 60d del close (actual vs 60 días)                      │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** `TVC:VIX 15.00`, `TVC:US10Y 5.00`, `NASDAQ:TLT 81.27` (extraídos hoy).
- **Propósito:** riesgo de cola / flujo defensivo vs agresivo.
- **Importancia:** el dashboard v2 los calcula como percentil 60d *desde la BD*, sin el sesgo de direcciones fijas de la referencia.

### 7.4 Momentum Top/Bottom

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ▲ TOP          │  ▼ BOTTOM                                                 │
│  MSTR  +15.06%  │  CL1!  −6.28%   RSI 55.0                                 │
│  MARA  +12.93%  │  QCOM  −5.16%   RSI 55.3                                 │
│  BTCUSD +6.19%  │  NFLX  −4.38%   RSI 36.7                                 │
│  ... último tick por activo (change_pct + RSI + ADX como contexto)          │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** TOP `MSTR +15.06 (RSI 65.4, ADX 38.3)`, BOTTOM `CL1! −6.28 (RSI 55.0, ADX 32.0)`.
- **Propósito:** identificar los extremos de la sesión rápidamente.
- **Importancia:** filtro rápido para TradingView; con ADX evita perseguir ruido (MSTR tiene ADX 38 = tendencia fuerte).

### 7.5 Calendario de Alto Impacto con Sorpresas

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ⭐ NFP        US   actual 250K  forecast 240K   sorpresa +4.2%  ✓         │
│  ⭐ CPI        US   actual 3.1%   forecast 2.9%   sorpresa +6.9%  ✓         │
│  ⭐ GDP q/q    DE   actual 0.1%   forecast 0.3%   sorpresa −66%  ✗         │
│  filtros: país ▾  importancia ≥1 ▾     sorpresa = (actual−forecast)         │
│  gap: sin eventos 2–3 en BD aún (solo −1/0/1) → estrella única por ahora    │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Estado real:** 579 eventos cargados; **253 con `actual_raw`+`forecast_raw`** → sorpresa %
  computable. Todos de importancia **≤1** (0 eventos 2–3 hasta ahora en BD).
- **Propósito:** eventos que pueden mover el mercado en las próximas horas, con reacción real vs consenso.
- **Importancia:** lee directo de `fact_economic_event` (no de `vw_heatmap_event_impact`, hoy vacía).
  Reemplaza el placeholder "≈" de la referencia con sorpresas reales. Filtro inicial **importancia ≥1**.

### 7.6 Historial del Score (retro radar desde mar, momentum desde ago)

```
Score Momentum (0-10)
  9│        ▄▄▄   ▄█▄                              ╱▔▔▔
  6│  ▄▄▄▄▄▀   ▀▀   ▀▄▄     ▄▄▄▄▄▄▄▄▄           ╱    ▔▔▔▔▄
  4│▀▘                                ▀▄▄▄▄▄▄▄▄▄▘          ▀▄▄▄▄▄
  └────────────────────────────────────────────────────────▶
   Ago 2026 (momentum) · Mar 2026 (radar)         2026-09-18
   zonas ⬜ COMPRAR (6.5–10) ▓ NEUTRAL ░ VENDER (0–4.5)  ← calibrables
```

- **Propósito:** ver cómo se movió el "estado del mercado" y **backtestear** las zonas.
- **Importancia:** diferenciador #1 sobre la referencia (que borra todo >48 h). **Limitación real:**
  el momentum solo arranca en **ago-2026** (~1 mes); el radar tiene 6 meses (mar-2026). El backtest
  de zonas COMPRAR/VENDER debe hacerse por componente con su propia ventana.

### 7.7 Precio con Contexto — QQQ / SPY / ORO (SMA20/50)

Gráfico de precio de la sesión (o 48 h) con SMA20 y SMA50, para el trader que opera los índices
que se siguen (QQQ/SPY) y el oro como refugio. Muestra tendencia a corto plazo y punto de entrada
respecto a medias móviles.

```
QQQ  Última hora (SMA20/50)
  328│        ▁▃█▆▃▁
  327│   ▂▄█▇▅▃    ▂▄
  326│▂▃▇▅▂        ▁▃▅▇
      └───▶ Precio ── SMA20 ── SMA50   [ 09:30–14:25 UTC ]
  contexto: precio>SMA20>SMA50 → sesión alcista confirmada

SPY  (análogo)     XAUUSD  (análogo)
   ▅▃▁▂▄▆▇█▅▂▁▃▄▆    ▆▇█▅▂▁▄▆█▇▅▃▁▂▄
   precio<SMA20<SMA50 → a la baja   precio>SMA20≈SMA50 → lateral alcista
```

- **Datos:** `fact_market_series` → `close` para `NASDAQ:QQQ`, `AMEX:SPY`, `OANDA:XAUUSD`
  (SMAs calculadas en SQL `AVG OVER ORDER BY`).
- **Propósito:** tendencia intradía de los 3 referentes más operados.
- **Importancia:** contexto rápido de "dónde está el mercado" antes de operar; refuerza la lectura del header.

### 7.8 Indicadores por Activo — RSI / ADX / CCI20 / BBPower / Volumen / Pivot

Portadas de la referencia: barras por activo con umbrales, para no perseguir ruido y detectar
sobrecompra/sobreventa, tendencia, presión compradora y anomalías de volumen. Filtran sobre el
último tick de cada símbolo.

```
RSI (Top 15)                 ADX (Top 15)
  NVDA ████████████▌ 65.4      MSTR ██████████ 38.3  █ tendencia
  AAPL ████████████  62.8      MSFT ████████░░ 28.1  █
  ...  umbral ▐70 sob   30 sob  ...  umbral ▐25 ▏20

CCI20 (treemap)              BBPower (barras ±)
  🔴 >+100  🔵 neutral  🟢 <-100   🟢 compradores ← → 🔴 vendedores

Volumen vs media 2d          % distancia a Pivot R3
  QQQ ██████████▌ 168%         NVDA ██▌ +0.9%  ← ya pasó R3
  ...  umbral ▐100 ▏150 alto    ...  ██████▌ +3.2%  falta para R3
```

- **Datos:** `fact_market_series` → `rsi`, `adx`, `cci20`, `bbpower`, `volume`,
  `pivot_camarilla_r3` (media 2d de volumen por rolling en SQL).
- **Propósito:** diagnóstico por activo; ADX evita perseguir ruido (MSTR ADX 38 = tendencia fuerte).
- **Importancia:** complementa el momentum agregado con lectura fina de los líderes/rezagados.

### 7.9 Distribución del Score

Histograma del score momentum en las últimas 2 semanas con cuartiles, para saber si el valor actual
es normal, poco probable o extremo respecto al contexto reciente.

```
Distribución Score (2 semanas)
  frec│
      │        ▁▃▅█▇▅▃▂
      │  ▂▄▆█▇▅▃▂▁▁   ▁▂▃▅▆▇
      └────────────────────▶ Score
        │   │    │   │    │
        1   Q25  5   Q75  10
             ^ Score actual 7.2 → poco probable (arriba del Q75)
  Poco probable: 24% · Muy raro: 6%
```

- **Datos:** serie `score_momentum` de `fact_market_score` (o recomputada del último mes de series).
- **Propósito:** normalidad del contexto: el score actual dentro/fuera del rango usual.
- **Importancia:** evita sobre-reaccionar a un score alto/bajo que en realidad es normal en el contexto reciente.

---

## 8. Motor de Score: Fórmulas y Calibración

Basado en el de referencia (portado a BD), con mejoras:

- **PASO 1 — score por símbolo [0,10]** = Σ(pesoᵢ · normᵢ)/Σ(pesoᵢ) con renorm de NaN. Indicadores: rsi (0–100), adx (0–50), cci20 (−200..200), bbpower (−50..50), volume/vol_avg_2d (0–2), change (−5..5). Pesos 20/15/15/15/15/20.
- **PASO 2 — momentum** = Σ(peso_sym · score_sym)/Σ(peso_sym), solo equity.
- **PASO 2b — score 15-min** = promedio de los últimos 5 PASO-1 por símbolo → PASO 2.
- **PASO 3 — radar intermarket** = Σ(peso_radar · norm_dir)/Σ(peso_radar); norm_dir = p·10 o (1−p)·10 según dirección de VIX/TLT/DXY/US10Y.

**Mejoras sobre la referencia (para evitar sus bugs):**
1. `clamp` final de señal a [0,10] (la referencia podía mostrar >100).
2. Zonas calibradas con el histórico disponible: **radar mar→hoy**, **momentum ago→hoy** (la referencia usaba 6.5/4.5 fijos y arrojaba radar "siempre VENDER"). Calibrar por componente con su propia ventana.
3. Volumen medio 2d → rolling en BD (agregación por partición mensual, no CSV).
4. Dirección del radar derivada de la correlación 60d real (no dirección fija del config).

---

## 9. Fases de Implementación

| Fase | Entregable | Actividad clave |
|---|---|---|
| **0** | Deuda restante | D2/D3 (cron/monitor), D6 (snapshot periódico heatmap), D7 (vista relajada), D8 (documentar gap eventos 2–3) |
| **1** | Esqueleto FastAPI | `core`, `db`/`repositories` (series/assets/events/heatmap), `/api/health` |
| **2** | Score retro-backfill | `backfill_score_service` → `fact_market_score`: **radar desde mar-2026, momentum desde ago-2026** |
| **3** | Servicios | score_service, heatmap_service, event_service (sorpresas), indicator_service, session_service |
| **4** | Frontend | Jinja2 + Plotly.js: **9 paneles** con datos vía `/api/*`, HTMX refresh |
| **5** | Calibración | zonas/radar con forward-return por componente; ajustar `config_dashboard.json` |
| **6** | Calidad | tests por capa, cobertura, despliegue puerto 8100, docs |

---

## 10. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Eventos sin importancia 2–3 en BD | panel 7.5 con filtro importancia ≥1; monitorizar y documentar gap (D8) |
| Mapa sectorial sin histórico (3 snapshots) | D6: snapshot periódico del heatmap; mientras, mapa solo "última ventana" con banner |
| `vw_heatmap_event_impact` vacía | vista relajada 6.3 + panel de calendario directo desde `fact_economic_event` |
| Retro-backfill 2.4 M filas → muchas particiones | procesar por mes en lotes, índice BRIN ya presente, `execute_values` |
| Momentum equity solo desde ago | calibrar por componente; radar 6 meses, momentum 1 mes (documentado) |
| Sesgo/datos sucios en histórico | calibración validada contra forward-return, no por inspección |
| Streamlit existente duplica paneles | decidir coexistencia o absorción (recomendado: reutilizar endpoints) |
| Config duplicada (universo 110/1.005) | fuente única en `config_dashboard.json` + seed de apoyo |

---

## 11. Criterios de Aceptación

1. `/health` OK con data, score, events, heatmap independientes (degradación sin crash).
2. `fact_market_score` poblada retro: **radar desde 2026-03-17, momentum desde 2026-08-22**, particiones mensuales + BRIN.
3. `fact_economic_event` con eventos y sorpresa calculada (579 cargados; ≥1 filtro panel).
4. Todos los paneles renderizan datos REALES de BD (no mock), incluidos los 3 extra (precio/indicadores/distribución).
5. Score clamp [0,10]; zonas documentadas y calibradas por componente con su ventana real.
6. Test suite por capa verde; imports sin ciclos.

---

## 12. Decisión de Arquitectura (por qué FastAPI y no Django/Flask/Streamlit)

| Opción | Veredicto |
|---|---|
| **FastAPI (elegido)** | Monolítico moderno, async, tipado con Pydantic en el borde, alto rendimiento para `/api/*` y SSE/HTMX. Capas estrictas. |
| Django | Más pesado para esto; ORM y admin que no necesitamos; sobre-procesamiento. |
| Flask | Válido pero sin tipado/OpenAPI nativo; reinventa validación. |
| Streamlit | Rápido para prototipos pero mezcla lógica y UI (contra el requisito de separar negocio/frontend) y no publica APIs reutilizables. |
| Dash (ref) | Igual a Streamlit + peso alto de callbacks; no da endpoints JSON limpios. |

**Justificación de "monolítico":** una sola app desplegable (`uvicorn proy_dashboard:app`) que sirve API + web; sube la complejidad solo donde aporta (capas, no microservicios).

---

## 13. Changelog

- **2026-09-18 (revisión)** — Análisis validado contra BD real: 579 eventos cargados (D1/D4 resueltas), retro limitado a ago para momentum, snapshots delgados (D6), vista evento-impacto relajada (D7), gap eventos 2–3 (D8). Añadidos 3 paneles extra con ASCII (precio SMA20/50, indicadores por activo, distribución del score). Objetivos, fases, riesgos y criterios actualizados.
- **2026-09-18** — Creación del roadmap con análisis de datos reales de `heatmap_stock` (2.427.921 series, 3.000 snapshots, 0 eventos), propuesta arquitectura FastAPI, 6 paneles con figuras ASCII y ejemplos de BD, fases y criterios. Solo propuesta — sin código aún.