# Reporte Técnico · Endpoint TradingView — timeframes, update_mode y filtros con temporalidades

**Período de evidencia:** 2026-09-21 al 2026-09-22
**Autor:** diagnóstico automatizado `wztest_*.py` (v2 + v3)
**Repositorio:** `proy_heatmap_stock`

---

## 0 · Resumen ejecutivo

Se validó el endpoint de datos de TradingView en dos frentes: (1) **semántica de timeframes y campos** sobre `GET /symbol` y `POST /america/scan`, y (2) **filtros (`filter`) con temporalidades** sobre el endpoint real del heatmap.

**Lo más importante en una frase:** el batch `POST /scan` que la v2 creyó refutado con HTTP 404 era una URL equivocada; en la ruta real `POST /america/scan?label-product=heatmap-stock` los **filtros aceptan temporalidades** (`RSI|15 > 70` devuelve 1.078 símbolos del universo americano en una sola llamada), lo que **desbloquea F3.1 / M-CAP-02** y cierra a favor la duda Q16 y H7b.

Hallazgos clave:
1. **Equity/ETF tienen 15 min de retraso** (`delayed_streaming_900`); futuros CME 10 min; VIX spot, cripto y FX en vivo. → H1 confirmada; el radar no puede decidir entradas.
2. **`close` base NO es precio de pre-market**; existen `premarket_close/change/volume` y `gap`. → H6, H20 confirmadas.
3. **Frontera de barra limpia** en `|15`: al cruzar la frontera se reinicia volumen (300) y RSI/change se recalculan; sin repintado. → H19, H21.
4. **Los filtros del POST aceptan sufijos `|TF`** en `left`, operan sobre la barra de ese timeframe y escalan al universo completo. → Q16 reabierta/cerrada a favor, H7b confirmada.
5. **Catálogo de timeframes válidos:** `1, 5, 15, 30, 60, 120, 240, 1W, 1M`. No válidos: `2, 3, 10, 45, 180, 360, 720, 1D, 2D`.
6. **58 campos confirmados como filtrables**, incluyendo `gap` y los 4 `premarket_*`.
7. **`FX_IDC:EURUSD` (primario actual en CONFIG_ACTIVOS) devuelve volume=0** → métricas de volumen de EURUSD rotas en producción.
8. **Rate limit 429** tras ~200 requests sin pausa; con pausa de 1,2 s no se reincide.

---

## 1 · Metodología

| Corrida | Comando | Cobertura |
| --- | --- | --- |
| 2343 (21/09) | `wztest_scraper_timeframes_v2.py --test D,F,G,H` | update_mode, FX, /scan, pivotes |
| 0810 (22/09) | `wztest_scraper_timeframes_v2.py --test E --force` | campos pre-market |
| 1300 (22/09) | `wztest_scraper_timeframes_v2.py --test C` | cruce de frontera de barra |
| 2242 (22/09) | `wztest_scraper_filters_v3.py` (nuevo, Tests J/K/L/M) | filtros con temporalidades, catálogo de TFs y campos filtrables |

Endpoints probados:
- `GET https://scanner.tradingview.com/symbol` → válido (v2)
- `POST https://scanner.tradingview.com/scan` → **HTTP 404** (la URL es la equivocada)
- `POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock` → **válido**, es el que usa el heatmap (v3)

**Fuentes consultadas en la carpeta `docs/testscrapper_timeframes`:**
| Archivo | Contenido |
| --- | --- |
| `report_2026-09-21-2343.md` + `-analisisyHipotesis.md` | Tests D, F, G, H + análisis |
| `report_2026-09-22-0810.md` + `-analisisyHipotesis.md` | Test E (pre-market) + análisis |
| `report_2026-09-22-1300.md` | Test C (frontera de barra) |
| `report_2026-09-22-2242.md` | Test J/K/L/M (filtros con TF) — generado en esta sesión |

Archivos de datos generados:
- `wztest_v2_result_20260922_044039.json` (D,F,G,H)
- `wztest_v2_result_20260922_130950.json` (E)
- `wztest_v2_result_20260922_173044.json` (C)
- `wztest_v3_result_20260922_224042.json` (J,K,L,M)

---

## 2 · Semántica de timeframes (sufijos `campo|TF`)

### 2.1 · Confirmación de que los sufijos modifican la barra

Probe de variación por timeframe sobre un mismo símbolo (Test B v2 + Test J v2/v3): pedir `campo`, `campo|5`, `campo|15`, `campo|30`, `campo|60` devuelve valores **distintos por TF**, coherentes con la barra de ese resolutivo. Ejemplo (NVDA, la corrida J):

```
RSI  (base)  = 59.99   RSI|15 = 75.40   RSI|60 = 74.57
close (base) = 229.74  close|15 = 229.75
volume|15    = reintrospec 300 tras la frontera
```
Evidencia completa en `wztest_v3_result_20260922_224042.json` (J2) y en la corrida B de la v2.

### 2.2 · Frontera de barra (Test C) → H19, H21 confirmadas

Muestreo NVDA TF=15m en torno a la frontera 17:30 UTC:

| Tiempo | close | volume\|15 | RSI\|15 | change\|15 |
| --- | --- | --- | --- | --- |
| 17:29:20 → 17:29:41 | 229.74 | 2.407.792 | 75.40 | +0.161 % |
| 17:29:46 → 17:30:07 | 229.72 | 2.431.147 | 75.34 | +0.157 % |
| **17:30:12 → 17:30:39** | **229.75** | **300** (reset) | **75.51** | **−0.00004 %** |

Conclusiones:
- Al cruzar la frontera, `volume|15` **se reinicia** (nuevo contador de la barra), `RSI|15` y `change|15` se recalculan sobre la barra nueva.
- `close` base sigue siendo el cierre diario (no cambia con la barra intra).
- No se observa repintado brusco: el valor previo a la frontera se mantiene estable y luego salta a la barra nueva de forma limpia.

### 2.3 · Catálogo de temporalidades válidas para filtros (Test K)

Probe: para cada TF, `greater(-1e9)` vs `greater(+1e9)` debe discriminar (n distinto). Patrón idéntico en RSI, ADX, volume, MACD.macd:

| Timeframe | ¿Filtra? | Nota |
| --- | --- | --- |
| `\|1` | ✅ | |
| `\|2`, `\|3` | ❌ | no devuelve datos |
| `\|5` | ✅ | |
| `\|10` | ❌ | no devuelve datos |
| `\|15` | ✅ | |
| `\|30` | ✅ | |
| `\|45` | ❌ | no devuelve datos |
| `\|60` | ✅ | |
| `\|120` | ✅ | |
| `\|180` | ❌ | no devuelve datos |
| `\|240` | ✅ | |
| `\|360`, `\|720` | ❌ | no devuelve datos |
| `\|1D`, `\|2D` | ❌ | la notación `D` no existe en este endpoint |
| `\|1W` | ✅ | |
| `\|1M` | ✅ | |

**Regla práctica:** usar `1, 5, 15, 30, 60, 120, 240, 1W, 1M`. El campo base (sin sufijo) se comporta como el timeframe diario. No usar `2, 3, 10, 45, 180, 360, 720, 1D, 2D`.

---

## 3 · update_mode por clase de activo (Test D) → H1, jerarquía de delays

| Símbolo | update_mode | Delay |
| --- | --- | --- |
| NASDAQ:NVDA / AMEX:SPY / NASDAQ:QQQ | `delayed_streaming_900` | 15 min |
| CBOE:VX1! | `delayed_streaming_900` | 15 min |
| CME_MINI:ES1! / NQ1! | `delayed_streaming_600` | **10 min (nuevo)** |
| TVC:VIX | `streaming` | 0 s |
| BINANCE:BTCUSDT | `streaming` | 0 s |
| FX:EURUSD / OANDA:EURUSD | `streaming` | 0 s (Test F) |

Jerarquía de delays:

| Clase | Delay |
| --- | --- |
| Índices de TVC (VIX spot) | 0 s |
| Cripto (BINANCE) | 0 s |
| FX (todos los proveedores) | 0 s |
| Futuros CME | 10 min |
| Equity / ETF | 15 min |

**Consecuencias:**
- H1 ✅: el radar de equity/ETF muestra datos de 15 min atrás incluso en pre-market.
- El banner `as_of` debe ser **por activo**, no global (M-DSH-02 reforzado).
- D1: la entrada no puede depender del radar de equity; usar fuente externa real-time.

---

## 4 · Pre-market (Test E) → H6, H20 confirmadas y campos nuevos

Muestra 09:09 ET (ventana pre-market):

| Símbolo | close (base) | premarket_close | premarket_change | premarket_volume | gap |
| --- | --- | --- | --- | --- | --- |
| NVDA | 227.38 | 226.242 | −0.500 % | 1.044.477 | +0.299 % |
| SPY | 773.50 | 773.96 | +0.059 % | 458.675 | +0.599 % |
| QQQ | 741.47 | 740.75 | −0.097 % | 782.666 | +0.893 % |

Conclusiones:
- H6 ✅: `close` base NO es el precio de pre-market; `premarket_close` sí lo es.
- H20 ✅: `close|5` y `close|15` incluyen actividad extendida (difieren de `close` base).
- **Campo nuevo:** `premarket_volume` existe y es útil como medida de convicción.
- `gap` existe pero su semántica exacta queda pendiente de T3.1 (¿vs open real de 09:31 ET?).
- H7b ✅ ampliada: `premarket_close/change/volume` + `gap` confirmados, también **filtrables** (Test L).

---

## 5 · Filtros (`filter`) con temporalidades (Test J/K/M) — el hallazgo central

### 5.1 · El endpoint correcto y el error de la v2

La v2 reportó **Q16 refutada** porque `POST https://scanner.tradingview.com/scan` devolvió **HTTP 404**. Ese es el endpoint genérico y no existe. El endpoint que usa el frontend del heatmap es:

```
POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
```

Sobre esta ruta, **todos** los tests J/K/L/M respondieron 200 y con datos reales (con pausa anti-429).

### 5.2 · Evidencia de que el filtro acepta `campo|TF` (Test J)

`symbols.tickers` + `columns` + `filter` con `left` sufijado por tiempo:

| Filtro | Coincidencias / 3 | Interpretación |
| --- | --- | --- |
| `RSI > 60` | 1 | valor global |
| `RSI\|15 > 60` | 1 | barra 15m |
| `RSI\|60 > 60` | 3 | barra 60m (todos arriba) |
| `close > 700` | 2 | global |
| `close\|15 > 700` | 2 | barra 15m |
| `volume\|15 > 1e6` | 3 | barra 15m |
| `change\|15 > 0` | 0 | barra 15m |
| `ADX\|15 > 25` | 3 | barra 15m |
| `MACD.macd\|15 > 0` | 0 | barra 15m |

Respuesta del mismo request devuelve las columnas sufijadas (J2):

```
NASDAQ:NVDA  close=228.87  RSI|15=53.47  RSI|60=74.57  vol|15=4,805,009
AMEX:SPY     close=773.38  RSI|15=50.17  RSI|60=67.43  vol|15=2,695,849
NASDAQ:QQQ   close=747.46  RSI|15=75.24  RSI|60=83.30  vol|15=2,329,908
```

### 5.3 · Escala al universo completo (Test M)

```json
{
  "columns": ["name","close","RSI|15","volume|15","market_cap_basic","change"],
  "markets": ["america"],
  "filter": [{"left":"RSI|15","operation":"greater","right":70}],
  "sort": {"sortBy":"market_cap_basic","sortOrder":"desc"},
  "range": [0,10]
}
```

→ `totalCount: 1078` símbolos con `RSI|15 > 70` de un universo de ~19.738, ordenado por mcap (TSM 81.3, MU 74.1, AMD 70.7, WMT, INTC, ASML, TCEHY, LRCX, ARM, KLAC).

### 5.4 · Catálogo de campos filtrables (Test L)

Probe de 83 campos con el discriminador `greater(-1e9)` vs `greater(+1e9)`.

**Filtrables (58):**
- Indicadores: `RSI`, `RSI7`, `ADX`, `CCI20`, `BBPower`, `ATR`, `MACD.macd`, `MACD.signal`, `MACD.hist`, `Stoch.K`, `Stoch.D`, `W.R`, `Mom`, `ROC`, `Volatility.D/W/M`, `P.SAR`
- Performance: `Perf.W`, `Perf.1M`, `Perf.3M`, `Perf.6M`, `Perf.Y`, `Perf.YTD`
- Precio/volumen: `close`, `open`, `high`, `low`, `volume`, `change`, `change_abs`
- Fundamentales: `price_52_week_high/low`, `average_volume_10d_calc`, `average_volume_30d_calc`, `number_of_employees`, `earnings_per_share_basic_ttm`, `revenue_per_share_ttm`, `operating_margin_ttm`, `gross_margin_ttm`, `net_margin_ttm`, `pricescale`
- Pivotes/mix: `Pivot.M.Classic.R1`, `Pivot.M.Camarilla.R1`, `Pivot.M.Camarilla.R3`, `Recommend.All`, `gap`, `premarket_close`, `premarket_change`, `premarket_volume`
- Medias/Bollinger: `EMA10/20/50`, `SMA10/20/50`, `BB.upper`, `BB.lower`

**Existen pero no discriminaron con ±1e9 (requieren otra operación/umbral, p.ej. mcap con umbral realista):** `Momentum`, `ROC21`, `TRIX`, `DMI.PDI/MDI/DX`, `Perf.D`, `RelVol`, `RelVolume_10d_calc`, `Value.Traded`, `market_cap_basic`, `total_shares_outstanding`, `float_shares_outstanding`, `P/E`, `P/S`, `P/B`, `Beta_1Y`, `target_mean_price`, `min_move`, `financial_rating`, `Pivot.D.Camarilla.R3`, `Pivot.W.Camarilla.R3`, `Analyst.Op.Recom`, `BB.middle`

**No filtran con `greater`:** `update_mode` (string; requeriría `equal`/`in`).

> ⚠ Precaución: la técnica ±1e9 es un cribado rápido. `market_cap_basic` y shares (>1e9 todos) necesitan umbrales reales (`market_cap_basic > 1e10`).

### 5.5 · Rate limit (429)

- Apareció tras ~200 requests rápidos en el descubrimiento manual.
- Con `REQUEST_DELAY_S = 1.2` y `MAX_RETRIES = 3` (reintento con backoff) en `post_scan()` la corrida completa v3 no volvió a tocar el límite.
- **Implicación producción:** 1 request POST para los 110 símbolos no es problema; el descubrimiento de campos (~200 requests) sí necesita pausa.

---

## 6 · Equivalencia FX (Test F) → Q23, Q24 cerradas

| Variante | close | volume | update_mode |
| --- | --- | --- | --- |
| FX:EURUSD | 1.14763 | 22.504 | streaming |
| FX_IDC:EURUSD | 1.14762 | **0** | streaming |
| OANDA:EURUSD | 1.14764 | 14.911 | streaming |

- Precios casi idénticos (±1 pip), volúmenes radicalmente distintos.
- **E-RAD-14:** `FX_IDC:EURUSD` (primario de EURUSD en CONFIG_ACTIVOS) devuelve `volume = 0` → RVOL/VWAP de EURUSD rotos en producción.
- Acción: cambiar primario a `OANDA:EURUSD`, respaldo `FX:EURUSD`.
- Q24: `volume` en FX es proxy del proveedor (conteo de ticks), no volumen nocional.

---

## 7 · Pivotes Camarilla (Test H) → Q17, H22 cerradas

- `Pivot.M.Camarilla.R3` existe en base y con sufijos `|5/|15/|30/|60`.
- `Pivot.D.Camarilla.R3` y `Pivot.W.Camarilla.R3` **no existen** (None).
- Pares idénticos en los 3 símbolos: `|5 = |15` (diario) y `|30 = |60` (semanal); base = mensual.
- Valores NVDA: base R3=230.025, diario=223.373, semanal=225.875.
- Pendiente: T6 (cálculo manual de R3 con H/L/C previos) para cierre definitivo de la semántica diaria/semanal.

---

## 8 · Impacto en el roadmap / informe v3

### 8.1 · Estado de hipótesis y dudas

| ID | Estado | Evidencia |
| --- | --- | --- |
| H1 (radar 15 min delay) | ✅ | update_mode `delayed_streaming_900` |
| H6 (`close` ≠ pre-market) | ✅ | Test E |
| H19 (frontera de barra) | ✅ | Test C |
| H20 (`close\|TF` incluye ext. hours) | ✅ | Test E |
| H21 (repintado) | ✅ | Test C |
| H22 (pivotes M base/semanal diaria) | ✅ estructural | Test H |
| H7a | ✅ | (previo) |
| H7b (sufijos premarket/update_mode/filtro) | ✅ | Test E + Test J/K/L/M |
| H23 | ✅ | (previo) |
| Q16 (`/scan` batch) | ✅ **REABIERTA y cerrada A FAVOR** | `POST /america/scan` acepta tickers+columns+filter |
| Q17 (Pivot.D./W.) | ✅ refutada | no existen |
| Q23 (FX equivalence) | ✅ | tres feeds distintos |
| Q24 (semántica volume FX) | ✅ | proxy por proveedor |
| D1 (fuente de entrada) | ✅ = (b) | H1 confirmada |

**Nueva redacción de H7b:** sufijos `|TF` funcionan en `columns` **y** en `filter` de `/america/scan`; `premarket_*` y `gap` confirmados y filtrables.

### 8.2 · Cambios concretos

1. **F3.1 / M-CAP-02 desbloqueado.** El "POST único para 110 símbolos" es viable:

```python
POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
{
  "symbols": {"tickers": ["<110 símbolos>"]},
  "columns": ["close","volume","RSI","RSI|15","RSI|60","ADX|15","CCI20|15",
              "BBPower|15","Pivot.M.Camarilla.R3","Perf.W","change",
              "gap","premarket_close","premarket_change","premarket_volume"],
  "filter": [{"left":"RSI|60","operation":"greater","right":60}]   # opcional
}
```
   - 1 round-trip, latencia medida ~1,5 s (incluye pausa anti-429). ThreadPoolExecutor del Plan B descartado.

2. **F3.2 / campos multi-TF ampliado:** base + bloque `|5` + bloque `|15` (+ opcional `|60`); ahora también pueden usarse en filtro.

3. **Config:** cambiar primario de EURUSD a `OANDA:EURUSD` (E-RAD-14).

4. **ETL / BD:** añadir columnas `premarket_close`, `premarket_change`, `premarket_volume`, `gap` a `fact_market_series` (ALTER TABLE nullable + backfill NULL), tal como detalla el análisis 0810.

---

## 9 · Scripts

| Script | Ruta | Tests |
| --- | --- | --- |
| v2 | `proy_scrapping_detail/wztest_scraper_timeframes_v2.py` | A–I |
| v3 (nuevo) | `proy_scrapping_detail/wztest_scraper_filters_v3.py` | J (filtros+TF), K (catálogo TF), L (campos filtrables), M (universo) |

`wztest_scraper_filters_v3.py` incluye pausa anti-429 (`REQUEST_DELAY_S=1.2`) y reintentos con backoff (`MAX_RETRIES=3`).

---

## 10 · Pendientes

| Ítem | Cómo cerrarlo |
| --- | --- |
| Semántica exacta de `gap` (T3.1) | comparar `gap` 09:29 ET con el `open` real 09:31 ET |
| Confirmar filtro de `update_mode` con operador `equal`/`in` | mini-probe dirigida |
| Semántica diaria/semanal de pivotes (T6) | cálculo manual de R3 con H/L/C previos |
| Confirmar campos "no discriminan" (mcap, shares) con umbral realista | probe con umbrales reales (p.ej. mcap > 1e10) |
| Persistencia de `premarket_*` y `gap` en BD | ALTER TABLE + backfill |

---

## Anexo A · Consistencia con la documentación existente

Del flujo interno (`heatmap_stock_endpoint_scanner.md`):
- El POST real del heatmap usa exactamente `/america/scan?label-product=heatmap-stock` con `Content-Type: application/json`, `Origin` y `Referer` de TradingView. Este reporte lo confirma y lo amplía (filtros con TF).
- §5.4 de esa doc advertía "no usar filtros: error 400 con el payload completo del frontend". **Matiz importante:** el error 400 venía del **payload completo** (filtros anidados `filter2`/`index_filters` reconstruidos por ingeniería inversa), no del objeto `filter` simple. Este reporte demuestra que **un filtro simple `{"left","operation","right"}` sí funciona**, incluso con `|TF` en `left`.
- `update_mode` en el rango de columnas confirma `delayed_streaming_900` documentado en esa doc.