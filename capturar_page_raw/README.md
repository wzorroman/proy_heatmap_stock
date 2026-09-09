# Captura de artefactos de TradingView Heatmap

Este proyecto descarga y guarda los archivos crudos que carga la ruta de TradingView:

https://es.tradingview.com/heatmap/stock/

Se usa Python y Playwright para abrir la página real, interceptar todas las respuestas de red y guardar:

- HTML principal
- archivos JavaScript
- JSON/XHR
- CSS, imágenes y otros recursos estáticos
- un archivo HAR con todas las llamadas de red

## Requisitos

Se recomienda usar el entorno virtual del proyecto:

```bash
source env/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Ejecución

```bash
source env/bin/activate
python capture_tradingview_heatmap.py --url "https://es.tradingview.com/heatmap/stock/" --output-dir raw
```

Los resultados se guardan en la carpeta `raw/`.

## Estructura de salida

```text
raw/
  network.har
  page.html
  page.png
  manifest.json
  responses/
    0001_...js
    0002_...json
    ...
```

Puedes revisar los JS y los payloads descargados para estudiar el contenido real que entrega la consulta.
