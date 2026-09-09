# Documentación de campos del heatmap de TradingView

## Objetivo

Este documento resume los datos reales que trae la URL de heatmap de TradingView y dónde encontrarlos dentro del proyecto capturado.

La página objetivo es:

https://es.tradingview.com/heatmap/stock/

## 1. Endpoint principal que alimenta el heatmap

El dato relevante del mapa de calor no viene del HTML inicial sino del endpoint de scanner de TradingView.

- URL: https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
- Método: POST
- Tipo: JSON
- Evidencia en este proyecto: `raw/responses/0196_america_scan_bf8828f8dd_8f5b42c8c525.json`

Este archivo es el más importante porque contiene la lista real de símbolos y sus métricas usadas para generar la vista.

### Contenido principal

```json
{
  "totalCount": 502,
  "data": [
    {
      "s": "NASDAQ:NVDA",
      "d": [ ... ]
    }
  ]
}
```

- `totalCount`: número total de símbolos devueltos.
- `data`: arreglo con cada símbolo.
- `s`: identificador del símbolo en el mercado.
- `d`: vector compacto de datos del símbolo.

## 2. Estructura de un símbolo

Cada registro tiene la forma:

```json
{
  "s": "NASDAQ:NVDA",
  "d": [
    ["common"],
    0.20663853482402852,
    -0.17551462621885205,
    0.8360691617421865,
    1.319493314567206,
    6.225214424052384,
    7.378921362979543,
    28.091637010676163,
    21.34748597466221,
    35.053057395790596,
    1.1687458962573938,
    -0.20402847716618652,
    0.8472847761107444,
    2.747898793711624,
    1.1556139198949509,
    5551675925838.097,
    131881678,
    658126815,
    533424155,
    30380263344.08,
    151606093103.4,
    122879588345.8,
    "Electronic Technology",
    "Tecnología electrónica",
    {"logoid": "nvidia", "style": "single"},
    230.345,
    100,
    "NVDA",
    "NVIDIA Corporation",
    "delayed_streaming_900"
  ]
}
```

## 3. Qué significa cada posición del arreglo `d`

A continuación se describe el significado observado en el payload capturado, con los hallazgos y validaciones recientes.

### 3.1. `d[0]`
- Tipo: lista
- Valor: `["common"]` o equivalente con el tipo de acción
- Descripción: clase de valor / tipo de activo. En la práctica representa el tipo de instrumento en el símbolo, por ejemplo `common`.

### 3.2. `d[1..21]`
- Tipo: flotantes / enteros
- Descripción: estos valores son las métricas compactadas que más importan para el heatmap.
- Función confirmada:
  - influyen en el score visual del tile,
  - participan en el orden relativo del símbolo dentro del conjunto,
  - están vinculados al cálculo de la fuerza del color,
  - se usan para comparar activos entre sí.
- Importante: no son campos autoexplicativos; el front-end los interpreta como un vector compactado de métricas y no como datos legibles del negocio.

### 3.3. `d[3]` = cambio diario del símbolo
- Tipo: float
- Valor de ejemplo: `0.8360691617421865` para NVDA, `-5.921113812389575` para TSLA, `6.0981464473574425` para MU
- Descripción: este es el campo más importante para entender el color del cuadro.
- Reglas observadas:
  - `> 0` => compra / verde / intensidad positiva
  - `< 0` => venta / rojo / intensidad negativa
  - mayor valor absoluto => más intensa la fuerza del color
- Ejemplo verificado:
  - NVDA: `+0.84%` en el frontend
  - TSLA: `-5.92%`
  - MU: `+6.10%`

### 3.4. `d[15]` = capitalización bursátil
- Tipo: float o número muy grande
- Valor de ejemplo: `5551675925838.097` para NVDA
- Descripción: representa la capitalización de mercado del símbolo.
- Conversión útil:
  - `5551675925838.097` ≈ 5.55T USD

### 3.5. `d[25]` = precio del símbolo
- Tipo: float
- Valor de ejemplo: `230.345` para NVDA, `353.9499` para TSLA, `1014.95` para MU
- Descripción: es el valor de precio que se ve en el análisis del heatmap para ese símbolo.

### 3.6. `d[22]` y `d[23]`
- Tipo: string
- Valor de ejemplo: `"Electronic Technology"` y `"Tecnología electrónica"`
- Descripción: sector de la empresa en el idioma original y traducido.

### 3.7. `d[24]`
- Tipo: object
- Valor de ejemplo: `{"logoid": "nvidia", "style": "single"}`
- Descripción: metadata del logo para render del ticker.

### 3.8. `d[26]`
- Tipo: int
- Valor de ejemplo: `100`
- Descripción: parece ser un estado de referencia / indicador adicional del símbolo, no un precio ni una métrica directamente legible por usuario.

### 3.9. `d[27]`
- Tipo: string
- Valor de ejemplo: `"NVDA"`
- Descripción: ticker público del activo.

### 3.10. `d[28]`
- Tipo: string
- Valor de ejemplo: `"NVIDIA Corporation"`
- Descripción: nombre de la empresa.

### 3.11. `d[29]`
- Tipo: string
- Valor de ejemplo: `"delayed_streaming_900"`
- Descripción: estado del stream o de la fuente de datos del símbolo.

## 4. Qué datos permiten generar el heatmap

Con estos campos, la página puede construir cada bloque del mapa de calor:

- símbolo
- nombre de la empresa
- ticker
- sector / industria
- precio
- market cap
- cambio diario
- fuerza de compra/venta
- color del tile
- orden relativo dentro de la grilla
- metadata visual (logo)
- estado del feed

En resumen, la lógica del heatmap se apoya principalmente en:

- `s` para identificar el activo,
- `d[3]` para el valor de cambio diario asociado a compra/venta y color,
- `d[15]` para capitalización bursátil,
- `d[25]` para precio,
- `d[22..23]` para sector,
- `d[27..29]` para la etiqueta visible del símbolo,
- `d[1..21]` para el vector compacto de score / orden visual / intensidad del tile.

## 5. Cómo interpretar el color del heatmap

El color del bloque no es un valor aleatorio; se deriva del cambio diario del símbolo.

### Regla observada

- `d[3] > 0` => verde / buy
- `d[3] < 0` => rojo / sell
- `abs(d[3])` grande => intensidad mayor

Ejemplos verificados:

- NVDA: `d[3] = 0.8360691617421865` => verde, compra ligera
- TSLA: `d[3] = -5.921113812389575` => rojo intenso, venta fuerte
- MU: `d[3] = 6.0981464473574425` => verde intenso, compra fuerte

Esto explica por qué un símbolo con `-5.92%` se ve en un tono de venta y otro con `+6.10%` en verde fuerte.

## 6. Cómo interpretar el ancho y área del cuadro

Este hallazgo es clave:

- El ancho del cuadro no viene en el payload del scanner.
- El área del tile se calcula en el renderer del frontend, no como un campo de la API.

En el bundle JS del heatmap se detectan funciones como:

- `getTilePadding`
- `getScaledPadding`
- `getPixelPerfectRectCoords`
- `getRectArea`
- `size.width`
- `size.height`

Esto demuestra que la geometría del bloque se deriva del layout del contenedor, número de elementos, padding y escala visual del canvas. En otras palabras:

- no existe un `box_width` en `d[]`
- el bloque se dibuja a partir del ancho disponible del contenedor y de la grilla del heatmap
- el ancho/alto del cuadrado es render-derived, no pertenece a la respuesta JSON del endpoint

Por tanto, el `area` del cuadro no es un dato del scanner sino un dato visual calculado en el navegador.

## 7. Dónde encontrar estos datos dentro del proyecto

### Archivo principal del scanner

- `raw/responses/0196_america_scan_bf8828f8dd_8f5b42c8c525.json`

Este es el archivo más importante para leer el contenido real del heatmap.

### Archivo del HTML inicial de la página

- `raw/responses/0001_heatmap_stock_e15e12d832f0.html`

Aquí se ve cómo se declara la página y qué bundle JS se usa. También menciona la configuración del producto y los endpoints del front-end.

### Manifest general

- `raw/manifest.json`

Este archivo contiene la lista total de requests capturadas y sus URLs, status y archivos asociados.

Se usa para ver qué recursos se cargaron y en qué orden.

## 8. Scripts relevantes del proyecto

### Script de captura

- `capture_tradingview_heatmap.py`

Es el script que abre la página real y guarda todos los archivos de red.

Funcionalidad:

- abre la URL con Playwright,
- intercepta respuestas de red,
- guarda HTML, JS, CSS, imágenes y JSON,
- genera `manifest.json` con metadatos.

### Script de exportación v2

- `heatmap/export_heatmap_v2.py`

Exporta el payload a un CSV legible con los campos semánticos y un raw backup con marca temporal. Incluye columnas como precio, market cap, cambio diario, intensidad y dirección de compra/venta.

### Script de pruebas

- `tests/test_capture_utils.py`

Valida utilidades auxiliares como:

- generación de nombres de archivo,
- extensión basada en tipo de contenido.

### Documentación

- `README.md`

Explica la forma de ejecutar el proyecto y la estructura de carpetas de salida.

## 9. Cómo interpretar la captura

Si quieres revisarlo manualmente, sigue este flujo:

1. Abre `raw/manifest.json` para ver todos los requests.
2. Localiza la entrada con la URL:
   `https://scanner.tradingview.com/america/scan?label-product=heatmap-stock`
3. Abre el archivo JSON asociado.
4. Revisa el campo `data[]`.
5. Inspecciona cada `d` para ver las métricas del símbolo.
6. Revisa `market_heatmap.js` para identificar cómo esas métricas se convierten en color, orden y layout.

## 10. Bundles JS relevantes para el frontend

Dentro de `raw/responses` hay varios archivos JS del frontend. Los más útiles para seguir la lógica visual del heatmap son:

- `0071_static_bundles_market_heatmap.4cf3eb0611e4747981e6.js_24d133c528fb.js`
- `0057_static_bundles_79264.b39b9106285abd5cad7d.js_26862d57ea73.js`
- `0070_static_bundles_runtime.c19e6b1def7a100191c2.js_935c3d0ff156.js`

Estos archivos contienen la lógica de render del mapa de calor y referencias a `ScanParamsManager`, `getScanData` y otros helpers del heatmap.

## 11. Conclusión

El campo más importante para reproducir el heatmap es el JSON del scanner, no el HTML. La fila del símbolo tiene un vector compacto `d` con métricas, sector, logo, ticker y nombre. Eso es lo que TradingView usa para pintar cada celda y agrupar la vista.

Los hallazgos recientes más importantes son:

- `d[3]` representa el cambio diario, y es la base del color y de la dirección de compra/venta.
- `d[15]` representa capitalización de mercado.
- `d[25]` representa el precio.
- el ancho y área del cuadro no se exponen en el payload del scanner; se calculan en el front-end a partir del layout.

## 12. Fuentes de referencia dentro del proyecto

- `raw/responses/0196_america_scan_bf8828f8dd_8f5b42c8c525.json`
- `raw/responses/0001_heatmap_stock_e15e12d832f0.html`
- `raw/responses/0071_static_bundles_market_heatmap.4cf3eb0611e4747981e6.js_24d133c528fb.js`
- `raw/manifest.json`
- `capture_tradingview_heatmap.py`
- `heatmap/export_heatmap_v2.py`
