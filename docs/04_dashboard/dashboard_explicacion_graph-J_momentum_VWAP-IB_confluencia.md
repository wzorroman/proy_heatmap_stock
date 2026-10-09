# Fila J — Momentum · VWAP+IB · Confluencia · Multi-TF (continuación intradía)

> **Ruta:** `docs/04_dashboard/dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md`
> **Código de fila:** J (J1 · J2 · J3 · J4), **2 + 4 + 3 + 3 = 12 columnas**, una sola fila.
> **Orden (izq→der):** **J1 Momentum → J2 VWAP+IB → J3 Confluencia → J4 Multi-TF**.
> **Endpoints:** `/partials/oportunidad_15m` · `/partials/vwap_ib` · `/partials/confluencia_fuerte` · `/partials/multiframe_j4`.
> **Configs:** `config/charts/J1_oportunidad.json` · `J2_vwap_ib.json` · `J3_confluencia.json` · `J4_multiframe.json`.
> **Docs detallados:** [`J1`](dashboard_explicacion_graph-J1_oportunidad_momentum.md) · [`J4`](dashboard_explicacion_graph-J4_multiframe_rsi_5m_15m.md).

---

## 0. Qué es la fila J

Es la fila de **continuación intradía**: busca activos que **se mueven a favor** (no reversión) y los confirma desde cuatro ángulos, de lo inmediato a lo amplio.

```
 [J1] Oportunidades Momentum 15m    →  ¿hay IMPULSO con volumen?        (lista)
 [J2] VWAP + Initial Balance (15m)  →  ¿rompió ESTRUCTURA y tiene flujo? (scatter)
 [J3] Confluencia Fuerte 5m/15m/1D  →  ¿está ALINEADO en 3 timeframes?   (cuadrícula)
 [J4] Multi-TF (RSI 5m vs 15m)      →  ¿coinciden 5m y 15m?              (barras)
```

Es un **embudo de confirmación**: J1 encuentra el candidato, J2 confirma la estructura intradía, J3 confirma la calidad multi-TF y J4 verifica la coherencia de RSI entre los dos TF cortos.

> **Analogía:** validar una salida en el mar. J1 = "hay viento" (movimiento); J2 = "la vela está orientada" (estructura); J3 = "superficie y fondo van igual" (multi-TF); J4 = "el viento de ahora y el de media altura soplan juntos" (RSI 5m ≈ 15m).

Todas las filas J1/J2/J3 son **clicables** (cargan las velas 15m). J4 es un gráfico (no clicable).

---

## 1. J1 — Oportunidades Momentum 15m

### 1.1 Qué es

Lista de acciones en **continuación alcista** a 15m, con **confirmación de volumen**. Cada fila tiene una **barra de impulso** (posición del RSI en la escala 50→100) y es clicable.

```
┌───────────────────────────────────────────────┐
│ J1  Oportunidades Momentum  [15m]  (+)        │
│ 3 oportunidades · RSI 50-70 · ADX ≥25 · Vol ≥1.2x · > VWAP │
├───────────────────────────────────────────────┤
│ 🖼 SBUX ★              [LARGO]                │
│ ▓▓▓▓▓▓▓│▓░░│░░░░░░░░░░  RSI 63   +0.69%       │
│ ADX 41 · Vol 1.47x · VWAP +1.26%              │
├───────────────────────────────────────────────┤
│ 🖼 VZ                  [LARGO]                │
│ ▓▓▓▓▓▓▓│░░│░░░░░░░░░░  RSI 63   +0.06%        │
│ ADX 28 · Vol 2.34x · VWAP +0.67%              │
├───────────────────────────────────────────────┤
│ 🖼 MCD                 [LARGO]                │
│ ▓▓▓▓▓▓▓▓▓│░░░░░░░░░░░  RSI 69   +0.07%        │
│ ADX 41 · Vol 1.56x · VWAP +1.32%              │
└───────────────────────────────────────────────┘
  ██ verde <60 · ██ ámbar 60-70 · ██ rojo ≥70
  │ marcas verticales en RSI 60 y 70 (cortes de color)
```

- **Barra de impulso** = RSI(15) en la escala **50 → 100**: `(RSI − 50) / 50 × 100`. El color indica intensidad: verde (<60), ámbar (60–70), rojo (≥70). El valor `RSI nn` va **dentro** de la barra (texto negro).
- **Marcas verticales** en los cortes de color (RSI 60 al 20% y RSI 70 al 40% de la barra).
- **`%Cambio`** a la derecha (verde ↑ / rojo ↓).
- **★** = el símbolo aparece en **≥2 de los 3 paneles** J1/J2/J3 (`_j_confluencia`).
- **Botón `(+)`** = popup con la leyenda (mecanismo genérico, igual que J2).

### 1.2 Por qué aparece cada activo (criterios)

Un equity entra si **todo** se cumple (`Oportunidad15mService._cumple`):

1. **Precio > VWAP** (momentum intradía positivo).
2. **RSI(15) entre 50 y 70** (fuerza sin sobrecompra extrema).
3. **ADX(15) ≥ 25** (tendencia fuerte).
4. **Volumen relativo ≥ 1.2x** (confirmación).
5. **Última barra alcista o plana** (`change_pct ≥ 0`) — continuidad, no reversión.

Se toman **hasta `oportunidad_max` (4)**, ordenadas por score.

### 1.3 Cómo se calcula

```
VWAP      = Σ(típico · vol) / Σ(vol) sobre las barras 15m
vol_ratio = volumen última barra / media 10 anteriores
score     = (10 − |RSI−60|/2) + ADX/5 + 2·vol_ratio + dist_vwap + change_pct
orden     = score descendente · corte = oportunidad_max (4)
```

### 1.4 Casos e interpretación

| Caso | Lectura |
|---|---|
| **Barra verde (<60) + Vol alto (≥1.5x) + ADX alto** | Continuación **fresca y fuerte** (mejor escenario) |
| **Barra ámbar (60-70) + Vol alto** | Impulso **caliente**; cerca del techo del rango |
| **RSI cerca de 70 (barra roja)** | Fuerza pero **ojo con la sobrecompra** (MCD 68.6) |
| **Vol bajo (~1.2x)** | Continuación **débil** → esperar que el volumen acompañe |
| **No aparece** | No hay movimiento con volumen → no operar |

- **Ventaja:** filtra ruido; sin volumen el movimiento no sostiene.
- **Nota:** es **long-only** (continuación alcista). La versión bajista sería simétrica.

### 1.5 Referencias

- Servicio: `services/oportunidad_15m_service.py`
- Vista: `web/views.py::oportunidad_15m` · Template: `partials/oportunidad_15m.html`
- Datos: `fact_market_bar_15m` (close, volume, vwap), `latest_market_tick` (rsi_15, adx_15).
- Leyenda `(+)`: `Settings.chart_help("oportunidad_15m")` → `config/charts/J1_oportunidad.json` (`meta.oportunidad_15m.ayuda`).
- Documento detallado: [`dashboard_explicacion_graph-J1_oportunidad_momentum.md`](dashboard_explicacion_graph-J1_oportunidad_momentum.md)

---

## 2. J2 — VWAP + Initial Balance (15m, estructura)

### 2.1 Qué es

**Scatter** que combina dos estructuras intradía:

- **IB**: ruptura del rango inicial 09:30–10:00 NY.
- **VWAP**: lado del VWAP acumulado.

**Tiempo de evaluación: 15m** (etiqueta ámbar `15m` en el título). Ejes: **X = distancia al VWAP (%)**, **Y = volumen relativo**. Color por lado.

```
 Vol
 4.8 ┤ ●DE
     │
 2.1 ┤  ●CCJ ●STX          │        ●NFLX
     │ ●CSCO               │   ●KO
 1.7 ┤                     │  ●XOM ●SPOT  ●UPS  ●TGT
 1.0 ┤─────────────────────┼──────────────────────────
     └──┬─────┬──────┬─────┼─────┬─────┬─────┬──────►
      −2%   −1%     0     │   +1%   +2%   +3%   dist VWAP
                  VWAP ────┤
   ◄──── CORTO (IB DOWN) ──┤── LARGO (IB UP) ─────────►

 verde = LARGO (IB UP + precio > VWAP) · rojo = CORTO (IB DOWN + precio < VWAP)
 línea vertical en 0 = VWAP · anillo dorado = confluencia fila J
 (posiciones de un snapshot 2026-10-08: DE, STX, CCJ, CSCO ⇦ | ⇨ NFLX, KO, XOM, SPOT, UPS, TGT)
```

> **Botón `(+)`.** El título de J2 tiene un `(+)` que muestra este **mapa general**
> (distancia al VWAP × volumen, con CORTO/LARGO y el anillo de confluencia) en un
> **popup sobrepuesto**, sin alterar el tamaño del card. El texto se declara en
> `config/charts/J2_vwap_ib.json` (`meta.vwap_ib.ayuda`), se lee con
> `Settings.chart_help("vwap_ib")` y se renderiza con el mecanismo genérico `ayuda` de
> `web/templates/partials/card_chart.html`.

### 2.2 Por qué aparece cada activo (criterios)

(`VwapIbService.setup`)

- **LARGO**: ruptura **ALCISTA** del IB **y** `close > VWAP` **y** `vol ≥ vol_min` (1.0x).
- **CORTO**: ruptura **BAJISTA** del IB **y** `close < VWAP` **y** `vol ≥ vol_min` (1.0x).
- Si está **dentro del IB** o del **lado incorrecto** del VWAP → **no aparece**.

### 2.3 Cómo se calcula

```
IB      = InitialBalanceService.evaluar(símbolo, barras, MARKET_TZ, 30)  → ALCISTA/BAJISTA/DENTRO
VWAP    = _vwap(barras 15m)[-1]
vol     = _volume_ratio(barras, 10)
dist    = (close − VWAP) / VWAP · 100
setup   = IB roto + lado correcto del VWAP + volumen (vol_min = 1.0)
orden   = volumen descendente · corte = max (10)
```

### 2.4 Casos e interpretación

| Caso | Cuadrante | Lectura |
|---|---|---|
| **CORTO fuerte** | X<0 (bajo VWAP), Y alto | DE −0.21% / 4.76x → rompió IB a la baja, bajo VWAP, con volumen → continuación bajista |
| **CORTO débil** | X<0, Y bajo | STX −1.95% / 2.05x → bajo VWAP, extensión media |
| **LARGO fuerte** | X>0, Y alto | SPOT +2.40% / 1.73x → rompió IB al alza, sobre VWAP, con volumen |
| **LARGO débil** | X>0, Y bajo | TGT +1.10% / 1.66x → sobre VWAP pero poco extendido |

- **Ventaja:** la **estructura** (IB) + el **flujo** (VWAP) son referencias mucho más objetivas que "sube/baja mucho".
- **Coherencia:** es el único **scatter** de la fila, aporta la vista analítica.

### 2.5 Referencias

- Servicio: `services/vwap_ib_service.py` (`scan`, `setup`)
- Chart: `web/charts.py::scatter_vwap_ib_option` · Vista: `web/views.py::vwap_ib`
- Datos: `fact_market_bar_15m` (OHLCV) + `initial_balance_service`.
- Config: `config/charts/J2_vwap_ib.json` (incluye `meta.vwap_ib.ayuda` = mapa del `(+)` y `meta.vwap_ib.tf` = `15m`).
- Ayuda `(+)`: `Settings.chart_help("vwap_ib")` · Tiempo: `Settings.chart_tf("vwap_ib")` → etiqueta `.ib-time`.

---

## 3. J3 — Confluencia Fuerte 5m/15m/1D (+ Volumen)

### 3.1 Qué es

Cuadrícula alineada de **columnas fijas**: **Símbolo · 5m · 15m · 1D · Vol · Señal**. Cada símbolo con **★** se repite en **≥2 paneles** de la fila J (confluencia). Al pasar el **mouse sobre el símbolo** aparece un **tooltip** con los datos (incluido el **Score**, que ya **no** ocupa columna).

```
        SÍMBOLO     5m    15m   1D    Vol              Señal
[logo] CSCO         ●      ●     ●   ████░░░░ 1.74x   SELL
[logo] STX ★        ●      ●     ●   ██████░ 2.05x    SELL
[logo] LOGI         ●      ●     ●   ████░░░░ 1.54x   SELL
[logo] DDOG         ●      ●     ●   ██░░░░░░ 1.26x   BUY
[logo] SHOP         ●      ●     ●   ██░░░░░░ 1.12x   SELL
  …   ★ = en ≥2 paneles de la fila J · minibarra volumen 1.0x→0% · 3.5x→100%
      ● verde = ALCISTA · ● rojo = BAJISTA · ● gris = NEUTRAL(dentro del tooltip)
```

Vista previa de la fila real (cuadrícula con `grid-template-columns` fijas compartidas por cabecera y filas → alineación exacta, tipo E3).

Tooltip (al pasar el mouse sobre el símbolo):

```
┌───────────────────────────────┐
│ NASDAQ:CSCO                   │
│ 5m            BAJISTA         │
│ 15m           BAJISTA         │
│ 1D            BAJISTA         │
│ RSI 5m/15m/1D 62/58/61        │
│ Score         -3              │
│ Volumen       1.74x           │
│ Setup         ALTA CONVICCIÓN BAJISTA │
└───────────────────────────────┘
```

### 3.2 Por qué aparece cada activo (criterios)

(`ConfluenciaService._analizar` + `vol_map`)

1. **Alineación multi-TF**: `score = signo(5m) + signo(15m) + signo(1D)`.
   - `score ≥ +2` → **COMPRAR/BUY** · `score ≤ −2` → **VENDER/SELL** (la señal se **muestra como BUY/SELL**).
2. **Confirmación por volumen** (panel 2.3):
   - `ALTA CONVICCIÓN {ALCISTA|BAJISTA}` si los TF coinciden **y** `vol ≥ 1.0x`.
   - `VIGILAR` si coinciden **sin** volumen (vol < 1.0x).
3. Los **NEUTRAL** (dispersión) **no se listan** (filtro `if f.get("setup")`).
4. **★ (confluencia)**: símbolo en **≥2 paneles** de la fila J (J1/J2/J3), helper `_j_confluencia`.

### 3.3 Cómo se calcula

```
Por timeframe (5m, 15m, 1D):
  RSI extremo (≥70 → BAJISTA, ≤30 → ALCISTA)
  si no: signo = signo(change_pct)
score  = Σ signos (−3..+3)
signal = COMPRAR si ≥+2 · VENDER si ≤−2 · NEUTRAL si no
vol    = vol_ratio (del screener 15m)
setup  = ALTA CONVICCIÓN si |score|≥2 y vol≥1.0x · VIGILAR si no
orden  = ALTA primero, luego |score| desc · corte = max (10)

Mini barra de volumen:
  vol_pct = clamp((vol − 1.0) / 2.5 · 100, 0, 100)   ← 1.0x→0% · 3.5x→100% (celeste uniforme)
```

### 3.4 Casos e interpretación

| Caso | Luces | Señal | Lectura |
|---|---|---|---|
| **ALTA CONVICCIÓN ALCISTA** | ●●● verde | **BUY** | Los 3 TF alcistas **+ volumen** → continuación alcista de alta calidad |
| **ALTA CONVICCIÓN BAJISTA** | ●●● rojo | **SELL** | Los 3 TF bajistas **+ volumen** → continuación bajista de alta calidad |
| **VIGILAR** | ●●○ | — | Coinciden 2 de 3 (o 3/3) **sin** volumen → falta confirmación |
| **NEUTRAL** | mixto | — | Dispersión → **no aparece** |

- **Ventaja:** reduce falsas entradas; el volumen confirma que la alineación no es solo técnica sino de **flujo**.
- **Coherencia:** cuadrícula de **columnas fijas** (tipo E3); la **minibarra** muestra la magnitud del volumen de forma uniforme (celeste).
- **Tooltip:** evita sobrecargar la fila mostrando los detalles (Score, RSI, Setup) solo on-hover.
- **★:** símbolo presente en ≥2 paneles de la fila J (confluencia).

### 3.5 Referencias

- Servicio: `services/confluencia_service.py` (`scan(vol_map=…)`, `_analizar`, `estado_tf`)
- Vista: `web/views.py::confluencia_fuerte` (orden `ALTA` → `|score|`; corte `confluencia_fuerte.max` = 10; `vol_pct`; helper `_j_confluencia`)
- Template: `partials/confluencia_fuerte.html` · CSS: `.cf-*` en `web/static/app.css`
- Datos: `fact_market_indicator_tf` (tf 5, 15), `latest_market_tick` (1D), screener (vol).
- Versión heatmap hermana: E3 `/partials/confluencia`.

---

## 4. J4 — Multi-TF (RSI 5m vs 15m)

### 4.1 Qué es

**Gráfico de barras horizontales agrupadas** (ECharts `bar`, `compact=True`): por cada acción, **barra azul = RSI 5m** y **barra ámbar = RSI 15m** (escala 0–100). El `[logo][ticker]` va **delante** de las barras (watermark). Sin números sobre las barras (solo tooltip).

```
J4  Multi-TF (RSI 5m vs 15m)
8 acciones · 5m y 15m ambos <40 o >60 · orden por promedio (5m+15m)/2

 PEP  ├────────────────────────────▓▓▓▓▓▓▓▓▓▓▓  5m 70 / 15m 73
SBUX  ├──────────────────────────────▓▓▓▓▓▓▓▓  5m 79 / 15m 63
AAPL  ├──────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓  5m 67 / 15m 74
 PG   ├──────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓  5m 65 / 15m 68
ABBV  ├────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓▓▓  5m 68 / 15m 63
SHOP  ├──────▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░                5m 39 / 15m 38
 UNH  ├─────▓▓▓▓▓▓▓▓▓▓▓▓░░                  5m 37 / 15m 36
 WDC  ├──────▓▓▓▓▓▓▓▓▓▓▓▓▓▓░                5m 38 / 15m 35
      ◄──── BAJO (<40) ──│─── ALTO (>60) ───►
                        50
```

### 4.2 Por qué aparece cada activo (criterios)

(`views.py::_multiframe_data`)

1. **Pool 1D**: `top_equity_rsi()` (acciones de **mayor capitalización con RSI 1D ≥ 60 o ≤ 40**).
2. **Tiene RSI 5m y RSI 15m**.
3. **Alineación corta**: **`(RSI5m < 40 y RSI15m < 40)`** **o** **`(RSI5m > 60 y RSI15m > 60)`**.
4. **Orden**: **promedio `(5m + 15m) / 2` descendente** (el más caliente intradía arriba).

> El **RSI 1D solo define el pool**, **no** el orden ni el filtro. Puede aparecer un nombre con 1D "bajo" en la zona ALTA (PEP: 1D 39.8 → 5m 70.4 / 15m 73.0).

### 4.3 Casos e interpretación

| Caso | RSI 5m / 15m | Lectura |
|---|---|---|
| **ALTO alineado** | ambos **> 60** | Impulso alcista coherente en los dos TF cortos |
| **BAJO alineado** | ambos **< 40** | Presión bajista coherente en los dos TF cortos |
| **5m > 15m** | azul más larga | Impulso **acelerando** (vigilar sobre-extensión) |
| **15m > 5m** | ámbar más larga | Posible **agotamiento** del impulso |
| **1D vs corto divergen** | — | **Transición de régimen** (PEP/SHOP): la señal más rica |

### 4.4 Referencias

- Vista: `web/views.py::multiframe_j4` · Chart: `web/charts.py::multiframe_option(..., compact=True)`
- Config: `config/charts/J4_multiframe.json` (incluye `meta.multiframe_j4.ayuda` = mapa del `(+)`) · CSS: `.cell.fill.j4` en `web/static/app.css`
- Ayuda `(+)`: `Settings.chart_help("multiframe_j4")` + popup `ayuda` en `web/templates/partials/card_chart.html`
- Documento detallado: [`dashboard_explicacion_graph-J4_multiframe_rsi_5m_15m.md`](dashboard_explicacion_graph-J4_multiframe_rsi_5m_15m.md)

> **⚠️ Precisión del dibujo:** las **líneas guía** de J4 están en **RSI 30/70** (extremos), pero el **filtro** de selección usa **40/60**. No confundir "el borde de la línea" con el corte real del filtro.

---

## 5. Cómo se leen juntas (la fila J)

```
┌──────────────┬──────────────┬───────────────┬──────────────┐
│ J1 Momentum  │ J2 VWAP+IB   │ J3 Confluencia│ J4 Multi-TF  │
│ "¿impulso?"  │ "¿estructura?"│ "¿calidad?"  │ "¿5m≈15m?"   │
│ lista        │ scatter      │ cuadrícula    │ barras       │
└──────┬───────┴──────┬───────┴──────┬────────┴──────┬───────┘
       │              │              │               │
   candidato  →   confirmación  →   filtro final  →  coherencia
```

**Ejemplos de confluencia entre paneles (snapshot 2026-10-08):**

| Símbolo | J1 Momentum | J2 VWAP+IB | J3 Confluencia | J4 Multi-TF | Lectura |
|---|---|---|---|---|---|
| **SBUX** | ✅ LARGO (RSI 63.1, ADX 41) | — | — | 🔄 ALTO (5m 78.5 / 15m 63.1) | Impulso confirmado, 5m **sobre-extendido** |
| **SHOP** | — | — | ✅ BAJISTA 3/3 (vol 1.12) | 🔄 BAJO (1D 68.9 → 38.9/38.3) | **Giro bajista** coherente J3+J4 |
| **STX** | — | ✅ CORTO (vol 2.05) | ✅ BAJISTA 3/3 (vol 2.05) | — | Estructura + alineación bajista con volumen |
| **PEP** | — | — | — | 🔄 ALTO (1D 39.8 → 70.4/73.0) | **Rebote intradía** sobre 1D frío |

- **Coincidencia en varios paneles** → mayor convicción.
- **Conflicto entre paneles** → **señal de cautela**; el mercado está en transición.
- **Solo en un panel** → señal aislada; esperar confirmación de los otros.

---

## 6. Analogías

- **Salir a navegar:** J1 = hay viento (impulso); J2 = la vela está orientada (estructura); J3 = superficie y fondo coinciden (multi-TF); J4 = viento de ahora y de media altura soplan juntos (RSI 5m≈15m).
- **Semáforo de la fila:** J1 = amarillo "en movimiento"; J2 = verde "estructura OK"; J3 = verde pleno "vía libre"; J4 = verde de "coherencia".
- **Filtros de café:** J1 deja pasar el movimiento; J2 retiene lo que no rompió estructura; J3 retiene lo que no está alineado; J4 retiene lo que no coincide en 5m/15m.

---

## 7. Resumen de decisión

| Aspecto | Decisión |
|---|---|
| **Fila** | J — continuación intradía, **2+4+3+3 = 12 columnas** |
| **Orden** | **J1 Momentum → J2 VWAP+IB → J3 Confluencia → J4 Multi-TF** |
| **J1 forma** | **Lista** con barra de impulso (`.op-*`) · long-only · click → velas · `(+)` |
| **J2 forma** | **Scatter**: X = dist. VWAP %, Y = volumen; color LARGO/CORTO · `(+)` |
| **J3 forma** | **Cuadrícula**: 3 luces 5m/15m/1D + **minibarra de volumen** + BUY/SELL + tooltip (Score, RSI, Setup); **★** de confluencia fila J |
| **J4 forma** | **Barras horizontales** agrupadas RSI 5m/15m, `compact`, watermark `[logo][ticker]` · `(+)` |
| **J2 reemplaza** | el card de lista de Bollinger 15m (J2 antiguo, retirado) |
| **J3 reemplaza** | el placeholder "Confluencia 5m/15m/1D" |
| **J4 reemplaza** | el H2 Multi-TF (retirado del dashboard); reutiliza su endpoint `multiframe` como gemelo no-compacto |
| **Endpoints** | `/partials/oportunidad_15m` · `/partials/vwap_ib` · `/partials/confluencia_fuerte` · `/partials/multiframe_j4` |
| **Configs** | `J1_oportunidad.json` · `J2_vwap_ib.json` · `J3_confluencia.json` · `J4_multiframe.json` |
| **Tests** | `tests/test_trading_15m.py` (VWAP+IB setup, confluencia + volumen) |

> **Resultado:** la fila J y la fila K juntas cubren **ambos regímenes**: J = continuación (a favor de la tendencia), K = reversión (contra-extensión). Un mismo símbolo puede aparecer en ambas → transición de régimen.

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
