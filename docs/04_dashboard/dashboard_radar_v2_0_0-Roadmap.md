# Roadmap Proyecto — Dashboard Radar Intermarket v2/v1.1.0 (PostgreSQL)

> **Proyecto:** `proy_dashboard` — Dashboard de Contexto Intermarket + Oportunidades 5–15 min  
> **Versión destino:** 1.1.0  
> **Base de datos fuente:** `heatmap_stock` (`192.168.18.121:5432`, PostgreSQL 17+)  
> **Fecha del documento:** 2026-10-07  
> **Stack real:** Python 3.13 / FastAPI + Jinja2 + HTMX + Apache ECharts, repositorios PostgreSQL sin ORM.  
> **Referencias:** `docs/scrapper_Roadmap_migracion_a_3-1-0.md`, `docs/heatmap_stock_Roadmap_bd_2026-09-11.md`, `proy_dashboard/docs/informe_graficos_2026-09-30.md`, `proy_dashboard/CHANGELOG.md`.  
> **Estado:** v1.0.0 implementado y operativo en puerto 8100. v1.1.0 en diseño — paneles de oportunidad 5–15 min validados contra BD real.

---

## ✅ Resumen del análisis (datos reales verificados en BD, 2026-10-07)

| Métrica | Valor en `heatmap_stock` |
|---|---|
| Filas en `fact_market_series` | **139.872** (particionadas `2026_03`…`2026_12` + BRIN; último tick 2026-10-07 18:35 UTC) |
| Filas en `fact_market_bar_15m` | **28.653** (123 símbolos; pipeline reactivado) |
| Filas en `fact_market_indicator_tf` | **259.364** (`tf` 5 y 15, 112 símbolos) |
| Activos en `latest_market_tick` | **123** (70 equity + 25 ETF + 12 forex + 9 future + 2 yield + 2 commodity + 2 crypto + 1 index) |
| `fact_heatmap_snapshot` | **190.000** filas · 19 sectores · última ventana 2026-10-07 18:30 UTC |
| `fact_economic_event` | **351 eventos** · 29 con `actual` + `forecast` |
| `fact_market_score` / `fact_market_score_agg` | **235.692** detalles / **1.932** agregados · score_market actual **4.25** · zona **VENDER** |
| Vistas analíticas | `vw_market_live`, `vw_heatmap_enriched`, `vw_market_score_history`, `vw_market_score_latest` |

**Ejemplos reales extraídos (último tick por activo, 2026-10-07):**
- TOP momentum día: `SPOT +5.25%`, `MU +4.00%`, `SMCI +3.18%`
- BOTTOM día: `MSTR −6.33%`, `MARA −6.25%`, `TER −5.06%`
- Tendencias fuertes (ADX 15m > 25): `MSTR ADX 46.1`, `MARA ADX 44.7`, `V ADX 42.0`, `NVDA ADX 37.0`
- Sobreventa fuerte 15m: `DDOG RSI 31.9 / CCI −193.5 / BBPower −2.46`
- Rupturas máx/min del día anterior: `AAPL`, `ADSK`, `AMZN`, `COST` rompieron máximo; `ARM`, `ASML`, `DDOG`, `MARA` rompieron mínimo

> ⚠️ **Hallazgo clave de esta revisión:** el dashboard v1.0.0 ya está operativo y fresco (score cada ~3 min). El salto a v1.1.0 no requiere más datos: requiere **combinar mejor los datos que ya existen** para descubrir oportunidades de trading 5–15 minutos.

---

## Tabla de Contenidos

1. [Propósito y Justificación](#1-propósito-y-justificación)
2. [Objetivos](#2-objetivos)
3. [Comparativa vs Proyecto de Referencia](#3-comparativa-vs-proyecto-de-referencia)
4. [Prerrequisitos / Deuda a Corregir](#4-prerrequisitos--deuda-a-corregir)
5. [Arquitectura (Monolítico Moderno en FastAPI)](#5-arquitectura-monolítico-moderno-en-fastapi)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [Diagramas ASCII de los Paneles](#7-diagramas-ascii-de-los-paneles)
8. [Nuevos Paneles de Oportunidad 5–15 min (v1.1.0)](#8-nuevos-paneles-de-oportunidad-5--15-min-v110)
9. [Motor de Score: Fórmulas y Calibración](#9-motor-de-score-fórmulas-y-calibración)
10. [Fases de Implementación](#10-fases-de-implementación)
11. [Riesgos y Mitigaciones](#11-riesgos-y-mitigaciones)
12. [Criterios de Aceptación](#12-criterios-de-aceptación)
13. [Decisión de Arquitectura](#13-decisión-de-arquitectura)
14. [Decisión de diseño — K1 · Reversión Bollinger 15m (dot-plot σ)](#14-decisión-de-diseño--k1--reversión-bollinger-15m-dot-plot-σ)
15. [Changelog](#15-changelog)

---

## 1. Propósito y Justificación

**Propósito:** construir el reemplazo del dashboard de contexto `app_backup_nasdaq/dashboard/` por un sistema que **lea directamente de PostgreSQL** y que, además del contexto macro/sectorial, entregue **paneles de oportunidad de trading intradía 5–15 minutos** basados en datos reales y combinaciones de indicadores.

**Justificación:**
1. La v1.0.0 ya demostró que el stack funciona: FastAPI + Jinja2 + HTMX + ECharts, lectura directa de `heatmap_stock`, score de mercado cada 3 minutos.
2. Los datos para operar 5–15 min ya están en BD: barras 15m, indicadores tf 5m/15m, último tick, rango inicial, VWAP, Bollinger.
3. El screener 15m existente emite señales, pero no destaca las de **mayor convicción** (confluencia + volumen + ruptura de estructura).
4. La v1.1.0 se enfoca en **acelerar el descubrimiento** de activos que merecen revisión profunda antes de operar.

**Relevancia:** el dashboard pasa de ser un "parte meteorológico" del mercado a una herramienta de **decisión operativa** para acciones.

---

## 2. Objetivos

| # | Objetivo | Medible |
|---|---|---|
| O1 | Dashboard v1.0.0 operativo en puerto **8100** | `/api/health` → OK; score fresco (< 10 min) |
| O2 | Score 0–10 persistido en `fact_market_score` / `_agg` | ~1.932 ciclos acumulados, particiones mensuales + BRIN |
| O3 | Paneles de contexto v1.0.0 renderizando datos reales | header, sectorial, momentum, calendario, health, evolución del score |
| **O4** | **Nuevos paneles de oportunidad 5–15 min en v1.1.0** | 8 paneles listados en §8, todos con datos reales de BD |
| **O5** | **Filtros de calidad sobre el screener 15m** | volumen relativo, confluencia multi-timeframe, ruptura de estructura |
| O6 | Capas separadas: negocio en `services/`, datos en `repositories/`, UI en `web/` | tests por capa + import-cycle limpios |

---

## 3. Comparativa vs Proyecto de Referencia

| Aspecto | `app_backup_nasdaq/dashboard` (ref) | **v2 / v1.1.0 propuesto** | Ventaja |
|---|---|---|---|
| Fuente de datos | CSV re-parseados | PostgreSQL + vistas `vw_*` + BRIN | consultas directas, sin cacheo manual |
| Histórico score | SQLite 48 h | `fact_market_score` particionado | backtest + calibración |
| Librería gráfica | Plotly.js | Apache ECharts 6.1.0 vendorizado | sin CDN, mejor rendimiento con miles de celdas |
| Screener intradía | no tenía | screener 15m + oportunidades 5–15m | decisión operativa, no solo contexto |
| Confluencia multi-TF | no tenía | 5m/15m/1D + volumen | filtra falsas entradas |
| Config | copia manual | `config_dashboard.json` + `.env` | fuente única, sin drift |
| UI | Dash | FastAPI + Jinja2 + HTMX + ECharts | endpoints JSON reutilizables, capas limpias |

---

## 4. Prerrequisitos / Deuda a Corregir

| # | Deuda | Estado hoy | Acción |
|---|---|---|---|
| D1 | `fact_economic_event` vacía | ✅ **RESUELTA** (351 eventos cargados) | mantener pipeline en vivo |
| D2 | Barras 15m desactualizadas | ✅ **RESUELTA** (pipeline reactivado; última barra 18:30 UTC) | monitorear con health |
| D3 | Score sin auditoría explícita | 🟡 **PENDIENTE** | registrar `persist_score` en `audit_sync_run` |
| D4 | `fact_heatmap_snapshot` sin histórico profundo | 🟡 **MEJORADO** (190k filas, ~8 días) | suficiente para mapa sectorial actual |
| D5 | Placeholders históricos | ⏳ **BLOQUEADO** por historia (< 60 días) | desbloquear automáticamente al acumular |

---

## 5. Arquitectura (Monolítico Moderno en FastAPI)

**Principio:** monolito con **capas estrictas** y **lógica de negocio sin HTML**:

```
proy_dashboard/
├── core/                 settings, logging, timezone, container DI
├── domain/               dataclasses puras
├── db/                   conector PostgreSQL (psycopg2)
├── repositories/         ÚNICA capa con SQL
├── services/             LÓGICA DE NEGOCIO:
│   ├── score_service.py        motor de score
│   ├── momentum_service.py     top/bottom, change vs rsi
│   ├── heatmap_service.py      sectorial, volumen, rango 52s
│   ├── indicator_service.py    RSI/ADX/CCI/BBPower por tf
│   ├── event_service.py        calendario + sorpresas
│   ├── session_service.py      fases de sesión
│   ├── health_service.py       frescura de datos
│   ├── bar_15m_service.py      velas 15m + SMA/Bollinger/VWAP
│   ├── screener_15m_service.py scanner 15m
│   ├── confluencia_service.py  alineación 5m/15m/1D
│   ├── initial_balance_service.py rango inicial 09:30–10:00 NY
│   ├── divergencia_service.py  divergencias precio/RSI 15m
│   └── sector_15m_service.py   cambio medio 15m por sector
├── api/                  routers FastAPI JSON
├── web/                  Jinja2 templates + HTMX + ECharts local
├── jobs/                 persist_score, check_score_freshness
├── tests/                pytest por capa
├── config_dashboard.json parámetros de negocio
└── pyproject.toml
```

---

## 6. Modelo de Datos

### 6.1 Tablas principales aprovechadas

| Tabla | Uso en dashboard v1.1.0 |
|---|---|
| `fact_market_series` | series por activo (close, rsi, adx, cci20, bbpower, volume, change_pct) |
| `fact_market_bar_15m` | velas OHLC 15m + volume_delta |
| `fact_market_indicator_tf` | indicadores técnicos por timeframe (5, 15) |
| `latest_market_tick` | último tick por activo (rsi, rsi_15, adx_15, cci20_15, bbpower_15) |
| `fact_heatmap_snapshot` | mapa sectorial + ranking |
| `fact_economic_event` | calendario + sorpresas |
| `fact_market_score` / `fact_market_score_agg` | score histórico por activo y de mercado |
| `dim_asset` | universo 1.700+ activos con sector/logo |

### 6.2 Particionamiento

| Tabla | Particiones | Nota |
|---|---|---|
| `fact_market_series` | 10 (mar–dic 2026) | Datos reales desde sep-2026 |
| `fact_market_bar_15m` | 16 (sep 2026 – dic 2027) | Datos reales desde sep-2026 |
| `fact_market_indicator_tf` | 16 (sep 2026 – dic 2027) | Datos reales desde sep-2026 |
| `fact_market_score` | 16 (sep 2026 – dic 2027) | Datos reales desde sep-2026 |
| `fact_heatmap_snapshot` | 4 (sep–dic 2026) | Datos reales desde sep-2026 |

---

## 7. Diagramas ASCII de los Paneles (v1.0.0 existentes)

Cada panel incluye: figura ASCII, propósito e importancia. Los paneles de oportunidad 5–15m se detallan en §8.

### 7.1 Header — Score de Mercado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ▶ MERCADO   Score 4.25 ▌▌▌▌░░░░░░░░░   Zona: VENDER   Cobertura 123        │
│  ▶ Momentum  4.82        Radar 3.68      15m 5.24                          │
│  ▶ Fase: Sesión Madura (14:00–16:00 ET)  Último ciclo 18:31 UTC            │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Propósito:** sentencia ejecutiva de "¿comprar/vender exposición?".
- **Importancia:** primera mirada antes de operar.

### 7.2 Mapa Sectorial

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Technology ████████████░░░░░░░░░░░░░░ (+)  Retail ██████░░░░░░░░░░░░ (+)   │
│  Financials ████████████░░░░░░░░░░░░░░ (+)  Health ████░░░░░░░░░░░░░░ (0)    │
│  Energy     ██░░░░░░░░░░░░░░░░░░░░░░░ (−)  Utility █░░░░░░░░░░░░░░░░ (−)    │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Propósito:** rotación sectorial de un vistazo.
- **Importancia:** identifica qué sectores lideran/rezagan.

### 7.3 Termómetro de Riesgo

```
┌────────────────────────────────────────────────────────────────────────────┐
│  VIX  █████████████████████░░░░░░░░░░ 15.00  (riesgo moderado)             │
│  US10Y ████████████████████████████░░ 5.00   (presión alcista)             │
│  DXY  ████████████████████████░░░░░░ 102.50  (dólar fuerte)                │
│  TLT  ███████████████████░░░░░░░░░░░ 81.27   (bonos débiles)               │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Propósito:** riesgo de cola / flujo defensivo vs agresivo.
- **Importancia:** contexto macro antes de operar.

### 7.4 Momentum Top/Bottom

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ▲ TOP          │  ▼ BOTTOM                                                 │
│  SPOT  +5.25%   │  MSTR  −6.33%   ADX 46.1                                 │
│  MU    +4.00%   │  MARA  −6.25%   ADX 44.7                                 │
│  SMCI  +3.18%   │  TER   −5.06%   ADX 24.1                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Propósito:** extremos de la sesión.
- **Importancia:** filtro rápido con ADX para evitar ruido.

### 7.5 Calendario de Alto Impacto con Sorpresas

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ⭐ Fed Interest Rate   US   actual 4.0%  forecast 4.0%  sorpresa 0.0%      │
│  CPI                   US   actual 3.1%  forecast 2.9%  sorpresa +6.9%     │
│  filtros: país ▾  importancia ≥1 ▾                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Propósito:** eventos que pueden mover el mercado.
- **Importancia:** anticipar volatilidad.

### 7.6 Evolución del Score de Mercado

```
Score de mercado (0-10)
  9│
  6│        ▄▄▄
  4│  ▄▄▄▄▄▀   ▀▀   ▀▄▄
  0│▀▘
   └────────────────────▶
     medianoche · apertura NY · ahora
```

- **Propósito:** ver cómo se movió el estado del mercado en las últimas horas.
- **Importancia:** contexto temporal del score.

### 7.7 Precio con Contexto — QQQ / SPY / IWM / ORO

```
QQQ  Últimas 48h (SMA20/50)
  760│        ▁▃█▆▃▁
  758│   ▂▄█▇▅▃    ▂▄
  756│▂▃▇▅▂        ▁▃▅▇
     └───▶ Precio ── SMA20 ── SMA50
```

- **Propósito:** tendencia intradía de los referentes más operados.
- **Importancia:** refuerza la lectura del header.

---

## 8. Nuevos Paneles de Oportunidad 5–15 min (v1.1.0)

Ordenados por **valor de importancia y aporte** para el trader. Cada panel incluye: figura ASCII, ejemplo con datos reales, cómo se lee, propósito, ventajas e importancia.

---

### 8.1 Oportunidades Momentum 15m — Continuación con Volumen

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Momentum 15m con volumen · 22 activos                                      │
│  ┌─────────┬──────────┬───────────┬───────────┬─────────┬─────────────────┐ │
│  │ SÍMBOLO │ CHANGE % │ RSI 15m   │ ADX 15m   │ VOL RAT │ SETUP           │ │
│  ├─────────┼──────────┼───────────┼───────────┼─────────┼─────────────────┤ │
│  │ 🟢 IBM  │ +0.30%   │  58.3     │  27.4     │  1.87x  │ CONT. ALCISTA   │ │
│  │ 🟢 MSFT │ +0.30%   │  61.2     │  25.1     │  1.08x  │ CONT. ALCISTA   │ │
│  │ 🔴 ASML │ −0.26%   │  41.2     │  24.1     │  1.39x  │ CONT. BAJISTA   │ │
│  │ ...     │          │           │           │         │                 │ │
│  └─────────┴──────────┴───────────┴───────────┴─────────┴─────────────────┘ │
│  fila clic → carga velas 15m · ordenado por |change %| · vol_ratio ≥ 1.0    │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** IBM +0.30% con volumen 1.87x; MSFT +0.30% con volumen 1.08x; ASML −0.26% con volumen 1.39x.
- **Cómo se lee:** verde = continuar alcista, rojo = continuar bajista. El volumen relativo confirma que hay interés real detrás del movimiento.
- **Propósito:** detectar movimientos en curso con confirmación de volumen.
- **Ventajas:** filtra ruido. Sin volumen, el movimiento probablemente no sostenga. Es el panel más accionable de continuación.
- **Importancia:** alta. Acelera el descubrimiento de activos en movimiento.
- **Datos:** `fact_market_bar_15m` + `latest_market_tick`.

---

### 8.2 Ruptura Máximo / Mínimo del Día Anterior

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Ruptura máx/min del día anterior · 45 activos · vol ≥ 1x                   │
│  ┌─────────┬───────────────┬──────────┬──────────────────┬─────────┐        │
│  │ SÍMBOLO │ TIPO          │ CLOSE    │ MÁX/MÍN AYER     │ VOL RAT │        │
│  ├─────────┼───────────────┼──────────┼──────────────────┼─────────┤        │
│  │ 🟢 AAPL │ ROMPE MAX     │ 336.49   │ 334.23           │  1.12x  │        │
│  │ 🟢 ADSK │ ROMPE MAX     │ 234.30   │ 230.92           │  2.53x  │        │
│  │ 🔴 ARM  │ ROMPE MIN     │ 297.90   │ 301.83           │  1.21x  │        │
│  │ 🔴 ASML │ ROMPE MIN     │ 1796.70  │ 1821.11          │  1.39x  │        │
│  │ ...     │               │          │                  │         │        │
│  └─────────┴───────────────┴──────────┴──────────────────┴─────────┘        │
│  fila clic → velas 15m · estructura clara para operar continuación          │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** 45 activos rompieron máximo o mínimo del día anterior (AAPL, ADSK, AMZN, COST al alza; ARM, ASML, DDOG, MARA a la baja).
- **Cómo se lee:** verde = rompe máximo de ayer (continuación alcista), rojo = rompe mínimo de ayer (continuación bajista). El volumen filtra rupturas débiles.
- **Propósito:** señal estructural de continuación basada en el rango previo.
- **Ventajas:** más objetiva que "sube mucho hoy". El máximo/mínimo del día anterior es un nivel clave de referencia para el mercado.
- **Importancia:** alta. Muchas señales y fácil de interpretar.
- **Datos:** `fact_market_bar_15m`.

---

### 8.3 Confluencia Fuerte 5m / 15m / 1D + Volumen

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Confluencia 5m/15m/1D + volumen                                            │
│  ┌─────────┬────────┬────────┬────────┬─────────┬─────────────────────────┐ │
│  │ SÍMBOLO │ 5m     │ 15m    │ 1D     │ VOL RAT │ SETUP                   │ │
│  ├─────────┼────────┼────────┼────────┼─────────┼─────────────────────────┤ │
│  │ 🟢 SHOP │ VERDE  │ VERDE  │ VERDE  │  1.84x  │ ALTA CONVICCIÓN ALCISTA │ │
│  │ 🟢 NVDA │ VERDE  │ VERDE  │ GRIS   │  1.52x  │ VIGILAR (2/3 + volumen) │ │
│  │ 🔴 MSTR │ ROJO   │ ROJO   │ ROJO   │  1.40x  │ ALTA CONVICCIÓN BAJISTA │ │
│  │ ...     │        │        │        │         │                         │ │
│  └─────────┴────────┴────────┴────────┴─────────┴─────────────────────────┘ │
│  verde=alcista · rojo=bajista · gris=neutral · fila clic → velas 15m        │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo esperado:** SHOP con 5m/15m/1D todos verdes + volumen 1.84x = alta convicción alcista.
- **Cómo se lee:**
  - **Alta convicción:** los 3 timeframes coinciden + volumen ≥ 1x.
  - **Vigilar:** 2 de 3 timeframes coinciden + volumen ≥ 1x.
  - **Neutral:** dispersión entre timeframes.
- **Propósito:** operar solo cuando corto, medio y largo plazo empujan en la misma dirección.
- **Ventajas:** reduce falsas entradas. El volumen añade confirmación de que la confluencia no es solo técnica sino también de flujo.
- **Importancia:** alta. Es el filtro de calidad sobre el screener.
- **Datos:** `fact_market_indicator_tf` (5, 15) + `latest_market_tick` + `fact_market_bar_15m` (volumen).

---

### 8.4 Tendencias en Marcha (ADX 15m > 25)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Tendencias en marcha · ADX 15m > 25 · 37 activos                           │
│  ┌─────────┬──────────┬─────────┬─────────┬────────────────────────────────┐ │
│  │ SÍMBOLO │ CHANGE % │ RSI 1D  │ ADX 15m │ NOTA                           │ │
│  ├─────────┼──────────┼─────────┼─────────┼────────────────────────────────┤ │
│  │ MSTR    │ −6.33%   │  55.5   │  46.1   │ tendencia bajista fuerte       │ │
│  │ MARA    │ −6.25%   │  37.3   │  44.7   │ tendencia bajista fuerte       │ │
│  │ V       │ +0.88%   │  57.5   │  42.0   │ tendencia alcista fuerte       │ │
│  │ NVDA    │ −1.02%   │  63.3   │  37.0   │ tendencia bajista fuerte       │ │
│  └─────────┴──────────┴─────────┴─────────┴────────────────────────────────┘ │
│  ADX > 25 filtra ruido; ideal para operar a favor de la tendencia            │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** 37 activos con ADX 15m > 25 hoy.
- **Cómo se lee:** ADX > 25 indica tendencia fuerte. El color indica dirección (alcista/bajista). Se ordena por ADX descendente.
- **Propósito:** evitar entrar en activos sin dirección.
- **Ventajas:** el ADX es un filtro clásico de calidad. Combina bien con el screener y el momentum.
- **Importancia:** media-alta. Filtro de calidad más que señal de entrada.
- **Datos:** `latest_market_tick`.
- **Estado / decisión:** **IMPLEMENTADO como K2** — **cuadrante σ × ADX** (4/12 columnas, fila K1/K2/K3). Documentación: [`dashboard_explicacion_graph-K2_tendencia_en_marcha.md`](dashboard_explicacion_graph-K2_tendencia_en_marcha.md) y [`dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md` §2.6](dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md).

---

### 8.5 VWAP + Initial Balance — Continuación de Ruptura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VWAP + Rango Inicial · oportunidades de continuación                       │
│  ┌─────────┬────────┬─────────┬─────────┬─────────┬────────────────────────┐ │
│  │ SÍMBOLO │ IB     │ HORA    │ VS VWAP │ VOL RAT │ SETUP                  │ │
│  ├─────────┼────────┼─────────┼─────────┼─────────┼────────────────────────┤ │
│  │ 🟢 SHOP │ UP     │ 10:30   │ +1.24%  │  1.84x  │ IB + VWAP + volumen    │ │
│  │ 🔴 MSTR │ DOWN   │ 10:15   │ −0.87%  │  1.40x  │ IB + VWAP + volumen    │ │
│  │ ⬛ XYZ  │ DENTRO │  —      │ +0.05%  │  0.80x  │ sin setup              │ │
│  └─────────┴────────┴─────────┴─────────┴─────────┴────────────────────────┘ │
│  fila clic → velas 15m · IB = rango 09:30–10:00 NY                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo esperado:** SHOP rompe IB_high a las 10:30 y está arriba del VWAP con volumen 1.84x.
- **Cómo se lee:**
  - **IB UP + precio > VWAP:** sesgo alcista confirmado por estructura y flujo.
  - **IB DOWN + precio < VWAP:** sesgo bajista confirmado.
  - **DENTRO o del lado incorrecto del VWAP:** no hay setup claro.
- **Propósito:** unir dos estructuras clave (rango inicial + VWAP) para confirmar continuación.
- **Ventajas:** el IB define el sesgo del día; el VWAP define el sesgo intradía. Cuando ambos coinciden, la probabilidad de continuación aumenta. Evita operar rupturas falsas del IB que no tienen el VWAP a favor.
- **Importancia:** media-alta. Requiere entender estructura, pero es muy poderoso.
- **Datos:** `fact_market_bar_15m` + `initial_balance_service`.

---

### 8.6 Líderes / Laggards del Período

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Rendimiento acumulado · últimos 8 días                                     │
│  ┌─────────────┬───────────┐  ┌─────────────┬───────────┐                  │ │
│  │ TOP         │           │  │ BOTTOM      │           │                  │ │
│  │ SHOP        │ +15.72%   │  │ MARA        │ −15.07%   │                  │ │
│  │ ADSK        │ +13.05%   │  │ STX         │ −13.35%   │                  │ │
│  │ CSCO        │ +10.42%   │  │ WDC         │ −11.08%   │                  │ │
│  │ ORCL        │  +8.79%   │  │ QCOM        │  −5.92%   │                  │ │
│  │ FTNT        │  +7.91%   │  │ NOC         │  −5.76%   │                  │ │
│  └─────────────┴───────────┘  └─────────────┴───────────┘                  │ │
│  contexto de tendencia intermedia; evita operar contra la fuerza            │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** SHOP +15.72% (top), MARA −15.07% (bottom) en los últimos 8 días.
- **Cómo se lee:** top = fuerza acumulada; bottom = debilidad acumulada. No es señal de entrada directa, es contexto.
- **Propósito:** identificar quién lleva fuerza real en el período.
- **Ventajas:** evita comprar rezagados en caída libre o vender líderes en tendencia. Complementa los paneles intradía con visión más amplia.
- **Importancia:** media. Contexto, no señal de timing.
- **Datos:** `fact_market_series` (primer vs último close del rango disponible).

---

### 8.7 Setups Multi-Indicador 15m

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Setups multi-indicador 15m · alta convicción                               │
│  ┌─────────┬─────────────┬─────────┬──────────┬───────────┬─────────┐      │ │
│  │ SÍMBOLO │ SETUP       │ RSI 15m │ CCI 15m  │ BBPower   │ VOL RAT │      │ │
│  ├─────────┼─────────────┼─────────┼──────────┼───────────┼─────────┤      │ │
│  │ 🟢 DDOG │ SOBREVENTA  │  31.9   │ −193.5   │ −2.46     │  1.53x  │      │ │
│  │         │   FUERTE    │         │          │           │         │      │ │
│  │ 🔴 FTNT │ SOBRECOMPRA │  70.5   │  +145.2  │  +4.12    │  2.04x  │      │ │
│  │         │   FUERTE    │         │          │           │         │      │ │
│  └─────────┴─────────────┴─────────┴──────────┴───────────┴─────────┘      │ │
│  señales raras pero de alta calidad; lista corta de vigilancia              │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** DDOG con RSI 15m 31.9, CCI −193.5, BBPower −2.46 + volumen 1.53x (sobreventa fuerte).
- **Cómo se lee:** verde = sobreventa fuerte (posible rebote), rojo = sobrecompra fuerte (posible corrección). Requiere 3 indicadores alineados + volumen.
- **Propósito:** detectar extremos donde varios indicadores coinciden.
- **Ventajas:** cuando RSI, CCI y BBPower coinciden en extremo, la probabilidad de reversión o pausa aumenta. Lista corta, alta calidad.
- **Importancia:** media. Señales raras pero valiosas.
- **Datos:** `latest_market_tick` (rsi_15, cci20_15, bbpower_15) + `fact_market_bar_15m` (volumen).

---

### 8.8 Cruces SMA 9/21 en 15m

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cruces SMA 9/21 en 15m · cambio de tendencia a corto plazo                 │
│  ┌─────────┬────────────────┬──────────┬──────────┬──────────┐              │ │
│  │ SÍMBOLO │ TIPO           │ CLOSE    │ SMA9     │ SMA21    │              │ │
│  ├─────────┼────────────────┼──────────┼──────────┼──────────┤              │ │
│  │ TXN     │ CRUCE ALCISTA  │ 285.51   │ 286.13   │ 286.04   │              │ │
│  │ ASML    │ CRUCE BAJISTA  │ 1796.70  │ 1803.23  │ 1803.48  │              │ │
│  │ ABBV    │ CRUCE BAJISTA  │ 272.31   │ 272.93   │ 273.09   │              │ │
│  └─────────┴────────────────┴──────────┴──────────┴──────────┘              │ │
│  poca frecuencia pero buena calidad; ideal para swing intradía              │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Ejemplo real:** 3 cruces hoy (TXN alcista; ASML y ABBV bajistas).
- **Cómo se lee:** cruce alcista = SMA9 cruza por arriba de SMA21; cruce bajista = por abajo. Señala cambio de tendencia a corto plazo.
- **Propósito:** detectar giros de tendencia en 15m.
- **Ventajas:** clásico y fácil de entender. Funciona mejor cuando se combina con volumen y contexto del día.
- **Importancia:** media-baja. Poca frecuencia, pero señales de calidad.
- **Datos:** `fact_market_bar_15m`.

---

## 9. Motor de Score: Fórmulas y Calibración

- **PASO 1 — score por símbolo [0,10]** = Σ(pesoᵢ · normᵢ)/Σ(pesoᵢ). Indicadores: rsi, adx, cci20, bbpower, volume_ratio, change_pct.
- **PASO 2 — momentum** = media de score_general sobre equity/ETF.
- **PASO 2b — score 15-min** = promedio de últimos N scores tf=15.
- **PASO 3 — radar intermarket** = blend ponderado de VIX/US10Y/DXY/TLT.
- **Zonas:** COMPRAR ≥ 6.5, VENDER ≤ 4.5, NEUTRAL entre medio.

---

## 10. Fases de Implementación

| Fase | Entregable | Actividad clave |
|---|---|---|
| **0** | Deuda y salud | Auditoría de `persist_score` en `audit_sync_run`; health enriquecido |
| **1** | Repositorios | Añadir métodos a `bar_15m_repo` e `indicator_repo` para los nuevos filtros |
| **2** | Servicios | Crear servicios de oportunidad: momentum_15m, ruptura_dia, confluencia_fortaleza, tendencias_adx, vwap_ib, laggards, multi_indicador, cruces_sma |
| **3** | Gráficos ECharts | Helpers en `web/charts.py` para tablas de oportunidad |
| **4** | Endpoints y parciales | `/partials/*` para cada uno de los 8 paneles; filas clicables → velas 15m |
| **5** | Dashboard | Ubicar paneles en parte inferior del grid, debajo de la tabla sectorial |
| **6** | Tests | Tests unitarios de servicios; tests de integración read-only |
| **7** | Calibración | Ajustar umbrales en `config_dashboard.json` con datos reales |

---

## 11. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Pocas señales de confluencia fuerte con criterios estrictos | Añadir grupo "vigilar" (2/3 timeframes + volumen) |
| Bollinger/multi-indicador con pocos datos produce falsos rechazos | Exigir al menos 20 barras y volumen ≥ 1x |
| Cruces SMA 9/21 muy raros | Combinar con volumen y mostrar como lista corta |
| Duplicación con screener 15m existente | Los nuevos paneles son filtros de calidad, no reemplazos |
| Historia corta (< 60 días) | Mantener placeholders históricos; no forzar backtest largo |

---

## 12. Criterios de Aceptación

1. Los 8 nuevos paneles renderizan datos reales de BD sin mock.
2. Las filas son clicables y actualizan el gráfico de velas 15m.
3. La confluencia incluye grupo "alta convicción" (3/3 + volumen) y "vigilar" (2/3 + volumen).
4. La ruptura máx/min filtra por volumen relativo ≥ 1x.
5. Los tests de los nuevos servicios pasan.
6. Documentación actualizada (roadmap + `CHANGELOG.md`).

---

## 13. Decisión de Arquitectura

| Opción | Veredicto |
|---|---|
| **FastAPI + Jinja2 + HTMX + ECharts (elegido)** | Monolítico moderno, endpoints JSON reutilizables, capas limpias, sin CDN. |
| Django | Demasiado peso; ORM y admin no necesarios. |
| Streamlit | Mezcla lógica y UI; no publica APIs limpias. |

---

## 14. Decisión de diseño — K1 · Reversión Bollinger 15m (dot-plot σ)

> Gráfico **K1** (`bollinger_scatter`). Documentación detallada: [`dashboard_explicacion_graph-K1_reversion_bollinger_dotplot.md`](dashboard_explicacion_graph-K1_reversion_bollinger_dotplot.md).

### 14.1 Contexto y problema

El primer dot-plot de Bollinger usaba una **tolerancia en % de precio** (±0.5%) para decidir si el precio estaba "cerca" de una banda. Ese criterio **no es invariante a la volatilidad**: cuando σ es muy pequeña (poca volatilidad), las bandas quedan angostas y el 0.5% de precio alcanza hasta la media. Resultado: aparecían activos **lejos de la banda en términos de σ** (ej. **V** a 1.58σ de la banda, **BA** a 1.40σ, **INTC** a 1.30σ, **MS** a 1.08σ) que en realidad estaban **cerca de la SMA20**, no en un extremo → **falsos positivos**.

### 14.2 Decisión: A + C

- **A · Tolerancia en σ (proximidad normalizada).** La selección pasa a medirse en **desviaciones estándar** (`bollinger_tol_sigma = 0.5`), no en % de precio. Un activo entra solo si está **dentro de 0.5σ de una banda** o **la superó**.
- **C · Dos estados visuales.** Se distingue:
  - **ACCIONABLE** → el precio **perforó** la banda (punto **relleno**).
  - **CERCA** → quedó dentro de `tol_sigma` σ (punto **hueco/atenuado**, watchlist).

### 14.3 Cómo se calcula

```
Bollinger(20, 2) sobre cierres 15m:
  SMA20 = media de 20 cierres
  σ     = (upper − SMA20) / k        (k = 2 por defecto)
  z     = (close − SMA20) / σ        (posición en la banda)

Selección (extremmos):
  d_sup = (upper − close) / σ ≤ tol_sigma   → RECHAZO HIGH / CORTO
  d_inf = (close − lower) / σ ≤ tol_sigma   → REBOTE LOW  / LARGO
  estado = ACCIONABLE si close supera la banda, si no CERCA
  además: vol_ratio ≥ bollinger_vol_min (1.0x)
  score  = 2·vol_ratio + max(0, dist_banda)
```

### 14.4 Características del gráfico

| Rasgo | Valor |
|---|---|
| Tipo | Dot-plot (scatter) |
| Eje X | Slot categórico por símbolo (sin valor, equiespaciado) |
| Eje Y | **Posición en la banda `z` (σ)**: +2 banda sup · 0 SMA20 · −2 banda inf |
| Líneas | Punteadas amarillas = **bandas de Bollinger (±2σ)**; gris = SMA20 |
| Color | **rojo = CORTO** · **verde = LARGO** |
| Relleno | **relleno = superó** (accionable) · **hueco = cerca** (watchlist) |
| Tamaño | Volumen relativo |
| Orden | **σ descendente** (escalera: más extendido arriba) |
| Tooltip | ícono + tipo + posición σ + close + dist. banda + volumen + RSI + score |
| Ancho | **4/12 columnas** (fila K1/K2/K3) |
| Máx. puntos | 10 (`bollinger_scatter_max`) |

### 14.5 Ventajas

- **Invariante a la volatilidad:** el criterio en σ compara peras con peras (un activo de $50 y uno de $500 en la misma escala).
- **Sin falsos positivos de tolerancia:** se descartan V/BA/INTC/MS (lejos de la banda en σ).
- **Separa accionable de watchlist:** relleno vs hueco evita confundir "ya perforó" con "está por llegar".
- **Lectura en un vistazo:** escalera descendente; extremos en las puntas.
- **Self-documenting:** leyenda con swatches + nota del eje y del score.

### 14.6 Archivos

- Servicio: `services/bollinger_15m_service.py` (`clasificar_banda`, `_tol_sigma`).
- Chart: `web/charts.py::scatter_bollinger_option`.
- Vista: `web/views.py::bollinger_scatter`.
- Config: `config/charts/K1_bollinger_scatter.json`, `config/charts/J2_bollinger.json`.
- Tests: `tests/test_trading_15m.py` (clasificación en σ, exclusión lejos de banda).

---

## 15. Changelog

- **2026-10-08 (K1 Bollinger dot-plot σ)** — Nueva sección 14. Decisión A + C para el gráfico K1: tolerancia en σ (`bollinger_tol_sigma = 0.5`) en lugar de % de precio, y doble estado **ACCIONABLE** (relleno, superó la banda) / **CERCA** (hueco, watchlist). Se corrige así el falso positivo de activos cerca de la media con σ pequeña (V/BA/INTC/MS). Card a 6/12 columnas, orden por σ descendente, máx. 10 puntos. Documentación detallada en `dashboard_explicacion_graph-K1_reversion_bollinger_dotplot.md`.
- **2026-10-07 (revisión v1.1.0)** — Actualización del roadmap con análisis de datos reales de `heatmap_stock` (139k series, 28k barras 15m, 259k indicadores tf, 190k snapshots). Propuesta de 8 nuevos paneles de oportunidad 5–15 min ordenados por valor/importancia, con figuras ASCII, ventajas, lectura y datos reales. Ajuste de confluencia para incluir grupo "vigilar" (2/3 + volumen). Filtro de ruptura máx/min por volumen relativo ≥ 1x.
- **2026-09-18 (revisión v1.0.0)** — Análisis validado contra BD: 579 eventos cargados, retro limitado a ago para momentum, snapshots delgados, vista evento-impacto relajada. Paneles de contexto con ASCII.
- **2026-09-18** — Creación del roadmap con análisis de datos reales de `heatmap_stock`, propuesta arquitectura FastAPI, 6 paneles con figuras ASCII y ejemplos de BD.
