# Fila J — Momentum · VWAP+IB · Confluencia (continuación intradía)

> **Ruta:** `docs/04_dashboard/dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md`
> **Código de fila:** J (J1 · J2 · J3), **4/12 columnas cada uno**, una sola fila.
> **Orden (izq→der):** **J1 Momentum → J2 VWAP+IB → J3 Confluencia**.
> **Endpoints:** `/partials/oportunidad_15m` · `/partials/vwap_ib` · `/partials/confluencia_fuerte`.
> **Configs:** `config/charts/J1_oportunidad.json` · `J2_vwap_ib.json` · `J3_confluencia.json`.

---

## 0. Qué es la fila J

Es la fila de **continuación intradía**: busca activos que **se mueven a favor** (no reversión) y los confirma desde tres ángulos, de lo inmediato a lo amplio.

```
 [J1] Oportunidades Momentum 15m   →  ¿hay IMPULSO con volumen?
 [J2] VWAP + Initial Balance (15m)  →  ¿rompió ESTRUCTURA y tiene flujo a favor?
 [J3] Confluencia Fuerte 5m/15m/1D  →  ¿está ALINEADO en los 3 timeframes?
```

Es un **embudo de confirmación**: J1 encuentra el candidato, J2 confirma la estructura intradía, J3 confirma la calidad multi-TF.

> **Analogía:** es como validar una salida en el mar. J1 dice "hay viento" (movimiento), J2 dice "la vela está orientada" (estructura), J3 dice "la corriente de superficie y la de fondo van igual" (multi-TF).

---

## 1. J1 — Oportunidades Momentum 15m

### 1.1 Qué es

Lista de acciones en **continuación alcista** a 15m, con **confirmación de volumen**. Cada fila es clicable y carga las velas 15m.

```
┌───────────────────────────────────────────────────────┐
│ J1  Oportunidades Momentum · 15m                      │
│ 3 oportunidades · RSI 50-70 · ADX ≥25 · Vol ≥1.2x · >VWAP │
├───────────────────────────────────────────────────────┤
│ [logo] SPOT      [Close 512.38] [RSI 64.3]  [LARGO]   │
│   Chg +0.06% · ADX 51.5 · Vol 1.78x · VWAP +2.57%      │
├───────────────────────────────────────────────────────┤
│ [logo] DIS       [Close 104.78] [RSI 64.0]  [LARGO]   │
│   Chg +0.10% · ADX 26.2 · Vol 1.62x · VWAP +0.81%      │
├───────────────────────────────────────────────────────┤
│ [logo] AMZN      [Close 259.67] [RSI 68.8]  [LARGO]   │
│   Chg +0.11% · ADX 33.1 · Vol 1.25x · VWAP +1.33%      │
└───────────────────────────────────────────────────────┘
```

### 1.2 Por qué aparece cada activo (criterios)

Un equity entra si **todo** se cumple (`Oportunidad15mService._cumple`):

1. **Precio > VWAP** (momentum intradía positivo).
2. **RSI(15) entre 50 y 70** (fuerza sin sobrecompra extrema).
3. **ADX(15) ≥ 25** (tendencia fuerte).
4. **Volumen relativo ≥ 1.2x** (confirmación).
5. **Última barra alcista o plana** (`change_pct ≥ 0`) — se busca continuidad, no reversión.

Los que no cumplen **no aparecen**.

### 1.3 Cómo se calcula

```
VWAP   = Σ(típico · vol) / Σ(vol) sobre las barras 15m
vol_ratio = volumen última barra / media 10 anteriores
score  = (10 − |RSI−60|/2) + ADX/5 + 2·vol_ratio + dist_vwap + change_pct
orden  = score descendente · corte = 4 (oportunidad_max)
```

### 1.4 Casos e interpretación

| Caso | Lectura |
|---|---|
| **Aparace con vol alto (≥1.5x) y ADX alto (>40)** | Continuación **fuerte** (SPOT: vol 1.78x, ADX 51.5). |
| **Aparece con vol bajo (~1.2x)** | Continuación **débil** → esperar que el volumen acompañe (AMZN: vol 1.25x). |
| **RSI cerca de 70** | Fuerza pero **ojo con la sobrecompra** (AMZN 68.8). |
| **No aparece** | No hay movimiento con volumen → no operar. |

- **Ventaja:** filtra ruido; sin volumen el movimiento no sostiene.
- **Nota:** es **long-only** (busca continuación alcista). La versión bajista sería simétrica.

### 1.5 Referencias

- Servicio: `services/oportunidad_15m_service.py`
- Vista: `web/views.py::oportunidad_15m` · Template: `partials/oportunidad_15m.html`
- Datos: `fact_market_bar_15m` (close, volume, vwap), `latest_market_tick` (rsi_15, adx_15).

---

## 2. J2 — VWAP + Initial Balance (15m, estructura)

### 2.1 Qué es

**Scatter** que combina dos estructuras intradía:

- **IB**: ruptura del rango inicial 09:30–10:00 NY.
- **VWAP**: lado del VWAP acumulado.

**Tiempo de evaluación: 15m** (barras de 15 min). Se muestra en el título como la
etiqueta ámbar `15m` (`<span class="ib-time">`), igual que en J3.

Ejes: **X = distancia al VWAP (%)**, **Y = volumen relativo**. Color por lado.

```
 Vol
 3.0 ┤ ●PANW
     │ ●TER  ●CCJ              ← IB DOWN + bajo VWAP = CORTO fuerte
 2.5 ┤
     │ ●TMO ●FTNT ●MCD ●TXN
 2.0 ┤                    │        ●V   ●LOGI
  1  ┤────────────────────┼────────────────────
     └──┬─────┬─────┬─────┼─────┬─────┬─────►
      −3%   −2%   −1%     0    +1%   +2%    dist VWAP
   ◄──── CORTO (IB DOWN) ─┤─ LARGO (IB UP) ────►

 verde = LARGO (IB UP + precio > VWAP) · rojo = CORTO (IB DOWN + precio < VWAP)
 línea vertical en 0 = VWAP
```

> **Botón `(+)`.** El título del card J2 tiene un botón `(+)` que muestra este
> **mapa general** (distancia al VWAP × volumen, con CORTO/LARGO y el anillo de
> confluencia) en un **popup sobrepuesto** al pasar el cursor o dar foco, sin alterar el
> ancho ni el alto del card. El texto se declara en `config/charts/J2_vwap_ib.json`
> (`meta.vwap_ib.ayuda`, lista de líneas), se lee con `Settings.chart_help("vwap_ib")`
> y se renderiza con el mecanismo genérico `ayuda` de
> `web/templates/partials/card_chart.html`.

### 2.2 Por qué aparece cada activo (criterios)

(`VwapIbService.setup`)

- **LARGO**: ruptura **ALCISTA** del IB **y** `close > VWAP` **y** `vol ≥ 1x`.
- **CORTO**: ruptura **BAJISTA** del IB **y** `close < VWAP` **y** `vol ≥ 1x`.
- Si está dentro del IB o del lado incorrecto del VWAP → **no aparece**.

### 2.3 Cómo se calcula

```
IB      = InitialBalanceService.evaluar(símbolo, barras, MARKET_TZ, 30)  → ruptura ALCISTA/BAJISTA/DENTRO
VWAP    = _vwap(barras 15m)[-1]
vol     = _volume_ratio(barras, 10)
dist    = (close − VWAP) / VWAP · 100
setup   = IB roto + lado correcto del VWAP + volumen
orden   = volumen descendente · corte = 10
```

### 2.4 Casos e interpretación

| Caso | Cuadrante | Lectura |
|---|---|---|
| **CORTO fuerte** | X<0 (bajo VWAP), Y alto | PANW −2.80% / 3.00x → rompió IB a la baja, bajo VWAP, con volumen → continuación bajista |
| **CORTO débil** | X<0, Y bajo | TXN −0.36% / 2.32x → apenas bajo VWAP, poca extensión |
| **LARGO fuerte** | X>0, Y alto | LOGI +0.40% / 2.19x → rompió IB al alza, sobre VWAP, con volumen |
| **LARGO débil** | X>0, Y bajo | V +0.32% / 2.26x → sobre VWAP pero poco extendido |

- **Ventaja:** la **estructura** (IB) + el **flujo** (VWAP) son referencias mucho más objetivas que "sube/baja mucho".
- **Coherencia:** es el único **scatter** de la fila, aporta la vista analítica.

### 2.5 Referencias

- Servicio: `services/vwap_ib_service.py`
- Chart: `web/charts.py::scatter_vwap_ib_option` · Vista: `web/views.py::vwap_ib`
- Datos: `fact_market_bar_15m` (OHLCV) + `initial_balance_service`.
- Config: `config/charts/J2_vwap_ib.json` (incluye `meta.vwap_ib.ayuda` = mapa del popup `(+)` y `meta.vwap_ib.tf` = `15m`).
- Ayuda `(+)`: `Settings.chart_help("vwap_ib")` + popup `ayuda` en `web/templates/partials/card_chart.html`.
- Tiempo de evaluación: `Settings.chart_tf("vwap_ib")` → etiqueta `.ib-time` (ámbar) en el título.

---

## 3. J3 — Confluencia Fuerte 5m/15m/1D (+ Volumen)

### 3.1 Qué es

Cuadrícula alineada de **7 columnas fijas**: Símbolo · 5m · 15m · 1D · **Score** · **Volumen (minibarra)** · **Señal BUY/SELL**. Cada símbolo con **★** se repite en **≥2 paneles** de la fila J (confluencia). Al pasar el **mouse sobre el símbolo** aparece un **tooltip** con los datos.

```
        SÍMBOLO       5m    15m   1D   Score   Vol              Señal
[logo] MS  ★          ●      ●     ●    +3   █████░░░░░ 2.29x   BUY
[logo] LOGI            ●      ●     ●    −3   ████░░░░░░ 2.19x   SELL
[logo] SPOT ★          ●      ●     ●    +3   ███░░░░░░░ 1.78x   BUY
[logo] BAC  ★          ●      ●     ●    +3   ██░░░░░░░░ 1.62x   BUY
[logo] DIS  ★          ●      ●     ●    +3   ██░░░░░░░░ 1.62x   BUY
[logo] PG              ●      ●     ●    −3   ██░░░░░░░░ 1.60x   SELL
  …   ★ = en ≥2 paneles de la fila J · minibarra volumen 1.0x→0% · 3.5x→100%
```

Vista previa de la fila real (cuadrícula, no listado): las columnas usan `grid-template-columns` fijas compartidas por cabecera y filas → alineación exacta (tipo E3).

Tooltip (al pasar el mouse sobre el símbolo):

```
┌───────────────────────────────┐
│ NASDAQ:MS                     │
│ 5m            ALCISTA         │
│ 15m           ALCISTA         │
│ 1D            ALCISTA         │
│ RSI 5m/15m/1D 62/58/61        │
│ Score         +3              │
│ Volumen       2.29x           │
│ Setup         ALTA CONVICCIÓN ALCISTA │
└───────────────────────────────┘
```

### 3.2 Por qué aparece cada activo (criterios)

(`ConfluenciaService._analizar` + `vol_map`)

1. **Alineación multi-TF**: `score = signo(5m) + signo(15m) + signo(1D)`.
   - `score ≥ +2` → **COMPRAR/BUY** · `score ≤ −2` → **VENDER/SELL** (la señal se **muestra como BUY/SELL**).
2. **Confirmación por volumen** (panel 2.3):
   - `ALTA CONVICCIÓN {ALCISTA|BAJISTA}` si los TF coinciden **y** `vol ≥ 1x`.
   - `VIGILAR` si coinciden **sin** volumen.
3. Los **NEUTRAL** (dispersión) no se listan.
4. **★ (confluencia)**: marca el símbolo cuando aparece en **≥2 paneles** de la fila J (J1/J2/J3), calculada por el helper `_j_confluencia`.

### 3.3 Cómo se calcula

```
Por timeframe (5m, 15m, 1D):
  rsi extrerno (≥70 → BAJISTA, ≤30 → ALCISTA) regla sobre el cambio
  si no: signo = signo(change_pct)
score  = Σ signos (−3..+3)
signal = COMPRAR si ≥+2 · VENDER si ≤−2 · NEUTRAL si no
vol    = vol_ratio (del screener 15m)
setup  = ALTA CONVICCIÓN si |score|≥2 y vol≥1x · VIGILAR si no
orden  = ALTA primero, luego |score|; corte = 10

Mini barra de volumen:
  vol_pct = clamp((vol − 1.0)/2.5 · 100, 0, 100)   ← 1.0x→0% · 3.5x→100% (celeste uniforme)
```

### 3.4 Casos e interpretación

| Caso | Luces | Señal | Lectura |
|---|---|---|---|
| **ALTA CONVICCIÓN ALCISTA** | ●●● verde | **BUY** | Los 3 TF alcistas **+ volumen** → continuación alcista de alta calidad |
| **ALTA CONVICCIÓN BAJISTA** | ●●● rojo | **SELL** | Los 3 TF bajistas **+ volumen** → continuación bajista de alta calidad |
| **VIGILAR** | ●●○ | — | Coinciden 2 de 3 (o 3/3) **sin** volumen → falta confirmación |
| **NEUTRAL** | mixto | — | Dispersión → no aparece |

- **Ventaja:** reduce falsas entradas; el volumen confirma que la alineación no es solo técnica sino de **flujo**.
- **Coherencia:** cuadrícula de **columnas fijas** (tipo E3) en el mismo card 4/12 que J1/J2; la **minibarra** muestra la magnitud del volumen de forma uniforme (celeste).
- **Tooltip:** evita sobrecargar la fila mostrando los detalles solo on-hover.
- **★:** símbolo presente en ≥2 paneles de la fila J (confluencia).

### 3.5 Referencias

- Servicio: `services/confluencia_service.py` (`scan(vol_map=…)`, `setup`)
- Vista: `web/views.py::confluencia_fuerte` (view model: `ticker`, `n_paneles`, `confluencia`, `vol_pct`; helper `_j_confluencia`)
- Template: `partials/confluencia_fuerte.html` · CSS: `.cf-*` en `web/static/app.css`
- Datos: `fact_market_indicator_tf` (tf 5, 15), `latest_market_tick` (1D), screener (vol).
- Versión heatmap hermana: E3 `/partials/confluencia`.

---

## 4. Cómo se leen juntas (la fila J)

```
┌──────────────┬──────────────┬──────────────────┐
│ J1 Momentum  │ J2 VWAP+IB   │ J3 Confluencia   │
│ "¿impulso?"  │ "¿estructura?"│ "¿calidad?"     │
│ lista        │ scatter      │ cuadrícula 7 col │
└──────┬───────┴──────┬───────┴────────┬─────────┘
       │              │                │
   candidato  →   confirmación  →   filtro final
```

**Ejemplos de confluencia entre paneles (snapshot 2026-10-08):**

| Símbolo | J1 Momentum | J2 VWAP+IB | J3 Confluencia | Lectura |
|---|---|---|---|---|
| **SPOT** | ✅ LARGO (RSI 64.3, ADX 51.5, vol 1.78x) | — | ✅ ALTA CONVICCIÓN ALCISTA | Continuación alcista **confirmada** (impulso + calidad) |
| **LOGI** | — | ✅ LARGO (IB UP, +0.40%, vol 2.19x) | ✅ ALTA CONVICCIÓN BAJISTA | ⚠️ **conflicto**: J2 alcista vs J3 bajista → cuidado |
| **DIS** | ✅ LARGO | — | ✅ ALTA CONVICCIÓN ALCISTA | Continuación alcista (impulso + calidad) |
| **AMZN** | ✅ LARGO | — | ✅ ALTA CONVICCIÓN ALCISTA | Continuación alcista |
| **TXN** | — | ✅ CORTO (bajo VWAP, −0.36%) | — | Estructura bajista, sin alineación multi-TF |

- **Coincidencia en varios paneles** → mayor convicción.
- **Conflicto entre paneles** (p. ej. LOGI J2↑ vs J3↓) → **señal de cautela**; el mercado está en transición.
- **Solo en un panel** → señal aislada; esperar confirmación de los otros.

---

## 5. Analogías

- **Salir a navegar:** J1 = hay viento (impulso); J2 = la vela está orientada (estructura); J3 = superficie y fondo coinciden (multi-TF).
- **Semáforo de la fila:** J1 = luz amarilla "en movimiento"; J2 = verde "estructura OK"; J3 = verde pleno "vía libre".
- **Filtros de café:** J1 deja pasar el movimiento; J2 retiene lo que no rompió estructura; J3 retiene lo que no está alineado.

---

## 6. Ventajas de la fila J

- **Cubre el sesgo de continuación** (complementa la fila K, que es de reversión).
- **Tres ángulos independientes:** impulso (J1) · estructura (J2) · calidad multi-TF (J3).
- **Coherencia visual:** lista → scatter → cuadrícula, todos con el mismo card (4/12) y alineación por columnas.
- **Clicable:** las filas de J1/J3 cargan las velas 15m.
- **Tooltip en J3** para no sobrecargar la vista.

---

## 7. Resumen de decisión

| Aspecto | Decisión |
|---|---|
| **Fila** | J — continuación intradía, **4/12 columnas cada card** |
| **Orden** | **J1 Momentum → J2 VWAP+IB → J3 Confluencia** (impulso → estructura → calidad) |
| **J1 forma** | **Lista** con tags (`.op-*`) · long-only · click → velas |
| **J2 forma** | **Scatter** (Opción C): X = dist. VWAP %, Y = volumen; color LARGO/CORTO |
| **J3 forma** | **Cuadrícula 7 col**: 3 luces 5m/15m/1D + **Score** + **minibarra de volumen** + BUY/SELL + tooltip al hover; **★** de confluencia fila J |
| **J2 reemplaza** | el card de lista de Bollinger 15m (J2 antiguo, retirado) |
| **J3 reemplaza** | el placeholder "Confluencia 5m/15m/1D" |
| **Endpoint J1** | `/partials/oportunidad_15m` |
| **Endpoint J2** | `/partials/vwap_ib` |
| **Endpoint J3** | `/partials/confluencia_fuerte` |
| **Configs** | `J1_oportunidad.json` · `J2_vwap_ib.json` · `J3_confluencia.json` |
| **Tests** | `tests/test_trading_15m.py` (VWAP+IB setup, confluencia + volumen) |

> **Resultado:** la fila J y la fila K juntas cubren **ambos regímenes**: J = continuación (a favor de la tendencia), K = reversión (contra-extensión). Un mismo símbolo puede aparecer en ambas → transición de régimen.

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*