# Heatmap export

Esta carpeta contiene una utilidad para consultar el endpoint del heatmap de TradingView y exportar los datos a CSV.

## Endpoint consultado

- https://scanner.tradingview.com/america/scan?label-product=heatmap-stock

## Ejecución

Desde la raíz del proyecto con el entorno virtual:

```bash
cd /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock
. .venv/bin/activate
python heatmap/export_heatmap_csv.py --output heatmap/heatmap_symbols.csv
```

## Salida

Genera un CSV con columnas como:

- symbol
- ticker
- company_name
- security_type
- sector
- sector_es
- logo
- stream_status
- metric_1 ... metric_21

## Requisitos

Se requiere instalar solo `requests` en el .venv del proyecto:

```bash
. .venv/bin/activate
python -m pip install requests
```
