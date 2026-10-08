# H1 · RSI 1D — acciones top por capitalización

> **Código:** H1 · **slug:** `rsi_limites`
> **Endpoint:** `/partials/rsi_limites`
> **Config:** `config/charts/H1_rsi_limites.json`
> **Servicio:** `services/heatmap_service.py::HeatmapService.top_equity_rsi`
> **Repositorio:** `repositories/heatmap_repo.py::HeatmapRepo.top_equity_rsi`
> **Chart:** `web/charts.py::scatter_rsi_option`
> **Vista:** `web/views.py::rsi_limites`
> **Ubicación en el dashboard:** card `cell fill` (6/12), en la fila junto a **H2 Multi-TF**.
> **Tiempo de evaluación:** **1D** (etiqueta ámbar `1D` en el título).

---

## 1. Qué es

Es un **dot-plot** (gráfico de puntos) que muestra el **RSI diario de las acciones más grandes por capitalización** que están **en zona de oportunidad** (RSI ≥ 60 o ≤ 40). Cada punto es una acción; **su altura es el RSI**, **su tamaño es la capitalización** y **su forma distingue si es un extremo o solo una zona de vigilancia**.

```
 ALTA (≥60)                                        BAJA (≤40)
 RSI
 100 ┤
  70 ┤══════════════════════════════  sobrecompra      (rojo relleno) · posible techo
  60 ┤──────────────────────────────  oportunidad alta (rojo hueco)   · vigilar
  50 ┤
  40 ┤──────────────────────────────  oportunidad baja (verde hueco)  · vigilar
  30 ┤══════════════════════════════  sobreventa       (verde relleno) · posible rebote
   0 ┤
     └──────────────┬───────────────► acciones
 ALTA (≥60)        ┊ divisor punteado      BAJA (≤40)

 relleno = extremo (≥70 / ≤30) · hueco = oportunidad (60–70 / 30–40)
 tamaño del punto = capitalización (más grande = mayor peso en el mercado)
 cabeceras `ALTA` / `BAJA` en las **cuatro esquinas** (arriba y abajo: izquierda ≥60 · derecha ≤40)
```

- **Eje Y** = RSI (0–100). Líneas amarillas de referencia en **30 y 70**.
- **Eje X** = “slot” por acción, sin etiquetas: **el ticker va sobre el punto** (se ocultan las etiquetas solapadas: `hideOverlap`).
- **Bandas de fondo** con tinte suave para cada zona (`markArea`).
- **Divisor vertical** `ALTA | BAJA` entre los dos bloques.

## 2. Por qué aparece cada activo (criterios de selección)

Un símbolo **entra** si cumple **todo** (`HeatmapRepo.top_equity_rsi` + `HeatmapService.top_equity_rsi`):

1. **Es `equity`/`common`** del universo de acciones configurado (`universe.stocks`).
2. **Tiene capitalización** en el snapshot (`fact_heatmap_snapshot`, última ventana) y **RSI** en el último tick (`latest_market_tick`).
3. **Está en oportunidad:** `rsi >= oportunidad_alto` (**60**) **o** `rsi <= oportunidad_bajo` (**40**).
4. Se ordena por **capitalización descendente** y se corta en `rsi.scatter_max` (**100**).

Es decir: **no aparece todo el mercado**, sino las **mayores por capitalización** que están en un **extremo relativo** de RSI. Las que están entre 40 y 60 quedan **fuera** (zona neutra).

> **Analogía:** es el **marcador de un partido entre los grandes**. No ves a todos los jugadores, solo a los pesos pesados que están **en racha** (calientes o fríos). Si un gigante está en un extremo, mueve al índice.

## 3. Cómo se calcula

```
1. snapshot = fact_heatmap_snapshot (última ventana) ⋈ latest_market_tick
2. filtrar  asset_class IN universe.stocks
3. filtrar  l.rsi IS NOT NULL y h.market_cap IS NOT NULL
4. filtrar  rsi >= oportunidad_alto (60) OR rsi <= oportunidad_bajo (40)
5. ordenar  market_cap DESC · corte  rsi.scatter_max (100)

Presentación (charts.scatter_rsi_option):
6. partir en dos bloques:  ALTA (rsi >= 60) | BAJA (rsi <= 40)
7. dentro de cada bloque, ordenar por RSI DESC  → escalera descendente
8. tamaño del punto = 9 + sqrt( (cap − cap_min) / (cap_max − cap_min) ) · 31
9. color:  rojo = zona alta (>=60) · verde = zona baja (<=40)
10. forma: relleno = extremo (>=70 / <=30) · hueco = oportunidad (60–70 / 30–40)
```

### Config (`config/charts/H1_rsi_limites.json`)

```json
"rsi": {
  "oportunidad_alto": 60,
  "oportunidad_bajo": 40,
  "limite_alto": 70,
  "limite_bajo": 30,
  "scatter_max": 100
}
```

Los cuatro umbrales se pasan al chart desde la vista (`settings.business("rsi", …)`), de modo que **el filtro y las bandas usan los mismos límites**.

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Eje Y** | RSI diario (0–100) |
| **Líneas amarillas 30 / 70** | límites de **sobreventa** / **sobrecompra** |
| **Bandas de fondo** | zonas: sobrecompra (≥70), oportunidad alta (60–70), oportunidad baja (30–40), sobreventa (≤30) |
| **Color del punto** | lado: **rojo** = zona alta (≥60) · **verde** = zona baja (≤40) |
| **Forma del punto** | **relleno** = extremo (≥70 / ≤30) · **hueco** = oportunidad (60–70 / 30–40) |
| **Tamaño del punto** | capitalización (√ normalizado) |
| **Etiqueta** | ticker sobre el punto (se ocultan solapadas) |
| **Cabeceras `ALTA` / `BAJA`** | rótulos separados en las **4 esquinas** (arriba y abajo): izquierda ≥60 · derecha ≤40 |
| **Divisor vertical** | línea **punteada gris claro** (`CLARO #c9d6e5`) entre ambos bloques |
| **Tiempo de evaluación** | etiqueta ámbar `1D` (`.ib-time`) junto al título |
| **Ayuda `(+)`** | popup sobrepuesto con el **mapa de zonas** |
| **Tooltip** | logo + ticker + zona + RSI + cambio % + capitalización + sector (`tooltipRows`) |

### Leyenda en pantalla (nota de la tarjeta)

```
N acciones en oportunidad (≥60 / ≤40) · relleno = extremo (30/70) · hueco = oportunidad · tamaño = capitalización
```

## 5. Casos y cómo leer cada uno

### 5.1 Banda de sobrecompra — RSI ≥ 70 (rojo relleno)

```
   70 ┤════════════════════  sobrecompra
      │        ●NVDA ●
      └────────────────────►
```

- **Qué significa:** sobrecompra diaria. El precio viene muy estirado al alza.
- **Lectura:** **posible techo / agotamiento**. En **tendencia fuerte** puede ser *band walking* (sigue subiendo), así que **no es señal de venta por sí sola**.
- **Revisar:** divergencia precio/RSI (D3/K3), volumen, y confirmación 15m/confluencia.

### 5.2 Oportunidad alta — RSI 60–70 (rojo hueco)

```
   70 ┤════════════════════  sobrecompra
   60 ┤────────────────────  oportunidad alta
      │   ○AAPL  ○MSFT  ○XOM
      └────────────────────►
```

- **Qué significa:** fuerza alcista **sin llegar a extremo**. Zona de **vigilancia/continuación**.
- **Lectura:** el RSI “calienta”; si **cruza 70** con volumen, pasa a sobrecompra; si **gira a la baja**, es enfriamiento temprano.
- **Revisar:** el cambio % (tooltip) y el ADX 15m (K2) para saber si hay tendencia real.

### 5.3 Zona neutra — RSI 40–60 (no aparece)

```
   60 ┤────────────────────
      │      (zona excluida por el filtro)
   40 ┤────────────────────
      └────────────────────►
```

- **Qué significa:** sin extremo relativo. **No se dibuja** por diseño: son activos sin señal clara.
- **Por qué:** el panel es una **lista corta de atención**; incluir el centro lo llenaría de ruido.

### 5.4 Oportunidad baja — RSI 30–40 (verde hueco)

```
   40 ┤────────────────────  oportunidad baja
   30 ┤════════════════════  sobreventa
      │   ○JNJ  ○GE  ○BABA
      └────────────────────►
```

- **Qué significa:** debilidad **sin llegar a extremo**.
- **Lectura:** el RSI “se enfría”; si **cruza 30**, pasa a sobreventa; si **gira al alza**, es recuperación temprana.
- **Revisar:** si el precio pierde soportes con volumen (continuación) o muestra divergencia alcista (D3/K3).

### 5.5 Banda de sobreventa — RSI ≤ 30 (verde relleno)

```
   30 ┤════════════════════  sobreventa
      │        ●BAC ●MS
      └────────────────────►
```

- **Qué significa:** sobreventa diaria; precio muy castigado.
- **Lectura:** **posible rebote** (o capitulación que continúa). Es el espejo del 5.1.
- **Revisar:** divergencia alcista, volumen climático y confirmación de giro.

### 5.6 Tamaño = capitalización

```
   ○  (pequeño)  →  acción de menor capitalización dentro del panel
   ●●● (grande)   →  mega-cap (mueve al índice)
```

- **Lectura:** un **mega-cap en extremo** pesa mucho más en el mercado y en los índices que una acción menor.
- **Regla:** mismo RSI, pero **más tamaño = más relevancia** (y suele tener más liquidez).

### 5.7 Combinaciones de lectura

| RSI | Forma | Cap | Lectura |
|---|---|---|---|
| ≥70 | relleno rojo | grande | Líder **sobrecomprado** → vigilar techo |
| 60–70 | hueco rojo | grande | Líder **calentando** → continuación/atención |
| 30–40 | hueco verde | grande | Líder **enfriando** → atención |
| ≤30 | relleno verde | grande | Líder **sobrevendido** → posible rebote |
| Cualquiera | — | pequeña | Señal **menor** (menos peso en el mercado) |

## 6. Ejemplos reales (snapshot 2026-10-08)

27 acciones en oportunidad (0 en sobrecompra · 11 en oportunidad alta · 13 en oportunidad baja · 3 en sobreventa):

| Ticker | RSI | Zona | Forma | Capitalización | Cambio % |
|---|---:|---|---|---:|---:|
| **SHOP** | 69.4 | Oportunidad alta | hueco | 212.16B | −0.68% |
| **FTNT** | 69.1 | Oportunidad alta | hueco | 139.46B | — |
| **XOM** | 63.4 | Oportunidad alta | hueco | 692.73B | +2.73% |
| **V** | 62.8 | Oportunidad alta | hueco | 708.15B | +2.05% |
| **AAPL** | 60.7 | Oportunidad alta | hueco | **4.96T** | +0.78% |
| **MSFT** | 60.7 | Oportunidad alta | hueco | **3.88T** | — |
| **JPM** | 34.0 | Oportunidad baja | hueco | 877.81B | +0.19% |
| **JNJ** | 37.4 | Oportunidad baja | hueco | 616.19B | −1.09% |
| **GS** | 28.5 | Sobreventa | relleno | 256.04B | −0.94% |
| **MS** | 27.0 | Sobreventa | relleno | 293.00B | −1.66% |
| **BAC** | 22.1 | Sobreventa | relleno | 370.69B | −1.06% |

Lectura del snapshot: la zona **alta** está poblada por mega-caps (AAPL, MSFT) y por fuerza en energía/tech (XOM, V), mientras la zona **baja/sobreventa** la dominan **bancos** (JPM, GS, MS, BAC) y defensivos (JNJ, PEP). El banco **BAC (RSI 22)** es el más sobrevendido de los grandes.

## 7. Oportunidades y qué revisar

1. **Reversión en mega-cap:** RSI ≤30 + relleno en una capitalización enorme (BAC/GS/MS) → candidato a rebote, pero **confirmar** con divergencia y volumen: en mercados bajistas fuertes la sobreventa continúa.
2. **Enfriamiento/calentamiento temprano:** huecos en 60–70 (AAPL, MSFT, XOM) y 30–40 (JPM, JNJ) son zonas de **vigilancia**, no de entrada.
3. **Confirmación cruzada:** H1 dice **“quién”** está en extremo; K2 (ADX 15m) dice si es **tendencia o rango**; K3 (divergencia 5m) y E3 (confluencia) confirman el **giro**.
4. **Tamaño:** prioriza los puntos **grandes** (más liquidez y peso en el índice).
5. **RSI es diario:** durante la sesión el valor se actualiza al tick; la lectura es de **contexto del día**, no intradía.

**Qué revisar siempre:**
- No es señal operativa por sí sola: es un **radar de atención**.
- `≥70` / `≤30` en tendencia fuerte → *band walking* (puede seguir).
- El eje X no tiene orden de importancia: el orden es **ALTA|BAJA por RSI**; el peso se ve en el **tamaño**.

## 8. Analogías

- **Marcador de gigantes:** solo los pesos pesados “en racha”; el resto del mercado no aparece.
- **Termómetro por pisos:** las bandas son las plantas del edificio (fiebre arriba, hipotermia abajo); el tamaño del punto es cuánta gente (capital) hay en esa planta.
- **Semáforo del RSI:** rojo = lado caliente, verde = lado frío; **sólido** = extremo, **hueco** = aviso previo.
- **Embudo:** primero filtra por capitalización (los que importan), luego por extremo (los que destacan).

## 9. Referencias de código

| Qué | Dónde |
|---|---|
| Servicio | `services/heatmap_service.py::HeatmapService.top_equity_rsi` |
| Repositorio / SQL | `repositories/heatmap_repo.py::HeatmapRepo.top_equity_rsi` |
| Chart (opción ECharts) | `web/charts.py::scatter_rsi_option` (+ `_fmt_cap`) |
| Vista / endpoint | `web/views.py::rsi_limites` |
| Plantilla de card | `web/templates/partials/card_chart.html` |
| Tooltip genérico | `web/templates/partials/card_chart.html` (renderer `tooltipRows`) |
| Config | `config/charts/H1_rsi_limites.json` (`meta.rsi_limites.tf = "1D"` · `meta.rsi_limites.ayuda` · umbrales `rsi`) |
| Tiempo de evaluación | `Settings.chart_tf("rsi_limites")` → etiqueta `.ib-time` (ámbar) |
| Ayuda `(+)` | `Settings.chart_help("rsi_limites")` |
| Panel hermano | H2 · `/partials/multiframe` (RSI 5m vs 15m) |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
