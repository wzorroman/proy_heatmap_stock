# K3 · Divergencia Precio / RSI 5m — scatter RSI ini × RSI fin

> **Código:** K3 · **slug:** `divergencia_5m`
> **Endpoint:** `/partials/divergencia_5m`
> **Config:** `config/charts/K3_divergencia_5m.json`
> **Servicio:** `services/divergencia_5m_service.py`
> **Chart:** `web/charts.py::scatter_divergencia_5m_option`
> **Ubicación en el dashboard:** card de **4/12 columnas**, en la **misma fila** que K1 y K2 (K3 cols 9–12).
> **Documentación complementaria:** [`dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md` §2.4](dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md).

---

## 1. Qué es

Es un **scatter** que muestra cada **divergencia precio/RSI en 5m** como un punto, con:
- **Eje X** = RSI en el **pivote inicial** (5m).
- **Eje Y** = RSI en el **pivote final** (5m).

Mide si el **impulso (RSI) se movió a favor o en contra del precio**, que es la esencia de una divergencia.

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
```

- **Diagonal `y = x`:** frontera. Por **encima** el RSI **subió**; por **debajo** el RSI **bajó**.
- **Color:** verde = **ALCISTA** · rojo = **BAJISTA**.

## 2. Por qué aparece cada activo

Un símbolo entra si se detecta una **divergencia** en sus barras de **5m**:

- **ALCISTA:** el precio hace un **mínimo más bajo** y el RSI, en ese mismo extremo, hace un **mínimo más alto**.
- **BAJISTA:** el precio hace un **máximo más alto** y el RSI hace un **máximo más bajo**.

El universo es el de **equity del último tick** (`latest_market_tick`). Es un panel de **detección temprana**: la versión 5m señala antes que la 15m (D3).

> **Analogía:** es como un **detector de agotamiento**: el precio sigue estirando, pero el "motor" (RSI) ya no acompaña.

## 3. Cómo se calcula

No hay tabla materializada de barras 5m; se **ensamblan desde los ticks** de `fact_market_series`:

```
1. ticks  = bar_repo.fetch_ticks(symbol, now − ventana_horas)
2. barras = Bar15mService.ensamblar_ticks_5m(ticks)      # buckets de 5 min → OHLCV
3. rsi    = RSI Wilder(14) sobre los cierres 5m
4. pivotes de máximo/mínimo locales (k barras a cada lado)
5. comparar los dos últimos pivotes:
     ALCISTA  = low2 < low1  y  rsi2 > rsi1 + rsi_min
     BAJISTA  = high2 > high1 y  rsi2 < rsi1 − rsi_min
6. min_sep = separación mínima (en barras) entre los dos pivotes
```

Lógica de detección compartida con `DivergenciaService.detectar` (15m).

### Config (`config/charts/K3_divergencia_5m.json`)

```json
"divergencia_5m": {
  "ventana_horas": 24,
  "pivote_k": 2,
  "rsi_min": 2.0,
  "min_sep": 5,
  "max": 12,
  "rsi_periodo": 14
}
```

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Eje X** | RSI en el pivote inicial (5m) |
| **Eje Y** | RSI en el pivote final (5m) |
| **Diagonal y = x** | frontera: encima = RSI subió · debajo = RSI bajó |
| **Color** | verde = ALCISTA · rojo = BAJISTA |
| **Tamaño** | constante |
| **Tooltip** | RSI ini · RSI fin · ΔRSI · ΔPrecio · P1 · P2 · badge (ALCISTA/BAJISTA) |
| **Tiempo de evaluación** | etiqueta ámbar `5m` (`.ib-time`) junto al título (mismo estilo que J2/J3) |
| **Ayuda `(+)`** | botón junto al título; al pasar el cursor/foco muestra el **mapa general de lectura** en un popup sobrepuesto (sin alterar el ancho/alto del card) |
| **Ancho** | 4/12 (fila K1/K2/K3) |

### Leyenda en pantalla

```
● verde = ALCISTA (mínimo de precio ↓ con RSI ↑)
● rojo  = BAJISTA (máximo de precio ↑ con RSI ↓)
─ diagonal y = x (RSI sin cambio)
```

## 5. Casos y cómo leer cada uno

### 5.0 Propiedad clave: la diagonal separa perfectamente

Por cómo se detectan, la diagonal `y = x` **no es aproximada, es exacta**:

- **ALCISTA** → `rsi2 > rsi1 + rsi_min` → **siempre por ENCIMA** de la diagonal.
- **BAJISTA** → `rsi2 < rsi1 − rsi_min` → **siempre por DEBAJO** de la diagonal.

El color y el lado de la diagonal son redundantes: ambos confirman el tipo.

### 5.1 Caso ALCISTA (verde, arriba de la diagonal)

```
 RSI fin
 47 ┤            ● fin
    │          ╱
    │        ╱   ← separación = ΔRSI (fuerza)
 43 ┤      ╱
    │    ╱ y = x
 40 ┤  ●╱ ini
    └──────────────────► RSI ini

 Precio: mínimo más BAJO ⬇     RSI: mínimo más ALTO ⬆
```

- **Qué pasó:** el precio hace un **mínimo más bajo**, pero el RSI en ese extremo hace un **mínimo más alto**.
- **Cómo se lee:** la presión **vendedora se agota** — el precio sigue cayendo pero el "motor" (RSI) ya no. Señal de posible **rebote** (giro al alza).
- **Fuerza:** más **lejos** de la diagonal (mayor ΔRSI) = más fuerte.
- **Confluencia:** más fiable si el `RSI ini` está en **sobreventa (< 40)** y el precio está cerca/bajo una banda (K1).
- **Ejemplos:** MSTR 40.4 → 46.6 (ΔRSI +6.2) · TGT 34.0 → 40.2 (ΔRSI +6.2) · PEP 39.7 → 42.7 (ΔRSI +3.0).

### 5.2 Caso BAJISTA (rojo, debajo de la diagonal)

```
 RSI fin
 81 ┤ ●╲ ini
    │    ╲ y = x
 77 ┤      ╲
    │        ╲   ← separación = ΔRSI (fuerza)
 73 ┤          ╲
    │            ● fin
 70 ┤
    └──────────────────► RSI ini

 Precio: máximo más ALTO ⬆     RSI: máximo más BAJO ⬇
```

- **Qué pasó:** el precio hace un **máximo más alto**, pero el RSI hace un **máximo más bajo**.
- **Cómo se lee:** la presión **compradora se agota** — el precio sigue subiendo pero el RSI ya no → posible **corrección** (giro a la baja).
- **Fuerza:** más **lejos** de la diagonal = más fuerte.
- **Confluencia:** más fiable si el `RSI ini` está en **sobrecompra (> 70)** y el precio cerca/sobre una banda superior (K1).
- **Ejemplos:** SHOP 80.1 → 76.6 (ΔRSI −3.5) · AMZN 69.7 → 66.9 (ΔRSI −2.8) · GOOGL 74.6 → 71.9 (ΔRSI −2.6).

### 5.3 Casos por fuerza de la divergencia

| Ubicación | ΔRSI | Lectura |
|---|---|---|
| **Cerca** de la diagonal | ≈ `rsi_min` (2.0) | Divergencia **débil** → poca convicción, pedir más confirmación |
| **Media** | 3–5 | Divergencia **normal** |
| **Lejos** de la diagonal | > 5 | Divergencia **fuerte** → mayor probabilidad de giro |

### 5.4 Casos por nivel de RSI (sobrecompra / sobreventa)

El punto donde caes **a lo largo** de la diagonal indica el **nivel** del RSI (no el cambio):

| Zona | Ejemplo | Lectura |
|---|---|---|
| **Abajo-izquierda** (RSI bajo) + ALCISTA | MSTR 40.4 · TGT 34.0 | Reversión desde **sobreventa** → más fuerte |
| **Arriba-derecha** (RSI alto) + BAJISTA | SHOP 80.1 · GOOGL 74.6 | Reversión desde **sobrecompra** → más fuerte |
| **Centro** (RSI 45–55) | — | Menos fiable (sin extremo de RSI) |

### 5.5 Confluencia con K1 / K2

| K3 | ¿También en K1/K2? | Lectura |
|---|---|---|
| Divergencia | **sí** (extremo de banda) | **Alta convicción** (confluencia) |
| Divergencia | **no** | Señal **temprana** (aún sin extremo) → vigilar |
| Sin divergencia | sí | Extremo sin confirmación de impulso |

> **Hoy:** PEP es la única confluencia — ALCISTA (K3) + banda inferior (K1) + ADX 29.5 (K2).

### 5.6 Mapa mental de la lectura

```
                 RSI fin
                   ▲
   BAJISTA desde   │           ●  (RSI alto → sobrecompra)
   sobrecompra     │         ╱
   (fuerte)        │       ╱
                   │     ╱  diagonal
   ALCISTA desde   │   ╱
   sobreventa   ●  │ ╱
   (fuerte)        └────────────────────► RSI ini
     lejos de la diagonal = fuerte
     cerca de la diagonal = débil
```

> **Botón `(+)`.** Este **mapa general** está disponible en el panel: el botón `(+)`
> junto al título muestra el mismo esquema en un **popup sobrepuesto** al pasar el
> cursor o dar foco (no altera el ancho ni el alto del card). El texto se declara en
> `config/charts/K3_divergencia_5m.json` (`meta.divergencia_5m.ayuda`), se lee con
> `Settings.chart_help("divergencia_5m")` y se renderiza con el mecanismo genérico `ayuda`
> de `web/templates/partials/card_chart.html`.

## 6. Ejemplos reales (snapshot 2026-10-08)

| Ticker | Tipo | RSI ini → fin | ΔRSI | ΔPrecio |
|---|---|---|---:|---:|
| **MSTR** | ALCISTA | 40.4 → 46.6 | +6.2 | −0.02% |
| **TGT** | ALCISTA | 34.0 → 40.2 | +6.2 | −0.02% |
| **PEP** | ALCISTA | 39.7 → 42.7 | +3.0 | −0.01% |
| **SHOP** | BAJISTA | 80.1 → 76.6 | −3.5 | +0.03% |
| **AMZN** | BAJISTA | 69.7 → 66.9 | −2.8 | +0.06% |
| **GOOGL** | BAJISTA | 74.6 → 71.9 | −2.6 | +0.05% |

## 7. Complemento con K1 y K2 (por qué van juntos)

Los tres paneles comparten la misma fila y se leen como una **tríada de confluencia**:

| Panel | Pregunta | Dimensión |
|---|---|---|
| **K1** Reversión Bollinger | ¿Está en un **extremo** de banda? | posición (σ) |
| **K2** Tendencias ADX | ¿Hay **tendencia** fuerte y el extremo es fiable? | régimen (ADX) |
| **K3** Divergencia 5m | ¿El **impulso se agota**? | confirmación (ΔRSI) |

Un mismo símbolo puede aparecer en varios:

- **extremo (K1) + rango (K2) + divergencia (K3)** → reversión de **alta convicción**.
- **extremo + tendencia a favor + divergencia** → continuación con confirmación.
- **extremo + tendencia en contra (band walking)** → descartar, aunque haya divergencia.

**Marcado en el gráfico:** los puntos con **anillo dorado** están en la tríada completa (**K1 ∩ K2 ∩ K3**) → **alta convicción**. El eje X/Y sigue siendo RSI; el anillo es la capa de confluencia.

> **Hoy (2026-10-08):** único con anillo = **PEP** — ALCISTA (K3) + banda inferior (K1) + ADX 29.5 (K2). El resto de K3 (MSTR, TGT, SHOP, AMZN, GOOGL) son señales **tempranas** (aún sin extremo de banda).

## 8. Ventajas

- **Detección temprana:** el 5m avisa antes que el 15m (D3).
- **Representa la esencia:** el eje Y vs la diagonal muestra directamente el movimiento del RSI respecto al precio.
- **Complementa a K1/K2:** añade la dimensión de **agotamiento de impulso** que ninguno de los otros dos tiene.
- **Consistente:** mismo formato de card, leyenda y tooltip genérico (`tooltipRows`) que K1/K2.

## 9. Analogías

- **Motor que pierde fuerza:** el auto (precio) sigue avanzando por inercia, pero el motor (RSI) ya no empuja → el movimiento no se sostiene.
- **Dos corredores:** precio y RSI corren juntos; cuando uno deja de seguir al otro, hay **divergencia**.
- **Termómetro del impulso:** la diagonal es el "0" (RSI sin cambio); alejarse por arriba/abajo mide **cuánto** se movió el RSI.
- **Resorte estirado sin fuerza:** el precio (resorte) se estira, pero la fuerza (RSI) no lo acompaña → vuelve.
- **Brújula:** la diagonal es el "norte" (impulso sin cambio); cada punto es cuánto se **desvió** el impulso.
- **Semáforo del agotamiento:** verde (ALCISTA) = se agota la venta; rojo (BAJISTA) = se agota la compra.

## 10. Referencias de código

| Qué | Dónde |
|---|---|
| Servicio | `services/divergencia_5m_service.py` (ensambla 5m desde ticks + `DivergenciaService.detectar`) |
| Ensamblado 5m | `services/bar_15m_service.py::Bar15mService.ensamblar_ticks_5m` |
| Chart | `web/charts.py::scatter_divergencia_5m_option` |
| Vista | `web/views.py::divergencia_5m` |
| Ayuda `(+)` | texto en `config/charts/K3_divergencia_5m.json` (`meta.divergencia_5m.ayuda`) + `Settings.chart_help` + popup en `web/templates/partials/card_chart.html` |
| Tooltip genérico | `web/templates/partials/card_chart.html` (renderer `tooltipRows`) |
| Config | `config/charts/K3_divergencia_5m.json` (`meta.divergencia_5m.ayuda` + `meta.divergencia_5m.tf = "5m"`) |
| Tiempo de evaluación | `Settings.chart_tf("divergencia_5m")` → etiqueta `.ib-time` (ámbar) en el título |
| Container | `core/container.py` (`divergencia_5m_service`) |
| Dashboard | `web/templates/dashboard.html` (`<div class="cell cuarto">` fila K1/K2/K3) |
| Tests | `tests/test_trading_15m.py` (`test_ensamblar_ticks_5m_agrupa`, `test_divergencia_5m_scan_sin_ticks`) |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*