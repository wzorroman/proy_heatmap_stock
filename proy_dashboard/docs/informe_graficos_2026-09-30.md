# Informe de Gráficos del Dashboard — Radar Intermarket

> **Proyecto:** `proy_dashboard`  
> **Fecha del informe:** 2026-09-30  
> **Base de datos:** `heatmap_stock` (PostgreSQL 17.10, localhost:5432)  
> **Generado por:** análisis automatizado del código fuente y de los datos reales de BD.

---

## 1. Resumen ejecutivo

El dashboard ya tiene un buen esqueleto de **contexto de mercado** (score macro, riesgo intermarket, precio de índices, momentum diario, sectorial y calendario económico) y ahora incorpora un paquete de **trading intradía a 15 min implementado**: **Velas 15m**, **Screener 15m** y **Confluencia 5m/15m/1D**, que conectan el precio intradía con señales de compra/venta por ticker.

> **Analogía general:** el dashboard pasó de ser un **parte meteorológico matutino** a incluir también el **espejo del vestidor**: además de decir si va a llover, muestra cómo te queda cada prenda (cada ticker) antes de salir.

---

## 2. Gráficos actuales y su valor de decisión

| Panel | Valor para el trader | Analogía |
|---|---|---|
| **Score de mercado + zona COMPRAR/VENDER** | Ambiente general del día | El **termómetro del mercado**: > 6.5 = día cálido (alcista), < 4.5 = frío (bajista). |
| **Riesgo intermarket (VIX, US10Y, DXY, TLT)** | Viento en contra o a favor | Los **cuatro vientos**: si soplan de frente, cualquier operación cuesta más. |
| **Precio QQQ/SPY/ORO + SMA20/50** | Tendencia de los referentes | El **GPS del mercado**: te dice si vas en dirección correcta. |
| **Momentum top/bottom (1D)** | Extremos del día | La **foto del podio**: quién gana y quién pierde hoy. |
| **RSI top-cap + Multi-TF RSI 5m/15m** | Sobrecompra/venta y alineación temporal | Un **termómetro por habitación**: frío/calor en cada timeframe. |
| **Sectorial + riesgo sectorial** | Rotación de sectores | El **mapa de calor de una ciudad**: qué barrios están de moda. |
| **Anomalía de volumen / rango 52s** | Confirmación y posición histórica | El **medidor de gasolina**: sin combustible, el movimiento no dura. |
| **Calendario económico** | Eventos que pueden mover el mercado | Las **obras en la carretera**: saber dónde puede haber atascos. |

---

## 3. Inventario de datos observado en BD (2026-09-30)

| Tabla / vista | Contenido | Filas / observación |
|---|---|---|
| `fact_market_series` | Ticks técnicos ~3 min (110 activos) | ~2.43 M filas; actual hasta 2026-09-29 |
| `fact_market_bar_15m` | Velas OHLC 15 min | **18 741 filas**, pero **estancada desde 2026-09-23 09:15** |
| `fact_market_indicator_tf` | Indicadores en tf `5` y `15` | 818 filas; datos recientes pero historia corta |
| `latest_market_tick` | Último tick por activo | 123 filas; incluye `rsi_15`, `cci20_15`, `bbpower_15`, `adx_15`, `pivot_r3_15` |
| `fact_heatmap_snapshot` | Snapshot sectorial | 9 001 filas; última ventana disponible |
| `fact_economic_event` | Calendario económico | 579 eventos cargados |
| `fact_market_score` / `fact_market_score_agg` | Score histórico | **No existen en BD** aunque el código las referencia |

> **Analogía del dato:** la base de datos es como una **cocina bien surtida**: tienes ingredientes frescos (`latest_market_tick`, `fact_market_series`) y otros que se empezaron a secar (`fact_market_bar_15m`). Antes de cocinar los nuevos gráficos hay que revisar la despensa.

---

## 4. Gaps críticos para trading a 15 min (estado tras implementación)

1. **`fact_market_bar_15m` desactualizado** → 🟡 **Mitigado:** `bar_15m_repo` ensambla barras 15m desde ticks (`fact_market_series`) cuando la barra materializada está vieja. Pendiente reactivar el pipeline.
2. **Sin cálculo de VWAP, Bollinger ni S/R a 15 min** → ✅ **Resuelto:** `services/bar_15m_service.py` calcula SMA 9/21, Bollinger 20/2 y VWAP.
3. **Sin screener 15 min** → ✅ **Resuelto:** `services/screener_15m_service.py` + parcial `/partials/screener_15m` en el dashboard.
4. **Sin detalle por ticker** → 🟡 **Parcial:** el clic en una fila del screener carga las velas 15m del ticker; falta una página dedicada de análisis.
5. **Tablas de score histórico no creadas** → ⬜ **Pendiente:** `fact_market_score` / `fact_market_score_agg` siguen sin migración.
6. **Sin breakout de rango inicial** → ✅ **Resuelto:** `services/initial_balance_service.py` + parcial `/partials/ib_acciones` (5.4a) y pastilla IB integrada en las tarjetas de precio (5.4b).
7. **Sin mapa sectorial 15m** → ✅ **Resuelto:** `services/sector_15m_service.py` + parcial `/partials/sector_15m` (5.5).
8. **Sin histograma de score 15m** → ✅ **Resuelto:** `ScoreService.distribucion_15min()` + `/partials/score_15m` (5.6).
9. **Sin detector de divergencias precio/RSI** → ✅ **Resuelto:** `services/divergencia_service.py` + `/partials/divergencia` (5.7).

---

## 5. Gráficos propuestos e implementados para soporte de compra/venta (15 min)

> **Leyenda de estado:** ✅ Implementado · 🟡 Parcial · ⬜ Propuesto (pendiente de implementar).
>
> Cada ficha incluye: qué muestra, reglas de señal, **analogía**, **diseño del gráfico (ASCII)** y **algoritmo de cálculo** (pseudocódigo, sin código fuente).

| # | Gráfico | Estado |
|---|---|---|
| 5.1 | Velas 15 min (volumen, SMA, Bollinger, VWAP) | ✅ Implementado |
| 5.2 | Screener 15 min de oportunidades | ✅ Implementado |
| 5.3 | Confluencia multi-timeframe 5m / 15m / 1D | ✅ Implementado |
| 5.4a | Breakout del rango inicial — **por acción** | ✅ Implementado |
| 5.4b | Rango inicial — **mercado**, integrado como pastilla IB en las tarjetas de precio (QQQ/SPY/IWM) | ✅ Implementado |
| 5.5 | Mapa de calor 15m por sector | ✅ Implementado |
| 5.6 | Histograma / distribución del score 15 min | ✅ Implementado |
| 5.7 | Alerta de divergencia precio / RSI 15m | ✅ Implementado |

---

### 5.1 Velas 15 min con volumen, SMAs, Bollinger y VWAP
**Estado:** ✅ Implementado — `services/bar_15m_service.py`, `web/templates/partials/velas_15m.html`, endpoint `/partials/velas_15m`.

**Qué muestra:** gráfico de velas de una acción con volumen, SMA 9/21, bandas de Bollinger, VWAP de sesión y una señal COMPRAR/VENDER/NEUTRAL.

**Reglas de señal implementadas:**
- **COMPRAR:** precio > VWAP, SMA9 > SMA21, volumen ≥ mínimo y RSI < sobrecompra.
- **VENDER:** precio < VWAP, SMA9 < SMA21, volumen ≥ mínimo y RSI > sobreventa.
- **NEUTRAL:** cualquier otro caso.

**Analogía:** es como conducir en una autopista: el **VWAP** es el carril central, las **bandas de Bollinger** son los arcenes y el **volumen** es el tráfico. Comprar es cambiar de carril hacia adelante solo cuando hay espacio (volumen) y vas en la misma dirección que el tráfico (tendencia).

**Diseño (ASCII):**
```text
Velas 15m — NASDAQ:MSTR
┌───────────────────────────────────────────────────────────────┐
│ Velas 15m  [ NASDAQ:MSTR ]                     ● COMPRAR       │
│ Close 1063.88  VWAP 1067.44  Vol 1.01  RSI 37.8  ADX 23.4      │
├───────────────────────────────────────────────────────────────┤
│ 1080 ┤                                        ╱ BB upper       │
│ 1075 ┤                  ╱╲        ╱╲        ╱                  │
│ 1070 ┤      ╱╲     ╱╲  ╱  ╲     ╱  ╲      ╱   SMA9            │
│ 1065 ┤   ╱╲╱  ╲  ╱  ╲╱    ╲  ╱     ╲   ═══════ VWAP           │
│ 1060 ┤  ╱      ╲╱          ╲╱       ╲ ╱                        │
│ 1055 ┤                                 ╲  SMA21                │
│ 1050 ┤                                  ╲ BB lower             │
├───────────────────────────────────────────────────────────────┤
│ volumen  ▁ ▂ ▄ ▅ █ ▆ ▅ ▄ ▃ ▂ ▁ ▂ ▄ ▆ █                         │
└───────────────────────────────────────────────────────────────┘
```

**Algoritmo de cálculo:**
```text
ALGORITMO Velas 15m
 1. Entrada: símbolo, ventana (48 h) y umbrales configurables.
 2. Leer barras 15m; si la última es más vieja que stale_min → ensamblar desde ticks.
 3. Ensamblar barra 15m:
      agrupar ticks por floor_15m(timestamp);
      open  = primer precio del grupo
      high  = máximo; low = mínimo
      close = último precio del grupo
      volume = Σ volumen del grupo
 4. SMA(n): media móvil simple de los últimos n cierres.
 5. Bollinger(20, 2): media ± 2·desviación estándar de 20 cierres.
 6. VWAP acumulado:
      precio típico = (O + H + L + C) / 4
      VWAP = Σ(típico × volumen) / Σ(volumen)
 7. Volumen relativo = volumen última barra / media de las 10 anteriores.
 8. RSI/ADX 15m: último valor disponible del tick.
 9. Señal:
      COMPRAR si close>VWAP ∧ SMA9>SMA21 ∧ ADX≥adx_min ∧ vol_ratio≥vol_min ∧ RSI<sobrecompra
      VENDER  si close<VWAP ∧ SMA9<SMA21 ∧ ADX≥adx_min ∧ vol_ratio≥vol_min ∧ RSI>sobreventa
      si no → NEUTRAL
10. Normalizar toda salida numérica a ≤ 4 decimales.
```

---

### 5.2 Screener 15 min de oportunidades
**Estado:** ✅ Implementado — `services/screener_15m_service.py`, `web/views.py::_screener_filas()`, `web/templates/partials/screener_15m.html`.

**Qué muestra:** ranking de acciones con logo, símbolo, distancia al VWAP, RSI 15m, ADX 15m, cambio %, volumen relativo y señal; filas clicables que actualizan el gráfico de velas.

**Señal resultante:** COMPRAR / VENDER / NEUTRAL por fila.

**Analogía:** es el **menú del día** de un restaurante: en vez de revisar la nevera entera, ves solo los platos listos para pedir. El trader elige de una lista corta y priorizada.

**Diseño (ASCII):**
```text
Screener 15 min
┌────────────────────────────────────────────────────────────────────────────┐
│ Acciones equity · mostrando 15 de 22 con señal (total 48)                   │
├─────────────┬───────────┬────────┬────────┬─────────┬───────────┬──────────┤
│ SÍMBOLO     │ DIST VWAP │ RSI15  │ ADX15  │ CHANGE  │ VOL RATIO │ SEÑAL    │
├─────────────┼───────────┼────────┼────────┼─────────┼───────────┼──────────┤
│ 🟢 SHOP     │  +1.24%   │  58.3  │  27.4  │ +2.15%  │   1.84x   │ COMPRAR  │ ← seleccionada
│ 🟢 NVDA     │  +0.91%   │  61.2  │  25.1  │ +1.60%  │   1.52x   │ COMPRAR  │
│ 🔴 MSTR     │  -0.87%   │  41.2  │  24.1  │ -1.60%  │   1.40x   │ VENDER   │
│ ⬛ XYZ      │  +0.10%   │  50.0  │  18.0  │ +0.05%  │   0.90x   │ NEUTRAL  │
└─────────────┴───────────┴────────┴────────┴─────────┴───────────┴──────────┘
  logo + símbolo · clic en fila → recarga el gráfico Velas 15m
  sin logo → cuadro negro (⬛) para no desalinear
```

**Algoritmo de cálculo:**
```text
ALGORITMO Screener 15m
 1. Universo = equities presentes en el último tick con barras recientes (≤ screener_horas).
 2. Por símbolo, calcular los indicadores del algoritmo 5.1
    (change %, VWAP, distancia al VWAP, volumen relativo, RSI 15m, ADX 15m).
 3. Clasificar señal COMPRAR / VENDER / NEUTRAL con las reglas del 5.1.
 4. Ordenar por fuerza mixta: COMPRAR > VENDER > NEUTRAL;
    dentro de cada grupo, por |change %| descendente.
 5. Selección final:
      si accionables ≥ 5  → mostrar hasta 20 con señal
      si accionables 1–4  → accionables + top movimiento hasta 15
      si accionables = 0  → top 15 por movimiento
 6. Enriquecer cada fila con el logo del símbolo.
 7. Normalizar todos los numéricos a ≤ 4 decimales.
```

---

### 5.3 Confluencia multi-timeframe 5m / 15m / 1D
**Estado:** ✅ Implementado — `services/confluencia_service.py`, `web/charts.py::confluencia_option()`, `web/templates/partials/confluencia.html`.

**Qué muestra:** heatmap de la dirección (alcista/bajista/neutral) de cada acción en 5m, 15m y 1D, sobre los mismos símbolos y en el mismo orden que el screener.

**Lectura de color (pastel):** verde = alcista, rojo = bajista, gris = neutral.

**Analogía:** es como remar un bote: si la corriente del río (1D), el viento (15m) y tus brazos (5m) empujan en la misma dirección, avanzas con poco esfuerzo. Si no, remas en contra y te cansas.

**Diseño (ASCII):**
```text
Confluencia 5m / 15m / 1D        verde = alcista · rojo = bajista · gris = neutral
                  5m          15m          1D
             ┌──────────┬──────────┬──────────┐
  SHOP       │ █ verde  │ █ verde  │ ░ gris   │
  NVDA       │ █ verde  │ ░ gris   │ █ verde  │
  MSTR       │ ▒ rojo   │ ▒ rojo   │ ▒ rojo   │
  LLY        │ █ verde  │ █ verde  │ █ verde  │
   ...       │          │          │          │
             └──────────┴──────────┴──────────┘
  ↑ encabezados de timeframe arriba (color claro)
  ↑ orden vertical = mismo orden del screener (primero arriba)
```

**Algoritmo de cálculo:**
```text
ALGORITMO Confluencia 5m/15m/1D
 1. Tomar la lista de símbolos del screener (mismo orden).
 2. Por símbolo, obtener la señal de cada timeframe: 5m, 15m, 1D.
 3. Codificar: ALCISTA = +1 · NEUTRAL = 0 · BAJISTA = −1.
 4. Construir matriz [símbolo × timeframe] con esos valores.
 5. Colorear con escala divergente pastel:
      −1 → rojo pastel (#e79a9a)
       0 → gris neutral  (#2f3844)
      +1 → verde pastel (#8fd19e)
 6. Invertir el eje Y para que el primer símbolo del screener quede arriba.
```

---

### 5.4 Breakout del rango inicial (Initial Balance)
**Estado:** ✅ Implementado — `services/initial_balance_service.py`, `web/views.py` (`/partials/ib_acciones`), plantilla `partials/ib_acciones.html`; y **5.4b integrado** en las tarjetas de precio (`partials/precios.html`).

**Decisión de diseño (actualizada):**
- **5.4a — por acción:** panel propio que lista las rupturas de cada equity del universo del screener (`/partials/ib_acciones`).
- **5.4b — mercado:** el IB de los índices de referencia **ya no es un card separado**; se integra como **pastilla `IB`** en las tarjetas de precio **QQQ / SPY / IWM** (junto a la señal COMPRAR/VENDER/NEUTRAL). En ORO se muestra `---` porque el concepto no aplica.
- El card independiente "Rango inicial — mercado" fue **eliminado** para no duplicar información; queda espacio reservado en la fila para un próximo gráfico.

Ambos indican explícitamente la **ventana horaria de apertura** `09:30–10:00 NY` (configurable con `ib_minutos`, por defecto 30 min).

**Qué muestra:** las barras de 15m de la apertura regular (09:30–10:00 NY) forman un rango. El panel marca si el precio lo rompió después, con la hora exacta de la ruptura.

**Reglas de señal implementadas:**
- **Ruptura alcista:** cierre de una barra posterior > `IB_high`.
- **Ruptura bajista:** cierre de una barra posterior < `IB_low`.
- **Sin ruptura (`DENTRO`):** el precio permanece entre `IB_low` e `IB_high`.

**Analogía:** es la **salida de una maratón**. Los primeros minutos definen quién toma la delantera. Si un corredor rompe el grupo inicial con fuerza, probablemente mantendrá el liderazgo durante la carrera.

**Diseño (ASCII) — 5.4a por acción:**
```text
Initial Balance — por acción            [09:30–10:00 NY]
┌───────────┬────────┬────────┬────────┬─────────┬───────┬──────────┐
│ SÍMBOLO   │ IB low │ IB high│ Close  │ FUERZA  │ HORA  │ RUPTURA  │
├───────────┼────────┼────────┼────────┼─────────┼───────┼──────────┤
│ 🟢 SHOP   │ 1055.1 │ 1062.4 │ 1068.9 │ +0.61%  │ 10:30 │ COMPRAR  │
│ 🔴 MSTR   │  980.0 │  992.5 │  971.2 │ -2.14%  │ 10:15 │ VENDER   │
│ ⬛ XYZ    │  100.0 │  101.5 │  101.0 │ +0.00%  │  —    │ DENTRO   │
└───────────┴────────┴────────┴────────┴─────────┴───────┴──────────┘
  clic en fila → actualiza el gráfico Velas 15m · ordenado por fuerza
```

**Diseño (ASCII) — 5.4b integrado en las tarjetas de precio:**
```text
Precio QQQ (NASDAQ-100) — SMA20/SMA50
┌──────────────────────────────────────────────────────────┐
│ [COMPRAR] [IB ALCISTA · 10:00]  Convicción 72/100  QQQ    │
│  precio + SMA20/SMA50 + métricas ...                      │
└──────────────────────────────────────────────────────────┘

Precio IWM (Russell 2000) — SMA20/SMA50
┌──────────────────────────────────────────────────────────┐
│ [NEUTRAL] [IB DENTRO]           Convicción 55/100  IWM    │
└──────────────────────────────────────────────────────────┘

Precio ORO (XAUUSD) — SMA20/SMA50
┌──────────────────────────────────────────────────────────┐
│ [NEUTRAL] [---]                 Convicción 50/100  ORO    │
└──────────────────────────────────────────────────────────┘
  pastilla IB: verde ALCISTA · rojo BAJISTA · ámbar DENTRO · --- sin IB
```

**Algoritmo de cálculo:**
```text
ALGORITMO Initial Balance (IB)
 1. Definir la ventana de apertura: 09:30 + ib_minutos (por defecto 30 → 10:00 NY).
 2. Agrupar las barras 15m por fecha local (America/New_York); usar la más reciente.
 3. Tomar las barras dentro de [09:30, 10:00):
      IB_high = máximo de los highs
      IB_low  = mínimo de los lows
 4. Recorrer las barras posteriores a las 10:00 en orden:
      si close > IB_high → ruptura ALCISTA (primera que ocurra)
      si close < IB_low  → ruptura BAJISTA (primera que ocurra)
      si no → DENTRO
 5. Fuerza:
      ALCISTA: (close − IB_high) / IB_high × 100
      BAJISTA: (IB_low − close) / IB_low × 100
 6. Guardar la hora local de la ruptura (HH:MM).
 7. 5.4a: aplicar a cada equity del screener y ordenar por fuerza desc.
    5.4b: evaluar QQQ/SPY/IWM y adjuntar la pastilla IB a su tarjeta de precio
          (ORO muestra "---" porque no tiene sesión NY).
```

---

### 5.5 Mapa de calor 15m por sector
**Estado:** ✅ Implementado — `services/sector_15m_service.py`, `web/charts.py::sector_15m_option()`, endpoint `/partials/sector_15m`.

**Qué muestra:** treemap del cambio % medio de las acciones en la última barra 15m agrupado por sector. El **color** va de verde a rojo según el cambio medio y el **área** de cada celda es proporcional al número de acciones con datos del sector.

**Analogía:** es como la **ola en un estadio**: primero se levanta un sector, luego el movimiento se contagia a otros. Si estás en el sector que inicia la ola, tienes viento a favor.

**Diseño (ASCII):**
```text
Mapa de calor 15m por sector (treemap · área = nº de acciones)
┌──────────────────────────────────┬───────────────────────┐
│                                  │  Salud                │
│   Tecnología                     │  +0.4%   (n=8)        │
│   +1.8%   (n=19)                 ├───────────┬───────────┤
│                                  │ Consumo   │ Financiero│
│                                  │ +0.9%     │ +0.1%     │
├──────────────────┬───────────────┴───────────┴───────────┤
│ Energía -0.9%    │ Utilities -1.6%   (n=3)                │
└──────────────────┴────────────────────────────────────────┘
  color = cambio % medio (verde ↑ / rojo ↓)   ·   área = nº de acciones
```

**Algoritmo de cálculo:**
```text
ALGORITMO Mapa de calor sectorial 15m
 1. Construir el mapa símbolo → sector (dim_asset vía latest_market_tick).
 2. Tomar las filas del screener 15m (cambio % de la última barra 15m por símbolo).
 3. Agrupar los cambios por sector.
 4. Cambio del sector = media aritmética de los cambios de sus miembros.
 5. Tamaño (área del treemap) = nº de acciones del sector con datos.
 6. Ordenar sectores por cambio medio desc.
 7. Colorear con escala divergente: <0 rojo, 0 gris, >0 verde.
    Rango **dinámico** simétrico = máx(|cambio|) (mínimo 0.05) para que los
    cambios 15m, que son pequeños, no queden todos en gris.
```

---

### 5.6 Histograma / distribución del score 15 min
**Estado:** ✅ Implementado — `services/score_service.py::distribucion_15min()/histograma_de_scores()`, `web/charts.py::score_hist_option()`, endpoint `/partials/score_15m`.

**Qué muestra:** histograma del score 15m de todas las acciones, con barras coloreadas por zona (verde ≥6.5, rojo ≤4.5, gris intermedio), una marca de la **media del mercado** y una **descripción/recomendación** de lo que está pasando, mostrada **debajo del gráfico**. **El título indica la temporalidad del cálculo** (p. ej. "Distribución score 15m").

**Analogía:** es un **examen estadístico**. Saber que sacaste 8/10 no dice mucho; saber que solo el 5% sacó más que tú sí. El trader sabrá si el mercado está en un extremo poco probable.

**Diseño (ASCII):**
```text
Distribución score 15m
n
 │        ▄
 │      ▄ █ ▄
 │    ▄ █ █ █ ▄         ┊ ← Mercado 5.4
 │  ▄ █ █ █ █ █ ▄       ┊
 │▄ █ █ █ █ █ █ █ ▄
 └┬────┬────┬────┬────┬───────► score
  3   4.5   6.5   8   10
  (rojo)  (gris)  (verde)

Media 5.4 · percentil 57 · 32% COMPRAR / 12% VENDER
"MERCADO MIXTO: 0% COMPRAR / 54% VENDER de 70 acciones.
 Media 4.58 (percentil 57). Sin sesgo claro; esperar ruptura."
```

**Algoritmo de cálculo:**
```text
ALGORITMO Histograma de score 15m
 1. Leer los últimos N registros (score_15min.last_n) por acción en tf=15
    de fact_market_indicator_tf (solo equities).
 2. Por acción, puntuar cada registro con el motor de score (RSI, ADX,
    CCI20, BBPower, cambio) y promediar sus últimas N puntuaciones.
 3. Definir bins uniformes entre el mínimo y el máximo de scores.
 4. Contar cuántas acciones caen en cada bin.
 5. Media del mercado = media de los scores de todas las acciones.
 6. Percentil = % de acciones con score ≤ media.
 7. Etiquetar zona: ≥6.5 COMPRAR · ≤4.5 VENDER · resto NEUTRAL.
 8. Elegir la sugerencia de un catálogo de 11 combinaciones según zona y
    % en cada extremo (el texto no repite las métricas de las etiquetas).
 9. Colorear barras por zona y marcar el bin de la media (línea amarilla).
```

---

### 5.7 Alerta de divergencia precio / RSI 15m
**Estado:** ✅ Implementado — `services/divergencia_service.py`, `web/views.py` (`/partials/divergencia`), plantilla `partials/divergencia.html`.

**Qué muestra:** lista de activos donde el precio hace máximo creciente pero el RSI no (divergencia **bajista**) o mínimo decreciente pero el RSI no (divergencia **alcista**). Cada fila es clicable y actualiza el gráfico de velas.

**Analogía:** es como un coche que acelera el motor pero no gana velocidad. El ruido es fuerte, pero la energía no se traduce en movimiento: algo se está agotando.

**Diseño (ASCII):**
```text
Divergencia precio / RSI  [15m]        3 alertas de 20 acciones
┌──────────────────────────────────────────────────────────┐
│ 🟢 WM    [COMPRAR]   P -0.10% · RSI 34.2→36.2            │  ← alcista
│ 🔴 ADSK  [VENDER ]   P +0.33% · RSI 68.7→66.7            │  ← bajista
│ 🟢 DDOG  [COMPRAR]   P -0.11% · RSI 58.7→60.3            │
└──────────────────────────────────────────────────────────┘
  verde = divergencia alcista (mín. más bajo, RSI más alto)
  rojo  = divergencia bajista (máx. más alto, RSI más bajo)

NASDAQ:XYZ — divergencia bajista
precio  ╱╲      ╱╲  ← precio: máximo creciente
       ╱  ╲    ╱
      ╱    ╲  ╱
RSI    ╱╲   ╲╱  ← RSI: máximo decreciente
      ╱  ╲
   ⇒ agotamiento del impulso
```

**Algoritmo de cálculo:**
```text
ALGORITMO Divergencia precio / RSI 15m
 1. Leer las barras 15m de la ventana (div_horas, por defecto 48 h).
 2. Calcular el RSI de Wilder (periodo 14) sobre los cierres.
 3. Detectar pivotes locales de máximos y de mínimos (ventana ±k velas).
 4. Tomar los dos últimos pivotes de máximos y de mínimos.
 5. Divergencia BAJISTA: máx2 > máx1 ∧ RSI2 < RSI1 − div_rsi_min.
    Divergencia ALCISTA: mín2 < mín1 ∧ RSI2 > RSI1 + div_rsi_min.
 6. Exigir separación mínima entre pivotes (min_sep) para evitar ruido.
 7. Ordenar por |Δ RSI| desc y limitar a div_max (por defecto 15).
 8. Salida por fila: símbolo, tipo, Δ precio %, RSI inicial→final.
```

---

### 5.8 Alcance del Initial Balance: ¿por acción o el mercado?
**Estado:** ✅ **Decidido e implementado** — se implementan **las dos opciones como subgráficos separados** (§5.4a y §5.4b).

**Pregunta original:** el rango inicial (09:30–10:00 NY) se puede calcular para **cada acción** del universo del screener o para **índices de mercado** (SPY, QQQ, IWM). La elección cambia el diseño y el valor de decisión del panel.

**Opción A — Por cada acción (recomendada):**
- Se calcula el rango IB de cada equity del mismo universo del screener.
- **Resultado:** listado de acciones que rompieron su rango hoy, accionable para operar.
- **Ejemplo:** “SHOP rompió IB_high con +1.8% y volumen 2.3x”.
- **Ventajas:** reutiliza `services/bar_15m_service.py` y el universo del screener; el trader ve el ticker exacto; escala a todas las acciones sin fuentes nuevas.

**Opción B — A nivel de mercado (SPY / QQQ / IWM):**
- Se calcula el IB de índices representativos.
- **Resultado:** mini-gauge o línea de contexto: “mercado dentro del IB / QQQ rompió al alza / IWM rompió a la baja”.
- **Ventajas:** da el sesgo general del día.
- **Desventajas:** no indica qué acción operar; ya está parcialmente cubierto por el panel de Precio QQQ/SPY/ORO.

**Diseño (ASCII) de las dos opciones:**
```text
OPCIÓN A — Breakout IB por acción              OPCIÓN B — IB del mercado
┌────────────────────────────────────────┐     ┌──────────────────────────────┐
│ Breakout rango inicial (09:30–10:00)    │     │ IB del mercado               │
├───────────┬──────────┬────────┬────────┤     │  SPY  ● broke high           │
│ SÍMBOLO   │ RUPTURA  │ FUERZA │ VOL    │     │  QQQ  ○ dentro del rango     │
├───────────┼──────────┼────────┼────────┤     │  IWM  ▼ broke low            │
│ 🟢 SHOP   │ IB_high ▲│ +1.8%  │ 2.3x   │     │                              │
│ 🔴 MSTR   │ IB_low  ▼│ -1.4%  │ 1.9x   │     │  ⇒ sesgo mixto               │
│ ⬛ XYZ    │ dentro   │  —     │ 0.8x   │     └──────────────────────────────┘
└───────────┴──────────┴────────┴────────┘
```

**Recomendación:** implementar **Opción A como panel principal** (mismo universo y orden que el screener) y añadir una **línea de contexto** con el IB de SPY/QQQ.

**Razones:**
1. El dashboard ya está construido alrededor de **acciones individuales** (screener + velas).
2. Reutiliza `bar_15m_service` y el universo del screener sin nuevas fuentes de datos.
3. Un listado de breakouts se traduce directamente en una decisión de compra/venta.
4. El contexto de mercado SPY/QQQ complementa pero no reemplaza la señal por acción.

**Decisión tomada (2026-09-30 y actualizada):**
- **5.4a por acción:** panel independiente en el dashboard → **`/partials/ib_acciones`**.
- **5.4b mercado:** **integrado** en las tarjetas de precio QQQ/SPY/IWM como **pastilla `IB`** (en lugar de un card aparte, que fue eliminado). Se agregó **IWM** como cuarta tarjeta de precio.
- Ambos usan la **ventana horaria `09:30–10:00 NY`** (parámetro `ib_minutos`, por defecto 30) y la **hora exacta de la ruptura**.
- La fila queda `ib_acciones` (3) + `sector_15m` (6) + **3 columnas reservadas** para un próximo gráfico.

---

## 6. Plan técnico de implementación (estado)

### Paso 0 — Asegurar datos 15 min
- ✅ Fallback implementado: `repositories/bar_15m_repo.py` ensambla barras desde ticks cuando `fact_market_bar_15m` está vieja.
- ⬜ Diagnosticar y reactivar el pipeline de `fact_market_bar_15m` (detenido el 2026-09-23).
- ⬜ Migración Alembic para `fact_market_score` y `fact_market_score_agg`.

### Paso 1 — Repositorios
- ✅ `repositories/bar_15m_repo.py`: barras 15m + fallback a ticks.
- ⬜ Ranking por indicador tf=15 en `indicator_repo.py`.
- ⬜ Agregación sectorial 15m en `heatmap_repo.py`.

### Paso 2 — Servicios
- ✅ `services/bar_15m_service.py`: OHLC 15m, SMA 9/21, Bollinger, VWAP, volumen relativo y señal. (Rango inicial aún no.)
- ✅ `services/screener_15m_service.py`: señales COMPRAR/VENDER/NEUTRAL y ranking.
- ✅ `services/confluencia_service.py`: alineación 5m/15m/1D.
- ✅ `services/initial_balance_service.py`: rango inicial por acción y de mercado.
- ✅ `services/sector_15m_service.py`: cambio medio 15m por sector.
- ✅ `services/score_service.py`: `distribucion_15min()` e `histograma_de_scores()` (histograma del score 15m + descripción).
- ✅ `services/divergencia_service.py`: divergencias precio/RSI 15m (`scan()`, `detectar()`, `rsi_serie()`).

### Paso 3 — Opciones ECharts en `web/charts.py`
- ✅ `candlestick_option(...)` con velas, indicadores y señal.
- ✅ `confluencia_option(...)` tipo heatmap (eje Y invertido, colores pastel).
- ✅ Screener renderizado como tabla HTML interactiva (no option ECharts).
- ✅ Initial Balance renderizado como parcial HTML (por acción) + pastilla en precios.
- ✅ `sector_15m_option(...)` treemap sectorial (cambio medio 15m).
- ✅ `score_hist_option(...)` histograma del score 15m con marca de media.

### Paso 4 — Endpoints y parciales
- ✅ `web/views.py`: `/partials/velas_15m`, `/partials/screener_15m`, `/partials/confluencia`.
- ✅ `web/views.py`: `/partials/ib_acciones`, `/partials/sector_15m`, `/partials/score_15m`, `/partials/divergencia` y pastilla IB en `/partials/precios` (5.4b).
- ✅ `api/routers/trading15m.py`: `/api/trading15m/velas`, `/screener`, `/confluencia`.

### Paso 5 — Dashboard
- ✅ Sección **“Trading 15 min”** agregada en `dashboard.html` en dos filas: `Screener 5 · Rango inicial 4 · Confluencia 3` y `Velas 7 · Mapa sectorial 5`.
- ✅ Gráfico de velas sincronizado con el clic del screener y resaltado de la fila seleccionada.
- ✅ Fila **IB por acción (3) + sectorial 15m (6) + divergencias 15m (3)**; IB de mercado integrado en las tarjetas de precio QQQ/SPY/IWM (5.4b) e IWM agregado como cuarta tarjeta.

### Paso 6 — Tests
- ✅ Tests unitarios de SMA, Bollinger, VWAP, volumen relativo y ensamblaje de ticks.
- ✅ Tests de señales del screener y confluencia.
- ✅ Tests del rango inicial (ruptura alcista/bajista, dentro, scan prioriza rupturas).
- ✅ Test de agregación sectorial 15m (media y orden).
- ✅ Tests del histograma de score 15m (`tf_label`, distribución/descripción, caso vacío y catálogo/selección de sugerencias).
- ✅ Tests de divergencias (RSI de Wilder, divergencia alcista/bajista y sin patrón).

---

## 7. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| `fact_market_bar_15m` desactualizado | Velas con datos viejos | Reactivar pipeline o agregar fallback desde `fact_market_series` |
| `fact_market_score` no existe | Historial de score falla | Crear migración Alembic antes de usar ese panel |
| `fact_market_indicator_tf` con poca historia | Backtest limitado | Calcular indicadores sobre barras 15m en lugar de depender de `indicator_tf` |
| Cálculos pesados en Python | Lentitud | Delegar agregaciones a SQL/PostgreSQL |
| Señales automáticas mal calibradas | Falsos positivos | Empezar con señales visuales + thresholds configurables en `config_dashboard.json` |

---

## 8. Conclusión

El dashboard combina una base sólida de **contexto macro y sectorial** con un paquete de **ejecución intradía a 15 min ya implementado**, lo que lo convierte de un “parte meteorológico” en una **herramienta de decisión operativa** para acciones.

**Implementado (§5.1–§5.7):** Velas 15m, Screener 15m (logos, filas clicables y selección resaltada), Confluencia 5m/15m/1D (mismos símbolos/orden que el screener, colores pastel), **Rango inicial (Initial Balance)** —**5.4a** panel por acción y **5.4b** pastilla IB integrada en las tarjetas de precio QQQ/SPY/IWM—, **Mapa de calor 15m por sector (5.5)**, **Histograma del score 15m (5.6)** y **Divergencias precio/RSI 15m (5.7)**.

> **Total de gráficos: 8 fichas** (5.1, 5.2, 5.3, 5.4a, 5.4b, 5.5, 5.6, 5.7) — **todas implementadas**. 5.4b se integra en el panel de precios, que además gana la tarjeta **IWM**.

**Próximos pasos recomendados:**
1. Reactivar el pipeline de `fact_market_bar_15m` para depender menos del fallback por ticks.
2. Definir el criterio 10 alcistas + 10 bajistas del screener (ver §D del anexo).
3. Crear la migración de `fact_market_score` si se quiere historial de score.
4. Calibrar umbrales de divergencia (`div_rsi_min`) con datos reales.

---

# Anexo — Actualización de implementación (2026-09-30)

> Esta sección documenta el estado **posterior a la implementación** del paquete de gráficos 15 min, el criterio real del screener y las decisiones de diseño tomadas durante la sesión.

## A. Estado de implementación

### A.1 Componentes entregados

| Capa | Archivo | Descripción |
|---|---|---|
| Servicio | `services/bar_15m_service.py` | OHLC 15m, SMA 9/21, Bollinger, VWAP, volumen relativo y señal. |
| Servicio | `services/screener_15m_service.py` | Scanner de equities con señal COMPRAR/VENDER/NEUTRAL. |
| Servicio | `services/confluencia_service.py` | Alineación 5m/15m/1D; acepta `symbols=` para respetar el orden del screener. |
| Servicio | `services/initial_balance_service.py` | Rango inicial 09:30–10:00 NY: `scan_por_accion(symbols)` y `scan_mercado()` (SPY/QQQ/IWM). |
| Servicio | `services/sector_15m_service.py` | Cambio medio 15m por sector (`por_sector()`, `agregar()`). |
| Servicio | `services/divergencia_service.py` | Divergencias precio/RSI 15m (`scan()`, `detectar()`, `rsi_serie()`). |
| Repositorio | `repositories/bar_15m_repo.py` | Barras 15m con fallback a ticks. |
| API | `api/routers/trading15m.py` | `/api/trading15m/velas`, `/screener`, `/confluencia`. |
| Vista | `web/views.py` | Parciales `/partials/velas_15m`, `/partials/screener_15m`, `/partials/confluencia`, `/partials/ib_acciones`, `/partials/sector_15m`, `/partials/score_15m`, `/partials/precios` (con pastilla IB) y helper `_screener_filas()`. |
| Gráficos | `web/charts.py` | `confluencia_option(...)` con eje Y invertido y datos de heatmap `[x=tf, y=símbolo, valor]`; `sector_15m_option(...)` treemap sectorial; `score_hist_option(...)` histograma del score 15m. |
| Parcial | `web/templates/partials/velas_15m.html` | Un solo gráfico de velas sincronizado con el screener. |
| Parcial | `web/templates/partials/screener_15m.html` | Tabla compacta, filas clicables y `data-symbol`. |
| Parcial | `web/templates/partials/confluencia.html` | Heatmap con los mismos símbolos/orden del screener. |
| Parcial | `web/templates/partials/ib_acciones.html` | 5.4a: rupturas de rango inicial por acción (tabla + hora de ruptura). |
| Parcial | `web/templates/partials/precios.html` | Tarjetas de precio (QQQ/SPY/IWM/ORO) con pastilla IB integrada (5.4b). |
| Parcial | `web/templates/partials/divergencia.html` | 5.7: lista de divergencias precio/RSI 15m (filas clicables). |
| Tests | `tests/test_trading_15m.py` | Cálculos de barra 15m, señales y rango inicial. |

### A.2 Layout final del dashboard

**Primera fila** (5 tarjetas, 12 columnas: `3 · 2 · 3 · 2 · 2`):

| Card | Clase | Columnas | Endpoint |
|---|---|---|---|
| Score / header | `cell tres` | 3 | `/partials/header` |
| Termómetro de riesgo | `cell dos` | 2 | `/partials/riesgo_gauges` |
| Movimiento FX / Macro | `cell tres` | 3 | `/partials/riesgo_fx` |
| Histograma del score 15m (5.6) | `cell dos` | 2 | `/partials/score_15m` |
| Health | `cell dos` | 2 | `/partials/health` |

- Termómetro, histograma y health van **1 grid más angostos** que score y FX.
- El histograma muestra la **temporalidad en el título** (`Distribución score 15m`).
- Las 5 tarjetas usan la clase **`.fila1`** para tener **altura uniforme**: todas igualan la altura de la más alta (el histograma de score).

La fila **Trading 15 min** se ubica debajo de *Alcistas/Bajistas del día* y se organiza en **dos filas** de 12 columnas.

**Fila del screener** — `Screener (5) + Rango inicial por acción (4) + Confluencia (3)`:

| Card | Clase | Columnas | Endpoint |
|---|---|---|---|
| Screener 15 min | `cell cinco` | 5 | `/partials/screener_15m?compact=1` |
| Rango inicial — por acción (5.4a) | `cell cuarto` | 4 | `/partials/ib_acciones` |
| Confluencia 5m / 15m / 1D | `cell tres` | 3 | `/partials/confluencia` |

- Los 3 suman 12 y comparten fila con **altura uniforme** (`card-trading` + `.chart-fill`).
- El **alto lo manda el screener**: rango inicial y confluencia se anclan a ese alto con `.cell.altura-screener` (`@media (min-width: 1101px)` → card `position:absolute; inset:0`).
- **Screener y Rango inicial son cards separados** (se descartó la tabla paralela en un solo card). El rango inicial lista **los mismos símbolos y en el mismo orden que el screener** (`evaluar_lote()`; sin IB → `—`), por lo que las filas quedan alineadas entre ambos cards.
- Al seleccionar un símbolo en el screener se **resalta su fila también en el rango inicial** (comparten `.screener-row` + `data-symbol`) y **sus 3 círculos en el heatmap de confluencia** (`highlightConfluencia()` + `emphasis`).
- El gráfico de velas es **único** y se actualiza al hacer clic en una fila del screener o del rango inicial por `hx-target="#trading-velas-card"`.
- El símbolo por defecto es el **primer símbolo del screener**.
- El heatmap de confluencia usa **exactamente la misma lista y el mismo orden** que el screener; el eje Y va invertido para que el primer símbolo quede arriba. Celdas como **círculos** (scatter) y leyenda en el `title` del encabezado.

**Fila Velas + Mapa de calor 15m** — `Velas 15m (7) + Mapa sectorial (5)`:

| Card | Clase | Columnas | Endpoint |
|---|---|---|---|
| Velas 15m | `cell siete` | 7 | `/partials/velas_15m` |
| Mapa de calor 15m por sector (5.5) | `cell cinco fill` | 5 | `/partials/sector_15m` |

- Primero el gráfico de velas y luego el mapa de calor; ambos comparten fila y altura.

Fila **Alcistas / Bajistas / Divergencias 15m** (5 + 5 + 2 columnas):

| Card | Clase | Columnas | Endpoint |
|---|---|---|---|
| Alcistas del día | `cell cinco` | 5 | `/partials/alcistas` |
| Bajistas del día | `cell cinco` | 5 | `/partials/bajistas` |
| Divergencias precio/RSI 15m (5.7) | `cell dos` | 2 | `/partials/divergencia` |

- Alcistas y bajistas se mantienen **uniformes** (5/5) y las divergencias ocupan solo **2 columnas**.
- Nueva clase `.cell.cinco` (span 5); a ≤1100 px pasa a 6 y a ≤900 px se apila a 12.

Notas de los paneles 15 min:

- El IB por acción indica la ventana **`09:30–10:00 NY`** (parámetro `ib_minutos`, por defecto 30) y la **hora exacta de la ruptura**; sus filas son clicables (actualizan el gráfico de velas).
- 5.5 es un treemap que colorea por cambio medio 15m y usa el área según el nº de acciones.
- 5.7 lista las divergencias (alcista verde / bajista rojo) con Δ precio % y RSI inicial→final; filas clicables.
- 5.6 (histograma) vive en la **primera fila**, entre FX/Macro y Health.
- **5.4b (mercado)** ya no ocupa un card propio: se muestra como **pastilla `IB`** dentro de las tarjetas de precio QQQ/SPY/IWM (ORO `---`).

### A.3 Ajustes visuales de esta sesión

| Ajuste | Detalle |
|---|---|
| Símbolo destacado en velas | `.velas-symbol-badge` con estilo tipo `zona-NEUTRAL` pero en azul (`--azul` + `--azul-soft`, borde y brillo). Se agregó la variable faltante `--azul: #58a6ff`, que además corrigió `.brand`. |
| Fila seleccionada del screener | Clase `.selected` (fondo `--azul-soft` + borde interior `--accent`) resaltada sobre el resto. |
| Sincronización de selección | `app.js`: `highlightScreenerRow()` + `syncScreenerSelection()` en `click`, `htmx:afterSwap` y `DOMContentLoaded`. Sin persistencia entre recargas. |
| Etiquetas vs valores | En `precio-meta` se separaron `.meta-label` (claro/atenuado `#9fb3c8`) y `.meta-value` (más claro `#f2f7ff`, bold) para contrastar. |
| Columnas del screener | La vista compacta agrega 3 columnas relevantes: **Dist VWAP, RSI15, ADX15**. Total: Símbolo, Dist VWAP, RSI15, ADX15, Change, Vol ratio, Señal. |
| Etiqueta de señal más pequeña | `.zona-sm` reduce padding (1px 6px) y fuente (0.62rem) de la etiqueta COMPRAR/VENDER dentro del screener. |
| Distribución de filas del screener | Filas más aireadas: `padding: 6px 4px`, `border-spacing: 0 3px`, zebra sutil, hover azul, números tabulares a la derecha y encabezado en mayúsculas. |
| Encabezados de confluencia | Las etiquetas de timeframe (5m, 15m, 1D) van arriba (`xAxis.position: top`), en color más claro que la leyenda (`CLARO #c9d6e5`, bold) y grid reajustado (`top 34`, `bottom 14`). |
| Estandarización numérica 15m | Helper `_r4()` en `bar_15m_service.py` limita a **4 decimales** la salida de OHLC, SMA9/21, Bollinger, VWAP y vol ratio; `screener_15m_service.py` reutiliza `_r4` para close, change%, VWAP, dist VWAP y vol ratio. |
| Logos en el screener | Cada fila muestra el logo (`web/logos.py::logo_url`) junto al símbolo (`.slogo`, 16×16). Si no existe logo se dibuja un **cuadro negro** (`.slogo-empty`) para mantener la alineación. `_screener_filas()` enriquece las filas con el logo. |
| Colores pastel de confluencia | Heatmap suavizado: `VERDE_PASTEL #8fd19e`, `ROJO_PASTEL #e79a9a` y neutral `#2f3844`, conservando la lectura verde alcista / rojo bajista. |
| Confluencia más angosta | El card pasa a `cell uno` (1 grid) y las celdas del heatmap se convierten en **círculos** (`scatter`, `symbol: circle`, `symbolSize: 11`), manteniendo la altura. Grid reajustado (`left 38`, etiquetas Y a `fontSize 8`). |
| Confluencia sin leyenda | Se elimina el `<p class="nota">` y la leyenda pasa al `title` del `<h2>` (tooltip nativo). |
| Rango inicial alineado al screener | El card **Rango inicial — por acción** (`/partials/ib_acciones`) lista **los mismos símbolos en el mismo orden que el screener** vía `evaluar_lote()`; los símbolos sin IB se muestran con `—`. |
| Vocabulario de señales | Rango inicial: `UP` / `DOWN` / `IN`. Screener: `BUY` / `SELL` / `NEUTRAL`. La clase de color sigue usando `zona-COMPRAR/VENDER/NEUTRAL`. |
| Altura mandada por el screener | `.cell.altura-screener` en rango inicial y confluencia: `position:absolute; inset:0` (`@media (min-width: 1101px)`) → ambos igualan el alto del screener. |
| Selección sincronizada | `app.js::highlightConfluencia()` resalta los 3 círculos del símbolo elegido con un **borde del propio tono vivo** (`#7ee787` / `#ff9492` / `#9fb3c8`, vía `itemStyle` por punto), **nítido** (`shadowBlur: 0`) y una **banda sutil** sobre la fila; se elimina el borde celeste. El rango inicial se resalta por compartir `.screener-row` + `data-symbol`. |
| Initial Balance | Etiqueta de horario `.ib-time` (`09:30–10:00 NY`, color ámbar) en el panel por acción. |
| Pastilla IB en precios (5.4b) | `.ib-badge` en las tarjetas QQQ/SPY/IWM: verde `ib-alcista`, rojo `ib-bajista`, ámbar `ib-dentro`; ORO muestra `---` (`ib-none`). |
| Cuarta tarjeta de precios | Se agrega **IWM (Russell 2000)** y `.precios-grid` pasa a 4 columnas (2 en ≤1500 px, 1 en ≤1100 px). |
| Título de tarjetas de precio | Se elimina la palabra "Precio"; la reemplaza el **logo/icono** del instrumento (`.precio-logo` o `.precio-icono` emoji cuando no hay logo, p. ej. IWM 🏭). El subnombre (`(S&P 500)`, `(Russell 2000)`, …) va en **azul** (`.precio-sub`). ORO usa un **lingote de oro** (`icono_url → oro_lingote.svg`). |
| Mapa de calor 15m por sector | Treemap con escala divergente **dinámica** (`min/max = ±máx|cambio|`) y colores `VERDE`/`ROJO`, área = nº de acciones; layout `cell seis fill`. Sin la escala dinámica todos los sectores quedaban grises por lo pequeños que son los cambios 15m. |
| Histograma del score 15m | Barras coloreadas por zona (verde ≥6.5, rojo ≤4.5, gris intermedio), **línea de la media en amarillo** (`AMARILLO`, punteada, width 2, etiqueta con fondo ámbar), **tiempo de cálculo en el título** y **sugerencia debajo del gráfico** con encabezado de métricas (`.score-interp-head` + `.score-interp-text`). El texto ya **no repite media/percentil/%**: se elige de un **catálogo de 11 combinaciones** (`ScoreService._opcion_analisis`). Grid con `containLabel` y márgenes mínimos para ocupar el **100% del ancho**. |
| Health en filas (sin tabla) | Lista `.health-list`: cada fila muestra el **módulo como label destacable** (`.health-mod`), seguido del **estado** (color `pos/neu/neg`) y el **detalle** (muted), sin scroll horizontal. Los timestamps se muestran en **hora de Lima** (`America/Lima`, `dd/mm HH:MM`), sin `T` ni `+00:00`. |
| Divergencias 15m | Lista `.div-list` con logo + ticker, pastilla ALCISTA/BAJISTA (verde/rojo) y `Δ precio % · RSI ini→fin`; hover azul y fila clicable que actualiza velas. |
| Altura uniforme fila 1 | Clase `.fila1` (`display:flex` + `.card { flex:1 1 auto }`): las 5 tarjetas igualan la altura de la más alta ("Distribución score"). |

### A.4 Verificación

- `venv/bin/pytest -q` → **116 passed, 1 warning**.
- Render validado: `card-trading`, `chart-fill`, `velas-symbol-badge`, `data-symbol` en velas y en filas del screener.
- Orden screener vs confluencia validado idéntico (p. ej. `SHOP, NVDA, LMT, LLY, MARA, …`).

---

## B. Criterio actual del screener 15 min

Implementado en `services/screener_15m_service.py` + selección final en `web/views.py::_screener_filas()`.

### B.1 Universo y datos

- Universo **dinámico**: todos los `equity` presentes en `latest_market_tick` con barras 15m recientes (`screener_horas`, por defecto 48 h).
- Por símbolo se calculan: cambio % de la última barra, VWAP, volumen relativo (media 10 barras), RSI 15m y ADX 15m.

### B.2 Regla de señal

| Señal | Condiciones |
|---|---|
| **COMPRAR** | `close > VWAP` **y** `ADX ≥ adx_min` **y** `vol_ratio ≥ vol_ratio_min` **y** `RSI < rsi_sobrecompra` |
| **VENDER** | `close < VWAP` **y** `ADX ≥ adx_min` **y** `vol_ratio ≥ vol_ratio_min` **y** `RSI > rsi_sobreventa` |
| **NEUTRAL** | Cualquier otro caso (`close`/`VWAP` nulos también ⇒ NEUTRAL) |

Umbrales configurables en `settings.business("trading_15m")`: `rsi_sobrecompra` (70), `rsi_sobreventa` (30), `adx_min` (20), `vol_ratio_min` (1.0), `screener_horas` (48).

### B.3 Orden y selección de filas

1. `scan()` ordena por **fuerza mixta**: `COMPRAR > VENDER > NEUTRAL`, y dentro de cada grupo por `|change_pct|` descendente.
2. `_screener_filas()` aplica la selección final:
   - Si hay **≥ 5 accionables**: muestra hasta **20** con señal (`mostrando N de M con señal`).
   - Si hay **1–4 accionables**: esos + los de mayor movimiento hasta 15 (`N con señal + K top movimiento`).
   - Si **no hay** accionables: top 15 por movimiento (`sin señales claras; mostrando top 15 por movimiento`).

### B.4 Screener vs. Rango inicial (Initial Balance): en qué se diferencian

Ambos paneles comparten el **mismo universo de entrada** (los `equity` de `latest_market_tick`), pero responden preguntas distintas y, por diseño, **no muestran lo mismo ni en el mismo orden**.

#### B.4.1 Pregunta que responde cada panel

| Panel | Pregunta | Qué mide |
|---|---|---|
| **Screener 15 min** | *"¿Hay momentum operativo ahora?"* | La barra actual frente a VWAP, con volumen, tendencia (ADX) y filtro de RSI. |
| **Rango inicial** | *"¿El precio rompió el rango de apertura y con qué fuerza?"* | La estructura de la sesión: rango `09:30–10:00 NY` y el primer cierre que lo supera. |

#### B.4.2 Misma lista de símbolos, distinta selección y orden

El panel de rango inicial **parte de la lista del screener** (`web/views.py::ib_acciones` → `_screener_filas()`), pero no la reproduce tal cual:

- `scan_por_accion()` (`services/initial_balance_service.py`) **reordena por `fuerza_pct` descendente** y **trunca a `ib_max_acciones` (15)**.
- Si ningún símbolo rompió, cae a los que quedaron `DENTRO`.
- Los símbolos cuyo IB no es evaluable se **descartan**: `evaluar()` devuelve `None` si hay menos de 2 barras **o** si el día más reciente **no tiene barras de apertura** `09:30–10:00`.

Consecuencia: el rango inicial **nunca muestra un ticker ajeno al screener**, pero puede mostrar **menos filas** y siempre en **otro orden**.

Además hay una diferencia temporal sutil: el IB busca hacia atrás **el día más reciente con barras de apertura** (itera días en orden inverso y retorna en el primero con IB), mientras que el screener usa una **ventana rolling de 48 h** (`screener_horas`). Si hoy faltan barras de apertura, el IB puede estar leyendo la sesión anterior.

#### B.4.3 Columnas

Solo coinciden en `Símbolo` y `Close`:

| Screener 15 min (vista compacta) | Rango inicial |
|---|---|
| Símbolo · Dist VWAP · RSI15 · ADX15 · Change · Vol ratio · **Señal** | Símbolo · **IB low** · **IB high** · Close · **Fuerza** · **Hora** · **Ruptura** |

- **Exclusivas del screener:** `Dist VWAP`, `RSI15`, `ADX15`, `Vol ratio`.
- **Exclusivas del rango inicial:** `IB low`, `IB high`, `Fuerza`, `Hora`, `Ruptura`.
- La vista **no compacta** del screener añade `Close` y `VWAP` (la compacta, usada en la fila Trading, las oculta).

#### B.4.4 Regla de señal

| Screener | Rango inicial |
|---|---|
| **COMPRAR**: `close > VWAP` ∧ `ADX ≥ 20` ∧ `vol_ratio ≥ 1.0` ∧ `RSI < 70` | **ALCISTA**: primer `close` posterior a `10:00` que supera `IB high` |
| **VENDER**: `close < VWAP` ∧ `ADX ≥ 20` ∧ `vol_ratio ≥ 1.0` ∧ `RSI > 30` | **BAJISTA**: primer `close` posterior a `10:00` que pierde `IB low` |
| **NEUTRAL**: cualquier otro caso | **DENTRO**: el precio no ha roto el rango |

- El screener **no usa SMA9/21** en su señal (esas SMA solo viven en el gráfico de velas).
- El IB **no usa volumen, VWAP, ADX ni RSI**: es puramente estructura de precio.
- Detalle de vocabulario: la fila `DENTRO` del IB se pinta con el estilo `zona-NEUTRAL` pero muestra el texto `DENTRO` (`web/templates/partials/ib_acciones.html`), a diferencia de `COMPRAR/VENDER/NEUTRAL` del screener.

#### B.4.5 Por qué pueden discrepar (y por qué es útil)

- Un ticker puede ser **ALCISTA** en IB y **NEUTRAL** en el screener → hubo ruptura **sin confirmación de momentum** (ADX bajo o volumen flojo).
- Un ticker puede ser **COMPRAR** en el screener y **DENTRO** en IB → hay **momentum sin ruptura** del rango de apertura.
- Leer ambos lados en paralelo es la señal más rica: coincidencia = confluencia estructura + momentum; desacuerdo = advertencia.

> **Nota de evolución:** se evalúa mostrar una **tabla paralela de rango inicial dentro del card del screener**, alineada fila a fila y en el mismo orden, para leer la discrepancia de un vistazo. El card independiente de rango inicial (§5.4a) se mantiene por ahora.

---

## C. Ventajas del screener actual

1. **Confirmación multifactorial:** no basta el precio; exige VWAP + tendencia (ADX) + volumen y filtra por RSI, reduciendo falsas rupturas.
2. **Ranking por fuerza, no solo dirección:** los movimientos más fuertes aparecen arriba sin importar el signo, útil para escanear ambos lados.
3. **Universo dinámico:** se adapta a los equities con datos reales, sin depender de una lista fija.
4. **Configurable sin código:** umbrales en `settings.business("trading_15m")`.
5. **Punto único de verdad:** `_screener_filas()` alimenta screener, confluencia y velas, garantizando símbolos y orden consistentes.
6. **Fallback:** si no hay señales, rellena con top movimiento; el card nunca queda vacío.
7. **Integración operativa:** filas clicables, resaltado de selección y sincronización con el gráfico de velas.

---

## D. Propuesta: 10 alcistas + 10 bajistas (ideas a futuro, de momento descartar)

### D.1 Comparación

| Aspecto | Actual (mixto) | 10 + 10 (propuesto) |
|---|---|---|
| Lectura rápida | Hay que leer columna a columna | Cada lado claramente separado |
| Balance | Puede mostrar 18 compras y 2 ventas | Siempre simétrico (long/short) |
| Enfoque | “¿Qué se mueve más?” | “¿Qué opero hoy?” |
| Neutrales | Aparecen si faltan accionables | Quedan fuera del top |
| Uso del espacio | Hasta 20 filas mezcladas | 20 filas equilibradas |

### D.2 Preguntas abiertas antes de implementar

1. **Cantidad fija:** ¿exactamente 10 y 10, o máximo 20 completando lo que exista?
2. **Métrica de fuerza:** ¿score interno del screener, `|change_pct|`, distancia al VWAP o confluencia 5m/15m/1D?
3. **Visual:** ¿una sola tabla con columna “Lado” o dos mini-tablas (Alcistas / Bajistas)?
4. **Fallback:** si solo hay 3 bajistas claros, ¿se rellenan con neutrales o se muestran solo esos 3?
5. **Confluencia:** ¿sigue usando la lista combinada de 20 o también se separa por lado?

---

## E. Pendientes / riesgos vigentes

| Tema | Estado | Acción sugerida |
|---|---|---|
| `fact_market_bar_15m` desactualizado | Mitigado con fallback a ticks en `bar_15m_repo` | Reactivar pipeline o mantener fallback |
| Decisión 10/10 del screener | Abierta | Responder preguntas de §D.2 |
| Confluencia con eje Y invertido | Implementado | Verificar visualmente en navegador |
| Persistencia de selección | No implementada (por diseño) | Reevaluar si se quiere recordar el ticker |

---

## F. Archivos tocados en la sesión

- `web/templates/dashboard.html` — spans 3/2/7 de la fila Trading.
- `web/static/app.css` — `.cell.dos`, `.cell.siete`, `.card-trading`, `.chart-fill`, `.velas-symbol-badge`, `.screener-row.selected`, `.meta-label`, `.meta-value`, `--azul`.
- `web/static/app.js` — sincronización del resaltado del screener.
- `web/templates/partials/velas_15m.html` — badge de símbolo y etiquetas/valores.
- `web/templates/partials/screener_15m.html` — `data-symbol` y `card-trading`.
- `web/templates/partials/confluencia.html` — `card-trading` y `chart-fill`.
- `web/charts.py` — eje Y invertido y datos de heatmap transpuestos.
- `web/views.py` — `_screener_filas()`, `/partials/ib_acciones`, `/partials/sector_15m` y pastilla IB en `/partials/precios`.
- `services/initial_balance_service.py` — servicio de rango inicial (`scan_por_accion`, `evaluar_symbol`).
- `services/sector_15m_service.py` — nuevo servicio de cambio medio 15m por sector.
- `services/score_service.py` — `distribucion_15min()` / `histograma_de_scores()` (histograma del score 15m + descripción).
- `web/templates/partials/ib_acciones.html` — panel 5.4a (por acción).
- `web/templates/partials/screener_15m.html` — tabla de señal 15m con etiquetas BUY/SELL/NEUTRAL.
- `web/templates/partials/ib_acciones.html` — rango inicial en el mismo orden del screener (símbolos sin IB → `—`).
- `services/initial_balance_service.py::evaluar_lote()` — mapa `{symbol: fila}` sin reordenar ni truncar, para alinear el rango inicial con el screener.
- `web/templates/partials/precios.html` — tarjetas de precio con pastilla IB (5.4b) e IWM.
- `web/charts.py::sector_15m_option()` — treemap sectorial 15m.
- `web/charts.py::score_hist_option()` — histograma del score 15m con marca de media.
- `web/views.py::score_15m` — endpoint `/partials/score_15m` con título por temporalidad.
- `config_dashboard.json` — tarjeta IWM en `precio.tarjetas` y campos `titulo`/`subtitulo`/`icono`/`icono_url` (sin la palabra "Precio").
- `web/static/iconos_mercado/oro_lingote.svg` — icono de lingote de oro para la tarjeta ORO.
- `core/container.py` — wiring de `InitialBalanceService` y `Sector15mService`.
- `config_dashboard.json` — claves `ib_minutos`, `ib_horas`, `ib_max_acciones`, `ib_mercado_simbolos`.
- `services/*`, `repositories/bar_15m_repo.py`, `api/routers/trading15m.py`, `tests/test_trading_15m.py`.
- `CHANGELOG.md` — bitácora de cambios.

---

*Fin del anexo — 2026-09-30.*
