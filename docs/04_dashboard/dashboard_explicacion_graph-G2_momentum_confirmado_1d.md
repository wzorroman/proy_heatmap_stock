# G2 · Momentum Confirmado — Change vs RSI (1D) — scatter Change% × RSI

> **Código:** G2 · **slug:** `change_rsi`
> **Título en pantalla:** *Momentum Confirmado — Change vs RSI (1D)*
> **Endpoint:** `/partials/change_rsi`
> **Config:** `config/charts/G2_change_rsi.json`
> **Servicio:** `services/momentum_service.py::MomentumService.change_rsi`
> **Chart:** `web/charts.py::change_rsi_option` (+ `change_rsi_visible`)
> **Vista:** `web/views.py::change_rsi`
> **Ubicación en el dashboard:** card de **6/12 columnas** (`.cell`), en la **misma fila** que G1 (Momentum diario) — `web/templates/dashboard.html:59-60`.

---

## 1. Qué es

Es un **diagrama de dispersión (scatter)** que coloca **cada acción** del universo como un punto en un plano de dos dimensiones:

- **Eje X** = **cambio % del día** (`change_pct`) → cuánto se movió el precio.
- **Eje Y** = **RSI diario** (`rsi`, 1D) → con cuánta fuerza lo hizo.

La idea es leer **si el movimiento del precio está confirmado por el impulso**: un cambio grande con un RSI que acompaña es *momentum confirmado*; un cambio grande con un RSI que no acompaña es *sospechoso* (posible agotamiento).

```
        Momentum Confirmado — Change vs RSI (1D)   ·  cada ● es una acción
   RSI
   85 ┤
   70 ┤· · · · · · · · · · · · · · · · · · · · · · · · · · · ·  RSI 70 (sobrecompra)
      │              ●sube
   50 ┤   ●cae           ●sube                    ●cae
      │        ●cae              ●sube
   30 ┤· · · · · · · · · · · · · · · · · · · · · · · · · · · ·  RSI 30 (sobreventa)
      │  ●cae                         ●sube
   15 ┤
      └─────────┬──────────────────────┬───────────────────┬──► Change %
           pierde mucho   pierde   0    gana        gana mucho
         (extremo izq)                       (extremo der)

   color: ● verde = sube (>+0.3%) · ● rojo = cae (<−0.3%) · ● amarillo = plano
          ─ línea vertical discontinua en Change 0
          ─ líneas horizontales discontinuas en RSI 70 (roja) y 30 (verde)
```

## 2. Por qué aparece cada activo

El gráfico **no detecta patrones**: dibuja el **estado del último tick** de cada acción del universo.

- **Universo:** clases de activo `universe.stocks = ["equity", "common"]` (`config/charts/A1_header.json`).
- **Filtro de datos:** solo entran activos con `change_pct` **y** `rsi` no nulos.
- **Orden:** por `|change_pct|` descendente (los movimientos más grandes primero; solo afecta el orden interno).
- **Filtro de oportunidad (zona central):** se **ocultan** los puntos sin valor de decisión → `RSI 40–60` **o** `|change| ≤ 0.3%` (ver §6).

> **Analogía:** es un **podio del día visto en un espejo**. En el eje X está “cuánto se movió” y en el eje Y “con cuánta fuerza”. Lo que el panel decide es *qué corredores merecen la pena mirar*: descarta a los que ni se movieron ni destacan en fuerza.

## 3. Cómo se calcula

No hay cálculo de indicadores: el dato ya viene en la tabla de último tick.

```
1. filas = latest_market_tick WHERE asset_class IN ('equity','common')
2. por fila:  change = change_pct ; rsi = rsi (1D)
3. descartar filas con change == null or rsi == null
4. ordenar por |change| descendente
5. (filtro de presentación) ocultar si  40 ≤ rsi ≤ 60  OR  |change| ≤ 0.3
6. color del punto:
      change >  +0.3  → verde   (VERDE  #3fb950)
      change <  −0.3  → rojo    (ROJO   #f85149)
      en medio        → amarillo(AMARILLO #d6a72c)
```

### Config (`config/charts/G2_change_rsi.json`)

```json
{ "meta": { "change_rsi": { "codigo": "G2", "titulo": "Momentum Confirmado — Change vs RSI" } } }
```

El gráfico por ahora **no expone umbrales en config**; los límites (RSI 70/30, color ±0.3%, zona central 40–60) están en `web/charts.py`.

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Eje X** | Change % (`change_pct`), rango **simétrico** `-L … +L` (0 siempre centrado) |
| **Eje Y** | RSI 1D, rango fijo **15–85** |
| **Línea vertical (0)** | frontera entre caída y subida (gris discontinua) |
| **Línea horizontal 70** | sobrecompra (roja discontinua) + texto sobrepuesto `sobrecompra  70` |
| **Línea horizontal 30** | sobreventa (verde discontinua) + texto `sobreventa  30` debajo de la línea |
| **Guía inferior de zonas** | palabras sobrepuestas al pie: `pierde mucho (−L) · pierde (−L/2) · 0 · gana (+L/2) · gana mucho (+L)` |
| **Color del punto** | signo del cambio: verde ↑ / rojo ↓ / amarillo plano |
| **Etiqueta** | ticker del activo sobre el punto (se ocultan solapadas: `hideOverlap`) |
| **Tooltip** | icono (logo) + ticker + badge `ALCISTA/BAJISTA/NEUTRO` + Cambio % + RSI 1D + Zona RSI (`tooltipRows`) |
| **Tiempo de evaluación** | etiqueta ámbar `1D` (`.ib-time`) junto al título |
| **Ayuda `(+)`** | junto al título; al pasar el cursor/foco muestra el **mapa de cuadrantes** en un popup sobrepuesto |
| **Tamaño** | constante (`symbolSize: 12`) |
| **Altura / acento** | 460 px · acento verde · `chart-change-rsi` |

> **Anotaciones sin alterar el tamaño.** Las palabras de zona y de RSI se dibujan
> **sobrepuestas dentro del área del gráfico** (segunda serie `scatter` con `symbolSize: 0`
> a `y = 15`, y etiquetas de `markLine`), por lo que **no cambian el ancho ni el alto**
> del panel.
>
> **Eje centrado.** El ancho del eje X es simétrico: `L = redondeo_par( max(|mín|, |máx|) )`
> (mínimo 2). Así el `0` queda siempre en el centro aunque un lado tenga menos puntos
> (p. ej. hoy `L = 8` → eje `−8 … +8`). La guía inferior se reparte uniforme en
> `−L, −L/2, 0, +L/2, +L`.
>
> **Texto del popup `(+)`.** El mapa de cuadrantes del botón `(+)` se declara en
> **`config/charts/G2_change_rsi.json`** (`meta.change_rsi.ayuda`, como **lista de líneas**),
> se lee con `Settings.chart_help("change_rsi")` y se renderiza con el mecanismo genérico
> `ayuda` de `web/templates/partials/card_chart.html`. Para cambiarlo, edita el JSON
> (no requiere tocar Python).

### Leyenda en pantalla (nota de la tarjeta)

```
N de M acciones · zona central (RSI 40–60 o cambio ±0.3%) oculta
· color por cambio · líneas RSI 30/70
```

## 5. Casos y cómo leer cada uno

Cruzar **lado** (Change) con **banda de RSI** produce 6 casos. La clave es: **lado derecho = compra potencial**, **lado izquierdo = venta potencial**, y la **banda** dice si ya está extendido o no.

### 5.1 Mapa general

```
                        Change %
             pierde ◄──────────────► gana
                     (0, izquierda)     (derecha)
        RSI 85  ┌──────────────┬──────────────┐
           ▲    │  B1 TECHO    │  A1 EUFORIA  │   RSI > 70
           │    │  cae + RSI↑  │  sube + RSI↑ │   (sobrecompra)
        RSI 70  ├──────────────┼──────────────┤
           │    │  B  VENTA    │  A  COMPRA   │   30 < RSI < 70
           │    │  cae sano    │  sube sano   │   (zona sana)
        RSI 30  ├──────────────┼──────────────┤
           ▼    │  B2 SOBRE-   │  A2 REBOTE   │   RSI < 30
        RSI 15  │  VENDIDO     │  (sorpresa)  │   (sobreventa)
                └──────────────┴──────────────┘
   A  = momentum ALCISTA confirmado   ·  B  = momentum BAJISTA confirmado
   A1/B1 = confirmado pero EXTENDIDO  ·  A2/B2 = contradicción (revisar)
```

### 5.2 A — Derecha-central: **compra de momentum sano** (sube, RSI 30–70)

```
   RSI 70 ┤━━━━━━━━━━━━━━━━━━━━
   65     ┤            ●NVDA
   55     ┤     ●AAPL        ← sube y el RSI acompaña sin sobrecompra
   45     ┤  ●MSFT
   30     ┤━━━━━━━━━━━━━━━━━━━━
          └───┬──────────┬───► Change %
              0        +2%
```

- **Qué pasó:** el precio sube y el RSI está subiendo pero aún **no en sobrecompra**.
- **Lectura:** **alcista confirmado con espacio para correr** → mejor candidato de compra.
- **Revisar:** que el RSI venga **en ascenso** (no plano) y confirmar con 15m (E1/F1) y confluencia (E3).

### 5.3 A1 — Derecha-superior: **alcista sobrecomprado / euforia** (sube, RSI > 70)

```
   RSI 85 ┤
   75     ┤        ●SMCI  ← sube con fuerza y ya en sobrecompra
   70 ┤━━━┿━━━━━━━━━━━━━━━━━
   60     ┤  ●AMD
          └───┬──────────┬───► Change %
              0        +5%
```

- **Qué pasó:** gran subida con RSI > 70.
- **Lectura:** **momentum fuerte pero extendido**. Puede **continuar** (trend-following) o **agotarse** (tirón/corrección).
- **Revisar:** volumen y divergencia (D3/K3). Si el RSI **deja de subir** mientras el precio sube → agotamiento.

### 5.4 A2 — Derecha-inferior: **rebote / sorpresa alcista** (sube, RSI < 30)

```
   55     ┤
   40     ┤
   30 ┤━━━┿━━━━━━━━━━━━━━━━━
   25     ┤     ●MCD  ●PEP  ← sube HOY pero el RSI sigue en sobreventa
          └───┬──────────┬───► Change %
              0        +2%
```

- **Qué pasó:** el precio sube con fuerza, pero el RSI **aún está en sobreventa** (no tuvo tiempo de girar).
- **Lectura:** **contradicción útil** → posible **cambio de tendencia / rebote desde abajo**, o un simple *bounce* dentro de una tendencia bajista.
- **Revisar:** los mínimos previos y si el RSI **empieza a cruzar al alza**. Es la zona de *“sorpresa”*: el precio ya se movió pero el RSI no lo refleja.

### 5.5 B — Izquierda-central: **venta de momentum sano** (cae, RSI 30–70)

```
   RSI 70 ┤━━━━━━━━━━━━━━━━━━━━
   60     ┤              ●CSCO
   50     ┤        ●MSFT        ← cae y el RSI acompaña sin sobreventa
   40     ┤   ●JNJ
   30     ┤━━━━━━━━━━━━━━━━━━━━
          └───┬──────────┬───► Change %
             −2%         0
```

- **Qué pasó:** el precio cae y el RSI está bajando pero **no en sobreventa**.
- **Lectura:** **bajista confirmado con espacio para caer** → candidato de venta/corto.
- **Revisar:** ADX 15m (K2) para saber si hay tendencia real y no ruido.

### 5.6 B1 — Izquierda-superior: **distribución / posible techo** (cae, RSI > 70)

```
   RSI 85 ┤
   75     ┤  ●XYZ   ← cae HOY pero el RSI sigue alto (sobrecompra)
   70 ┤━━━┿━━━━━━━━━━━━━━━━━
   60     ┤
          └───┬──────────┬───► Change %
             −2%         0
```

- **Qué pasó:** fuerte caída con RSI todavía en sobrecompra.
- **Lectura:** **aviso de techo / distribución** o simplemente un retroceso dentro de una tendencia alcista fuerte.
- **Revisar:** volumen de la caída y los máximos recientes; si el RSI **cruza** por debajo de 70, se confirma debilidad.

### 5.7 B2 — Izquierda-inferior: **bajista sobrevendido / capitulación** (cae, RSI < 30)

```
   40     ┤
   30 ┤━━━┿━━━━━━━━━━━━━━━━━
   22     ┤ ●BAC        ●MS
          └───┬──────────┬───► Change %
             −2%         0
```

- **Qué pasó:** gran caída con RSI ya en sobreventa.
- **Lectura:** **agotamiento o capitulación** → posible rebote técnico, o continuación si el mercado es muy débil.
- **Revisar:** divergencia alcista (D3/K3) y si el precio pierde/perfora soportes con volumen.

### 5.8 Casos por “extremo lateral” (los extremos de Change)

Los **extremos laterales** son las columnas de más a la izquierda y más a la derecha; ahí está la mayor parte de la *oportunidad potencial*:

| Extremo | Banda RSI | Lectura |
|---|---|---|
| **Derecho lejano** (+5% o más) | RSI 30–70 | Compra de **momentum fuerte** confirmado |
| **Derecho lejano** | RSI > 70 | Momentum **eufórico** → seguir con cuidado de tirón |
| **Derecho lejano** | RSI < 30 | **Rebote** inesperado → giro alcista potencial |
| **Izquierdo lejano** (−5% o menos) | RSI 30–70 | Venta de **momentum fuerte** confirmado |
| **Izquierdo lejano** | RSI < 30 | **Capitulación** → rebote o continuación |
| **Izquierdo lejano** | RSI > 70 | **Techo/distribución** → aviso de giro |

### 5.9 Casos por posición vertical (los extremos superior/inferior)

- **Banda superior (RSI > 70):** zona caliente. Buena para **tendencia** (si sube) y para **reversión** (si cae).
- **Banda inferior (RSI < 30):** zona fría. Buena para **rebote** (si sube) y para **continuación bajista** (si cae).
- **Cerca de la línea vertical 0:** cambio nulo; el panel los **oculta** si además el RSI es central.

## 6. Filtro de la zona central (estado actual)

Para no llenar el gráfico de puntos sin valor de decisión, la vista oculta los activos que cumplen **cualquiera** de estas dos condiciones:

```
ocultar  ⇔  (40 ≤ RSI ≤ 60)  OR  (|change %| ≤ 0.3%)
```

- **RSI 40–60:** no hay extremo de impulso (ni sobrecompra ni sobreventa).
- **|change| ≤ 0.3%:** el precio prácticamente no se movió.

Se **conservan** los puntos que destacan en **al menos una** dimensión: extremos de RSI (≥60 o ≤40) o cambios relevantes (>0.3% en valor absoluto).

```
   ANTES (todos)                     DESPUÉS (oportunidad)
   ● ● ● ● ● ●                        ●           ●
   ● ● ● ● ● ●     →                  ●           ●
   ● ● ● ● ● ●                        ●           ●
   (centro lleno)                     (centro limpio, quedan extremos)
```

> **Analogía:** es como filtrar una **fila de corredores**: quitas a los que ni se movieron del sitio ni destacan en fuerza; dejas a los que corrieron fuerte o están en un extremo físico (arriba = agotados, abajo = reventados).

## 7. Ejemplos reales (snapshot 2026-10-08)

Universo: **70 acciones** · visibles tras el filtro: **22** · ocultas: **48**.

| Ticker | Change % | RSI 1D | Cuadrante | Lectura breve |
|---|---:|---:|---|---|
| **MARA** | −6.28 | 33.5 | Izq-central | Bajista con espacio para caer |
| **SBUX** | −4.59 | 26.7 | Izq-inferior | Capitulación / posible rebote |
| **PEP** | +2.31 | 35.9 | Der-inferior | Rebote con RSI aún bajo (sorpresa) |
| **MCD** | +2.50 | 38.2 | Der-inferior | Rebote desde zona baja |
| **XOM** | +2.75 | 63.5 | Der-central | Alcista confirmado con espacio |
| **V** | +1.91 | 62.6 | Der-central | Alcista confirmado con espacio |
| **CSCO** | −1.36 | 61.3 | Izq-central | Venta con RSI aún alto (aún no sobreventa) |
| **MSFT** | −1.12 | 62.7 | Izq-central | Retroceso con impulso alto |
| **BAC** | −0.96 | 21.9 | Izq-inferior | Muy sobrevendido (RSI 22) |
| **MS** | −1.06 | 28.2 | Izq-inferior | Sobreventa / rebote potencial |
| **ABBV** | −0.59 | 62.3 | Izq-central | Caída leve con RSI alto |

> Los valores son un snapshot en vivo y cambian durante la sesión (el panel se refresca cada `htmx_refresh_ms`).

## 8. Oportunidades y qué revisar

1. **Compra de momentum sano:** lado derecho con RSI 30–70 (p. ej. XOM, V). Confirmar con 15m (E1/F1) y confluencia (E3).
2. **Venta de momentum sano:** lado izquierdo con RSI 30–70 (p. ej. MARA, CSCO).
3. **Rebote / giro alcista:** extremo derecho con RSI < 30 (p. ej. PEP, MCD, LMT) → el RSI aún no confirma; vigilar que empiece a girar al alza.
4. **Capitulación / posible suelo:** extremo izquierdo con RSI < 30 (p. ej. SBUX, BAC, MS) → buscar divergencia alcista (D3/K3).
5. **Techo / distribución:** extremo izquierdo con RSI > 70 → raro y avisado; comprobar volumen y máximos.

**Qué revisar siempre antes de operar:**

- Este panel es **2D** (solo cambio y RSI): no codifica **volumen**, **ADX** ni **sector**.
- El **RSI es diario** y el **cambio es del día**: durante la sesión el punto se mueve pero el RSI solo cambia al cerrar la vela → confirmación parcialmente diferida.
- El **rango Y fijo 15–85** puede recortar visualmente RSI extremos (<15 o >85).
- Con **muchos símbolos**, algunas etiquetas se ocultan por solape (`hideOverlap`) → usa el tooltip.

## 9. Analogías

- **Espejo del podio:** el eje X es “cuánto corrió” y el eje Y “con cuánta fuerza”. Un corredor que corrió mucho y con fuerza (derecha-arriba) es el líder del día.
- **Motor y velocímetro:** el precio es el coche, el RSI el velocímetro. Si el coche acelera pero el velocímetro no sube, algo no cuadra (agotamiento); si suben juntos, el movimiento es real.
- **Termómetro del impulso:** la línea 70 es “fiebre” (sobrecompra) y la 30 “hipotermia” (sobreventa); el centro 40–60 es “temperatura ambiente” (sin oportunidad).
- **Imán y límites:** los extremos laterales son los imanes de la atención; el centro es el pasillo por donde nadie destaca.
- **Semáforo de cuadrantes:** derecha = verde (comprar), izquierda = rojo (vender), arriba = precaución (extendido), abajo = esperanza (agotado).
- **Carrera de fondo:** un movimiento grande con RSI central es un corredor con reservas; con RSI en extremo, es uno al que ya le queda poca gasolina.

## 10. Referencias de código

| Qué | Dónde |
|---|---|
| Servicio (datos) | `services/momentum_service.py::MomentumService.change_rsi` |
| Repositorio | `repositories/latest_tick_repo.py::fetch_all` |
| Chart (opción ECharts) | `web/charts.py::change_rsi_option` |
| Filtro de oportunidad | `web/charts.py::change_rsi_visible` / `_change_rsi_neutro` |
| Vista | `web/views.py::change_rsi` |
| Plantilla de card | `web/templates/partials/card_chart.html` |
| Render ECharts | `web/static/app.js::renderChart` |
| Config | `config/charts/G2_change_rsi.json` (`meta.change_rsi.ayuda` = mapa del popup `(+)` · `meta.change_rsi.tf = "1D"`) |
| Ayuda `(+)` | `Settings.chart_help("change_rsi")` + popup `ayuda` en `web/templates/partials/card_chart.html` |
| Tiempo de evaluación | `Settings.chart_tf("change_rsi")` → etiqueta `.ib-time` (ámbar) en el título |
| Dashboard | `web/templates/dashboard.html:59-60` (`.cell` = 6/12) |
| Universo | `config/charts/A1_header.json` → `universe.stocks` |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
