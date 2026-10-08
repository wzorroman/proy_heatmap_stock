# Roadmap — Nuevos Paneles de Oportunidad 5–15 min en `proy_dashboard` v2.1.0

> **Proyecto:** `proy_dashboard` — Dashboard de Contexto + Trading Intradía  
> **Versión destino:** 2.1.0  
> **Base de datos fuente:** `heatmap_stock` (`192.168.18.121:5432`, PostgreSQL 17+)  
> **Fecha del documento:** 2026-10-07  
> **Stack:** Python 3.13 / FastAPI + Jinja2 + HTMX + Apache ECharts, repositorios PostgreSQL sin ORM.  
> **Referencias:** `proy_dashboard/docs/informe_graficos_2026-09-30.md`, `proy_dashboard/CHANGELOG.md`, `proy_dashboard/config_dashboard.json`.

---

## ✅ Resumen del análisis (datos reales verificados en BD, 2026-10-07)

| Métrica | Valor en `heatmap_stock` |
|---|---|
| Filas en `fact_market_series` | **139.872** (particionadas, último tick 2026-10-07 18:35 UTC) |
| Filas en `fact_market_bar_15m` | **28.653** (123 símbolos, pipeline reactivado) |
| Filas en `fact_market_indicator_tf` | **259.364** (`tf` 5 y 15, 112 símbolos) |
| Activos en `latest_market_tick` | **123** (70 equity + 25 ETF + otros) |
| Score agregado actual | `score_market = 4.25` · `zona = VENDER` |
| Calendario económico | 351 eventos, 29 con `actual` + `forecast` |

**Hallazgo clave:** el dashboard ya tiene datos frescos y suficientes para operar intradía, pero faltan paneles que **filtren y rankeen oportunidades de alta convicción** en ventanas de 5–15 minutos, complementando al screener existente.

---

## 1. Propósito y Justificación

**Propósito:** añadir paneles que indiquen, de un vistazo, qué activos merecen una revisión profunda para operar en timeframe de 5–15 minutos. No reemplazan el análisis del trader, pero aceleran el descubrimiento.

**Justificación:**
1. El screener 15m ya emite señales COMPRAR/VENDER/NEUTRAL, pero no destaca las de **mayor convicción** (confluencia multi-timeframe + volumen + ruptura de estructura).
2. La divergencia precio/RSI 15m ya funciona; se puede replicar la lógica a **5m** para detectar señales más tempranas.
3. Las bandas de Bollinger 15m + volumen identifican puntos de **reversión o continuación** que el screener no cubre.
4. Todos los datos necesarios ya existen: `fact_market_bar_15m`, `fact_market_indicator_tf`, `latest_market_tick`, `dim_asset`.

---

## 2. Paneles Propuestos

Cada panel incluye: figura ASCII, ejemplo con datos reales, propósito e importancia.

### Estado de implementación

| # | Panel | Estado | Implementación |
|---|---|---|---|
| 2.1 | Oportunidades Momentum 15m | ✅ Implementado | **J1** · `/partials/oportunidad_15m` |
| 2.2 | Reversión Bollinger 15m | ✅ Implementado | **K1** · `/partials/bollinger_scatter` (dot-plot σ) — J2 lista retirado |
| 2.3 | Confluencia Fuerte 5m/15m/1D + Vol | ✅ Implementado | **J3** · `/partials/confluencia_fuerte` (5m/15m/1D + volumen) |
| 2.4 | Divergencia Precio / RSI 5m | ✅ Implementado | **K3** · `/partials/divergencia_5m` (scatter RSI ini × RSI fin) |
| 2.5 | VWAP + Initial Balance | ✅ Implementado | **J2** · `/partials/vwap_ib` (scatter Vol × dist. VWAP) |
| 2.6 | Tendencias en Marcha (ADX 15m) | ✅ Implementado | **K2** · `/partials/tendencia_15m` (σ × ADX) |

> **Nueva fila K (analítica, 4/12 cada uno):** **K1** Reversión Bollinger (σ) · **K2** Tendencias (ADX) · **K3** Divergencia 5m — se leen como tríada: K1 «dónde» · K2 «¿es fiable?» · K3 «¿cuándo entrar?».
>
> **Nueva fila J (continuación, 4/12 cada uno):** **J1** Momentum · **J2** VWAP+IB · **J3** Confluencia + Vol — de lo inmediato a lo amplio. Documentación detallada: [`dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md`](dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md).

---

### 2.1 Oportunidades Momentum 15m — Continuación con Volumen ✅ IMPLEMENTADO

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Oportunidades Momentum 15m · Continuación con Volumen                       │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┬───────────────────────┐ │
│  │ SÍMBOLO │ CLOSE   │ RSI 15m │ ADX 15m │ VOL RAT │ SETUP                 │ │
│  ├─────────┼─────────┼─────────┼─────────┼─────────┼───────────────────────┤ │
│  │ 🟢 SPOT │ 512.38  │  64.3   │  51.5   │  1.78x  │ CONT. ALCISTA ▲ LARGO │ │
│  │ 🟢 DIS  │ 104.78  │  64.0   │  26.2   │  1.62x  │ CONT. ALCISTA ▲ LARGO │ │
│  │ 🟢 AMZN │ 259.67  │  68.8   │  33.1   │  1.25x  │ CONT. ALCISTA ▲ LARGO │ │
│  └─────────┴─────────┴─────────┴─────────┴─────────┴───────────────────────┘ │
│  fila clic → carga velas 15m · ordenado por score · max 4 oportunidades      │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Estado:** implementado en dashboard (`/partials/oportunidad_15m`) — fila ubicada justo antes del Calendario de hoy.
- **Ejemplo real (datos actuales):** SPOT 512.38 (+0.06%) RSI 64.3 / ADX 51.5 / Vol 1.78x; DIS 104.78 (+0.10%) RSI 64.0 / ADX 26.2 / Vol 1.62x; AMZN 259.67 (+0.11%) RSI 68.8 / ADX 33.1 / Vol 1.25x.
- **Criterios:** precio > VWAP, RSI(15) entre 50–70, ADX(15) ≥ 25, volumen relativo ≥ 1.2x, última barra alcista o plana (change_pct ≥ 0).
- **Propósito:** detectar movimientos en curso con confirmación de volumen, ideales para operar a favor del impulso en 15m.
- **Importancia:** filtra ruido. Sin volumen, el movimiento probablemente no sostenga.
- **Datos:** `fact_market_bar_15m` (close, volume, vwap), `latest_market_tick` (rsi_15, adx_15).

---

### 2.2 Reversión en Bollinger 15m — Pinchazos de Banda + Volumen ✅ IMPLEMENTADO

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  Reversión Bollinger 15m · 5 activos cerca de banda + vol ≥ 1x                │
│  ┌─────────┬──────────────┬──────────┬─────────┬────────────────────────────┐ │
│  │ SÍMBOLO │ TIPO         │ CLOSE    │ VOL RAT │ NOTA                       │ │
│  ├─────────┼──────────────┼──────────┼─────────┼────────────────────────────┤ │
│  │ 🟢 UNH  │ REBOTE LOW   │ 372.31   │  4.00x  │ bajo banda inferior    --  │ │
│  │ 🟢 PANW │ REBOTE LOW   │ 404.98   │  3.00x  │ cerca banda inferior   --  │ │
│  │ 🔴 TER  │ RECHAZO HIGH │ 412.00   │  2.97x  │ cerca banda superior   ++  │ │
│  │ 🟢 CCJ  │ REBOTE LOW   │  88.95   │  2.71x  │ cerca banda inferior   --  │ │
│  │ 🔴 TXN  │ RECHAZO HIGH │ 289.94   │  2.32x  │ sobre banda superior   ++  │ │
│  └─────────┴──────────────┴──────────┴─────────┴────────────────────────────┘ │
│  fila clic → velas 15m · señal de reversión, no de continuación               │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Estado:** ✅ **IMPLEMENTADO como K1** — dot-plot σ (`/partials/bollinger_scatter`, 4/12 en la fila K1/K2/K3). El card compacto de lista (`/partials/bollinger_15m`, J2) se **retiró** del dashboard (celda vacía).
- **Ejemplo real (datos actuales):** UNH rebotó en la banda inferior con volumen 4.00x; PANW y CCJ cerca de la banda inferior; TER y TXN rechazaron la banda superior.
- **Criterios:** Bollinger(20, 2) sobre cierres 15m; `close` dentro del 0.5% de una banda; volumen relativo ≥ 1.0x.
- **Propósito:** detectar activos en extensión que pueden revertir o al menos pausar.
- **Importancia:** complementa el screener (que busca tendencia) con entradas de reversión.
- **Datos:** `fact_market_bar_15m` (OHLC, volume_delta). Bollinger(20,2) calculado en servicio.
- **Documentación detallada:** ver [`dashboard_explicacion_graph-K1_reversion_bollinger_dotplot.md`](dashboard_explicacion_graph-K1_reversion_bollinger_dotplot.md) — versión dot-plot (σ), criterios, score, órdenes de lectura, esquinas y ejemplos.

---

### 2.3 Confluencia Fuerte 5m / 15m / 1D + Volumen  ✅ IMPLEMENTADO

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  Confluencia total 5m/15m/1D + volumen ≥ 1x                                   │
│  ┌─────────┬─────┬─────┬─────┬─────────┬───────────────────────────┐ │
│  │ SÍMBOLO │ 5m  │ 15m │ 1D  │ VOL RAT │ SETUP                     │ │
│  ├─────────┼─────┼─────┼─────┼─────────┼───────────────────────────┤ │
│  │ 🟢 SHOP │ 🟢  │ 🟢  │ 🟢  │  1.84x  │ ALTA CONVICCIÓN ALCISTA ▲ │ │
│  │ 🔴 MSTR │ 🔴  │ 🔴  │ 🔴  │  1.40x  │ ALTA CONVICCIÓN BAJISTA ▼ │ │
│  │ ...     │     │     │     │         │                           │ │
│  └─────────┴─────┴─────┴─────┴─────────┴───────────────────────────┘ │
│  fila clic → velas 15m · los 3 timeframes deben coincidir + volumen           │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Estado:** ✅ **IMPLEMENTADO como J3** — `/partials/confluencia_fuerte`: **semáforo de 3 luces** (5m · 15m · 1D) por símbolo + **tooltip al pasar el mouse** sobre el símbolo (RSI 5m/15m/1D, score, volumen, setup). `ALTA CONVICCIÓN` si los 3 TF coinciden y vol ≥ 1x; `VIGILAR` si coinciden sin volumen. (La versión heatmap sigue en E3 `/partials/confluencia`.)
- **Ejemplo esperado:** activos del screener con cambio positivo en 5m, 15m y 1D, y volumen por encima de la media.
- **Propósito:** operar solo cuando corto, medio y largo plazo empujan en la misma dirección.
- **Importancia:** reduce falsas entradas. Es el filtro de "calidad" sobre el screener.
- **Datos:** `fact_market_indicator_tf` (tf 5, 15), `latest_market_tick` (change_pct, rsi).

---

### 2.4 Divergencia Precio / RSI 5m — scatter RSI ini × RSI fin  ✅ IMPLEMENTADO (K3)

```
 RSI fin (5m)
 80 ┤          ●SHOP (BAJ)
    │
 70 ┤              ●AMZN ●GOOGL (BAJ)
 60 ┤
 50 ┤
 40 ┤  ●MSTR ●TGT ●PEP (ALC)
 30 ┤
    └──┬────┬────┬────┬────┬────┬──►
      30   40   50   60   70   80   RSI ini (5m)
   encima de y=x = ALCISTA (RSI↑) · debajo = BAJISTA (RSI↓)
   ● verde = ALCISTA (mínimo de precio ↓, RSI ↑)
   ● rojo  = BAJISTA (máximo de precio ↑, RSI ↓)
```

- **Código:** K3 · **slug:** `divergencia_5m` · **Endpoint:** `/partials/divergencia_5m`
- **Ubicación:** card de **4/12 columnas**, en la **misma fila que K1 y K2** (K1 ↑4 + K2 ↑4 + K3 ↑4 = 12).
- **Diseño elegido (Opción B):** scatter **RSI en el pivote inicial (X) × RSI en el pivote final (Y)**; diagonal `y = x`; color por tipo (verde ALCISTA / rojo BAJISTA).
- **Ejemplo real (snapshot 2026-10-08):** MSTR 40.4→46.6 (ALC), TGT 34.0→40.2 (ALC), PEP 39.7→42.7 (ALC), SHOP 80.1→76.6 (BAJ), AMZN 69.7→66.9 (BAJ), GOOGL 74.6→71.9 (BAJ).
- **Propósito:** detectar agotamiento del impulso **antes** que el panel 15m (misma lógica, ventana más temprana).
- **Cómo se lee:** por **encima** de la diagonal el RSI subió → mejor soporte para una **ALCISTA**; por **debajo** el RSI bajó → transición a **BAJISTA**.
- **Datos:** barras 5m **ensambladas** desde `fact_market_series` (no hay tabla materializada de 5m) + RSI Wilder(14) sobre los cierres 5m.
- **Config:** `config/charts/K3_divergencia_5m.json` (`pivote_k=2`, `min_sep=5`, `rsi_min=2.0`, `ventana_horas=24`).

> **Complemento con K1/K2 (tríada K):** en la misma fila, **K1 = «dónde»** (extremo de banda), **K2 = «¿es fiable?»** (régimen ADX), **K3 = «¿cuándo entrar?»** (confirmación por divergencia 5m). Solo K1 = aviso; K1+K2 = descarta reversiones contra tendencia fuerte; **K1+K2+K3 = alta convicción** (se marca con **anillo dorado** en K3). Hoy el único símbolo en la tríada completa es **PEP**.

---

### 2.5 VWAP + Initial Balance — Continuación de Ruptura  ✅ IMPLEMENTADO

```
 Vol
 3.0 ┤ ●PANW
     │ ●TER  ●CCJ                ← IB DOWN + bajo VWAP = CORTO fuerte
 2.5 ┤
     │ ●TMO ●FTNT ●MCD ●TXN
 2.0 ┤                    │        ●V   ●LOGI
  1  ┤────────────────────┼────────────────────
     └──┬─────┬─────┬─────┼─────┬─────┬─────►
      −3%   −2%   −1%     0    +1%   +2%    dist VWAP
   ◄──── CORTO (IB DOWN) ─┤─ LARGO (IB UP) ────►

 X = distancia al VWAP (%) · Y = volumen relativo
 verde = LARGO (IB UP + > VWAP) · rojo = CORTO (IB DOWN + < VWAP)
```

- **Estado:** ✅ **IMPLEMENTADO como J2** — `/partials/vwap_ib`: scatter **X = distancia al VWAP (%) × Y = volumen relativo**, color por lado (verde LARGO / rojo CORTO), línea vertical en 0 = VWAP. (El IB por acción sigue en E2 `/partials/ib_acciones`.)
- **Ejemplo esperado:** activos del screener que rompieron IB_high o IB_low y que además están arriba/abajo del VWAP con volumen.
- **Propósito:** unir dos estructuras clave (rango inicial + VWAP) para confirmar continuación.
- **Importancia:** el IB define el sesgo del día; el VWAP define el sesgo intradía. Cuando coinciden, la probabilidad aumenta.
- **Datos:** `fact_market_bar_15m` + `initial_balance_service` existente.

---

### 2.6 Tendencias en Marcha (ADX 15m) — cuadrante σ × ADX · filtro de régimen de K1 ✅ DECIDIDO

> **Código:** **K2** · **slug:** `tendencia_15m` · **Endpoint:** `/partials/tendencia_15m`
> **Ubicación:** card de **4/12 columnas**, en la **misma fila que K1 y K3** (fila K1/K2/K3) → K1 cols 1–4, K2 cols 5–8, K3 cols 9–12.
> **Origen:** roadmap v2 §8.4 «Tendencias en Marcha (ADX 15m > 25)».

**Propósito:** responder «¿hay tendencia fuerte y hacia dónde?» para saber si una señal de reversión de K1 es aprovechable (rango) o **peligrosa** (*band walking*). K2 es el **filtro de régimen** de K1: muestra los **mismos símbolos que K1** (universo compartido e intersectado con `ADX 15m ≥ umbral`), con la dimensión ADX añadida.

#### 2.6.0 Opciones consideradas y selección

Se evaluaron **4 opciones** de chart para el panel:

| Opción | Ejes | Universo | Ventaja | Desventaja |
|---|---|---|---|---|
| **A — Dot-plot ADX** | X=slot, Y=ADX | todos ADX≥25 | mismo lenguaje que K1 | ranking sin información de dirección |
| **B — Cuadrante Change% × ADX** | X=change%, Y=ADX | todos ADX≥25 | cuadrante clásico, analítico | universo **distinto** de K1 → los dos cards no muestran los **mismos** símbolos |
| **C — Barras horizontales ADX** | barras ADX | todos ADX≥25 | ranking claro | pierde RSI 1D y cambio% |
| **D — Cuadrante σ × ADX** ✅ | **X=z_banda, Y=ADX** | **universo K1 ∩ ADX≥25** | **comparte eje X y universo con K1** | requiere que K2 consuma `Bollinger15mService` |

**Opción seleccionada: D.** Razones:
- **Comparte universo y eje X con K1** (σ) → K1 y K2 se leen como una sola vista: K1 = `z_banda` (dot-plot), K2 = `z_banda × ADX` (cuadrante). **Los dos cards muestran los mismos símbolos.**
- **Color = lado de K1** (CORTO rojo / LARGO verde) → coherencia visual total.
- Añade exactamente el dato que K1 no tiene: el **régimen** de tendencia.
- Descarta los símbolos que K1 marca pero están en rango (ADX < 25) — reversiones de más calidad.

#### 2.6.1 Figura ASCII (chart real)

```
 ADX 15m
 70 ┤              ●ADSK 67.7
 60 ┤
 50 ┤
 40 ┤        ●TER 40.4    ●COST 43.9
    │        ●CCJ 41.8
 30 ┤  ●LLY 32.1 ●UNH 31.4 ●TXN 36.2
    │  ●PEP 29.5   ●PANW 34.9
    │  ●TGT 27.2
 25 ┤─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  umbral ADX ≥ 25
     └──┬──────┬──────┬─────┬──────┬──────┬──►
      -3σ    -2σ   -1σ   0    +1σ    +2σ    Posición en banda (σ)
```

- **Eje X** = `z_banda` (σ). Mismo concepto que el **eje Y del card K1**. Marcas verticales: `0` (SMA20) y `±k` (bandas de Bollinger, k = 2).
- **Eje Y** = `adx_15`. Marca horizontal en `25` (umbral de tendencia fuerte).
- **Color**: rojo = **CORTO** (rechazo banda superior) · verde = **LARGO** (rebote banda inferior) — **mismo color que K1** por lado.
- **Tooltip** (renderer genérico `tooltipRows`): Posición (σ) · ADX 15m · Close · Chg % · RSI 15m · Score · badge con el `tipo` de K1 (`RECHAZO HIGH` / `REBOTE LOW`).

#### 2.6.2 Leyenda en pantalla

```
● rojo = CORTO   ● verde = LARGO
─ ─ ─  bandas de Bollinger (±2σ)   ─  SMA20 (media)
línea horizontal amarilla = umbral ADX ≥ 25
```

#### 2.6.3 Cómo se calcula

K2 consume el **universo de K1** y filtra adicionalmente por ADX:

```
Universo K1 = activos que tocan/superan una banda de Bollinger (σ) con volumen ≥ 1x
K2 = universo_K1 ∩ {adx_15 ≥ adx_min (25 por defecto)}

z     = (close − SMA20) / σ          ← compartido con K1
adx   = ADX 15m                       ← de latest_market_repo
lado  = CORTO si banda sup, LARGO si banda inf  ← de K1

Eje X = z_banda
Eje Y = adx_15
```

Implementación: `Tendencia15mService` recibe `Bollinger15mService` + `latest_tick_repo` (vía container); llama `bollinger.scan(limit=…)` y filtra por ADX.

#### 2.6.4 Interpretación

**Cuadrante (ADX vs posición en banda):**

| Zona Y | Lectura |
|---|---|
| **Arriba (ADX ≥ 25)** | **Tendencia fuerte** — el extremo de banda ocurre dentro de un mercado tendido |
| **Abajo (ADX < 25)** | **Rango / sin tendencia** — el extremo de banda ocurre en lateral |

**Matriz de decisión K1 × K2** (el valor real de tenerlos juntos):

```
                          K2 · ADX 15m
                 ┌────────────────────┬───────────────────────────────┐
                 │  RANGO (ADX < 25)  │  TENDENCIA (ADX ≥ 25)         │
   ┌─────────────┼────────────────────┼───────────────────────────────┤
   │ K1 CORTO    │  reversión ✅      │  dir BAJISTA → corto a favor ✅│
   │ (banda sup) │  (rango)           │  dir ALCISTA → band walking ⚠️ │
   ├─────────────┼────────────────────┼───────────────────────────────┤
   │ K1 LARGO    │  reversión ✅      │  dir ALCISTA → largo a favor ✅│
   │ (banda inf) │  (rango)           │  dir BAJISTA → band walking ⚠️ │
   └─────────────┴────────────────────┴───────────────────────────────┘
```

- **K1 + K2 = "zona × régimen"** juntos.
- Extremo + rango → **reversión clásica** (el mejor escenario de K1).
- Extremo + tendencia **a favor** de la reversión → entrada de **continuación de calidad**.
- Extremo + tendencia **en contra** → **descartar** (*band walking*).

#### 2.6.5 Ejemplos reales (snapshot 2026-10-08)

**Universo K1** (top por score) intersectado con **ADX ≥ 25**:

| Ticker | z (σ) | ADX 15m | K1 lado | K1 tipo | Dir |
|---|---:|---:|---|---|---|
| TXN | +3.27 | 36.2 | CORTO | RECHAZO HIGH (sobre sup.) | BAJISTA |
| TER | +1.91 | 40.4 | CORTO | RECHAZO HIGH (cerca sup.) | BAJISTA |
| CCJ | −1.69 | 41.8 | LARGO | REBOTE LOW | BAJISTA |
| PANW | −1.78 | 34.9 | LARGO | REBOTE LOW | BAJISTA |
| PEP | −1.92 | 29.5 | LARGO | REBOTE LOW | BAJISTA |
| UNH | −3.27 | 31.4 | LARGO | REBOTE LOW (bajo inf.) | BAJISTA |

> MCD, TMO, FTNT, UPS (también en K1) **quedan fuera de K2** porque su ADX 15m < 25 (rango).

**Lectura combinada K1 × K2:**

| Activo | K1 | K2 | Veredicto |
|---|---|---|---|
| **TXN** | CORTO (superó sup.) | ✅ superior (ADX 36.2) | reversión contra tendencia BAJISTA → corto del rebote ✅ alineado |
| **TER** | CORTO (cerca sup.) | ✅ superior (ADX 40.4) | igual, tendencia **muy fuerte** ✅ alineado (fuerte) |
| **CCJ** | LARGO (bajo inf.) | ✅ inferior (ADX 41.8) | rebote **contra** tendencia BAJISTA → ⚠️ band walking |
| **PANW** | LARGO (bajo inf.) | ✅ inferior (ADX 34.9) | ⚠️ band walking |
| **PEP** | LARGO (bajo inf.) | ✅ inferior (ADX 29.5) | ⚠️ band walking leve |
| **UNH** | LARGO (bajo inf.) | ✅ inferior (ADX 31.4) | ⚠️ band walking; aunque vol = 4x |

Es decir, en este snapshot **casi todos los extremos de K1 están en tendencias fuertes** → el escenario de reversión "pura" (rango) no aparece; las reversiones de K1 son contra tendencia fuerte, que requieren confirmación extra.

#### 2.6.6 Relación con K1 (por qué van juntos)

K1 es un panel **contrarian**: falla con *band walking* (en tendencia el precio se pega a la banda y sigue). K2 mide exactamente eso. Leídos juntos:

- **K1 dice «dónde»** (qué activo está en un extremo de banda).
- **K2 dice «en qué régimen»** (si hay tendencia fuerte y hacia dónde).
- Extremo + tendencia **a favor** de la reversión → entrada de continuación de calidad.
- Extremo + tendencia **en contra** → descartar (band walking).
- Extremo + rango → reversión clásica (el mejor escenario de K1).

#### 2.6.7 Ventajas

- **Comparte universo y eje X con K1** → no hay listas nuevas; K1 y K2 muestran los **mismos símbolos**.
- **Comparte eje X (σ)** con K1 → visualmente coherente (K1 en Y, K2 en X; mismo concepto).
- **Filtra falsos positivos de K1** → elimina reversiones contra tendencia fuerte (band walking).
- **Cobertura completa** → K1 (reversión) + K2 (tendencia) cubren los dos regímenes en la misma fila.
- **Autoexplicativo** → los cuadrantes y la línea de umbral cuentan la historia.

#### 2.6.8 Detalles técnicos (para ejecutar)

**Ficha del gráfico:**

| Rasgo | Valor |
|---|---|
| Tipo | Scatter (cuadrante) |
| Eje X | `z_banda` (value) · nombre «Posición en banda (σ)» — **compartido con K1** |
| Eje Y | `adx_15` (value) · nombre «ADX 15m» |
| Líneas guía | X = 0 (SMA20) y X = ±k (bandas Bollinger), Y = `adx_min` (umbral ADX) |
| Color | rojo = CORTO (K1) · verde = LARGO (K1) — **mismo color que K1** |
| Orden / corte | score desc · tope = `trading_15m.bollinger_scatter_max` (mismo que K1) |
| Tooltip | Posición (σ) · ADX 15m · Close · Chg % · RSI 15m · Score · badge con `tipo` de K1 |
| Ancho | **4/12** (fila K1/K2/K3) |

**Archivos a crear:**

| Archivo | Contenido |
|---|---|
| `proy_dashboard/services/tendencia_15m_service.py` | `Tendencia15mService(bollinger_service, latest_tick_repo, settings)` · `scan()` consume K1 y filtra por ADX |
| `proy_dashboard/config/charts/K2_tendencia.json` | `meta` (código K2, slug `tendencia_15m`) + bloque `tendencia` |

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `proy_dashboard/web/charts.py` | `scatter_tendencia_option(puntos, *, adx_min=25.0, k=2.0)` (X=σ, Y=ADX, markLine X=0/±k y Y=adx_min, markArea opcional, `tooltipRows`) |
| `proy_dashboard/web/templates/partials/card_chart.html` | Tooltip genérico vía `opt.tooltipRows` (reutilizable por K1 y K2) |
| `proy_dashboard/web/views.py` | `@router.get("/tendencia_15m")` → `_card(...)` con leyenda y nota |
| `proy_dashboard/core/container.py` | import + atributo + wiring de `Tendencia15mService` (con `bollinger_service`) |
| `proy_dashboard/web/templates/dashboard.html` | `<div class="cell seis" hx-get="/partials/tendencia_15m" …>` justo tras el cell de K1 |
| `proy_dashboard/api/routers/trading15m.py` | (opcional) `GET /api/trading15m/tendencias` |
| `proy_dashboard/tests/test_trading_15m.py` | tests de `scan()` con fake `Bollinger15mService` y fake `LatestTickRepo` |

**Config (`config/charts/K2_tendencia.json`):**

```json
{
  "meta": { "tendencia_15m": { "codigo": "K2", "titulo": "Tendencias en Marcha (ADX 15m)" } },
  "tendencia": { "adx_min": 25 }
}
```

> K2 reutiliza `trading_15m.bollinger_scatter_max` para fijar el tope del scan al de K1 → garantiza los mismos símbolos.

#### 2.6.9 Criterios de aceptación

1. El card K2 renderiza datos reales (Bollinger + `latest_market_tick`) sin mock.
2. En la **misma fila** que K1 y K3, **4/12 columnas** cada uno.
3. Líneas guía visibles: X = 0 (SMA20), X = ±2 (bandas Bollinger), Y = `adx_min`.
4. Colores verde/rojo por lado de K1 (CORTO/LARGO); tooltip con `tipo` y datos.
5. K2 muestra **los mismos símbolos que K1** filtrados por ADX (universo compartido).
6. `Tendencia15mService` con tests; suite en verde.

---

## 3. Verificación de la tarjeta "QQQ (NASDAQ-100) — SMA20/SMA50"

Revisé el cálculo de `PrecioService._score` con los datos reales de 2026-10-07 18:35 UTC:

| Activo | Close | RSI | ADX | BBPower | SMA20 | SMA50 | Vol ratio | Momentum | Radar | Score | Señal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 757.55 | 67.8 | 15.8 | +20.93 | 757.12 | 756.80 | 1.06 | 4.81 | 3.68 | **39.4** | VENDER |
| SPY | 777.48 | 60.1 | 10.5 | +11.05 | 777.39 | 777.00 | 1.07 | 4.81 | 3.68 | **39.4** | VENDER |
| IWM | 278.20 | 35.7 | 38.0 | −7.73 | 278.07 | 277.97 | 1.05 | 4.81 | 3.68 | **34.4** | VENDER |
| ORO | 4110.28 | 37.3 | 20.9 | −161.85 | 4111.52 | 4112.90 | 1.02 | 4.81 | 3.68 | **4.4** | VENDER |

**Desglose del score QQQ:**
- `momentum * 3` = 14.4
- `close > sma20` = +25
- `adx < 20` = 0
- `rsi` entre 30 y 70 = 0
- `bbpower > 0` = +10
- `vol_ratio` entre 0.8 y 1.2 = 0
- `radar < 4.5` = −10
- **Total = 39.4** → zona VENDER (≤40)

**Observación:** la señal de VENDER no significa que QQQ esté cayendo fuerte; significa que el score compuesto no alcanza el umbral de compra. El radar está débil (3.68) y resta puntos. Los índices están planos/cercanos a las medias.

---

## 4. Fases de Implementación

| Fase | Entregable | Actividad clave |
|---|---|---|
| **1** | Repositorios | Añadir métodos a `bar_15m_repo` e `indicator_repo` para soportar los nuevos filtros. |
| **2** | Servicios | Crear `momentum_15m_service`, `bollinger_15m_service`, `confluencia_fortaleza_service`, `divergencia_5m_service`, `tendencia_15m_service`. |
| **3** | Gráficos ECharts | Helpers en `web/charts.py` para tablas de oportunidad y dot-plots/scatters (`scatter_bollinger_option`, `scatter_tendencia_option`). |
| **4** | Endpoints y parciales | `/partials/momentum_15m`, `/partials/reversion_bollinger`, `/partials/confluencia_fortaleza`, `/partials/divergencia_5m`, `/partials/vwap_ib`, `/partials/bollinger_scatter` (K1), `/partials/tendencia_15m` (K2). |
| **5** | Dashboard | Ubicar los nuevos paneles en la parte inferior del grid, debajo de la tabla sectorial. |
| **6** | Tests | Tests unitarios de los servicios con datos sintéticos; tests de integración opcionales. |

---

## 5. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Pocas señales de confluencia fuerte con criterios estrictos | Relajar a "2 de 3 timeframes alineados" o añadir versión "2/3 + volumen". |
| Bollinger con pocos datos produce falsos rechazos | Exigir al menos 20 barras y volumen ≥ 1x. |
| Divergencia 5m muy ruidosa | Aumentar `min_sep` entre pivotes y requerir ADX ≥ 15. |
| Duplicación con screener 15m existente | Estos paneles son **filtros de calidad** sobre el screener, no reemplazos. |

---

## 6. Criterios de Aceptación

1. Los paneles de este roadmap (incluye K1 dot-plot y K2 tendencias) renderizan datos reales de BD sin mock.
2. Las filas son clicables y actualizan el gráfico de velas 15m.
3. Los tests de los nuevos servicios pasan.
4. El dashboard mantiene su layout actual; los nuevos paneles van en la parte inferior.
5. Documentación actualizada (este roadmap + `CHANGELOG.md`).

---

## 7. Changelog

- **2026-10-08 (fila J: Momentum · VWAP+IB · Confluencia+Vol)** — Sección **2.5** implementada como **J2** (`/partials/vwap_ib`, **scatter Vol × dist. VWAP**, Opción C) y **2.3** como **J3** (`/partials/confluencia_fuerte`, 5m/15m/1D **+ volumen**). Fila J a **4/12** cada uno, orden **Momentum → VWAP+IB → Confluencia** (impulso → estructura → calidad). Backend: `VwapIbService`, `ConfluenciaService` (+ `vol_map`/`setup`), charts `scatter_vwap_ib_option`. El card J2 (lista Bollinger 15m) se retiró.
- **2026-10-08 (fila K1/K2/K3)** — Los tres paneles analíticos comparten una fila de **4/12 columnas cada uno** (K1 Reversión Bollinger σ, K2 Tendencias ADX, K3 Divergencia 5m).
- **2026-10-08 (K3 Divergencia 5m)** — Sección **2.4** implementada como **scatter RSI ini × RSI fin** (Opción B), card de **4/12**. Backend: `Divergencia5mService` (barras 5m ensambladas desde `fact_market_series`), chart `scatter_divergencia_5m_option`, endpoint `/partials/divergencia_5m`, config `K3_divergencia_5m.json`.
- **2026-10-08 (K2 Tendencias en Marcha)** — Sección **2.6**: card K2 «Tendencias en Marcha (ADX 15m)» como **cuadrante σ × ADX** (Opción D), **4/12 columnas** en la fila K1/K2/K3. Mismo universo y eje X (σ) que K1, filtrado por `ADX 15m ≥ 25`. Incluye figura ASCII, cálculo, matriz de decisión K1×K2, ejemplos reales y detalles técnicos (`K2_tendencia.json`, `scatter_tendencia_option`, tooltip genérico `tooltipRows`, tests). Fases 2–4 actualizadas.
- **2026-10-07** — Creación del roadmap v2.1.0 con análisis de datos reales de `heatmap_stock` (139k series, 28k barras 15m, 259k indicadores tf). Propuesta de 5 nuevos paneles de oportunidad 5–15 min con figuras ASCII, verificación del score de QQQ/SPY/IWM/ORO, fases, riesgos y criterios de aceptación.
