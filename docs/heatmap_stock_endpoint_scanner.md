# Documentación técnica: Endpoint Scanner del Heatmap de TradingView

## 1. Resumen

El heatmap de TradingView se alimenta de un endpoint POST que devuelve un JSON con la lista de símbolos del mercado americano y sus métricas. Este documento describe cómo consultar el endpoint, los tipos de datos que devuelve, las dificultades encontradas y las soluciones implementadas.

**Endpoint confirmado:**

```
POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
```

**Script actualizado:** `heatmap/export_heatmap_v3.py`

---

## 2. Cómo consultar el endpoint

### 2.1. Headers requeridos

```http
POST /america/scan?label-product=heatmap-stock HTTP/1.1
Host: scanner.tradingview.com
Accept: application/json, text/plain, */*
Accept-Language: es-ES,es;q=0.9,en;q=0.8
Content-Type: application/json
Origin: https://es.tradingview.com
Referer: https://es.tradingview.com/heatmap/stock/
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36
```

**Puntos críticos:**

- `Content-Type` debe ser `application/json`. El uso de `application/x-www-form-urlencoded` causa que el endpoint devuelva items con `d[]` vacío.
- `Origin` y `Referer` son verificados por CORS. Sin ellos el endpoint puede rechazar o devolver datos incompletos.
- `User-Agent` debe simular un navegador real.

### 2.2. POST body (payload)

El body debe ser un JSON con las columnas solicitadas explícitamente. Un body vacío `{}` o sin body devuelve 19,738 items con `d[]` vacío.

```json
{
  "columns": [
    "typespecs", "change", "change_abs",
    "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y", "Perf.YTD",
    "Volatility.D",
    "price_52_week_high", "price_52_week_low",
    "market_cap_basic",
    "average_volume_30d_calc", "average_volume_10d_calc", "volume",
    "total_shares_outstanding", "total_shares_outstanding_fundamental",
    "number_of_employees",
    "earnings_per_share_basic_ttm", "revenue_per_employee_ttm",
    "gross_profit_1Y_growth_fq",
    "sector",
    "logoid", "close", "pricescale",
    "name", "update_mode", "currency"
  ],
  "markets": ["america"],
  "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"}
}
```

### 2.3. Ejemplo con curl

```bash
curl -s -X POST 'https://scanner.tradingview.com/america/scan?label-product=heatmap-stock' \
  -H 'accept: application/json' \
  -H 'content-type: application/json' \
  -H 'origin: https://es.tradingview.com' \
  -H 'referer: https://es.tradingview.com/heatmap/stock/' \
  -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36' \
  -d '{"columns":["typespecs","change","change_abs","market_cap_basic","close","name","sector"],"markets":["america"]}' \
  --max-time 30
```

### 2.4. Ejemplo con Python requests

```python
import requests

URL = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://es.tradingview.com",
    "referer": "https://es.tradingview.com/heatmap/stock/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}
BODY = {
    "columns": ["typespecs","change","change_abs","market_cap_basic","close","name","sector"],
    "markets": ["america"],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
}

response = requests.post(URL, headers=HEADERS, json=BODY, timeout=60)
data = response.json()

# Verificar que hay datos reales
items = data.get("data", []) or []
has_data = any(
    isinstance(it, dict) and isinstance(it.get("d"), list) and len(it["d"]) > 0
    for it in items
)
print(f"Items: {len(items)}, con datos: {has_data}")
```

---

## 3. Estructura de la respuesta

### 3.1. Formato general

```json
{
  "totalCount": 19738,
  "data": [
    {
      "s": "NASDAQ:NVDA",
      "d": [["common"], -2.04, -4.57, 5277658956795.32, 218.99, "NVDA", "Electronic Technology"]
    }
  ]
}
```

- `totalCount`: número total de símbolos en el mercado consultado.
- `data`: array con cada símbolo.
- `s`: identificador del símbolo (formato `EXCHANGE:TICKER`).
- `d`: array compacto de valores. El orden de los valores corresponde al orden de las columnas solicitadas en el POST body.

### 3.2. Formato de un símbolo

```json
{
  "s": "NASDAQ:NVDA",
  "d": [
    ["common"],                          // [0]  typespecs
    -2.0431886261009495,                 // [1]  change (%)
    -4.569999999999978,                  // [2]  change_abs
    -1.3818247288112677,                 // [3]  Perf.1M
    6.9510885482768625,                  // [4]  Perf.3M
    18.484750162232323,                  // [5]  Perf.6M
    24.038722826086968,                  // [6]  Perf.Y
    15.417072721047223,                  // [7]  Perf.YTD
    2.978821362799263,                   // [8]  Volatility.D
    236.54,                              // [9]  price_52_week_high
    164.27,                              // [10] price_52_week_low
    5280358156773.225,                   // [11] market_cap_basic
    124779164.86666682,                  // [12] average_volume_30d_calc
    141049890.60000172,                  // [13] average_volume_10d_calc
    48954077,                            // [14] volume
    24100000000,                         // [15] total_shares_outstanding
    24100000000,                         // [16] total_shares_outstanding_fundamental
    42000,                               // [17] number_of_employees
    7.9482,                              // [18] earnings_per_share_basic_ttm
    null,                                // [19] revenue_per_employee_ttm
    null,                                // [20] gross_profit_1Y_growth_fq
    "Electronic Technology",             // [21] sector
    "nvidia",                            // [22] logoid
    219.102,                             // [23] close (precio)
    100,                                 // [24] pricescale
    "NVDA",                              // [25] name (ticker)
    "delayed_streaming_900",             // [26] update_mode
    "USD"                                // [27] currency
  ]
}
```

---

## 4. Tipos de datos por columna

| Índice | Columna API | Tipo | Descripción | Ejemplo NVDA |
|--------|-------------|------|-------------|--------------|
| 0 | `typespecs` | `list[str]` | Tipo de instrumento | `["common"]` |
| 1 | `change` | `float` | Cambio diario porcentual | `-2.04` |
| 2 | `change_abs` | `float` | Cambio absoluto en precio | `-4.57` |
| 3 | `Perf.1M` | `float` | Performance 1 mes (%) | `-1.38` |
| 4 | `Perf.3M` | `float` | Performance 3 meses (%) | `+6.95` |
| 5 | `Perf.6M` | `float` | Performance 6 meses (%) | `+18.48` |
| 6 | `Perf.Y` | `float` | Performance 1 año (%) | `+24.04` |
| 7 | `Perf.YTD` | `float` | Performance año en curso (%) | `+15.42` |
| 8 | `Volatility.D` | `float` | Volatilidad diaria | `2.98` |
| 9 | `price_52_week_high` | `float` | Precio máximo 52 semanas | `236.54` |
| 10 | `price_52_week_low` | `float` | Precio mínimo 52 semanas | `164.27` |
| 11 | `market_cap_basic` | `float` | Capitalización de mercado (USD) | `5.28T` |
| 12 | `average_volume_30d_calc` | `float` | Volumen promedio 30 días | `124.8M` |
| 13 | `average_volume_10d_calc` | `float` | Volumen promedio 10 días | `141.0M` |
| 14 | `volume` | `int` | Volumen actual | `48.9M` |
| 15 | `total_shares_outstanding` | `int` | Acciones en circulación | `24.1B` |
| 16 | `total_shares_outstanding_fundamental` | `int` | Acciones fundamentales | `24.1B` |
| 17 | `number_of_employees` | `int` | Número de empleados | `42000` |
| 18 | `earnings_per_share_basic_ttm` | `float` | Ganancia por acción (TTM) | `7.95` |
| 19 | `revenue_per_employee_ttm` | `float\|null` | Ingreso por empleado | `null` |
| 20 | `gross_profit_1Y_growth_fq` | `float\|null` | Crecimiento ganancia bruta | `null` |
| 21 | `sector` | `str` | Sector en inglés | `"Electronic Technology"` |
| 22 | `logoid` | `str` | ID del logo para render | `"nvidia"` |
| 23 | `close` | `float` | Precio de cierre actual | `219.10` |
| 24 | `pricescale` | `int` | Escala de precio | `100` |
| 25 | `name` | `str` | Ticker del activo | `"NVDA"` |
| 26 | `update_mode` | `str` | Estado del stream | `"delayed_streaming_900"` |
| 27 | `currency` | `str` | Moneda | `"USD"` |

### 4.1. Campos que pueden ser `null`

- `revenue_per_employee_ttm`: no disponible para la mayoría de símbolos.
- `gross_profit_1Y_growth_fq`: no disponible para la mayoría de símbolos.
- `number_of_employees`: puede ser `null` para ETFs y otros instrumentos.
- `earnings_per_share_basic_ttm`: puede ser `null` para instrumentos sin ganancias.

### 4.2. Campos que el endpoint ya no provee

- `sectorTranslated`: en la captura antigua (sep 2026) el campo `d[23]` contenía la traducción del sector al español (ej: `"Tecnología electrónica"`). Actualmente el endpoint retorna `null` para este campo. Se omitió del POST body.

---

## 5. Dificultades encontradas y soluciones

### 5.1. Content-Type incorrecto

**Problema:** Los scripts v1 y v2 (`export_heatmap_csv.py`, `export_heatmap_v2.py`) usaban `content-type: application/x-www-form-urlencoded; charset=UTF-8`. Con este header, el endpoint devolvía 19,738 items pero todos con `d[]` vacío (`[]`).

**Solución:** Cambiar a `content-type: application/json`. Este es el Content-Type que usa el frontend de TradingView.

**Evidencia:**

```
Con x-www-form-urlencoded: d=[] para todos los items
Con application/json + body explícito: d=[...] con datos reales
```

### 5.2. Body vacío o sin columnas

**Problema:** Los scripts v1/v2 enviaban `data=None` (sin body) o body vacío `{}`. El endpoint interpreta esto como "devolver todos los símbolos pero sin campos", y retorna items con `d[]` vacío.

**Solución:** Enviar un body JSON explícito con la lista de columnas en el campo `columns`. El orden de las columnas en el array determina el orden de los valores en `d[]`.

### 5.3. Ruta de fallback rota

**Problema:** `export_heatmap_v2.py` definía:

```python
CAPTURED_SCAN_PATH = ROOT_DIR / "raw" / "responses" / "0196_america_scan_bf8828f8dd_8f5b42c8c525.json"
```

Pero `ROOT_DIR` apunta a `proy_heatmap_stock/`, no a `proy_heatmap_stock/capturar_page_raw/`. El directorio `proy_heatmap_stock/raw/` no existe. Además, el archivo real se llama `0191_america_scan...` (no `0196_`).

**Solución:** El script v3 no usa fallback. Consulta directamente el endpoint y valida que la respuesta tenga datos reales.

### 5.4. Payload completo causa error 400

**Problema:** Enviar el payload completo del frontend (con filtros `filter`, `filter2`, `index_filters`, etc.) causa un error 400:

```json
{"totalCount": 0, "error": "json parse error", "data": null}
```

**Causa:** La estructura exacta de los filtros es generada dinámicamente por el JS del frontend y puede cambiar entre versiones. Los filtros reconstruidos por ingeniería inversa no son 100% compatibles con el endpoint actual.

**Solución:** No usar filtros. El endpoint devuelve todos los ~19,738 símbolos del mercado americano cuando se solicitan las columnas sin filtros.

### 5.5. Datos vacíos en horario de mercado

**Problema:** Se observó que el endpoint devolvía datos vacíos en ciertos horarios. Esto se debe a que el endpoint tiene un comportamiento diferente cuando el mercado está cerrado o en transición.

**Solución:** El script v3 valida explícitamente que la respuesta tenga items con `d[]` no vacío. Si el endpoint no devuelve datos reales, lanza un error en lugar de generar un CSV con datos vacíos.

---

## 6. Detalles técnicos de la implementación

### 6.1. Script `export_heatmap_v3.py`

**Ubicación:** `heatmap/export_heatmap_v3.py`

**Dependencias:** Solo `requests` (no necesita Playwright, Selenium, ni navegador).

**Flujo:**

1. Envía POST al endpoint con headers correctos y body JSON con columnas.
2. Valida que la respuesta tenga items con `d[]` no vacío.
3. Normaliza cada ítem mapeando `d[i]` a nombres semánticos.
4. Exporta tres archivos:
   - CSV normalizado (columnas con nombres legibles).
   - CSV raw (symbol + vector `d` serializado como JSON).
   - JSON crudo (respuesta completa del endpoint).
5. Mide y reporta tiempos de cada fase.

**Uso:**

```bash
cd proy_heatmap_stock
. .venv/bin/activate
python heatmap/export_heatmap_v3.py
```

**Archivos generados:**

```
heatmap/
  heatmap_v3.csv                          # CSV normalizado (~6 MB)
  heatmap_v3_raw_YYYYMMDD_HHMMSSZ.csv    # CSV raw con vector d (~8 MB)
  heatmap_v3_raw_YYYYMMDD_HHMMSSZ.json   # JSON crudo del endpoint (~7 MB)
```

### 6.2. Tiempos de ejecución (benchmark)

| Fase | Tiempo |
|------|--------|
| Fetch + parse del endpoint | ~3.7s |
| Normalización de 19,738 items | ~0.2s |
| Export CSV normalizado | ~0.4s |
| Export CSV raw | ~0.5s |
| Export JSON crudo | ~0.5s |
| **TOTAL** | **~5.3s** |

### 6.3. Mapeo de columnas a campos del vector `d`

El POST body define el orden de las columnas. El endpoint devuelve los valores en el mismo orden. El script mapea cada posición del array `d` a su nombre de columna usando el índice correspondiente.

```python
COLUMNS = [
    "typespecs",        # d[0]
    "change",           # d[1]
    "change_abs",       # d[2]
    "Perf.1M",          # d[3]
    # ... (28 columnas en total)
    "currency",         # d[27]
]

# Para un item dado:
field_map = {col: d[i] for i, col in enumerate(COLUMNS)}
```

### 6.4. Campos derivados calculados

El script calcula campos adicionales a partir de los datos del endpoint:

| Campo derivado | Fuente | Fórmula |
|----------------|--------|---------|
| `exchange` | `s` | Parte antes del `:` en el símbolo |
| `ticker` | `s` | Parte después del `:` en el símbolo |
| `security_type` | `typespecs` | Primer elemento del array |
| `market_cap_trillions` | `market_cap_basic` | `value / 1e12` |
| `market_direction` | `change` | `"buy"` si > 0, `"sell"` si < 0, `"neutral"` si = 0 |

---

## 7. Comparación entre versiones

### v1 (`export_heatmap_csv.py`)

- Content-Type: `application/x-www-form-urlencoded` (incorrecto).
- Body: `data=None` (sin body).
- Resultado: datos vacíos con 19,738 items.
- Fallback: ruta incorrecta (`proy_heatmap_stock/raw/` que no existe).

### v2 (`export_heatmap_v2.py`)

- Content-Type: `application/x-www-form-urlencoded` (incorrecto).
- Body: `data=None` (sin body).
- Resultado: datos vacíos con 19,738 items.
- Fallback: ruta incorrecta (mismo problema que v1).
- Campo `sectorTranslated`: incluido pero el endpoint ya no lo provee.

### v3 (`export_heatmap_v3.py`)

- Content-Type: `application/json` (correcto).
- Body: JSON explícito con 28 columnas.
- Resultado: datos reales para 19,738 símbolos.
- Sin fallback: valida datos y falla si no hay datos reales.
- Sin `sectorTranslated`: campo eliminado del endpoint.
- Benchmark: ~5.3s para descargar y exportar todo.

---

## 8. Notas sobre el frontend de TradingView

### 8.1. Cómo el frontend construye el POST body

El bundle JS del heatmap (`market_heatmap.*.js`) usa una clase `ScanParamsManager` que construye dinámicamente el payload con:

- Columnas configuradas por el dataset (stock, crypto, etc.).
- Filtros según el tipo de instrumento (stock common, stock preferred, excluyendo pre-IPO).
- Ordenamiento por market cap descendente.
- Opciones de idioma (`lang: "es"`).

### 8.2. Geometría del tile (no está en el endpoint)

El ancho, alto y área del rectángulo del heatmap **no** vienen en la respuesta del endpoint. Se calculan en el frontend usando:

- Dimensión del contenedor disponible.
- `pixelRatio` del canvas.
- Número de símbolos a renderizar.
- Funciones `getPixelPerfectRectCoords` y `getRectArea`.

### 8.3. Color del tile

El color se deriva directamente del campo `change` (cambio diario %):

```python
if change > 0:
    color = "green"    # compra
elif change < 0:
    color = "red"      # venta
else:
    color = "neutral"

intensity = abs(change)  # fuerza visual
```

---

## 9. Archivos relevantes del proyecto

| Archivo | Descripción |
|---------|-------------|
| `heatmap/export_heatmap_v3.py` | Script actual para descargar datos reales |
| `heatmap/export_heatmap_v2.py` | Script anterior (con bugs en Content-Type y fallback) |
| `heatmap/export_heatmap_csv.py` | Script anterior (mismos bugs que v2) |
| `capturar_page_raw/capture_tradingview_heatmap.py` | Captura completa de la página con Playwright |
| `capturar_page_raw/raw/responses/0191_america_scan_*.json` | JSON capturado con Playwright (502 símbolos) |
| `docs/documentacion_campos_heatmap.md` | Documentación de campos del heatmap |
| `docs/render_heatmap_tecnico.md` | Detalles del render visual del frontend |
| `proy_heatmap/config.py` | Configuración del scrapper con endpoint y headers |

---

## 10. Validación rápida

Para verificar que el endpoint funciona correctamente:

```bash
# Test rápido con curl
curl -s -X POST 'https://scanner.tradingview.com/america/scan?label-product=heatmap-stock' \
  -H 'content-type: application/json' \
  -H 'origin: https://es.tradingview.com' \
  -H 'referer: https://es.tradingview.com/heatmap/stock/' \
  -d '{"columns":["name","close","change","market_cap_basic"],"markets":["america"]}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', []) or []
has_data = any(isinstance(it.get('d'), list) and len(it['d']) > 0 for it in items)
print(f'Items: {len(items)}, datos reales: {has_data}')
if has_data:
    first = next(it for it in items if isinstance(it.get('d'), list) and len(it['d']) > 0)
    print(f'Ejemplo: {first[\"s\"]} -> {first[\"d\"]}')
"
```

Salida esperada:

```
Items: 19738, datos reales: True
Ejemplo: NASDAQ:NVDA -> ['NVDA', 218.99, -2.04, 5277658956795.32]
```
