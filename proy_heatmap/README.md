# Proy Heatmap Stock

Scraper del heatmap de TradingView que consulta el endpoint en tiempo real
y almacena los datos en PostgreSQL.

## Componentes

| Archivo | Descripcion |
|---------|-------------|
| scrapper_heatmap_v1.py | Script principal: consulta endpoint, top 1000 stocks, INSERT en BD |
| app.py | Frontend Streamlit (solo llama al servicio) |
| application/heatmap_service.py | Logica de negocio y transformacion (pivot de precios, labels) |
| application/db/heatmap_repository.py | Consultas SQL |
| config.py | Configuracion (endpoint, headers, columnas, conexion BD) |
| create_partitions.py | Crea particiones mensuales para tablas de hechos |
| db/postgresql_connection.py | Conector PostgreSQL |
| utils/config_logging.py | Logger (rotacion diaria, retiene 14 dias) |

## Ejecucion manual

```bash
cd proy_heatmap
python scrapper_heatmap_v1.py
```

## Ejecucion periodica (cron)

El script esta diseniado para ejecutarse cada 5 minutos via cron.

### Configurar crontab

```bash
crontab -e
```

Agregar la linea:

```
*/5 * * * * cd /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_heatmap && /usr/bin/python3 scrapper_heatmap_v1.py >> /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/logs/cron_heatmap.log 2>&1
```

### Verificar crontab activo

```bash
crontab -l
```

### Logs de cron

```bash
tail -f /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/logs/cron_heatmap.log
```

## Base de datos

**Conexion:** PostgreSQL `heatmap_stock` en `localhost:5432`

### Tablas principales

| Tabla | Tipo | Descripcion |
|-------|------|-------------|
| dim_asset | Dimension | Un registro por simbolo (symbol, ticker, exchange, sector, etc.) |
| fact_heatmap_snapshot | Hecho (particionada) | Snapshot por simbolo x timestamp. Campos: price, daily_change_pct, market_cap, raw_vector, raw_metadata |
| audit_sync_run | Auditoria | Log de cada ejecucion (status, records_fetched, records_upserted) |

### Particionado

Las tablas de hechos se particionan mensualmente:
- `fact_heatmap_snapshot_2026_09`
- `fact_heatmap_snapshot_2026_10`
- ...

Las particiones se crean automaticamente al ejecutar el script.

## Datos capturados

Cada ejecucion inserta los **top 1000 stocks** por market cap con:

- **28 campos** en el vector `d[]` (typespecs, change, close, market_cap, sector, etc.)
- **Redondeo** a 4 decimales (2 para market_cap)
- **Timestamp UTC** del momento de la consulta

### Mapeo de campos

| Indice d[] | Campo | Descripcion |
|------------|-------|-------------|
| d[0] | typespecs | Tipo de activo (stock, etf, etc.) |
| d[1] | change | Cambio porcentual diario |
| d[2] | change_abs | Cambio absoluto diario |
| d[3] | Perf.1M | Performance 1 mes |
| d[4] | Perf.3M | Performance 3 meses |
| d[5] | Perf.6M | Performance 6 meses |
| d[6] | Perf.Y | Performance anual |
| d[7] | Perf.YTD | Performance year-to-date |
| d[8] | Volatility.D | Volatilidad diaria |
| d[9] | price_52_week_high | Maximo 52 semanas |
| d[10] | price_52_week_low | Minimo 52 semanas |
| d[11] | market_cap_basic | Capitalizacion de mercado |
| d[12] | average_volume_30d_calc | Volumen promedio 30 dias |
| d[13] | average_volume_10d_calc | Volumen promedio 10 dias |
| d[14] | volume | Volumen actual |
| d[15] | total_shares_outstanding | Acciones en circulacion |
| d[16] | total_shares_outstanding_fundamental | Acciones fundamentales |
| d[17] | number_of_employees | Numero de empleados |
| d[18] | earnings_per_share_basic_ttm | EPS basico TTM |
| d[19] | revenue_per_employee_ttm | Ingreso por empleado TTM |
| d[20] | gross_profit_1Y_growth_fq | Crecimiento bruto 1 ano |
| d[21] | sector | Sector del activo |
| d[22] | logoid | ID del logo |
| d[23] | close | Precio de cierre actual |
| d[24] | pricescale | Escala de precios |
| d[25] | name | Nombre/ticker |
| d[26] | update_mode | Estado del stream |
| d[27] | currency | Moneda |

## Endpoints consultados

```
POST https://scanner.tradingview.com/america/scan?label-product=heatmap-stock
Content-Type: application/json
```

## Variables de entorno (.env)

```
BD_HEATMAP_SERVER=localhost
BD_HEATMAP_PORT=5432
BD_HEATMAP_DATABASE=heatmap_stock
BD_HEATMAP_USER=postgres
BD_HEATMAP_PASSWORD=postgres
```

## Requisitos

```bash
pip install requests psycopg2-binary python-dotenv pytz
```

## Auditoria

Cada ejecucion se registra en la tabla `audit_sync_run` con:

- `script_name`: nombre del script
- `run_start`: timestamp de inicio
- `run_end`: timestamp de fin
- `records_fetched`: registros obtenidos del endpoint
- `records_upserted`: registros insertados/actualizados en BD
- `records_failed`: registros fallidos (fetched - upserted)
- `status`: SUCCESS o FAILED
- `error_message`: mensaje de error (si aplica)
- `execution_mode`: cron

### Consultar auditoria

```sql
SELECT run_id, script_name, run_start, run_end,
       records_fetched, records_upserted, status, error_message
FROM audit_sync_run
ORDER BY run_start DESC
LIMIT 10;
```

---

## Frontend (Streamlit)

Aplicacion web que muestra los datos del heatmap de la ultima hora
con auto-refresh cada 2.5 minutos.

### Arquitectura

```
app.py                          <- Streamlit UI (solo llama al servicio)
application/
    heatmap_service.py          <- Logica de negocio (pivot, labels, formato)
    db/
        heatmap_repository.py   <- Consultas SQL
db/
    postgresql_connection.py    <- Conector generico (existe)
config.py                       <- Configuracion (existe)
```

Flujo de dependencias:

```
app.py (UI)
   │
   ▼
application/heatmap_service.py    (orquesta + transforma)
   │
   ▼
application/db/heatmap_repository.py   (SQL puro)
   │
   ▼
db/postgresql_connection.py
   │
   ▼
PostgreSQL (fact_heatmap_snapshot / dim_asset)
```

### Ejecucion

```bash
cd proy_heatmap
streamlit run app.py --server.port 8501
```

Abrir en el navegador: `http://localhost:8501`

### Funcionalidades

- **Tabla de evolucion de precios**: ultimos 6 snapshots (aprox 30 min) por stock, cada columna es una marca de tiempo `HH:MM`
- **Columna Asset**: combina ticker + nombre de la empresa + sector como label `[Sector]`
- **Precio a color**: verde si subio, rojo si bajo, negro si sin cambio (comparado con el snapshot anterior)
- **Market Cap legible**: `$5.27T`, `$987.65M`, etc.
- **Filtros**: busqueda por simbolo, filtro por sector
- **Metricas**: total stocks, subieron, bajaron, cambio promedio
- **Orden**: market cap descendente (desde SQL)
- **Auto-refresh**: cada 2.5 minutos

### Vista de la tabla

```
┌─────────┬──────────────────────────────┬──────────┬──────────┬────────────┬─────────┬─────────┬─────────┐
│ Symbol  │ Asset                        │ Price    │ Change%  │ Market Cap │ 12:45   │ 12:40   │ 12:35   │
├─────────┼──────────────────────────────┼──────────┼──────────┼────────────┼─────────┼─────────┼─────────┤
│ NVDA    │ NVDA [Electronic Technology] │ $218.49  │  +2.35%  │ $5.27T     │ 218.50  │ 218.49  │ 218.42  │
│ AAPL    │ AAPL [Electronic Technology] │ $323.96  │  +1.12%  │ $4.73T     │ 323.98  │ 323.96  │ 323.97  │
│ MSFT    │ MSFT [Technology Services]   │ $415.20  │  -0.45%  │ $3.08T     │ 415.21  │ 415.20  │ 415.14  │
│ AMZN    │ AMZN [Retail Trade]          │ $218.94  │  +1.87%  │ $2.31T     │ 218.93  │ 218.94  │ 218.35  │
│ TSLA    │ TSLA [Consumer Durables]     │ $345.12  │  -2.15%  │ $1.10T     │ 345.11  │ 345.12  │ 345.80  │
│ META    │ META [Technology Services]   │ $542.30  │  +0.89%  │ $1.37T     │ 542.31  │ 542.30  │ 542.35  │
└─────────┴──────────────────────────────┴──────────┴──────────┴────────────┴─────────┴─────────┴─────────┘

Precio en verde si subio respecto al snapshot anterior, rojo si bajo, negro si sin cambio.
```

### Dependencias del frontend

```bash
pip install streamlit
```

O instalar todas las dependencias:

```bash
pip install -r requirements.txt
```

### Architecture Decision Records (ADR)

**Por que Streamlit?**
- Rapido de desarrollar (minimal code)
- Auto-refresh nativo con `st.rerun()`
- Ideal para apps de datos
- No requiere conocimientos de HTML/CSS/JS

**Por que separar en capas?**
- `app.py` solo maneja UI, sin logica de negocio
- `heatmap_service.py` orquesta las consultas
- `heatmap_repository.py` contiene SQL puro
- Facil de reusar desde otros endpoints (FastAPI, Flask, etc.)
