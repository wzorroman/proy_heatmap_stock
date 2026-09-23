# 📊 Sistema de Captura de Datos TradingView - Documentación Técnica

## 📋 Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Componentes Principales](#componentes-principales)
4. [Configuración de Crontab](#configuración-de-crontab)
5. [Módulo: Scraper de Activos (scraper_live_tradingview_v3.py)](#módulo-scraper-de-activos)
6. [Módulo: Calendario Económico (calendario_tradingview_live_v3.py)](#módulo-calendario-económico)
7. [Módulo: Monitor de Procesos (monitor_tradingview_live_v3.py)](#módulo-monitor-de-procesos)
8. [Scripts de Ejecución (Shell)](#scripts-de-ejecución-shell)
9. [Estructura de Datos](#estructura-de-datos)
10. [Mantenimiento y Resolución de Problemas](#mantenimiento-y-resolución-de-problemas)

---

## Visión General

Este sistema automatiza la captura de datos financieros desde TradingView, proporcionando:

- **📈 Datos de activos en tiempo real** (NASDAQ, Forex, Metales, Bonos, Energía)
- **📅 Calendario económico** con eventos financieros globales
- **🔍 Monitoreo continuo** de la salud de los procesos
- **🗄️ Gestión inteligente de datos** con rotación automática (7 días LIVE + histórico mensual)
- **⏰ Ejecución programada** con horarios específicos (Lunes a Viernes, excluyendo fines de semana desde Viernes 17:00)

---
## Estructura del Proyecto
    ´´´text
    /home/wilson/CODE_MAIN/app_backup_nasdaq/
    ├── 📁 DATOS_LIVE/ # Directorio principal de datos
    │ ├── 📁 NASDAQ-QQQ/ # Datos del activo QQQ
    │ │ ├── NASDAQ-QQQ.csv # Datos LIVE (últimos 7 días)
    │ │ └── 📁 NASDAQ-QQQ_YYYYMM/ # Histórico mensual
    │ │ └── historico_NASDAQ-QQQ_YYYYMM.csv
    │ ├── 📁 OANDA-XAUUSD/ # Datos del Oro (XAUUSD)
    │ │ ├── OANDA-XAUUSD.csv
    │ │ └── 📁 OANDA-XAUUSD_YYYYMM/
    │ ├── 📁 OANDA-EURUSD/ # Datos del EUR/USD
    │ │ ├── OANDA-EURUSD.csv
    │ │ └── 📁 OANDA-EURUSD_YYYYMM/
    │ ├── 📁 calendario_economico/ # Calendario económico
    │ │ ├── eventos_calendario.csv # Eventos últimos 7 días
    │ │ ├── checkpoint.json # Punto de control
    │ │ ├── 📁 logs/ # Logs del calendario
    │ │ └── 📁 YYYY-MM/ # Histórico mensual
    │ │ └── historico_YYYYMM.csv
    │ └── 📁 consolidados/ # Reportes consolidados
    │
    ├── 📁 venv/ # Entorno virtual Python
    │
    ├── 📄 scraper_live_tradingview_v3.py # Scraper de activos
    ├── 📄 calendario_tradingview_live_v3.py # Calendario económico
    ├── 📄 monitor_tradingview_live_v3.py # Monitor de procesos
    ├── 📄 run_scraper_tradingview.sh # Script ejecución scraper
    ├── 📄 run_calendario_tradingview.sh # Script ejecución calendario
    ├── 📄 notificador_telegram.py # Notificaciones Telegram
    ├── 📄 .env # Variables de entorno
    │
    └── 📁 logs_ejecucion/ # Logs de ejecución
    ├── scraper_YYYYMMDD_HHMMSS.log
    └── calendario_YYYYMMDD_HHMMSS.log
    ´´´

---

## Componentes Principales

### 1. **Scraper de Activos** (`scraper_live_tradingview_v4.py`)
Captura datos en tiempo real de 34+ activos financieros:
- **NASDAQ Core**: QQQ
- **Sentimiento**: BTC, VIX, DXY
- **Forex**: EURUSD, AUDUSD, USDJPY, GBPUSD
- **Metales**: Oro (XAUUSD), Plata (SLV)
- **Bonos**: SHY, IEF, TLT, US02Y, US10Y
- **Energía**: OIL, XLE

**Campos capturados por activo:**
- `close`: Precio de cierre
- `volume`: Volumen
- `RSI`: Relative Strength Index
- `CCI20`: Commodity Channel Index
- `BBPower`: Bollinger Bands Power
- `ADX`: Average Directional Index
- `Pivot.M.Camarilla.R3`: Nivel de pivote
- `Perf.W`: Rendimiento semanal (%)
- `change`: Cambio porcentual

### 2. **Calendario Económico** (`calendario_tradingview_live_v5.py`)
Captura eventos económicos globales con:
- **Países**: US, GB, DE, FR, IT, ES, CN, JP, AU, CA, CH
- **Importancia**: 1 (baja), 2 (media), 3 (alta)
- **Campos**: Título, país, fecha, actual, esperado, previo, sorpresa

### 3. **Monitor de Procesos** (`monitor_tradingview_live_v3.py`)
Supervisa la salud de todos los procesos:
- Verifica timestamps de últimos datos
- Calcula ciclos perdidos
- Envía alertas consolidadas por Telegram
- Previene spam (máx 1 alerta cada 30 minutos)

---

## Configuración de Crontab

### Horarios de Ejecución

| Día | Horario | Scraper (3min) | Calendario (15min) | Monitor (5min) |
|-----|---------|----------------|-------------------|----------------|
| **Lunes a Jueves** | 00:00 - 23:59 | ✅ Activo | ✅ Activo | ✅ Activo |
| **Viernes** | 00:00 - 16:59 | ✅ Activo | ✅ Activo | ✅ Activo |
| **Viernes** | 17:00 - 23:59 | ❌ Inactivo | ❌ Inactivo | ❌ Inactivo |
| **Sábado** | Todo el día | ❌ Inactivo | ❌ Inactivo | ❌ Inactivo |
| **Domingo** | Todo el día | ❌ Inactivo | ❌ Inactivo | ❌ Inactivo |

### Comandos Crontab Actuales

```bash
# ============== NASDAQ ===========

# 📈 SCRAPER DE ACTIVOS (cada 3 minutos)
# Lunes a jueves: 00:00 a 23:59
*/3 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh

# Viernes: 00:00 a 16:59
*/3 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh

# 📅 CALENDARIO ECONÓMICO (cada 15 minutos)
# Lunes a jueves: 00:00 a 23:59
*/15 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh

# Viernes: 00:00 a 16:59
*/15 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh

# 🔍 MONITOR DE PROCESOS (cada 5 minutos)
# Lunes a jueves: 00:00 a 23:59
*/5 0-23 * * 1-4 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1

# Viernes: 00:00 a 16:59
*/5 0-16 * * 5 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1
```
### **Explicación de Campos Crontab**

| **Campo** | **Valores** | **Significado** |
| --- | --- | --- |
| `*/3` | Cada 3 minutos | Frecuencia de ejecución |
| `0-23` | Horas 00 a 23 | Rango de horas del día |
| `0-16` | Horas 00 a 16 | Rango de horas (hasta 16:59) |
| `*` | Todos | Días del mes / Meses |
| `1-4` | Lunes a Jueves | Días de la semana (1=Lunes, 4=Jueves) |
| `5` | Viernes | Día de la semana |

---

## **Módulo: Scraper de Activos**

### **Características Técnicas**

**Mecanismo de Extracción:**

- Consulta directa al scanner de TradingView (`scanner.tradingview.com/symbol`)
- Sin dependencias de librerías externas (solo `requests`)
- Redundancia con símbolos primarios y de respaldo
- Pausas aleatorias (2.5-5 segundos) para evitar bloqueos

**Gestión de Datos:**

- Rotación automática cada 7 días
- Histórico mensual en carpetas separadas
- Formato CSV con timestamp UTC

### **Campos del DataFrame**

```python
{
    'timestamp_utc': 1742572800,           # Timestamp Unix en segundos UTC
    'fecha_iso': '2026-03-21T12:00:00Z',   # Fecha ISO legible
    'simbolo': 'NASDAQ:QQQ',                # Símbolo del activo
    'close': 485.32,                        # Precio de cierre
    'volume': 12500000,                     # Volumen
    'RSI': 65.4,                            # RSI (0-100)
    'CCI20': 120.5,                         # CCI20
    'BBPower': 2.3,                         # Bollinger Bands Power
    'ADX': 28.5,                            # ADX
    'Pivot.M.Camarilla.R3': 490.15,         # Nivel pivote R3
    'Perf.W': 2.5,                          # Rendimiento semanal (%)
    'change': 1.2                           # Cambio porcentual
}
```

### **Uso**

```bash
# Ejecución normal (captura todos los activos)
python3 scraper_live_tradingview_v3.py

# Generar reporte consolidado
python3 scraper_live_tradingview_v3.py --consolidate
```

---

## **Módulo: Calendario Económico**

### **Características Técnicas**

**API Utilizada:**

- Endpoint: `https://economic-calendar.tradingview.com/events`
- Rango: Último día + próximos 2 días
- Filtros: Países configurados, importancia ≥ 1

**Gestión de Datos:**

- Eventos recientes en `eventos_calendario.csv` (últimos 7 días)
- Histórico mensual en `YYYY-MM/historico_YYYYMM.csv`
- Checkpoint para reanudación (`checkpoint.json`)
- Eliminación automática de duplicados

### **Campos del DataFrame**

```python
{
    'timestamp_utc': 1742572800,                  # Timestamp del evento
    'fecha_iso': '2026-03-21T12:00:00Z',          # Fecha ISO original
    'fecha_humana': '2026-03-21 12:00:00 UTC',    # Fecha legible
    'titulo': 'Fed Interest Rate Decision',       # Título del evento
    'pais': 'US',                                 # Código país
    'importancia': 3,                             # 1-3 (alta)
    'categoria': 'Monetary Policy',               # Categoría
    'actual': '5.25',                             # Valor actual
    'esperado': '5.25',                           # Valor esperado
    'previo': '5.50',                             # Valor previo
    'unidad': '%',                                # Unidad de medida
    'moneda': 'USD',                              # Moneda
    'es_futuro': False,                           # Evento futuro?
    'sorpresa': 0.0,                              # Sorpresa = actual - esperado
    'timestamp_captura': 1742576400               # Momento de captura
}
```

### **Uso**

```bash
# Captura normal (ejecutar cada 15-30 minutos)
python3 calendario_tradingview_live_v3.py

# Con países específicos
python3 calendario_tradingview_live_v3.py --paises "US,GB,DE,FR"

# Generar reporte consolidado
python3 calendario_tradingview_live_v3.py --consolidate

# Limpiar duplicados en históricos
python3 calendario_tradingview_live_v3.py --clean

# Ver estado actual
python3 calendario_tradingview_live_v3.py --status

# Forzar rotación manual (mantener 14 días)
python3 calendario_tradingview_live_v3.py --rotate-now --dias-mantener 14
```

---

## **Módulo: Monitor de Procesos**

### **Funcionalidades**

**Verificaciones Realizadas:**

1. Existencia de archivos CSV y JSON
2. Timestamp de última actualización
3. Ciclos perdidos vs intervalo configurado
4. Estado de cada proceso (OK / WARNING / ALERTA)

**Umbrales de Alerta:**

- **WARNING**: > 1.5 ciclos sin actualizar
- **ALERTA**: > 2 ciclos sin actualizar
- **Prevención de Spam**: Máx 1 alerta cada 30 minutos

**Procesos Monitorizados:**

- 3 activos principales (QQQ, XAUUSD, EURUSD) - intervalo 5 min
- 1 calendario económico - intervalo 15 min

### **Configuración en `.env`**

bash

```
# Telegram Bot Configuration
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### **Estructura de Alertas**

```json
{
    "nombre": "NASDAQ-QQQ.csv",
    "proceso": "scraper_live_tradingview_v3.py (QQQ)",
    "tipo": "activo",
    "diferencia": 15.5,           // minutos sin actualizar
    "ciclos_perdidos": 3.1,       // ciclos perdidos
    "ultima_fecha": "2026-03-21 10:30:00",
    "error": null
}
```

### **Uso**

```bash
# Ejecución manual
cd /home/wilson/CODE_MAIN/app_backup_nasdaq
python3 monitor_tradingview_live_v3.py
```

---

## **Scripts de Ejecución (Shell)**

### **`run_scraper_tradingview.sh`**

**Funcionalidades:**

- Verifica existencia de directorios y scripts
- Carga variables de entorno desde `.env`
- Ejecuta el scraper con logging detallado
- Verifica resultados (archivos CSV generados)
- Limpia logs antiguos (> 2 días)

**Logs Generados:**

- `logs_ejecucion/scraper_YYYYMMDD_HHMMSS.log`

### **`run_calendario_tradingview.sh`**

**Funcionalidades:**

- Similar al scraper, pero para calendario económico
- Verifica archivos `eventos_calendario.csv` y `checkpoint.json`
- Muestra estadísticas de eventos capturados
- Limpia logs de calendario y ejecución

**Logs Generados:**

- `logs_ejecucion/calendario_YYYYMMDD_HHMMSS.log`
- `DATOS_LIVE/calendario_economico/logs/calendario_YYYYMMDD_HHMMSS.log`

---

## **Estructura de Datos**

### **Formato CSV (Activos)**

csv

```
timestamp_utc,fecha_iso,simbolo,close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change
1742572800,2026-03-21T12:00:00Z,NASDAQ:QQQ,485.32,12500000,65.4,120.5,2.3,28.5,490.15,2.5,1.2
```

### **Formato CSV (Calendario)**

csv

```
timestamp_utc,fecha_iso,fecha_humana,titulo,pais,importancia,categoria,actual,esperado,previo,unidad,moneda,es_futuro,sorpresa,timestamp_captura
1742572800,2026-03-21T12:00:00Z,2026-03-21 12:00:00 UTC,Fed Decision,US,3,Monetary Policy,5.25,5.25,5.50,%,USD,False,0.0,1742576400
```

### **Formato JSON (Checkpoint)**

json

```json
{
  "ultimo_timestamp": 1742572800,
  "ultima_fecha": "2026-03-21T12:00:00+00:00",
  "eventos_acumulados": 150,
  "eventos_encontrados": 25,
  "fecha_ultima_revision": "2026-03-21T15:30:00+00:00",
  "timestamp": "2026-03-21T15:30:00+00:00"
}
```

---

## **Mantenimiento y Resolución de Problemas**

### **Verificar Estado del Sistema**

```bash
# Ver estado del calendario
python3 calendario_tradingview_live_v3.py --status

# Ver archivos generados
ls -la DATOS_LIVE/NASDAQ-QQQ/
ls -la DATOS_LIVE/calendario_economico/

# Verificar últimos registros
tail -5 DATOS_LIVE/NASDAQ-QQQ/NASDAQ-QQQ.csv
tail -20 DATOS_LIVE/calendario_economico/eventos_calendario.csv
```

### **Revisar Logs**

```bash
# Logs de ejecución
tail -50 logs_ejecucion/scraper_$(date +%Y%m%d)*.log
tail -50 logs_ejecucion/calendario_$(date +%Y%m%d)*.log

# Logs del calendario
tail -50 DATOS_LIVE/calendario_economico/logs/calendario_*.log
```

### **Limpieza Manual**

```bash
# Limpiar duplicados en históricos
python3 calendario_tradingview_live_v3.py --clean

# Forzar rotación manual (mantener 14 días)
python3 calendario_tradingview_live_v3.py --rotate-now --dias-mantener 14
```

### **Problemas Comunes**

| **Problema** | **Posible Causa** | **Solución** |
| --- | --- | --- |
| **Archivos no se actualizan** | Proceso detenido | Verificar logs, reiniciar servicio |
| **Error 429 en API** | Rate limit | Pausa automática implementada |
| **Telegram no envía alertas** | Token inválido | Verificar `.env` y credenciales |
| **Rotación no funciona** | Permisos de escritura | Verificar permisos en `DATOS_LIVE/` |
| **Timestamps futuros** | Zona horaria incorrecta | Verificar UTC en configuraciones |

### **Reinicio de Procesos**

```bash
# Ejecutar manualmente para probar
/home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh
/home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh

# Verificar crontab
crontab -l

# Editar crontab si es necesario
crontab -e
```

---

## **Notas Importantes**

1. **Zona Horaria**: Todos los timestamps están en **UTC** para evitar ambigüedades
2. **Rotación Automática**: Datos LIVE mantienen últimos 7 días, histórico mensual permanente
3. **Prevención de Spam**: Monitor envía alertas cada 30 minutos máximo
4. **Redundancia**: Scraper tiene símbolos primarios y de respaldo
5. **Logs**: Rotación automática cada 2 días para evitar acumulación