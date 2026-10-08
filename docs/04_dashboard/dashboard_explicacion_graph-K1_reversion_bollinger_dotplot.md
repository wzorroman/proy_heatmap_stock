# K1 · Reversión Bollinger 15m — dot-plot (σ)

> **Código:** K1 · **slug:** `bollinger_scatter`
> **Endpoint:** `/partials/bollinger_scatter`
> **Config:** `config/charts/K1_bollinger_scatter.json`
> **Servicio:** `services/bollinger_15m_service.py`
> **Chart:** `web/charts.py::scatter_bollinger_option`
> **Ubicación en el dashboard:** fila **K1/K2/K3**, card de **4/12 columnas** (K1 cols 1–4), antes del Calendario (L1).

---

## 1. Qué es

Es un **dot-plot** (gráfico de puntos) que muestra, para cada acción, **qué tan lejos está su precio de su propia banda de Bollinger**, medida en **desviaciones estándar (σ)**.

Es el **duplicado visual** del panel compacto «J2 Reversión Bollinger 15m», pero reordenado para *leer el patrón de un vistazo* en lugar de listar filas.

```
 +2σ ┤ ●TXN  ●TER ●ADSK              ← esquina superior (extensión al alza)
 +1σ ┤            ●NFLX ●MS ●INTC ●BA
  0  ┤──────────────────────────────  SMA20 (media)
 -1σ ┤                        ●V ●SBUX ●MCD
 -2σ ┤                           ●CCJ ●TMO ●GE ●PANW ●LLY ●PEP
 -3σ ┤                                        ●FTNT ●UPS ●TGT ●UNH   ← esquina inferior
     └──────────────────────────────►
      mayor σ ────────────────► menor σ
```

---

## 2. Por qué aparece cada activo (criterios de selección)

Un símbolo **entra** al gráfico solo si cumple **todo** lo siguiente (`Bollinger15mService._analizar_symbol`):

1. **Tiene barras 15m suficientes:** al menos `ventana + 1` = **21 barras** en las últimas `bollinger_horas` (48 h por defecto).
2. **Es un extremo, medido en σ:** está **dentro de `bollinger_tol_sigma`** (**0.5σ** por defecto) de una banda o **la superó**:
   - `(upper − close) / σ ≤ 0.5` → **RECHAZO HIGH** → **CORTO**
   - `(close − lower) / σ ≤ 0.5` → **REBOTE LOW** → **LARGO**
3. **Tiene volumen de confirmación:** `vol_ratio ≥ bollinger_vol_min` (**1.0x** por defecto), donde `vol_ratio = volumen última barra / media de las 10 anteriores`.
4. **Tiene RSI 15m** disponible (para el tooltip).

Los que no cumplen **no aparecen**: por eso el gráfico **no** muestra todo el universo, sino solo las acciones **en un extremo de banda con volumen**.

> **Decisión A + C (2026-10-08):**
> - **A — Tolerancia en σ, no en % de precio.** La distancia se mide en desviaciones estándar, así el filtro es **invariante a la volatilidad**. Antes (±0.5% de precio) se colaban activos con σ pequeña que estaban **cerca de la media**, no de la banda (ej. V a 1.58σ, BA a 1.40σ, INTC a 1.30σ). Con σ quedan fuera.
> - **C — Dos estados visuales:** **ACCIONABLE** (punto relleno) si el precio **perforó** la banda; **CERCA** (punto hueco/atenuado) si quedó dentro de `tol_sigma` σ (watchlist).
>
> **Analogía:** es como una **foto de las acciones que están tocando los bordes de su carril**. No ves todo el mercado; solo los que se salieron o están a punto de salirse de su carril de volatilidad. Y ahora la foto se toma en "unidades de carril" (σ), no en centímetros, así no engaña a los carriles angostos.

---

## 3. Cómo se calcula (Bollinger 20, 2)

Sobre los **cierres** de las barras 15m:

```
SMA20  = media de los últimos 20 cierres
σ      = desviación estándar (muestral) de esos 20 cierres
upper  = SMA20 + 2σ        (banda superior)
lower  = SMA20 − 2σ        (banda inferior)

z = (close − SMA20) / σ    (posición en la banda, en σ)
```

Interpretación de `z`:

| z | Significado |
|---|---|
| `+2` | banda **superior** de Bollinger |
| `0` | **SMA20** (media) |
| `−2` | banda **inferior** de Bollinger |

En el eje Y del dot-plot **cada punto vale su `z`**. Las líneas punteadas amarillas en `±2` son, literalmente, **las bandas de Bollinger**; la línea gris en `0` es la media.

> **Analogía:** el `z` es el **"medidor de estiramiento"** de un resorte. `+2σ` = el resorte está estirado al máximo hacia arriba; `−2σ` = estirado al máximo hacia abajo; `0` = en reposo (media).

---

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Eje X** | "Slot" del símbolo (categórico, equiespaciado). **No codifica ningún valor**; solo da una columna a cada acción para que las etiquetas no se solapen. |
| **Eje Y** | Posición en la banda `z` (σ): `+2` banda superior · `0` SMA20 · `−2` banda inferior. |
| **Líneas punteadas amarillas** | Bandas de Bollinger (`±2σ`). |
| **Línea gris en 0** | SMA20 (media). |
| **Color del punto** | Lado: **rojo = CORTO** (rechazo banda superior) · **verde = LARGO** (rebote banda inferior). |
| **Relleno del punto** | **Relleno = ACCIONABLE** (el precio perforó la banda) · **hueco/atenuado = CERCA** (watchlist, dentro de `tol_sigma` σ). |
| **Tamaño del punto** | Volumen relativo (`vol_ratio`). |
| **Etiqueta sobre el punto** | Ticker (sin prefijo de exchange). |
| **Tooltip** | Ícono + ticker + tipo (coloreado) + Posición σ + Close (+%) + Dist. banda + Volumen + RSI 15m + Score + nota. |
| **Ayuda `(+)`** | botón junto al título; al pasar el cursor/foco muestra el **mapa general** (eje σ, bandas, CORTO/LARGO, relleno/hueco) en un popup sobrepuesto (sin alterar el ancho/alto del card). |

### Leyenda en pantalla

```
● CORTO · rechazo banda superior      ● LARGO · rebote banda inferior
● relleno = superó banda              ○ hueco = cerca (watchlist)
┄ bandas de Bollinger (±2σ)           ─ SMA20 (media)
──────────────────────────────────────────────────────────────────────────
Eje Y = posición en la banda (σ): +2 = banda superior · 0 = SMA20 · −2 = banda inferior.
Punto relleno = perforó la banda (accionable); hueco = cerca (watchlist).
Score = 2·volumen + penetración (ver tooltip).
```

> **Botón `(+)`.** Además de la leyenda de swatches, el título tiene un botón `(+)`
> que muestra el **mapa general** del dot-plot (eje σ con bandas, CORTO/LARGO y
> relleno/hueco) en un **popup sobrepuesto** al pasar el cursor o dar foco. El texto se
> declara en `config/charts/K1_bollinger_scatter.json` (`meta.bollinger_scatter.ayuda`,
> lista de líneas), se lee con `Settings.chart_help("bollinger_scatter")` y se renderiza
> con el mecanismo genérico `ayuda` de `web/templates/partials/card_chart.html`.

---

## 5. Casos de clasificación

La clasificación se hace en `clasificar_banda(close, upper, lower, tol)` y devuelve `(tipo, lado, nota, dist_banda)`:

| Tipo | Lado | Condición (en σ) | `estado` | `nota` |
|---|---|---|---|---|
| **RECHAZO HIGH** | **CORTO** | `(upper − close)/σ ≤ tol_sigma` | `ACCIONABLE` si superó, si no `CERCA` | `sobre banda superior` / `cerca banda superior` |
| **REBOTE LOW** | **LARGO** | `(close − lower)/σ ≤ tol_sigma` | `ACCIONABLE` si superó, si no `CERCA` | `bajo banda inferior` / `cerca banda inferior` |

### Sub-casos: "sobre/bajo" (accionable) vs "cerca" (watchlist)

- **"sobre" / "bajo"** → el precio **ya perforó** la banda → `estado = ACCIONABLE` (punto **relleno**).
- **"cerca"** → el precio está **dentro de `tol_sigma` σ** de la banda pero **aún no la tocó** → `estado = CERCA` (punto **hueco**, watchlist).

```
RECHAZO HIGH (CORTO)                       REBOTE LOW (LARGO)
   upper ─────────────────                    ──────────────── lower
     │  "sobre" (close > upper)                "bajo" (close < lower)   │
     │  "cerca" (dentro de 0.5σ)               "cerca" (dentro de 0.5σ) │
```

> **Analogía:** "cerca" es el corredor **acercándose a la línea**; "sobre/bajo" es el que **ya la cruzó**.

---

## 6. El score

Fórmula (`Bollinger15mService._score`):

```
score = 2 · vol_ratio + max(0, dist_banda)
```

- `vol_ratio`: volumen de la última barra 15m / media de las 10 anteriores. **Peso 2 por cada 1x.**
- `dist_banda`: penetración de la banda en % (positiva si la superó/perforó; negativa si quedó "cerca"). `max(0, ·)` → **solo suma cuando penetró** la banda.

**El score está dominado por el volumen.** La penetración es un bono pequeño.

| Zona del score | Interpretación |
|---|---|
| **Alto** (ej. 8.8) | Volumen fuerte **y** banda penetrada → **máxima convicción**: el mercado está validando el extremo con volumen. |
| **Bajo** (ej. 3.8) | Volumen moderado **y/o** solo "cerca" (sin penetrar) → **señal débil**: zona de reversión sin confirmación. |

> **Ojo:** el score **no** incluye σ. Por eso un activo muy extendido (TXN +3.27σ) puede tener score medio (5.13) si su volumen no es el más alto, y uno menos extendido (PANW −1.78σ) puede tener score alto (6.00) por su volumen (3.0x). **El score premia la confirmación de volumen, no la magnitud de la extensión.**

### Desglose real (snapshot 2026-10-08)

| Ticker | vol | dist% | 2·vol | penet. | score | lado |
|---|---:|---:|---:|---:|---:|---|
| UNH | 4.00 | 0.81 | 8.00 | 0.81 | **8.81** | LARGO |
| PANW | 3.00 | −0.07 | 6.00 | 0.00 | 6.00 | LARGO |
| TER | 2.97 | −0.04 | 5.93 | 0.00 | 5.93 | CORTO |
| CCJ | 2.71 | −0.11 | 5.42 | 0.00 | 5.42 | LARGO |
| TXN | 2.32 | 0.50 | 4.64 | 0.50 | 5.13 | CORTO |
| MCD | 2.36 | −0.08 | 4.71 | 0.00 | 4.71 | LARGO |
| FTNT | 2.26 | 0.08 | 4.51 | 0.08 | 4.59 | LARGO |
| MS | 2.29 | −0.44 | 4.57 | 0.00 | 4.57 | CORTO |
| V | 2.26 | −0.42 | 4.52 | 0.00 | 4.52 | LARGO |
| UPS | 2.03 | 0.19 | 4.05 | 0.19 | 4.25 | LARGO |
| TMO | 2.10 | −0.14 | 4.19 | 0.00 | 4.19 | LARGO |
| INTC | 2.05 | −0.49 | 4.10 | 0.00 | 4.10 | CORTO |
| PEP | 2.03 | −0.02 | 4.06 | 0.00 | 4.06 | LARGO |
| NFLX | 2.03 | −0.28 | 4.06 | 0.00 | 4.06 | CORTO |
| LLY | 2.03 | −0.06 | 4.05 | 0.00 | 4.05 | LARGO |
| ADSK | 2.00 | −0.16 | 4.00 | 0.00 | 4.00 | CORTO |
| GE | 1.99 | −0.08 | 3.98 | 0.00 | 3.98 | LARGO |
| SBUX | 1.95 | −0.27 | 3.91 | 0.00 | 3.91 | LARGO |
| TGT | 1.87 | 0.14 | 3.73 | 0.14 | 3.87 | LARGO |
| BA | 1.92 | −0.35 | 3.84 | 0.00 | 3.84 | CORTO |

---

## 7. Cómo se lee: opciones de orden

El eje X es categórico, así que **el orden de las columnas es una decisión de lectura**. Hoy el gráfico se ordena **por σ descendente**.

### Opción 1 — Orden por σ descendente (actual) ✅

```
 +2 ┤ ●TXN  ●TER ●ADSK              ← CORTO (rojo), extensión arriba
 +1 ┤            ●NFLX ●MS ●INTC ●BA
  0 ┤──────────────────────────────  SMA20
 -1 ┤                        ●V ●SBUX ●MCD
 -2 ┤                           ●CCJ ●TMO ●GE ●PANW ●LLY ●PEP
 -3 ┤                                        ●FTNT ●UPS ●TGT ●UNH  ← LARGO (verde)
    └──────────────────────────────►
     mayor σ ────────────────► menor σ
```

**Cómo se lee:** escalera descendente; arranca en los más extendidos al alza y termina en los más extendidos a la baja.
**Ventajas:** el patrón salta a la vista; los extremos quedan en las puntas; comparás "cuán extendido" cada activo sin leer tickers.
**Qué tomar en cuenta:** el orden **no** refleja importancia operativa; el volumen/score se ve por el **tamaño del punto** y el tooltip.

### Opción 2 — Orden por tipo (CORTO izquierda, LARGO derecha)

```
 +2 ┤ ●TXN ●TER ●ADSK ●NFLX        │  CORTO (rechazo banda superior)
  0 ┤──────────────────────────────┤  SMA20
 -1 ┤                              │ ●V ●SBUX ●MCD
 -2 ┤                              │    ●CCJ ●TMO ●GE ●PANW ●LLY ●PEP
 -3 ┤                              │               ●FTNT ●UPS ●TGT ●UNH
    └──────────────────────────────┘
     ◄────── CORTO ──────  ────── LARGO ──────►
```

**Cómo se lee:** dos bloques; mitad izquierda = cortos, mitad derecha = largos.
**Ventajas:** balance de mercado inmediato (cuántos cortos vs largos); comparación directa dentro de cada lado.
**Qué tomar en cuenta:** en la práctica, con estos datos, **coincide con la opción 1** (los CORTO tienen `z>0` y los LARGO `z<0`). Solo diferirían si apareciera un CORTO con `z<0` o viceversa.

### Opción 3 — Orden por score (cola de prioridad)

```
 +2 ┤      ●TER          ●TXN        ●NFLX ●ADSK
  0 ┤──────────────────────────────────────────  SMA20
 -1 ┤ ●PANW ●CCJ ●MCD          ●V
 -2 ┤         ●FTNT     ●TMO ●PEP ●LLY ●SBUX
 -3 ┤●UNH          ●UPS                 ●TGT
    └──────────────────────────────────────────►
     score alto ─────────────────────► score bajo
```

**Cómo se lee:** de izquierda a derecha, los "mejores" (más volumen + penetración) primero.
**Ventajas:** lo primero que ves es lo más accionable (UNH, PANW, TER…).
**Qué tomar en cuenta:** el gráfico queda en **zigzag** (rojo, verde, rojo…) y pierde forma legible; no se "lee" el mercado, hay que ir ticker por ticker.

### Resumen de órdenes

| Orden | Forma | Ideal para | Costo |
|---|---|---|---|
| **σ / tipo** | escalera descendente | leer el patrón y los extremos de un vistazo | no prioriza volumen |
| **score** | zigzag | actuar sobre los mejores primero | ilegible como patrón |

> **Recomendación del proyecto:** ordenar por **σ** para la lectura visual y dejar el **score** para el tooltip (y el volumen para el tamaño del punto). Así no se pierde la prioridad, pero el gráfico se vuelve legible.

---

## 8. Las esquinas: qué se recomienda

Las **esquinas** son los extremos del eje σ: arriba (`z ≈ +2` y más) y abajo (`z ≈ −2` y menos). El **centro** (`z ≈ 0`) **no es esquina**: son activos que quedaron dentro de la banda por σ grande o por la tolerancia de precio; ahí no hay reversión clara (es ruido).

**Regla base:** tocar la banda **no** es señal por sí sola; es una **zona de atención**. La entrada necesita confirmación.

1. **Confirmación de giro:** vela de reversión (envolvente, martillo en la inferior / estrella fugaz en la superior), divergencia precio/RSI, o volumen climático (score alto).
2. **Confluencia con RSI:** superior → RSI sobrecomprado (≈70) refuerza el CORTO; inferior → RSI sobreventa (≈30) refuerza el LARGO. RSI neutro ⇒ señal más débil.
3. **Tendencia (ADX):** ADX alto ⇒ la banda puede **"caminar"** (*band walking*); operar contra tendencia fuerte es lo más peligroso. La reversión es más fiable en rango/lateral.
4. **Gestión de riesgo:** stop **más allá del extremo**; **tamaño menor** cuanto más extremo el σ; **objetivo = SMA20** (la media), no la banda opuesta.
5. **"cerca" vs "sobre/bajo":** "cerca" = preventivo (esperar confirmación); "sobre/bajo" = extensión ya confirmada, pero también mayor probabilidad de continuación.

> **Analogía de la esquina:** estar en la banda es como **estirar un elástico al máximo**. Puede volver (reversión), pero si sigues tirando, se estira más (continuación). Por eso no basta con "tocó la banda".

---

## 9. Ejemplos puntuales (snapshot 2026-10-08)

| Activo | Lado | Zona | z | dist. banda | RSI 15m | ADX 15m | Vol | Score | Convicción |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| **TXN** | CORTO | esquina superior | **+3.27** | +0.50% (sobre) | 57.8 | 36.2 | 2.32x | 5.13 | baja-media |
| **TER** | CORTO | cerca superior | +1.91 | −0.04% (cerca) | 46.8 | 40.4 | 2.97x | 5.93 | baja |
| **TGT** | LARGO | bajo inferior | −2.68 | +0.14% (bajo) | 35.9 | 27.2 | 1.87x | 3.87 | baja |
| **UNH** | LARGO | esquina inferior | **−3.27** | +0.81% (bajo) | 29.2 | 31.4 | 4.00x | 8.81 | media-alta |

### TXN — CORTO (esquina superior)
- Tendencia alcista fuerte (ADX 36.2), precio 0.50% **sobre** la banda superior, z **+3.27**.
- **Riesgo:** RSI **neutro (57.8)**, no agotado → propenso a *band walking*.
- **Recomendación:** esperar **vela de rechazo** o **divergencia RSI**; stop sobre el máximo (≈290.5); objetivo SMA20 (286.26). Si el RSI pasa a >70 sin girar, abortar.

### TER — CORTO (cerca de la banda superior)
- Precio a 0.04% de la banda (aún no la tocó), **ADX 40.4** (tendencia muy fuerte), RSI 46.8 neutro.
- **Riesgo:** el caso más preventivo contra la tendencia más fuerte → alta probabilidad de que **rompa la banda** y siga.
- **Recomendación:** esperar el toque y el rechazo confirmado; si rompe 412.16 con volumen, el corto se **invalida**. Stop sobre 412.5; objetivo SMA20 (408.56). Tamaño reducido.

### TGT — LARGO (rebote banda inferior)
- Perforó la banda inferior 0.14%, RSI 35.9, ADX 27.2, vol 1.87x, **score 3.87 (el más bajo)**, σ pequeña (0.31).
- **Riesgo:** σ chica ⇒ la perforación puede ser **ruido**; sin volumen/score que confirmen.
- **Recomendación:** señal **débil**; esperar martillo/vela de giro y RSI girando al alza. Stop bajo el mínimo (<152.0); objetivo SMA20 (153.17).

### UNH — LARGO (esquina inferior)
- El **más extendido** (−3.27σ), perforó 0.81% bajo la banda, **RSI 29.2 (sobreventa)**, **vol 4.00x**, **score 8.81 (el más alto)**, ADX 31.4.
- **A favor:** mejor confluencia (extensión extrema + sobreventa + volumen climático).
- **Recomendación:** **mejor candidato a rebote**. Entrada cerca de 372 con vela de reversión; stop bajo el mínimo (≈371); objetivo SMA20 (380.11, ≈ +2%). Respetar que ADX 31 ⇒ la tendencia bajista puede seguir.

### Lectura de conjunto
- **Esquinas:** TXN (arriba, +3.27σ) y UNH (abajo, −3.27σ). TER pegado a la esquina superior sin tocar; TGT cerca de la inferior con poca σ.
- **Los cuatro tienen ADX > 25** ⇒ todos en tendencia; la reversión es contra-movimiento y falla más. Regla: **confirmación + stop fuera del extremo + tamaño reducido**.
- **Ranking de calidad de señal (según el modelo):** **UNH > TXN > TER > TGT**.
- **RSI:** en TXN y TER **no** acompaña (57.8 y 46.8); en UNH y TGT **sí** refuerza (29.2 y 35.9).

---

## 10. Ventajas de este gráfico

- **Convierte 20 filas en un patrón:** ves de un vistazo quién está estirado arriba y quién abajo.
- **Comparable entre activos:** el `z` normaliza por volatilidad, así que un activo de $50 y uno de $500 se comparan en la misma escala (σ).
- **Las líneas son reales:** las punteadas son **las bandas de Bollinger** (±2σ), no umbrales de otro indicador.
- **Triple codificación:** posición (σ) + color (lado) + tamaño (volumen) en un solo punto.
- **Tooltip rico:** ícono, tipo coloreado, close, distancia a banda, volumen, RSI y score sin salir del gráfico.
- **Autoexplicativo:** leyenda con swatches + nota del eje y del score.

---

## 11. Analogías

- **Elástico:** el `z` mide cuánto está estirado el precio respecto a su media. `±2σ` = estirado al máximo; puede volver, o estirarse más si sigues tirando.
- **Carriles:** cada acción tiene su "carril" de volatilidad (bandas). El gráfico muestra quién está tocando el borde del carril.
- **Resorte / temperatura:** `z` es como una temperatura normalizada: no importa el activo, todos se leen en la misma escala.
- **Escalera:** ordenado por σ, el gráfico es una escalera: arriba los "calientes" (extensión al alza), abajo los "fríos" (extensión a la baja).

---

## 12. Referencias de código

| Qué | Dónde |
|---|---|
| Selección + cálculo (`z`, score, clasificación) | `services/bollinger_15m_service.py` |
| Clasificación pura (testeable) | `Bollinger15mService.clasificar_banda` |
| Construcción del chart (eje σ, líneas, datos) | `web/charts.py::scatter_bollinger_option` |
| Tooltip HTML + leyenda + redondeo | `web/templates/partials/card_chart.html` |
| Estilos tooltip/leyenda | `web/static/app.css` (`.tt*`, `.leyenda*`) |
| Vista / endpoint | `web/views.py::bollinger_scatter` |
| Config | `config/charts/K1_bollinger_scatter.json` (incluye `meta.bollinger_scatter.ayuda` = mapa del popup `(+)`) |
| Ayuda `(+)` | `Settings.chart_help("bollinger_scatter")` + popup `ayuda` en `web/templates/partials/card_chart.html` |
| Panel compacto hermano | J2 · `/partials/bollinger_15m` |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
