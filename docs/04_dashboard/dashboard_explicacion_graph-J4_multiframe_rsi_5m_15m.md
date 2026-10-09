# J4 · Multi-TF (RSI 5m vs 15m) — alineación intradía de la selección 1D

> **Código:** J4 · **slug:** `multiframe_j4`
> **Endpoint:** `/partials/multiframe_j4`
> **Config:** `config/charts/J4_multiframe.json`
> **Servicio:** `services/heatmap_service.py::HeatmapService.top_equity_rsi` + `services/indicator_service.py::por_indicador`
> **Chart:** `web/charts.py::multiframe_option(..., compact=True)`
> **Vista:** `web/views.py::multiframe_j4` (helper `_multiframe_data`)
> **Plantilla:** `web/templates/partials/card_chart.html`
> **Ubicación en el dashboard:** card `cell tres fill j4` (**3/12 columnas**), al final de la **fila J** (J1+J2+J3+J4 = 2+4+3+3 = 12).
> **Forma:** **gráfico de barras horizontales agrupadas** (ECharts `bar`), 2 series: **RSI 5m** (azul) y **RSI 15m** (ámbar).
> **Leyenda:** botón `(+)` en el título → popup con el mapa (ver §4).
> **Gemelo histórico:** `/partials/multiframe` (H2, no-compacto) quedó **retirado del dashboard**; su única aparición viva es J4.

---

## 0. Panorama general

La **fila J** es la zona de **continuación intradía**: busca activos a favor del movimiento y los confirma desde cuatro ángulos. J4 cierra la fila respondiendo la última pregunta: **¿los timeframes cortos (5m y 15m) están alineados entre sí?**

```
[J1] Oportunidades Momentum 15m → ¿hay IMPULSO con volumen?         (lista)
[J2] VWAP + Initial Balance     → ¿rompió ESTRUCTURA con flujo?      (scatter)
[J3] Confluencia Fuerte 5m/15m/1D → ¿está ALINEADO en 3 timeframes?  (cuadrícula)
[J4] Multi-TF (RSI 5m vs 15m)   → ¿coinciden 5m y 15m?               (barras)
```

J4 **no filtra por dirección de precio** como J3: compara la **magnitud del RSI** en los dos timeframes cortos. Es el **chequeo de coherencia intradía**.

> **Analogía:** J3 es el parte meteorológico de 3 días; **J4 es la foto de ahora**: ¿el viento de superficie (5m) y el de media altura (15m) soplan juntos?

---

## 1. Qué es J4

Es un **gráfico de barras horizontales agrupadas** donde **cada acción** (fila del eje Y) tiene **dos barras**:

- **Barra azul** = RSI de **5m**.
- **Barra ámbar** = RSI de **15m**.

Cada barra se dibuja en la escala **0–100**. Solo se listan las acciones de la **selección RSI 1D top** (mayor capitalización en oportunidad 1D) cuyo **RSI 5m y RSI 15m están ambos por encima de 60 o ambos por debajo de 40**.

```
J4  Multi-TF (RSI 5m vs 15m)
8 acciones · 5m y 15m ambos <40 o >60 · orden por promedio (5m+15m)/2

 RSI  0        30    40        60    70       100
      │         ╎     ╎         ╎     ╎         │
 PEP  ├────────────────────────────▓▓▓▓▓▓▓▓▓▓▓  RSI 5m 70
      ├─────────────────────────────▓▓▓▓▓▓▓▓▓▓  RSI 15m 73
 SBUX ├──────────────────────────────▓▓▓▓▓▓▓▓  RSI 5m 79
      ├──────────────────────────▓▓▓▓▓▓▓▓▓▓▓    RSI 15m 63
 AAPL ├──────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓▓  RSI 5m 67
      ├────────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓  RSI 15m 74
  PG  ├──────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓    RSI 5m 65
      ├───────────────────────────▓▓▓▓▓▓▓▓▓▓▓    RSI 15m 68
 ABBV ├────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  RSI 5m 68
      ├────────────────────────▓▓▓▓▓▓▓▓▓▓▓▓▓▓    RSI 15m 63
 SHOP ├──────▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░                RSI 5m 39
      ├──────▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░               RSI 15m 38
  UNH ├─────▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░                 RSI 5m 37
      ├─────▓▓▓▓▓▓▓▓▓▓▓▓░░                   RSI 15m 36
  WDC ├──────▓▓▓▓▓▓▓▓▓▓▓▓▓▓░                 RSI 5m 38
      ├─────▓▓▓▓▓▓▓▓▓▓▓▓░░                   RSI 15m 35
      ◄──────── BAJO (<40) ───│─── ALTO (>60) ────────►
                              50
```

- **Zona ALTA** (derecha): RSI 5m y 15m **ambos > 60**.
- **Zona BAJA** (izquierda): RSI 5m y 15m **ambos < 40**.
- Como el filtro exige que **ambos** TF estén del mismo lado, **no hay mezclas** dentro de una fila: la fila es o "todo caliente" o "todo frío".

---

## 2. Por qué aparece cada activo (criterios)

(`views.py::_multiframe_data`)

Un símbolo entra si cumple **todo**:

1. **Está en la selección 1D top**: `heatmap_service.top_equity_rsi()` → acciones de **mayor capitalización** con **RSI 1D ≥ 60 o ≤ 40** (parámetros `rsi.oportunidad_alto` = 60, `rsi.oportunidad_bajo` = 40). Es el **pool** del gráfico (100 por defecto, `rsi.scatter_max`).
2. **Tiene RSI 5m y RSI 15m** calculados (`indicator_service.por_indicador("rsi", "5"/"15")`).
3. **Alineación de corto plazo**: **`(RSI5m < 40 y RSI15m < 40)`** **o** **`(RSI5m > 60 y RSI15m > 60)`**.

4. **Orden**: **promedio de RSI `(5m + 15m) / 2` descendente** → primero el activo más caliente.

> ⚠️ **El RSI 1D solo define el pool, NO el orden ni el filtro.** Por eso puede aparecer una acción con 1D "bajo" en la zona ALTA (p. ej. **PEP**: 1D 39.8 → pool BAJO, pero 5m 70.4 y 15m 73.0 → zona ALTA y arriba por promedio). Ese contraste es, precisamente, la información valiosa (ver §5.3).

Los que no cumplen **no aparecen**.

---

## 3. Cómo se calcula

```
1. pool = top_equity_rsi()                    → RSI 1D top-cap con RSI 1D ∈ [0,40] ∪ [60,100]
           (100 símbolos por defecto, rsi.scatter_max)

2. rsi5_map  = {symbol: rsi5}    (último indicador tf="5")
   rsi15_map = {symbol: rsi15}   (último indicador tf="15")

3. filtrar:  symbol ∈ pool  ∧  ( (rsi5<40 ∧ rsi15<40) ∨ (rsi5>60 ∧ rsi15>60) )

4. ordenar:  (rsi5 + rsi15) / 2 DESC  ← primero el más caliente intradía

5. series:   "RSI 5m"  = [rsi5  de cada symbol]
             "RSI 15m" = [rsi15 de cada symbol]
```

### Parámetros

| Clave | Valor | Origen | Uso |
|---|---|---|---|
| `rsi.oportunidad_alto` | **60** | `H1_rsi_limites.json` | umbral ALTO del filtro 5m/15m y del pool 1D |
| `rsi.oportunidad_bajo` | **40** | `H1_rsi_limites.json` | umbral BAJO del filtro 5m/15m y del pool 1D |
| `rsi.scatter_max` | **100** | `H1_rsi_limites.json` | tamaño máximo del pool 1D |

> **Nota de coherencia visual.** Las **líneas guía** dibujadas en el gráfico están en **RSI 30 y 70** (verde/rojo punteadas, `markLine` en `multiframe_option`), mientras que el **filtro** usa **40 y 60**. Es decir, las líneas marcan los **extremos de sobrecompra/sobreventa** (contexto), no el umbral exacto del filtro. Ver §7 (punto a vigilar).

---

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Barra azul (`RSI 5m`)** | RSI del timeframe de 5 minutos (0–100) |
| **Barra ámbar (`RSI 15m`)** | RSI del timeframe de 15 minutos (0–100) |
| **Eje X** | RSI (0–100); líneas guía punteadas en **30** (verde) y **70** (rojo) |
| **Eje Y** | una fila por acción; en `compact` el eje se oculta |
| **Watermark `[logo][ticker]`** | identidad del activo, **delante de las barras**, alineado a la derecha |
| **Tooltip** | al pasar el mouse: valores de RSI 5m/15m de esa fila (trigger `axis`, shadow) |
| **Sin valores en la barra** | en `compact=True` el número se ve solo en el tooltip (gráfico limpio) |
| **Ancho 98%** | el card se estira casi por completo para aprovechar los 3/12 |
| **Ayuda `(+)`** | popup sobrepuesto con esta **leyenda** (botón junto al título, patrón J2) |

### Leyenda (botón `(+)`)

El título de J4 tiene un botón **`(+)`** que muestra el **mapa/leyenda** en un **popup sobrepuesto** (CSS `.chart-help`/`.chart-help-pop`, mismo patrón que J2):

```
Mapa general — Multi-TF (RSI 5m vs 15m)
Eje X = RSI (0-100) · azul = RSI 5m · ámbar = RSI 15m

  RSI  0      30    40        60    70      100
       │       ┊     ┊         ┊     ┊        │
 ABBV  ├──────────────────────▓▓▓▓▓▓▓▓▓▓▓▓▓▓
       ├──────────────────────▓▓▓▓▓▓▓▓▓▓▓▓
 SHOP  ├─────▓▓▓▓▓▓▓▓▓▓▓▓░░
       ◄── BAJO (<40) ──┼── ALTO (>60) ──►

  Selección: RSI 1D top (mayor capitalización)
  Filtro: RSI 5m y 15m ambos <40 o ambos >60
  Orden: promedio (5m+15m)/2 descendente
  5m más largo que 15m = impulso acelerando
  15m más largo que 5m = posible agotamiento
  ⚠ líneas guía del gráfico en 30/70; el filtro usa 40/60
```

El texto se declara en `config/charts/J4_multiframe.json` (`meta.multiframe_j4.ayuda`, lista de líneas), se lee con `Settings.chart_help("multiframe_j4")` y se renderiza con el mecanismo genérico `ayuda` de `web/templates/partials/card_chart.html`.

Modo **compact** (el de J4, `ancho="98%"`):
- `grid` al mínimo (`left/right: 4`, `top: 22`, `bottom: 16`).
- `axisLabel` del eje Y × símbolos **oculto**; en su lugar va el **watermark** con `[logo][ticker]`.
- `barWidth 16%`, `barGap 55%`, `barCategoryGap 30%` → barras finas y aireadas.
- `label.show = False` (sin números sobre las barras).

---

## 5. Casos y cómo leerlos

### 5.1 Casos por zona

| Caso | RSI 5m / 15m | Lectura |
|---|---|---|
| **ALTO alineado** | ambos **> 60** | Impulso alcista coherente en 5m y 15m → continuación de corto |
| **BAJO alineado** | ambos **< 40** | Presión bajista coherente en 5m y 15m → continuación de caída |
| **Sin fila** | no alineados (p. ej. 5m 55 / 15m 72) | **No aparece**: los TF cortos no coinciden |

### 5.2 Casos por separación entre las dos barras (5m vs 15m)

| Separación | Lectura |
|---|---|
| **Barras casi iguales** | 5m y 15m en sintonía → señal **limpia** |
| **La barra de 5m más larga** (5m > 15m) | El corto plazo está **más caliente** que el medio → impulso **acelerando** (vigilar sobre-extensión) |
| **La barra de 15m más larga** (15m > 5m) | El medio ya venía caliente y el 5m se **enfría** → posible **agotamiento** del impulso |

### 5.3 Casos por relación con el RSI 1D (el pool)

| 1D | 5m/15m | Lectura |
|---|---|---|
| ALTO (≥60) | ALTO (>60) | **Confirmación total**: diario y corto alineados |
| ALTO (≥60) | BAJO (<40) | **Giro bajista intradía** sobre nombre caliente (p. ej. **SHOP**: 1D 68.9 → 5m/15m ~38) |
| BAJO (≤40) | ALTO (>60) | **Rebote intradía** sobre nombre frío (p. ej. **PEP**: 1D 39.8 → 5m 70.4 / 15m 73.0) |
| BAJO (≤40) | BAJO (<40) | **Confirmación total a la baja** |
| — | extremos (5m 79) | **Sobre-extensión de corto** → riesgo de retroceso (**SBUX**: 5m 78.5) |

### 5.4 Qué **no** dice J4

- **No** da orden de compra/venta (a diferencia de J3). Solo muestra **estado de RSI** en dos TF.
- **No** mide estructura de precio (VWAP/IB): eso es J2.
- **No** mide volumen: eso es J1/J3.
- **No** es "multi-TF completo": compara **5m vs 15m**; el 1D solo entra como pool (no ordena ni filtra).

---

## 6. Ejemplos reales (snapshot 2026-10-08)

**8 acciones en J4** (ambos TF cortos alineados). Se muestran **como aparecen en el gráfico**: ordenadas por **promedio `(5m+15m)/2` descendente** (el más caliente arriba).

| Ticker | RSI 1D (pool) | RSI 5m | RSI 15m | Prom. | Zona | Lectura |
|---|---|---:|---:|---:|---:|---|---|
| **PEP** | **39.8** | **70.4** | **73.0** | **71.7** | ALTO | 🔄 **Rebote**: 1D frío, 5m/15m calientes |
| **SBUX** | **32.8** | **78.5** | **63.1** | **70.8** | ALTO | 🔄 **Rebote + 5m sobre-extendido** (5m ≫ 15m) |
| **AAPL** | 62.0 | 66.5 | 73.6 | 70.0 | ALTO | 15m más caliente → venía fuerte; 5m aún >60 |
| **PG** | 60.9 | 65.0 | 68.2 | 66.6 | ALTO | Alineado, sintonía media |
| **ABBV** | 66.4 | 68.0 | 62.6 | 65.3 | ALTO | Alineado alcista, 5m algo por encima de 15m |
| **SHOP** | **68.9** | **38.9** | **38.3** | **38.6** | BAJO | 🔄 **Giro bajista intradía** sobre nombre caliente |
| **UNH** | 39.9 | 37.3 | 36.2 | 36.8 | BAJO | Alineado bajista |
| **WDC** | 37.0 | 38.3 | 34.8 | 36.6 | BAJO | Alineado bajista (15m más frío) |

El gradiente es **continuo de arriba a abajo**: PEP (71.7) en la cima → WDC (36.6) al fondo. Como el filtro exige ambos TF del mismo lado, no hay filas en 40–60; el bloque ALTO y el bloque BAJO quedan agrupados.

Lecturas destacadas:
- **SBUX** tiene la **mayor separación** (5m 78.5 vs 15m 63.1): el corto plazo está mucho más caliente → impulso acelerando, con **riesgo de retroceso**.
- **PEP** y **SHOP** son los dos **cruces de régimen** (1D contra intradía): los casos más informativos.
- **AAPL** muestra 15m (73.6) > 5m (66.5) → el medio venía más caliente; el 5m se enfría un poco.

---

## 7. Cómo leerlo (paso a paso)

1. **¿En qué zona está la fila?**
   - Todas las barras a la **derecha (>60)** → clima intradía comprador.
   - Todas a la **izquierda (<40)** → clima intradía vendedor.
2. **Compara las dos barras de cada fila**: ¿la azul (5m) o la ámbar (15m) es más larga?
   - 5m > 15m → aceleración.
   - 15m > 5m → posible agotamiento.
3. **Cruza con el orden**: J4 ordena por **promedio `(5m+15m)/2` desc**, así que las primeras filas son las **más calientes intradía** y las últimas las **más frías** (gradiente continuo).
4. **Busca cruces 1D↔intradía** (PEP, SHOP): son transiciones de régimen, la señal más rica del panel.
5. **Combínalo con la fila J** (§8): si J4 coincide con J2/J3, sube la convicción; si **contradice**, cautela.

**Punto a vigilar (precisión del dibujo):** las **líneas guía** del gráfico están en **30/70** (extremos de sobrecompra/sobreventa), pero el **filtro** que decide qué acciones aparecen usa **40/60**. Al mirar el gráfico, no interpretes "el borde de las líneas" como el corte del filtro; el corte real (40/60) no está dibujado.

---

## 8. Cómo se lee con el resto de la fila J (casos reales)

| Símbolo | J1 Momentum | J2 VWAP+IB | J3 Confluencia | J4 Multi-TF | Lectura conjunta |
|---|---|---|---|---|---|
| **SBUX** | ✅ LARGO (RSI 63.1, ADX 41) | — | — | 🔄 ALTO (5m 78.5 / 15m 63.1) | Impulso confirmado **intradía**, pero 5m **sobre-extendido** → ojo |
| **SHOP** | — | — | ✅ BAJISTA 3/3 (vol 1.12) | 🔄 BAJO (1D 68.9 → 38.9/38.3) | **Giro bajista** coherente: J3 y J4 apuntan abajo |
| **STX** | — | ✅ CORTO (vol 2.05) | ✅ BAJISTA 3/3 (vol 2.05) | — (no está en el pool 1D top) | Estructura + alineación bajista con volumen |
| **ABBV** | — | — | — | ALTO (68.0/62.6) | Solo coherencia de RSI intradía |
| **PEP** | — | — | — | 🔄 ALTO (1D 39.8 → 70.4/73.0) | Rebote intradía sobre 1D frío |

Regla práctica:
- **J1/J2/J3 + J4 mismo lado** → **alta convicción**.
- **J4 contradice a J3** → el corto plazo se está dando la vuelta (transición).
- **J4 solo** (sin J1/J2/J3) → es contexto, no señal operativa.

---

## 9. Analogías

- **Foto del viento:** J4 compara el viento de superficie (5m) y el de media altura (15m); si soplan juntos, buena vela.
- **Dos termómetros:** azul = 5m, ámbar = 15m; miras si marcan la misma "fiebre".
- **Marco y foto:** el 1D (pool) es el marco; J4 es la **foto de ahora** dentro de ese marco.

---

## 10. Referencias de código

| Qué | Dónde |
|---|---|
| Datos | `web/views.py::_multiframe_data` |
| Vista / endpoint | `web/views.py::multiframe_j4` |
| Chart | `web/charts.py::multiframe_option(series, categorias, compact=True, logos, tickers)` |
| Servicio | `services/heatmap_service.py::top_equity_rsi` |
| Indicadores | `services/indicator_service.py::por_indicador("rsi", "5"/"15")` |
| Plantilla | `web/templates/partials/card_chart.html` (script ECharts + `ticker()` + `num()`) |
| Config | `config/charts/J4_multiframe.json` (`meta.multiframe_j4`: `codigo`, `titulo`) |
| Umbrales | `config/charts/H1_rsi_limites.json` (`rsi.oportunidad_alto/bajo`, `rsi.scatter_max`) |
| Dashboard | `web/templates/dashboard.html` (`cell tres fill j4`) · CSS `.cell.fill.j4` en `web/static/app.css` |
| Gemelo no-compacto (retirado) | `web/views.py::multiframe` → `/partials/multiframe` · `H2_multiframe.json` |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
