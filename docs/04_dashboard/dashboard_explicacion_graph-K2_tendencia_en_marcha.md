# K2 · Tendencias en Marcha (ADX 15m) — cuadrante σ × ADX

> **Código:** K2 · **slug:** `tendencia_15m`
> **Endpoint:** `/partials/tendencia_15m`
> **Config:** `config/charts/K2_tendencia.json`
> **Servicio:** `services/tendencia_15m_service.py`
> **Chart:** `web/charts.py::scatter_tendencia_option`
> **Ubicación en el dashboard:** card de **4/12 columnas**, en la **misma fila** que K1 y K3 (K2 cols 5–8).
> **Documentación complementaria:** [`dashboard_radar_v2_0_0-Roadmap.md`](dashboard_radar_v2_0_0-Roadmap.md) y [`dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md` §2.6](dashboard_radar_v2_1_0-Roadmap_oportunidades_5m15m.md) (decisión de cuadrante σ × ADX).

---

## 1. Qué es

Es un **cuadrante (scatter)** que muestra, **para los mismos activos que K1**, qué tan fuerte es la tendencia a 15m (ADX). Comparte universo con K1 y comparte el **eje X** (σ), de manera que ambos cards se leen como **una sola vista**: K1 = posición en la banda · K2 = posición en la banda × régimen.

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

- **Eje X** = `z_banda` (σ): idéntico al eje Y del card K1 · marcas en ±k (bandas) y 0 (SMA20).
- **Eje Y** = `adx_15` (0–25 = sin tendencia · ≥25 = tendencia fuerte).
- **Línea vertical punteada** en X = 0 (SMA20).
- **Líneas verticales punteadas amarillas** en X = ±k (bandas de Bollinger, k = 2).
- **Línea horizontal punteada** en Y = `adx_min` (umbral de tendencia, 25).
- **Color del punto** = lado de K1: **rojo = CORTO** (rechazo banda superior) · **verde = LARGO** (rebote banda inferior).

## 2. Por qué aparece cada activo

K2 **no escanea el universo completo**: toma los mismos símbolos que K1 (universo compartido) y aplica un filtro adicional de **ADX 15m ≥ umbral**.

```
universo_K1 = activos que tocan/superan una banda de Bollinger (σ) con volumen ≥ 1x
K2 = universo_K1 ∩ {adx_15 ≥ adx_min (25)}
```

Por eso **los símbolos de K2 son un subconjunto (o igual) de los de K1**, no una lista nueva del mercado.

> **Analogía:** es como una **foto del mismo grupo de corredores (K1) pero con filtro de "tendencia"**: solo muestra los que además corren con viento a favor. Si un activo de K1 no aparece en K2, es que está en una **zona de reversión sin tendencia** (típico de rango/lateral).

## 3. Cómo se calcula

```
Para cada activo del universo_K1:
  z     = (close − SMA20) / σ          (Bollinger 20, σ)   ← compartido con K1
  adx   = ADX 15m                       ← de latest_market_tick
  si adx ≥ adx_min:
    entra al cuadrante K2

Eje X = z
Eje Y = adx
Orden en K1 = score desc
Mismo K1∩ADX en K2
```

Función pura (testeable): `Tendencia15mService.scan()` consume `Bollinger15mService.scan(limit=...)` y filtra por ADX.

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **Eje X** | `z_banda` (σ): **mismo eje Y del card K1** · nombres de bandas ±k y SMA20 |
| **Eje Y** | `adx_15`: 0–25 sin tendencia · ≥25 tendencia fuerte |
| **Líneas verticales** | X = 0 (SMA20), ±k (bandas de Bollinger) |
| **Línea horizontal** | Y = `adx_min` (umbral de tendencia) |
| **Color** | **rojo = CORTO** · **verde = LARGO** (mismo código que K1) |
| **Badge en tooltip** | Tipo de K1 (`RECHAZO HIGH` / `REBOTE LOW`) |
| **Tooltip** | Posición (σ) · ADX 15m · Close · Chg % · RSI 15m · Score |
| **Ayuda `(+)`** | botón junto al título; al pasar el cursor/foco muestra el **mapa general (matriz K1 × K2)** en un popup sobrepuesto (sin alterar el ancho/alto del card) |
| **Tamaño** | Constante (el "peso" ya está en el X = σ) |

### Leyenda en pantalla

```
● rojo = CORTO (rechazo banda superior)   ● verde = LARGO (rebote banda inferior)
┄ bandas de Bollinger (±2σ)             ─ SMA20 (media)
línea horizontal = umbral ADX ≥ 25
```

## 5. Interpretación de cada caso

### 5.1 Cuadrantes (eje Y: tendencia fuerte / no)

| Zona Y | Lectura |
|---|---|
| **Arriba (ADX ≥ 25)** | **Tendencia fuerte** — el extremo de banda ocurre dentro de un mercado tendido |
| **Abajo (ADX < 25)** | **Rango / sin tendencia** — el extremo de banda ocurre en lateral |

### 5.2 Matriz de decisión K1 × K2 (el punto clave)

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

> **Botón `(+)`.** Esta **matriz K1 × K2** (el mapa general) está disponible en el
> panel: el botón `(+)` junto al título la muestra en un **popup sobrepuesto** al pasar
> el cursor o dar foco (no altera el ancho ni el alto del card). El texto se declara en
> `config/charts/K2_tendencia.json` (`meta.tendencia_15m.ayuda`), se lee con
> `Settings.chart_help("tendencia_15m")` y se renderiza con el mecanismo genérico `ayuda`
> de `web/templates/partials/card_chart.html`.

> **Nota:** el eje Y de K2 mide la **fuerza** de tendencia (ADX); la **dirección** (alcista/bajista) no se dibuja en el eje — se lee en el tooltip («Chg») o se infiere del cambio diario.

- **K1 + K2 = "zona × régimen"** juntos.
- Extremo + rango → **reversión clásica** (el mejor escenario de K1).
- Extremo + tendencia **a favor** de la reversión → entrada de **continuación de calidad**.
- Extremo + tendencia **en contra** → **descartar** (*band walking*).

## 6. Ejemplos reales (snapshot 2026-10-08)

Universo K1 (top por score) intersectado con ADX ≥ 25:

| Ticker | z (σ) | ADX 15m | K1 lado | K1 tipo | En K2 |
|---|---:|---:|---|---|---|
| **TXN** | +3.27 | 36.2 | CORTO | RECHAZO HIGH (sobre sup.) | ✅ sí |
| **TER** | +1.91 | 40.4 | CORTO | RECHAZO HIGH (cerca sup.) | ✅ sí |
| **MCD** | −1.54 | <25 | LARGO | REBOTE LOW | no — rango |
| **CCJ** | −1.69 | 41.8 | LARGO | REBOTE LOW | ✅ sí |
| **TMO** | −1.72 | <25 | LARGO | REBOTE LOW | no — rango |
| **PANW** | −1.78 | 34.9 | LARGO | REBOTE LOW | ✅ sí |
| **PEP** | −1.92 | 29.5 | LARGO | REBOTE LOW | ✅ sí |
| **FTNT** | −2.29 | <25 | LARGO | REBOTE LOW | no — rango |
| **UPS** | −2.58 | <25 | LARGO | REBOTE LOW | no — rango |
| **UNH** | −3.27 | 31.4 | LARGO | REBOTE LOW (bajo inf.) | ✅ sí |

Lectura combinada (la **dirección** se toma del cambio diario, visible en el tooltip «Chg»):

| Activo | K1 | ADX 15m | Dir (Chg) | Veredicto |
|---|---|---|---:|---|
| **TXN** | CORTO (superó sup.) | 36.2 | BAJISTA | corto del rebote **a favor** de la bajista → ✅ alineado |
| **TER** | CORTO (cerca sup.) | 40.4 | BAJISTA | igual, tendencia **muy fuerte** → ✅ alineado |
| **CCJ** | LARGO (bajo inf.) | 41.8 | BAJISTA | largo **contra** la bajista → ⚠️ band walking |
| **PANW** | LARGO (bajo inf.) | 34.9 | BAJISTA | ⚠️ band walking |
| **PEP** | LARGO (bajo inf.) | 29.5 | BAJISTA | ⚠️ band walking leve |
| **UNH** | LARGO (bajo inf.) | 31.4 | BAJISTA | ⚠️ band walking (aunque vol = 4x) |

Es decir, en este snapshot todos los extremos de K1 están **dentro de tendencias fuertes** (ADX ≥ 25) y el mercado es bajista: los **CORTO** (TXN, TER) van **a favor** de la tendencia (corto del rebote), mientras los **LARGO** (CCJ, PANW, PEP, UNH) van **contra** (compran rebotes en un mercado bajista) → estos últimos requieren confirmación extra.

## 7. Complemento con K1 (por qué van juntos)

K1 es un panel **contrarian**: falla con *band walking* (en tendencia, el precio se pega a la banda y sigue). K2 ataca exactamente esa debilidad.

| K1 | K2 | Lectura |
|---|---|---|
| **«dónde»** | **«régimen»** | combinación = señal filtrada |
| Sin K2 | sin K2 | aviso crudo (puede ser trampa) |
| K1 + K2 (rango) | — | reversión clásica ✅ |
| K1 + K2 (tendencia a favor) | — | entrada de continuación ✅ |
| K1 + K2 (tendencia en contra) | — | descartar (band walking) ⚠️ |

> **Analogía:** K1 te dice **"dónde mirar"** (extremo de banda); K2 te dice **"cuándo es fiable"** (régimen). Juntos, convierten un aviso en una **señal filtrada**.

## 8. Ventajas

- **Comparte universo con K1** → no hay listas nuevas; misma operación, dos lentes.
- **Comparte eje X** → visualmente coherente con K1 (mismo σ).
- **Filtra falsos positivos de K1** → descarta reversiones contra tendencia fuerte.
- **Cobertura completa** → K1 (reversión) + K2 (tendencia) cubren los dos regímenes en la misma fila.
- **Autoexplicativo** → los cuadrantes y la línea de umbral cuentan la historia.

## 9. Analogías

- **Foto del mismo grupo con dos lentes:** K1 (lente "dónde") + K2 (lente "régimen").
- **Carril + tráfico:** K1 ve el borde del carril; K2 ve si hay tráfico (tendencia) en esa dirección.
- **Elástico + viento:** K1 ve cuánto se estira el precio; K2 ve si el viento lo empuja más.

## 10. Referencias de código

| Qué | Dónde |
|---|---|
| Servicio | `services/tendencia_15m_service.py` (`scan()` consume `Bollinger15mService.scan(limit=...)` y filtra por ADX) |
| Chart | `web/charts.py::scatter_tendencia_option` |
| Vista | `web/views.py::tendencia_15m` |
| Ayuda `(+)` | texto en `config/charts/K2_tendencia.json` (`meta.tendencia_15m.ayuda`) + `Settings.chart_help` + popup en `web/templates/partials/card_chart.html` |
| Tooltip genérico | `web/templates/partials/card_chart.html` (renderer `tooltipRows`) |
| Config | `config/charts/K2_tendencia.json` + `tendencia.adx_min` |
| Container | `core/container.py` (wired tras `Bollinger15mService`) |
| Dashboard | `web/templates/dashboard.html` (`<div class="cell seis">` al lado de K1) |
| Tests | `tests/test_trading_15m.py` (`test_tendencia_scan_universo_k1_filtrado_por_adx`) |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*