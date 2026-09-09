# Render técnico del heatmap de TradingView

## 1. Origen de datos y fuente de verdad

La vista del heatmap se nutre de dos capas:

1. La capa de datos del scanner, que devuelve la lista de símbolos y su vector compacto `d`.
2. La capa de render del frontend, que calcula la posición, tamaño y color del rectángulo visible en la grilla.

La fuente de verdad del contenido del heatmap es este endpoint:

- `https://scanner.tradingview.com/america/scan?label-product=heatmap-stock`
- Método: `POST`
- Archivo capturado del proyecto: `raw/responses/0196_america_scan_bf8828f8dd_8f5b42c8c525.json`

Ejemplo real del payload:

```json
{
  "totalCount": 502,
  "data": [
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
  ]
}
```

---

## 2. Mapeo del vector `d` y de los campos `heatmap_metric_*`

La exportación del proyecto genera columnas como `heatmap_metric_1` ... `heatmap_metric_21`, y esas columnas corresponden al bloque de métricas compactas del vector `d[1..21]`.

### Mapeo exacto

| Campo exportado | Índice real de `d` | Significado | Valor de ejemplo para NVDA |
| --- | --- | --- | --- |
| `heatmap_metric_1` | `d[1]` | métrica compacta 1 | `0.20663853482402852` |
| `heatmap_metric_2` | `d[2]` | métrica compacta 2 | `-0.17551462621885205` |
| `heatmap_metric_3` | `d[3]` | cambio diario porcentual principal | `0.8360691617421865` |
| `heatmap_metric_4` | `d[4]` | métrica compacta 4 | `1.319493314567206` |
| `heatmap_metric_5` | `d[5]` | métrica compacta 5 | `6.225214424052384` |
| `heatmap_metric_6` | `d[6]` | métrica compacta 6 | `7.378921362979543` |
| `heatmap_metric_7` | `d[7]` | métrica compacta 7 | `28.091637010676163` |
| `heatmap_metric_8` | `d[8]` | métrica compacta 8 | `21.34748597466221` |
| `heatmap_metric_9` | `d[9]` | métrica compacta 9 | `35.053057395790596` |
| `heatmap_metric_10` | `d[10]` | métrica compacta 10 | `1.1687458962573938` |
| `heatmap_metric_11` | `d[11]` | métrica compacta 11 | `-0.20402847716618652` |
| `heatmap_metric_12` | `d[12]` | métrica compacta 12 | `0.8472847761107444` |
| `heatmap_metric_13` | `d[13]` | métrica compacta 13 | `2.747898793711624` |
| `heatmap_metric_14` | `d[14]` | métrica compacta 14 | `1.1556139198949509` |
| `heatmap_metric_15` | `d[15]` | capitalización de mercado | `5551675925838.097` |
| `heatmap_metric_16` | `d[16]` | métrica compacta 16 | `131881678` |
| `heatmap_metric_17` | `d[17]` | métrica compacta 17 | `658126815` |
| `heatmap_metric_18` | `d[18]` | métrica compacta 18 | `533424155` |
| `heatmap_metric_19` | `d[19]` | métrica compacta 19 | `30380263344.08` |
| `heatmap_metric_20` | `d[20]` | métrica compacta 20 | `151606093103.4` |
| `heatmap_metric_21` | `d[21]` | métrica compacta 21 | `122879588345.8` |

### Mapeo de los campos legibles fuera del vector

Estos no forman parte del bloque 1..21, pero sí son campos importantes del mismo registro:

| Índice real | Nombre de exportación | Valor para NVDA | Significado |
| --- | --- | --- | --- |
| `d[0]` | `field_0_asset_class` | `["common"]` | tipo de valor / clase del instrumento |
| `d[3]` | `field_3_daily_change_pct` | `0.8360691617421865` | cambio diario porcentual principal |
| `d[15]` | `field_15_market_cap` | `5551675925838.097` | market cap |
| `d[22]` | `field_22_sector` | `Electronic Technology` | sector |
| `d[23]` | `field_23_sector_es` | `Tecnología electrónica` | sector traducido |
| `d[24]` | `field_24_logo` | `{"logoid":"nvidia","style":"single"}` | metadata del logo |
| `d[25]` | `field_25_price` | `230.345` | precio |
| `d[27]` | `field_27_ticker` | `NVDA` | ticker |
| `d[28]` | `field_28_company_name` | `NVIDIA Corporation` | nombre de empresa |
| `d[29]` | `field_29_stream_status` | `delayed_streaming_900` | estado del feed |

También vale la pena resaltar que el vector `d` no es “autodescriptivo” ni una tabla SQL; es un vector compacto de métricas, y el frontend interpreta los valores según el orden. El heatmap usa principalmente:

- `d[3]` para color y dirección,
- `d[15]` para market cap,
- `d[25]` para precio,
- `d[22..29]` para metadata visible,
- `d[1..21]` para la parte compacta del score visual.

---

## 3. Ejemplo de Nvidia: cómo se entiende el dato

En el CSV generado por el proyecto, la fila de NVDA aparece así:

```csv
NASDAQ:NVDA,NVDA,NVIDIA Corporation,common,Electronic Technology,Tecnología electrónica,...,230.345,5551675925838.097,0.8360691617421865,...
```

Interpretación:

- símbolo: `NASDAQ:NVDA`
- ticker: `NVDA`
- empresa: `NVIDIA Corporation`
- sector: `Electronic Technology`
- precio: `230.345`
- capitalización: `5551675925838.097`
- cambio diario: `0.8360691617421865`

El cambio diario es el valor más importante para el color del rectángulo del mapa de calor.

### Regla observada

- `d[3] > 0` => verde / compra / intensidad positiva
- `d[3] < 0` => rojo / venta / intensidad negativa
- `abs(d[3])` => fuerza de la intensidad visual

Ejemplos verificados:

- NVDA: `d[3] = 0.8360691617421865` => verde ligero
- TSLA: `d[3] = -5.921113812389575` => rojo fuerte
- MU: `d[3] = 6.0981464473574425` => verde fuerte

---

## 4. Cómo se calcula el color del tile

La lógica del frontend convierte el valor del cambio diario en un color visual. La regla esencial es:

```python
if change > 0:
    color = "green"
elif change < 0:
    color = "red"
else:
    color = "neutral"

intensity = abs(change)
```

Esto está en línea con el proyecto, donde la exportación genera:

- `market_direction`: `buy` / `sell` / `neutral`
- `heatmap_color`: `green` / `red` / `neutral`
- `heatmap_color_intensity`: `abs(daily_change_pct)`

El valor visual no viene como un campo separado del JSON; se deriva del contenido del vector en tiempo de render.

---

## 5. Cómo se calcula la geometría del rectángulo

La clave del render es que el tamaño del cuadro no viene en la respuesta del endpoint. La geometría viene del frontend.

### Evidencia técnica encontrada en el bundle JS

En el bundle capturado de la ruta raw se encuentran estas funciones:

- `getPixelPerfectRectCoords`
- `getRectArea`
- `arrayToPixelRatio`
- `sizeCoordsToAbs`
- `getMultiplyCoefficient`

La evidencia más clara es esta función que aparece minificada:

```js
function m(t,e=1,o=1){
  const s=e*o;
  let{x:i,y:n,width:r,height:a}=t;
  [i,n,r,a]=[i*s,n*s,r*s,a*s];
  const[l,c,h,u]=[Math.round(i),Math.round(n),Math.round(r),Math.round(a)];
  return [l,c,h+(Math.round(i+r)-l-h),u+(Math.round(n+a)-c-u)];
}
```

Esto significa:

1. El rectángulo `t` tiene `{ x, y, width, height }`.
2. Se multiplica por un factor de escala `s = e * o`.
3. Se redondea a píxeles enteros para evitar artefactos de subpixel.
4. El valor final se alinea a coordenadas de pantalla.

### Fórmula de área de rectángulo

El bundle usa `getRectArea` justo antes de dibujar cada símbolo. La intención del check es evitar dibujar un rectángulo que sea demasiado pequeño para el canvas.

En el código aparece esta lógica:

```js
if ((0,Y.getRectArea)(c,h,r,s) < s) return;
```

Y en el mismo helper se observa una expresión de producto:

```js
function a(t,e,o,s){return t*e*o*s}
```

Esto es coherente con una fórmula de área del tipo:

```text
area ≈ width * height * scale * pixelRatio
```

Es decir, el área del tile no es un campo del payload. Es una cantidad calculada por el renderer usando el tamaño del rectángulo y la escala del canvas.

### Conclusión sobre la geometría

El ancho y alto del cuadro se calculan así:

- se toma la dimensión del contenedor,
- se aplica `pixelRatio`,
- se redondea (`Math.round`) a coordenadas enteras,
- se ajusta el rectángulo con `getPixelPerfectRectCoords`,
- y finalmente se dibuja en canvas.

En otras palabras:

- no existe un campo `width` del tile en el payload del scanner,
- el rectángulo no viene en `d[]`,
- el área del cuadro es propiedad del frontend y del layout visual.

---

## 6. Reconstitución técnica del tile para reconstruir el cuadro

Para reconstruir el cuadro del heatmap, bastan estos pasos:

1. Leer `data[]` del endpoint del scanner.
2. Tomar cada símbolo y extraer:
   - `s` -> identificador del símbolo
   - `d[3]` -> cambio diario para color
   - `d[15]` -> market cap
   - `d[25]` -> precio
   - `d[22..29]` -> sector, logo, ticker, etc.
3. Para el render visual:
   - calcular la escala (`pixelRatio`)
   - convertir el rectángulo base a píxeles:

```js
const s = pixelRatio * scaleFactor;
let { x, y, width, height } = rect;
[x, y, width, height] = [x*s, y*s, width*s, height*s];
```

4. Redondear posición y dimensiones para mantener la alineación de píxeles:

```js
const [x1, y1, w1, h1] = [Math.round(x), Math.round(y), Math.round(width), Math.round(height)];
```

5. Calcular el área del rectángulo y evitar dibujar si es demasiado pequeña:

```js
area = width * height * scale * pixelRatio
```

6. Aplicar el color:

```python
if change > 0:
    color = "green"
elif change < 0:
    color = "red"
else:
    color = "neutral"
```

---

## 7. Archivos relevantes del proyecto

- `raw/responses/0196_america_scan_bf8828f8dd_8f5b42c8c525.json` – payload real del scanner
- `raw/responses/0001_heatmap_stock_e15e12d832f0.html` – HTML inicial con el contexto del heatmap
- `raw/responses/0071_static_bundles_6976.b2c042ba6b4928240347.js_aa2eaf001532.js` – bundle JS con la lógica de render del rectángulo
- `heatmap/export_heatmap_v2.py` – exportador con mapeo semántico
- `heatmap/heatmap_symbols.csv` – exportación legible con el ejemplo de NVDA
- `raw/manifest.json` – manifest de capturas

---

## 8. Conclusión

La reconstrucción técnica del heatmap requiere combinar dos cosas:

- datos del API: el vector `d` y los metadatos del símbolo,
- lógica del frontend: rectángulos, escala, redondeo, color y área del tile.

La parte más crítica para la reproducción del cuadro es entender que:

- `d[3]` decide el color del bloque,
- `d[15]` aporta market cap,
- `d[25]` aporta precio,
- `d[1..21]` aporta el vector compacto de métricas,
- y la geometría visual del rectángulo no se guarda en el JSON, sino que se calcula en el render del navegador.
