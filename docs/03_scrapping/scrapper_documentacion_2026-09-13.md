# Informe Técnico — Proyecto `proy_scrapping_detail`

| Campo | Valor |
|---|---|
| **Proyecto** | `proy_scrapping_detail` — Radar Intermarket TradingView |
| **Ruta del código** | `/home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_scrapping_detail` |
| **Componentes** | Scraper de activos (V4), Calendario económico (V4), Monitor de procesos (V3) |
| **Versión de código** | (VERSION 3.0) - V4 (scraper y calendario) · V3 (monitor) |
| **Fecha del informe** | 2026-09-13 |
| **Elaborado por** | Documentación técnica automática |
| **Alcance** | Exclusivamente `proy_scrapping_detail` |
| **Fuente de datos** | API/scanner de TradingView (pública, sin autenticación) |
| **Persistencia** | Sistema de archivos (CSV / JSON), sin base de datos |

---

## Tabla de Contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura general y flujo](#2-arquitectura-general-y-flujo)
3. [Estructura de directorios](#3-estructura-de-directorios)
4. [Configuración de activos — `config.py`](#4-configuración-de-activos--configpy)
5. [Scraper de activos — `scraper_live_tradingview_v4.py`](#5-scraper-de-activos--scraper_live_tradingview_v4py)
6. [Calendario económico — `calendario_tradingview_live_v4.py`](#6-calendario-económico--calendario_tradingview_live_v4py)
7. [Monitor de procesos — `monitor_tradingview_live_v3.py`](#7-monitor-de-procesos--monitor_tradingview_live_v3py)
8. [Scripts de ejecución (Shell)](#8-scripts-de-ejecución-shell)
9. [Tipos de datos y esquemas](#9-tipos-de-datos-y-esquemas)
10. [Fuentes de datos (endpoints)](#10-fuentes-de-datos-endpoints)
11. [Persistencia y rotación de datos](#11-persistencia-y-rotación-de-datos)
12. [Programación cron](#12-programación-cron)
13. [Dependencias y entorno](#13-dependencias-y-entorno)
14. [Observaciones e inconsistencias detectadas](#14-observaciones-e-inconsistencias-detectadas)
15. [Apéndices (muestras reales)](#15-apéndices-muestras-reales)

---

## 1. Resumen ejecutivo

`proy_scrapping_detail` es un sistema de **captura de datos financieros** de TradingView
organizado en tres procesos independientes que se ejecutan vía `cron` en estaciones Linux:

1. **Scraper de activos** (`scraper_live_tradingview_v4.py`): consulta el endpoint
   `/symbol` del scanner de TradingView para **110 símbolos únicos** (primarios y
   respaldos) definidos en `config.py`. Por cada símbolo guarda 8 métricas técnicas
   (`close`, `volume`, `RSI`, `CCI20`, `BBPower`, `ADX`, pivote Camarilla R3, `Perf.W`,
   `change`), más metadatos de tiempo (`timestamp_utc`, `fecha_iso`, `simbolo`).
2. **Calendario económico** (`calendario_tradingview_live_v4.py`): consume la API
   `economic-calendar.tradingview.com/events` y almacena **raw, sin filtrar ni
   transformar**, los 21 campos que devuelve la API para 11 países.
3. **Monitor de procesos** (`monitor_tradingview_live_v3.py`): evalúa la frescura de
   los archivos mediante timestamps, calcula "ciclos perdidos" y notifica por
   **Telegram** (una alerta consolidada, con anti-spam de 30 min).

No existe base de datos: toda la persistencia es en **CSV y JSON** con rotación
automática (LIVE de 7 días + histórico mensual). El diseño es *zero-library* para la
extracción (solo `requests`), con redundancia primario/respaldo, backoff ante HTTP 429,
circuit breaker y lock de exclusión mutua (`fcntl`) para evitar solapamiento de ciclos.

> **Nota:** el código de `monitor_tradingview_live_v3.py` y `readme.md` mencionan un
> módulo `notificador_telegram.py` que **no está presente** en el repositorio (ver
> [§14](#14-observaciones-e-inconsistencias-detectadas)).

---

## 2. Arquitectura general y flujo

```
                         crontab (Lun–Jue / Vie hasta 16:59)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
run_scraper_tradingview.sh   run_calendario_tradingview.sh   monitor_tradingview_live_v3.py
   (cada 3 min)                 (cada 15 min)                   (cada 5 min)
        │                            │                            │
        ▼                            ▼                            ▼
scraper_live_tradingview_v4  calendario_tradingview_live_v4    MonitorTradingView
        │                            │                            │
        │ requests.get               │ requests.get               │ lee CSV/JSON
        ▼                            ▼                            ▼
scanner.tradingview.com       economic-calendar...          DATOS_LIVE/*
  /symbol                       /events                      DATOS_LIVE_CALENDARIO/*
        │                            │                            │
        ▼                            ▼                            ▼
DATOS_LIVE/{SYMBOL}/         DATOS_LIVE_CALENDARIO/       Telegram Bot API
  {SYMBOL}.csv                 calendario_economico/      (notificador_telegram)
  {SYMBOL}_{YYYYMM}/             eventos_calendario.csv
    historico_*.csv              checkpoint.json
                                 YYYY-MM/historico_*.csv
```

**Flujo del scraper (por símbolo):**

```
CONFIG_ACTIVOS → set(primarios ∪ respaldos) → sorted()
   → por símbolo:
       fetch_from_scanner()  ──200──► dict JSON + timestamp_utc + fecha_iso + simbolo
              │
              ├─ "429" → backoff [15s, 45s, 120s] → reintentos
              └─ None  → pausa 20s + contador fallos
                         └─ 3 fallos consecutivos → CIRCUIT BREAKER (exit 1)
       append a CSV (header condicional) → rotar_datos() (mueve >7 días a histórico)
       sleep aleatorio 0.4–1.2 s
   → si --consolidate: consolidar_analisis()
```

**Flujo del calendario:**

```
ventana [hoy-1d, hoy+2d] → fetch_calendar_events() (RAW)
   → evento_a_dict() (None→'', + timestamp_captura)
   → guardar_eventos() (dedup por id, merge con existente)
   → rotar_eventos_recientes() (>7 días → histórico mensual)
   → guardar_checkpoint()
```

---

## 3. Estructura de directorios

```
proy_scrapping_detail/
├── config.py                             # Universo de activos y metadatos
├── scraper_live_tradingview_v4.py        # Scraper de activos V4
├── calendario_tradingview_live_v4.py     # Calendario económico V4
├── monitor_tradingview_live_v3.py        # Monitor de procesos V3
├── run_scraper_tradingview.sh            # Wrapper shell del scraper
├── run_calendario_tradingview.sh         # Wrapper shell del calendario
├── requirements.txt                      # Dependencias Python
├── .env                                  # Variables reales (no versionado)
├── .env_demo                             # Plantilla de variables
├── .gitignore / .dockerignore            # Exclusiones
├── readme.md                             # Documentación del autor (desactualizada)
├── readme_crontab.md                     # Líneas de crontab de referencia
├── DATOS_LIVE/                           # Salida del scraper
│   ├── {EXCHANGE-TICKER}/                # Ej. NASDAQ-QQQ (110 carpetas)
│   │   ├── {EXCHANGE-TICKER}.csv         # Datos LIVE (últimos 7 días)
│   │   └── {EXCHANGE-TICKER}_{YYYYMM}/   # Histórico mensual
│   │       └── historico_{EXCHANGE-TICKER}_{YYYYMM}.csv
│   └── consolidados/                     # Snapshots consolidados (--consolidate)
│       └── consolidado_{YYYYMMDD_HHMMSS}.csv
├── DATOS_LIVE_CALENDARIO/                # Salida del calendario
│   └── calendario_economico/
│       ├── eventos_calendario.csv        # Eventos últimos 7 días
│       ├── checkpoint.json               # Punto de control
│       ├── logs/
│       │   └── calendario_{YYYYMMDD_HHMMSS}.log
│       └── {YYYY-MM}/                    # Histórico mensual
│           └── historico_{YYYYMM}.csv
├── venv/                                 # Entorno virtual Python
├── __pycache__/
└── .coverage                             # Artefacto de cobertura
```

**Conteos reales observados (2026-09-13):**

| Elemento | Cantidad |
|---|---|
| Carpetas de activos en `DATOS_LIVE/` | 110 |
| Categorías en `CONFIG_ACTIVOS` | 21 |
| Claves de activo (primario+respaldo) en `CONFIG_ACTIVOS` | 93 |
| Símbolos únicos (primarios ∪ respaldos) | 110 |
| Entradas en `METADATOS_ACTIVOS` | 15 |
| Eventos en `eventos_calendario.csv` | 66 (+1 cabecera) |

---

## 4. Configuración de activos — `config.py`

`config.py` es un módulo de datos puro (sin lógica) que define el universo de activos.
Es importado por el scraper (`from config import CONFIG_ACTIVOS`).

### 4.1 `CONFIG_ACTIVOS`

Diccionario de **dos niveles**:

```
CONFIG_ACTIVOS : Dict[str, Dict[str, Dict[str, str]]]
  { "CATEGORIA": { "CLAVE": { "primario": "EXCHANGE:TICKER",
                              "respaldo": "EXCHANGE:TICKER" }, ... }, ... }
```

- `CATEGORIA`: agrupación temática (21 en total).
- `CLAVE`: identificador corto del activo (ej. `QQQ`, `ORO`, `US10Y`).
- `primario` / `respaldo`: símbolos en formato TradingView `EXCHANGE:TICKER`.
  El respaldo es un instrumento alternativo usado como redundancia.

**Categorías y activos (conteo de claves):**

| Categoría | Claves | Activos |
|---|---|---|
| `NASDAQ_CORE` | 1 | QQQ |
| `SENTIMIENTO` | 5 | BTC, VIX, DXY, MSTR, MARA |
| `FOREX_CENTINELA` | 4 | EURUSD, AUDUSD, USDJPY, GBPUSD |
| `METALES_SPOT` | 2 | ORO, PLATA |
| `BONOS_ETF_TEC` | 3 | SHY, IEF, TLT |
| `BONOS_YIELD` | 2 | US02Y, US10Y |
| `ENERGIA` | 2 | OIL, XLE |
| `INDICES_ETF_USA` | 4 | SPY, VOO, VGT, NDX |
| `FOREX_EXTRA` | 3 | USDCAD, GBPJPY, NZDUSD |
| `FINANZAS_BANCOS` | 6 | BRK.B, JPM, V, BAC, MS, BLK, GS |
| `CONSUMO_DEFENSIVO` | 4 | PG, KO, PEP, COST |
| `RETAIL_CONSUMO` | 6 | WMT, HD, MCD, SBUX, BABA, TGT |
| `SALUD_FARMACIA` | 5 | LLY, UNH, JNJ, ABBV, TMO |
| `INDUSTRIAL_LOGISTICA` | 4 | GE, UPS, DE, WM |
| `AEROESPACIAL_DEFENSA` | 3 | BA, LMT, NOC |
| `ENERGIA_ACCIONES` | 2 | CCJ, XOM |
| `TELECOM_MEDIA` | 2 | DIS, VZ |
| `TECNOLOGIA_GIGANTES` | 7 | AAPL, AMZN, GOOGL, META, MSFT, NFLX, TSLA |
| `SEMICONDUCTORES` | 11 | NVDA, ASML, MU, QCOM, TSM, AVGO, ARM, INTC, SMCI, TER, TXN |
| `SOFTWARE_SAAS` | 8 | ADSK, CRM, DDOG, FTNT, NOW, ORCL, PANW, SHOP, SPOT |
| `HARDWARE_INFRAESTRUCTURA` | 7 | IBM, CSCO, DELL, HPQ, LOGI, STX, WDC |

> Los activos comentados en el archivo (`MA`, `CL`, `NKE`, `TM`, `AAL`, `CCL`, `RCL`,
> `MRK`, `PFE`, `CAT`, `CVX`, `MRVL`, `ADI`, `ABNB`, `ACN`, `DOCN`, `NET`, `SNOW`,
> `VIAJES_OCIO` completo) no forman parte del universo activo.

**Observaciones de catálogo embebidas en el código:**

- `METALES_SPOT["ORO"]["primario"] = OANDA:XAUUSD`, respaldo `SAXO:XAUUSD`. Se eliminó
  `CAPITALCOM:XAUUSD/GOLD` por devolver `null`.
- `INDICES_ETF_USA["NDX"]` usa `NASDAQ:NDX` porque `CAPITALCOM:NAS100` devuelve `null`.
- `SOFTWARE_SAAS["SHOP"]` resuelve a `NASDAQ:SHOP` (conflicto con NYSE resuelto).

### 4.2 `METADATOS_ACTIVOS`

Complemento de `CONFIG_ACTIVOS` que indica cómo participa cada símbolo en los *scores*
de radar/momentum. Los símbolos ausentes se tratan como `equity` con `peso: 1.0`.

```
METADATOS_ACTIVOS : Dict[str, Dict[str, Any]]
  { "VIX": {"categoria": "macro", "peso": 0.0, "peso_radar": 20, "direccion": "invertida"}, ... }
```

**Campos:**

| Campo | Tipo | Significado |
|---|---|---|
| `categoria` | `str` | Taxonomía (`macro`, etc.) |
| `peso` | `float` | Peso en Score Momentum (0.0 = excluido) |
| `peso_radar` | `int` | Peso en el blend intermarket del radar |
| `direccion` | `str` | `normal` o `invertida` (para interpretar el signo) |

**Entradas definidas (15):**

| Símbolo | Categoría | Peso | Peso radar | Dirección |
|---|---|---|---|---|
| `VIX` | macro | 0.0 | 20 | invertida |
| `DXY` | macro | 0.0 | 15 | invertida |
| `TLT` | macro | 0.0 | 15 | normal |
| `US10Y` | macro | 0.0 | 15 | invertida |
| `ORO` | macro | 0.0 | 15 | invertida |
| `OIL` | macro | 0.0 | 10 | invertida |
| `US02Y` | macro | 0.0 | — | — |
| `BTC` | macro | 0.0 | — | — |
| `EURUSD` | macro | 0.0 | — | — |
| `AUDUSD` | macro | 0.0 | — | — |
| `USDJPY` | macro | 0.0 | — | — |
| `GBPUSD` | macro | 0.0 | — | — |
| `USDCAD` | macro | 0.0 | — | — |
| `GBPJPY` | macro | 0.0 | — | — |
| `NZDUSD` | macro | 0.0 | — | — |

### 4.3 Constantes finales

| Constante | Valor | Uso |
|---|---|---|
| `CATEGORIA_DEFAULT` | `"equity"` | Categoría para símbolos no listados |
| `PESO_DEFAULT` | `1.0` | Peso para símbolos no listados |

---

## 5. Scraper de activos — `scraper_live_tradingview_v4.py`

**Cabecera del módulo:** `RADAR INTERMARKET - SCORER & PERSISTENCE ENGINE V4`,
versión V4 (2026-08-22). Ejecutable directo (`python3 scraper_live_tradingview_v4.py`).

### 5.1 Constantes de módulo

| Constante | Valor | Tipo | Descripción |
|---|---|---|---|
| `CAMPOS` | `"close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"` | `str` | Campos solicitados al scanner |
| `HEADERS` | `{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/91..."}` | `dict` | Cabecera HTTP de la petición |
| `BASE_DIR` | `"DATOS_LIVE"` | `str` | Directorio raíz de salida |
| `ESPERAS_BACKOFF_429` | `[15, 45, 120]` | `list[int]` | Esperas progresivas ante HTTP 429 (máx 180 s) |
| `PAUSA_ENFRIAMIENTO_ERROR` | `20` | `int` | Segundos de pausa tras fallo aislado |
| `MAX_FALLOS_CONSECUTIVOS` | `3` | `int` | Umbral del circuit breaker |

### 5.2 `fetch_from_scanner(symbol) -> dict | str | None`

Consulta directa al scanner por un símbolo.

- **Endpoint:** `GET https://scanner.tradingview.com/symbol`
- **Query params:** `symbol=<EXCHANGE:TICKER>`, `fields=<CAMPOS>`, `no_404=true`
- **Headers:** `HEADERS` (User-Agent de navegador)
- **Timeout:** 12 s

**Lógica:**

1. Realiza `requests.get(...)`.
2. Si `status_code == 200`: parsea JSON, e **inyecta** los campos:
   - `timestamp_utc` = `int(datetime.now(timezone.utc).timestamp())` (segundos Unix UTC)
   - `fecha_iso` = `"%Y-%m-%dT%H:%M:%SZ"` UTC
   - `simbolo` = `symbol` solicitado
   Retorna el `dict`.
3. Si `status_code == 429`: retorna el literal `"429"` (señal de rate-limit).
4. Cualquier otro caso o excepción: imprime error y retorna `None`.

| Retorno | Significado | Tratamiento en `main` |
|---|---|---|
| `dict` | Éxito, datos completos | Escribe CSV y resetea contador de fallos |
| `"429"` | Rate limit | Backoff progresivo y reintentos |
| `None` | Error/otro estado | Cuenta fallo, pausa 20 s, posible circuit breaker |

### 5.3 `sanitizar_nombre(nombre) -> str`

Normaliza el símbolo para usarlo como nombre de carpeta/archivo:

- Reemplaza `":"` por `"-"` → `NASDAQ:QQQ` ⇒ `NASDAQ-QQQ`
- Elimina `"!"` → `CME_MINI:NQ1!` ⇒ `CME_MINI-NQ1`

### 5.4 `rotar_datos(file_path, folder_name) -> None`

Implementa la **rotación de 7 días** y el archivado mensual.

1. Lee el CSV con `pandas.read_csv`; si no existe o está vacío, retorna.
2. Convierte `timestamp_utc` (int, segundos) a `timestamp_dt` (`datetime` UTC)
   con `pd.to_datetime(..., unit='s', utc=True)`.
3. Calcula `limite_7_dias = ahora_utc - timedelta(days=7)`.
4. Separa en:
   - `historico_df` = filas con `timestamp_dt <= limite`
   - `live_df` = filas con `timestamp_dt > limite`
5. Elimina la columna auxiliar `timestamp_dt`.
6. Si hay históricos: agrupa por `mes_folder = "%Y%m"`, crea
   `DATOS_LIVE/{folder}_{YYYYMM}/`, y hace **append** a
   `historico_{folder}_{YYYYMM}.csv` (con cabecera condicional: solo si el archivo
   no existe o está vacío).
7. Sobrescribe el CSV LIVE con `live_df`.
8. Cualquier excepción se captura e imprime (`Error rotación {folder}`), sin propagar.

> **Efecto secundario:** el CSV LIVE se reescribe ordenando por la partición temporal,
> pero se conserva el orden original dentro de cada subconjunto.

### 5.5 `consolidar_analisis() -> None`

Genera un único CSV con la **última fila** de cada archivo CSV de activo.

1. Crea `DATOS_LIVE/consolidados/`.
2. Recorre `DATOS_LIVE` con `os.walk`, tomando archivos `*.csv` que **no** empiecen por
   `historico_` y cuyo nombre no contenga `"consolidado"`.
3. Lee cada CSV y agrega `df.iloc[-1:]` (última fila) a una lista.
4. Concatena todo (`pd.concat`) y guarda
   `consolidados/consolidado_{YYYYMMDD_HHMMSS}.csv`.
5. Imprime ruta y número de símbolos consolidados.

Se invoca solo con el flag `--consolidate`.

### 5.6 `main() -> None`

1. **Argparse:** `--consolidate` (flag booleano) → genera consolidado al final.
2. **Lock exclusivo:** abre `/tmp/scraper_live_tradingview_v4.lock` y aplica
   `fcntl.flock(..., LOCK_EX | LOCK_NB)`. Si otra instancia lo tiene, imprime aviso y
   sale con código `0` (sin duplicar escrituras).
3. **Universo de símbolos:** recorre `CONFIG_ACTIVOS`, agrega todos los `primario` y
   `respaldo` a un `set`, y los ordena alfabéticamente.
4. **Bucle por símbolo** (`i` desde 0):
   - `folder_clean = sanitizar_nombre(symbol)`, crea `DATOS_LIVE/{folder_clean}/`.
   - `csv_file = DATOS_LIVE/{folder_clean}/{folder_clean}.csv`.
   - Llama `fetch_from_scanner(symbol)`.
   - **Si `"429"`:** itera `ESPERAS_BACKOFF_429` (15, 45, 120 s) reintentando; corta al
     primer resultado distinto de `"429"`.
   - **Si `dict`:** resetea `fallos_consecutivos = 0`; construye `DataFrame` de una fila y
     hace append al CSV (cabecera solo si el archivo no existe o está vacío); llama
     `rotar_datos(...)`.
   - **Si `None`:** incrementa `fallos_consecutivos`, imprime fallo, duerme
     `PAUSA_ENFRIAMIENTO_ERROR` (20 s). Si alcanza `MAX_FALLOS_CONSECUTIVOS` (3),
     imprime **CIRCUIT BREAKER** y `sys.exit(1)`.
   - **Pausa humana:** si no es el último símbolo, `time.sleep(random.uniform(0.4, 1.2))`.
5. Si `--consolidate`, ejecuta `consolidar_analisis()`.

**Códigos de salida:** `0` (lock ocupado / éxito), `1` (circuit breaker o excepción).

**Cálculo de duración del ciclo:** 110 símbolos × ~0.8 s de pausa + latencia de red ≈ 135 s,
compatible con un cron de `*/3` minutos, aunque el propio docstring advierte el riesgo de
solape si la red es lenta (de ahí el lock).

### 5.7 Retornos y efectos por función (resumen)

| Función | Entrada | Salida | Efecto lateral |
|---|---|---|---|
| `fetch_from_scanner` | `symbol: str` | `dict` / `"429"` / `None` | Ninguno (solo red) |
| `sanitizar_nombre` | `nombre: str` | `str` | Ninguno |
| `rotar_datos` | `file_path`, `folder_name` | `None` | Reescribe LIVE, crea históricos |
| `consolidar_analisis` | — | `None` | Crea CSV consolidado |
| `main` | `argv` | `None` (o `exit`) | Escribe CSVs, lock, consolidado |

---

## 6. Calendario económico — `calendario_tradingview_live_v4.py`

**Cabecera:** `CALENDARIO ECONOMICO TRADINGVIEW - CAPTURA RAW V4`, fecha 2026-08-31.
Objetivo explícito: **capturar raw, sin filtrar ni transformar**. La normalización se
hará en un script separado (no incluido en este proyecto).

### 6.1 Constantes

| Constante | Valor | Tipo |
|---|---|---|
| `CALENDAR_API` | `"https://economic-calendar.tradingview.com/events"` | `str` |
| `PAISES_POR_DEFECTO` | `"US,GB,DE,FR,IT,ES,CN,JP,AU,CA,CH"` | `str` |
| `HEADERS` | `{"Origin": "https://es.tradingview.com", "Referer": "https://es.tradingview.com/", "User-Agent": "...Chrome/120..."}` | `dict` |
| `BASE_DIR` | `Path("DATOS_LIVE_CALENDARIO")` | `Path` |
| `CALENDARIO_DIR` | `BASE_DIR / "calendario_economico"` | `Path` |
| `EVENTOS_RECIENTES` | `CALENDARIO_DIR / "eventos_calendario.csv"` | `Path` |
| `CHECKPOINT_FILE` | `CALENDARIO_DIR / "checkpoint.json"` | `Path` |
| `LOG_DIR` | `CALENDARIO_DIR / "logs"` | `Path` |
| `DIAS_MANTENER_DEFAULT` | `7` | `int` |
| `CAMPOS_API` | lista de 21 campos (ver §9.2) | `list[str]` |

### 6.2 `setup_logging() -> Logger`

- Crea `logs/calendario_{YYYYMMDD_HHMMSS}.log` (nombre por marca de tiempo de arranque).
- Configura `logging.basicConfig` nivel `INFO`, formato
  `'%(asctime)s - %(levelname)s - %(message)s'`, con dos handlers: `FileHandler` (UTF-8)
  y `StreamHandler` (stdout).
- Se ejecuta **a nivel de módulo**: `logger = setup_logging()`, por lo que cada ejecución
  genera un archivo de log nuevo.

### 6.3 `fetch_calendar_events(desde, hasta, paises) -> List[Dict]`

- Serializa el rango a ISO `%Y-%m-%dT%H:%M:%S.000Z`.
- **Params:** `from`, `to`, `countries`.
- **Timeout:** 15 s.
- Si `status_code == 200` y `data['status'] == 'ok'`: retorna `data['result']` (lista de
  eventos). Si el status no es `ok`, warning y `[]`.
- Si `status_code == 429`: log de rate limit, `time.sleep(30)` y `[]`.
- Otro estado: error HTTP y `[]`.
- Maneja `Timeout`, `ConnectionError` y excepción genérica, retornando `[]`.

### 6.4 `evento_a_dict(evento_raw) -> Dict`

- Itera `CAMPOS_API`; toma `evento_raw.get(campo)` y convierte `None` → `''`.
- Agrega `timestamp_captura = datetime.now(timezone.utc).isoformat()`.
- **No** transforma ni normaliza ningún valor de la API.

### 6.5 `asegurar_directorios() -> None`

Crea `CALENDARIO_DIR` y `LOG_DIR` con `mkdir(parents=True, exist_ok=True)`.

### 6.6 `cargar_checkpoint() -> Dict`

- Si `checkpoint.json` existe, lo parsea y retorna; ante error, warning.
- Si no existe, retorna el checkpoint por defecto:

```python
{
    'ultimo_timestamp': 0,
    'ultima_fecha': '',
    'eventos_acumulados': 0,
    'eventos_encontrados': 0,
    'fecha_ultima_revision': ''
}
```

### 6.7 `guardar_checkpoint(ultimo_timestamp, eventos_acumulados, eventos_encontrados=0)`

Escribe `checkpoint.json` con:

| Clave | Tipo | Cálculo |
|---|---|---|
| `ultimo_timestamp` | `int` | Recibido |
| `ultima_fecha` | `str` | `datetime.fromtimestamp(ts, utc).isoformat()` |
| `eventos_acumulados` | `int` | Recibido |
| `eventos_encontrados` | `int` | Recibido |
| `fecha_ultima_revision` | `str` | `datetime.now(utc).isoformat()` |

### 6.8 `rotar_eventos_recientes(force_rotate=False, dias_mantener=7) -> int`

1. Si no existe el CSV o está vacío, retorna `0`.
2. Parsea `date` a `_fecha_dt` (`pd.to_datetime(..., utc=True, errors='coerce')`).
3. `limite = ahora_utc - dias_mantener`; separa recientes (`>=`) e históricos (`<`).
4. **Modo force:** si no hay históricos pero hay recientes, amplía el límite a
   `dias_mantener * 2` para forzar el movimiento.
5. Si no hay históricos, retorna `0` sin tocar el CSV.
6. Reescribe el CSV principal solo con recientes (sin columna auxiliar).
7. Agrupa históricos por `%Y-%m`; crea `CALENDARIO_DIR/YYYY-MM/` y
   `historico_YYYYMM.csv`. Si ya existe, concatena y aplica
   `drop_duplicates(subset=['id'], keep='last')`.
8. Retorna el número de eventos históricos movidos.

### 6.9 `guardar_eventos(eventos, auto_rotate=True, dias_mantener=7) -> None`

1. Si la lista está vacía, retorna.
2. Crea `DataFrame`, deduplica por `id` (`keep='last'`).
3. Si existe el CSV principal, lo lee, concatena, vuelve a deduplicar por `id` y
   sobrescribe. Si no existe o está vacío, escribe directo.
4. Si `auto_rotate`, llama `rotar_eventos_recientes(dias_mantener=...)`.

> Captura `pd.errors.EmptyDataError` cuando el CSV existe pero está vacío.

### 6.10 `mostrar_estado() -> None`

Imprime estado del archivo principal: ruta, total de eventos, columnas, y distribución
por `importance` si la columna existe. Se invoca con `--status`.

### 6.11 `reset_mes() -> None`

- Calcula `mes_actual = "%Y-%m"`, `anio`, `mes`.
- Borra (`unlink`): `eventos_calendario.csv`, el `historico_YYYYMM.csv` del mes actual y
  `checkpoint.json` (solo si existen).
- Loguea los archivos eliminados. Se invoca con `--reset-month`.

### 6.12 `capturar_eventos(...) -> Tuple[int, int]`

Firma:
```python
capturar_eventos(paises=PAISES_POR_DEFECTO, dias_adelante=2, incluir_pasado=1,
                 auto_rotate=True, dias_mantener=7) -> Tuple[int, int]
```

1. `ahora = now(utc)`; `desde = ahora - incluir_pasado`; `hasta = ahora + dias_adelante`.
2. `fetch_calendar_events(desde, hasta, paises)`.
3. Si no hay eventos: warning, `guardar_checkpoint(0,0,0)` y retorna `(0, 0)`.
4. Convierte a dicts (`evento_a_dict`), llama `guardar_eventos(...)`.
5. Calcula `max_ts` como el mayor `date` de los eventos (ISO → timestamp). Ante error,
   `max_ts = 0`.
6. `guardar_checkpoint(max_ts, len(eventos_para_guardar), len(eventos_raw))`.
7. Retorna `(nuevos_guardados, total_encontrados)`.

### 6.13 `main() -> None`

**Argumentos CLI:**

| Flag | Tipo | Default | Descripción |
|---|---|---|---|
| `--paises` | `str` | `PAISES_POR_DEFECTO` | Países separados por coma |
| `--dias` | `int` | `2` | Días hacia adelante (acotado a `min(args.dias, 2)`) |
| `--pasado` | `int` | `1` | Días hacia atrás |
| `--no-rotate` | flag | `False` | Desactiva rotación automática |
| `--rotate-now` | flag | `False` | Fuerza rotación manual |
| `--dias-mantener` | `int` | `7` | Días a mantener en archivo principal |
| `--status` | flag | `False` | Muestra estado y checkpoint |
| `--reset-month` | flag | `False` | Borra histórico del mes actual |

**Orden de ejecución:** `asegurar_directorios()` → si `--status` → si `--reset-month` →
si `--rotate-now` → `capturar_eventos(...)`. El acotado `min(args.dias, 2)` limita la
ventana futura a 2 días aunque se pase un valor mayor.

---

## 7. Monitor de procesos — `monitor_tradingview_live_v3.py`

**Cabecera:** `MONITOR DE PROCESOS TRADINGVIEW - SCRAPER Y CALENDARIO V2` (nombre de
archivo V3). Ejecución asíncrona con `asyncio.run(main())`.

### 7.1 Configuración y validaciones de arranque

- Carga `.env` con `python-dotenv` (primero `Path(__file__).parent/'.env'`, si no
  `load_dotenv()`).
- Importa `TelegramNotificador` desde `notificador_telegram` (**módulo ausente**, ver §14).
  Si falla, imprime error y `sys.exit(1)`.
- Lee `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `SERVER_ID` (default `"WZAUMA"`).
- Si faltan token o chat id → `sys.exit(1)`. Convierte chat id a `int` si es posible.

**Constantes:**

| Constante | Valor | Significado |
|---|---|---|
| `MAX_CICLOS_ESPERAR` | `2` | Umbral de ALERTA (ciclos perdidos > 2) |
| `CICLO_ALERTA_WARNING` | `1.5` | Umbral de WARNING |
| `TIEMPO_ESPERA_MIN_EVITAR_SPAM` | `60` | Segundos mínimos entre alertas (docstring dice 30 min) |
| `BASE_DIR` | `Path("DATOS_LIVE")` | Directorio de datos |
| `CALENDARIO_LOG_DIR` | `BASE_DIR/"calendario_economico"/"logs"` | Ruta de logs (desalineada, ver §14) |

### 7.2 `ARCHIVOS_A_MONITOREAR`

Lista de 4 configuraciones (dicts):

| Ruta monitoreada | Intervalo | Tipo | Campo timestamp | Cron |
|---|---|---|---|---|
| `DATOS_LIVE/NASDAQ-QQQ/NASDAQ-QQQ.csv` | 5 min | activo | `timestamp_utc` | `*/5` |
| `DATOS_LIVE/OANDA-XAUUSD/OANDA-XAUUSD.csv` | 5 min | activo | `timestamp_utc` | `*/5` |
| `DATOS_LIVE/OANDA-EURUSD/OANDA-EURUSD.csv` | 5 min | activo | `timestamp_utc` | `*/5` |
| `DATOS_LIVE/calendario_economico/checkpoint.json` | 15 min | calendario | `fecha_ultima_revision` | `*/15` |

La entrada de calendario incluye `'es_json': True` y `'log_dir'`. El monitor **no** usa el
path real del calendario V4 (`DATOS_LIVE_CALENDARIO/...`), lo que produce la alerta
"Archivo no encontrado" de forma permanente (ver §14).

### 7.3 Clase `MonitorTradingView`

#### `__init__`

- Instancia `TelegramNotificador(token, chat_id)`.
- `self.alertas_previas = self.cargar_alertas_previas()`.
- `self.archivo_estado = Path(__file__).parent / 'ultima_alerta_tradingview.json'`.

#### `cargar_alertas_previas() -> Dict[str,str]`

Lee `alertas_tradingview_previas.txt`; cada línea tiene formato
`proceso|...|timestamp`; devuelve `{proceso: timestamp}`. Tolerante a líneas vacías.

#### `debe_enviar_alerta_agrupada() -> bool`

- Si no existe `ultima_alerta_tradingview.json` → `True`.
- Lee `fecha` y calcula `diferencia = now() - fecha`.
- Si `diferencia.total_seconds() < TIEMPO_ESPERA_MIN_EVITAR_SPAM` → `False` (evita spam).
- Cualquier excepción → `True`.

> Con el valor real `60`, sólo bloquea alertas dentro del mismo minuto. El comentario del
> código sugiere que la intención original era 30 minutos (`1800`).

#### `guardar_estado_alerta(alertas_data) -> None`

Escribe `ultima_alerta_tradingview.json` con `fecha` (ISO), `total_alertas` y lista
`procesos` (`nombre` de cada alerta).

#### `obtener_ultimas_lineas_log(log_dir, n_lineas=50) -> (str|None, str)`

- Valida existencia de `log_dir`.
- Busca `calendario_*.log` ordenados inversamente y toma el más reciente.
- Retorna `(ruta_log, ultimas_n_lineas)` o `(None, mensaje_error)`.

#### `obtener_ultimo_timestamp(archivo, tipo='activo', campo_timestamp=None)`

Retorna tupla `(ultimo_timestamp, fecha_str, error, campo_usado)`.

1. Si el archivo no existe → `(None, None, "Archivo no encontrado", None)`.
2. Si `tipo == 'calendario'` y el nombre es `checkpoint.json` delega a
   `obtener_ultimo_timestamp_checkpoint`.
3. Lee el CSV con pandas; si está vacío → error.
4. Selección de campo:
   - `calendario`: `timestamp_captura` (obligatorio).
   - `activo`: `campo_timestamp` o `timestamp_utc`; si no, fallback a `timestamp`.
5. Convierte el valor a `float` si es posible.
6. Busca fecha legible en `fecha_humana`, `datetime` o `fecha_iso`.
7. Si es `activo` y el timestamp está a más de 1 h en el futuro → error.
8. Excepción → error como string.

#### `obtener_ultimo_timestamp_checkpoint(archivo)`

Lee `checkpoint.json`, extrae `fecha_ultima_revision`, la convierte a timestamp y
`fecha_str` (`%Y-%m-%d %H:%M:%S`). Maneja `JSONDecodeError` y excepción genérica.
Retorna también `eventos_encontrados`/`eventos_acumulados` internamente (no en la tupla).

#### `enviar_alerta_agrupada(alertas_data, log_calendario=None) -> None` (async)

- Respeta el anti-spam (`debe_enviar_alerta_agrupada`).
- Construye un mensaje Markdown con:
  - Cabecera `🚨 [SERVER_ID] PROCESOS LIVE CAÍDOS | [n]`.
  - Bloque `ACTIVOS` (nombre, proceso, última fecha, minutos, ciclos, error).
  - Bloque `CALENDARIO` (nombre, proceso, última ejecución, eventos, último evento).
  - Últimas 1000 caracteres del log del calendario en bloque de código.
  - Acciones recomendadas.
- Envía con `await self.notificador.enviar(mensaje, titulo=...)` y guarda estado.

#### `verificar_procesos() -> List[Dict]` (async)

Bucle sobre `ARCHIVOS_A_MONITOREAR`; para cada uno:

1. Si el archivo no existe → agrega alerta con `error='ARCHIVO NO ENCONTRADO'`.
2. Obtiene el timestamp; si hay error → agrega alerta.
3. Convierte a `datetime` UTC (por timestamp numérico o ISO).
4. Calcula `diferencia = hora_actual - ultima_fecha`, `minutos` y
   `ciclos_perdidos = minutos / intervalo`.
5. Clasifica:
   - `ciclos_perdidos > 2` → `🔴 ALERTA` (agrega a `alertas_data`; captura log del
     calendario si aplica).
   - `> 1.5` → `🟡 ADVERTENCIA`.
   - resto → `🟢 OK`.
6. Muestra resumen (`mostrar_resumen`), envía alerta agrupada si hay alertas y guarda log
   de ejecución.

#### `mostrar_resumen(estados, alertas_data, warnings) -> None`

Imprime tabla de estados agrupada por tipo (activos / calendario) con emoji, nombre,
estado, fecha y diferencia; luego advertencias y alertas críticas.

#### `guardar_log_ejecucion(alertas_data) -> None`

Anexa a `logs_ejecucion/monitor_tradingview_{YYYYMMDD}.log` una línea por ejecución con
las alertas o `OK`.

### 7.4 `main()` (async)

Instancia `MonitorTradingView`, ejecuta `verificar_procesos()` y sale con:
`0` sin alertas, `1` con alertas, `2` ante excepción (con `traceback`).

---

## 8. Scripts de ejecución (Shell)

Ambos scripts son *wrappers* robustos que preparan el entorno y ejecutan su Python.
Cargan `./.env` con `set -a; source; set +a`, y usan `PROJECT_DIR` y `SERVER_ID`.

### 8.1 `run_scraper_tradingview.sh`

**Variables:** `PROJECT_DIR` (default `/home/wilson/CODE_MAIN/app_backup_nasdaq`),
`SCRAPER_SCRIPT="$PROJECT_DIR/scraper_live_tradingview_v4.py"`,
`VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"`,
`LOG_DIR="$PROJECT_DIR/logs_ejecucion"`, `EXEC_LOG=scraper_{timestamp}.log`.

| Función | Descripción |
|---|---|
| `log()` | Escribe a stdout y al log de ejecución con fecha |
| `get_python_cmd()` | Devuelve venv si existe, si no `/usr/bin/python3`; `1` si no hay |
| `check_directories()` | Valida `PROJECT_DIR`, script y Python |
| `load_env_vars()` | Carga `$PROJECT_DIR/.env` |
| `check_directorios_datos()` | Crea `DATOS_LIVE/{NASDAQ-QQQ,OANDA-XAUUSD,OANDA-EURUSD}` |
| `run_scraper()` | `cd` al proyecto y ejecuta el scraper (append al log), captura código |
| `check_resultados()` | Verifica 3 CSVs críticos (>1 línea) y cuenta CSVs totales |
| `cleanup_old_logs()` | Borra `scraper_*.log` con más de 2 días |
| `main()` | Orquesta todo y `exit $EXIT_CODE` |

En el log se declara "118 activos", dato descriptivo (el universo real es 110 símbolos
únicos).

### 8.2 `run_calendario_tradingview.sh`

Estructura análoga, con `CALENDARIO_SCRIPT="$PROJECT_DIR/calendario_tradingview_live_v4.py"`
y `EXEC_LOG=calendario_{timestamp}.log`.

| Función | Descripción |
|---|---|
| `check_directorio_calendario()` | Crea `DATOS_LIVE/calendario_economico` y `.../logs` |
| `run_calendario()` | Ejecuta el calendario y captura código |
| `check_resultados()` | Verifica `eventos_calendario.csv` (nº eventos) y `checkpoint.json` |
| `cleanup_old_logs()` | Borra logs de ejecución y de calendario > 2 días |

> El shell referencia `DATOS_LIVE/calendario_economico`, pero el script Python V4 escribe
> en `DATOS_LIVE_CALENDARIO/calendario_economico` (inconsistencia, ver §14).

---

## 9. Tipos de datos y esquemas

### 9.1 CSV de activos — `DATOS_LIVE/{SYMBOL}/{SYMBOL}.csv`

Las columnas se derivan del `dict` que devuelve el scanner más los 3 campos inyectados.
El orden real observado en el archivo es alfabético tras el *round-trip* por pandas.

**Cabecera real observada:**

```
ADX,BBPower,CCI20,Perf.W,Pivot.M.Camarilla.R3,RSI,change,close,volume,timestamp_utc,fecha_iso,simbolo
```

**Tabla de campos:**

| Columna | Tipo (Python/Pandas) | Origen | Descripción |
|---|---|---|---|
| `ADX` | `float` | Scanner | Average Directional Index |
| `BBPower` | `float` | Scanner | Bollinger Bands Power |
| `CCI20` | `float` | Scanner | Commodity Channel Index (20) |
| `Perf.W` | `float` | Scanner | Rendimiento semanal (%) |
| `Pivot.M.Camarilla.R3` | `float` | Scanner | Pivote Camarilla R3 |
| `RSI` | `float` | Scanner | Relative Strength Index |
| `change` | `float` | Scanner | Cambio porcentual |
| `close` | `float` | Scanner | Precio de cierre |
| `volume` | `int` | Scanner | Volumen |
| `timestamp_utc` | `int` (segundos Unix UTC) | Inyectado (scraper) | Momento de captura |
| `fecha_iso` | `str` (`%Y-%m-%dT%H:%M:%SZ`) | Inyectado (scraper) | Fecha legible UTC |
| `simbolo` | `str` (`EXCHANGE:TICKER`) | Inyectado (scraper) | Símbolo solicitado |

**Ejemplo real:**

```csv
ADX,BBPower,CCI20,Perf.W,Pivot.M.Camarilla.R3,RSI,change,close,volume,timestamp_utc,fecha_iso,simbolo
9.093774192295202,2.141676372458278,-4.260033047897424,-0.6207035567078428,730.169,50.76704987100507,0.8734425489282959,714.88,26646503,1789323133,2026-09-13T18:12:13Z,NASDAQ:QQQ
```

### 9.2 CSV de calendario — `eventos_calendario.csv`

**21 campos de `CAMPOS_API` + `timestamp_captura`:**

| Columna | Tipo esperado | Descripción / contenido |
|---|---|---|
| `id` | `int` (string en CSV) | Identificador único del evento (clave de dedup) |
| `title` | `str` | Título del evento |
| `country` | `str` (ISO-2) | País (ej. `US`, `JP`) |
| `indicator` | `str` | Indicador macroeconómico |
| `ticker` | `str` | Ticker del indicador (ej. `ECONOMICS:AUINTR`) |
| `comment` | `str` | Descripción larga |
| `category` | `str` | Categoría (ej. `mny`, `bsnss`) |
| `period` | `str` | Periodo de referencia (ej. `Jul`) |
| `referenceDate` | `str` ISO | Fecha de referencia del dato |
| `source` | `str` | Fuente oficial |
| `source_url` | `str` | URL de la fuente |
| `actual` | `str`/num | Valor actual publicado |
| `previous` | `str`/num | Valor previo |
| `forecast` | `str`/num | Valor esperado |
| `actualRaw` | `str`/num | Valor actual raw |
| `previousRaw` | `str`/num | Valor previo raw |
| `forecastRaw` | `str`/num | Valor esperado raw |
| `currency` | `str` | Moneda (ej. `USD`, `JPY`) |
| `unit` | `str` | Unidad (ej. `%`) |
| `importance` | `int` | Importancia (`-1`, `0`, `1`, `2`, `3`) |
| `date` | `str` ISO | Fecha/hora del evento |
| `timestamp_captura` | `str` ISO | Momento de captura (añadido por el script) |

**Ejemplo real (fragmento):**

```csv
421311,RBA Hunter Speech,AU,Interest Rate,ECONOMICS:AUINTR,"...",mny,,,Reserve Bank,http://www.rba.gov.au/,,,,,,,AUD,,0,2026-09-14T02:30:00.000Z,2026-09-13T18:10:47.976743+00:00
```

### 9.3 `checkpoint.json`

| Clave | Tipo | Descripción |
|---|---|---|
| `ultimo_timestamp` | `int` | Mayor `date` de los eventos (segundos Unix) |
| `ultima_fecha` | `str` ISO | Fecha legible de ese timestamp |
| `eventos_acumulados` | `int` | Eventos guardados en la última captura |
| `eventos_encontrados` | `int` | Eventos devueltos por la API |
| `fecha_ultima_revision` | `str` ISO | Momento de la última ejecución |

**Ejemplo real:**

```json
{
  "ultimo_timestamp": 1789491600,
  "ultima_fecha": "2026-09-15T17:00:00+00:00",
  "eventos_acumulados": 66,
  "eventos_encontrados": 66,
  "fecha_ultima_revision": "2026-09-13T18:10:48.017528+00:00"
}
```

### 9.4 CSV consolidado — `DATOS_LIVE/consolidados/consolidado_{ts}.csv`

Concatenación de la última fila de cada CSV de activo; conserva las mismas columnas que
§9.1 y añade `symbol`/ruta según el `DataFrame` resultante.

### 9.5 JSON de estado del monitor

| Archivo | Contenido |
|---|---|
| `ultima_alerta_tradingview.json` | `fecha`, `total_alertas`, `procesos[]` |
| `alertas_tradingview_previas.txt` | Líneas `proceso|timestamp` |

---

## 10. Fuentes de datos (endpoints)

| Uso | Método | URL | Timeout | Formato |
|---|---|---|---|---|
| Scraper de activos | `GET` | `https://scanner.tradingview.com/symbol` | 12 s | JSON |
| Calendario económico | `GET` | `https://economic-calendar.tradingview.com/events` | 15 s | JSON |
| Notificación (monitor) | `POST` | Telegram Bot API (vía `notificador_telegram`, ausente) | — | JSON |

**Params del scanner:** `symbol`, `fields`, `no_404=true`.

**Params del calendario:** `from`, `to`, `countries` (fechas ISO `...000Z`).

**Headers del scraper:** solo `User-Agent` (Chrome 91 / Windows).

**Headers del calendario:** `Origin`, `Referer` (`https://es.tradingview.com/`) y
`User-Agent` (Chrome 120 / Linux).

**Consideraciones de acceso:** ambas APIs son públicas y no requieren autenticación; el
scraper implementa mitigación de rate-limiting (HTTP 429) mediante backoff y *circuit
breaker*.

---

## 11. Persistencia y rotación de datos

### 11.1 Estrategia

| Dataset | Archivo "caliente" | Retención | Archivo frío |
|---|---|---|---|
| Activos | `DATOS_LIVE/{SYM}/{SYM}.csv` | 7 días | `DATOS_LIVE/{SYM}_{YYYYMM}/historico_{SYM}_{YYYYMM}.csv` |
| Calendario | `DATOS_LIVE_CALENDARIO/.../eventos_calendario.csv` | 7 días | `.../{YYYY-MM}/historico_{YYYYMM}.csv` |
| Consolidados | `DATOS_LIVE/consolidados/consolidado_{ts}.csv` | Sin rotación | — |
| Logs de ejecución | `logs_ejecucion/*.log` | 2 días (borrado por shell) | — |
| Logs de calendario | `.../calendario_economico/logs/*.log` | 2 días (borrado por shell) | — |

### 11.2 Escritura incremental

- **Activos:** `DataFrame.to_csv(mode='a', header=escribir_header)`, donde
  `escribir_header = not exists(file) or size(file) == 0`.
- **Calendario:** lectura + concatenación + `drop_duplicates(subset='id', keep='last')` +
  sobrescritura completa. El histórico también deduplica por `id`.

### 11.3 Exclusión mutua

El scraper usa `/tmp/scraper_live_tradingview_v4.lock` con `fcntl.flock(LOCK_EX |
LOCK_NB)`. El archivo de lock se abre en modo `"w"` al inicio y nunca se desbloquea
explícitamente (se libera al terminar el proceso).

---

## 12. Programación cron

### 12.1 Horarios

| Día | Rango horario | Scraper (`*/3`) | Calendario (`*/15`) | Monitor (`*/5`) |
|---|---|---|---|---|
| Lunes a Jueves | 00:00–23:59 | Activo | Activo | Activo |
| Viernes | 00:00–16:59 | Activo | Activo | Activo |
| Viernes | 17:00–23:59 | Inactivo | Inactivo | Inactivo |
| Sábado / Domingo | Todo el día | Inactivo | Inactivo | Inactivo |

### 12.2 Comandos de referencia (`readme_crontab.md`)

```bash
# Scraper (cada 3 min) - Lun-Jue
*/3 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh
# Scraper (cada 3 min) - Vie hasta 16:59
*/3 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh

# Calendario (cada 15 min) - Lun-Jue
*/15 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh
# Calendario (cada 15 min) - Vie hasta 16:59
*/15 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh

# Monitor (cada 5 min) - Lun-Jue
*/5 0-23 * * 1-4 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1
# Monitor (cada 5 min) - Vie hasta 16:59
*/5 0-16 * * 5 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1
```

El `readme_crontab.md` documenta además una réplica de estas líneas para el servidor
`/home/wilson/BACKUP_DAILY/app_backup_nasdaq` (servidor `wz`).

**Campo cron, explicación:**

| Campo | Valor | Significado |
|---|---|---|
| minuto | `*/3` / `*/15` / `*/5` | Cada 3 / 15 / 5 minutos |
| hora | `0-23` / `0-16` | Rango de horas |
| día mes / mes | `*` | Todos |
| día semana | `1-4` / `5` | Lunes–Jueves / Viernes |

---

## 13. Dependencias y entorno

### 13.1 `requirements.txt`

| Dependencia | Uso |
|---|---|
| `requests` | Llamadas HTTP al scanner y al calendario; notificación externa |
| `pandas` | Lectura/escritura CSV, rotación, deduplicación, consolidación |
| `tabulate` | Utilidad de tablas (referenciada, no usada explícitamente en los scripts) |
| `python-telegram-bot==22.6` | Notificaciones Telegram (consumida por el módulo ausente) |
| `python-dotenv` | Carga de variables desde `.env` |

> El archivo incluye el comentario `# sudo apt-get install expect`, lo que sugiere el uso
> previo de scripts `expect` (no presentes).

### 13.2 Variables de entorno (`.env` / `.env_demo`)

| Variable | Ejemplo/Default | Consumida por |
|---|---|---|
| `TELEGRAM_TOKEN` | `"TU_API_TOKEN"` | Monitor / notificador |
| `TELEGRAM_CHAT_ID` | `"TU_CHAT_ID"` | Monitor / notificador |
| `PROJECT_DIR` | `/home/wilson/CODE_MAIN/app_backup_nasdaq` | Shell scripts |
| `SERVER_ID` | `"WZAUMA"` / `"WZ-PC"` | Shell scripts y monitor |

---

## 14. Observaciones e inconsistencias detectadas

> Sección de valor añadido: puntos que conviene revisar durante el mantenimiento.

1. **Módulo `notificador_telegram.py` ausente.**
   `monitor_tradingview_live_v3.py:47` importa `from notificador_telegram import
   TelegramNotificador`, pero el archivo no existe en el repositorio. En consecuencia, el
   monitor termina con `sys.exit(1)` al arrancar (`ImportError`). La notificación por
   Telegram no puede funcionar tal cual está el árbol de archivos.

2. **Ruta del calendario desalineada.**
   El monitor vigila `DATOS_LIVE/calendario_economico/checkpoint.json` (`monitor...py:111`),
   pero el calendario V4 escribe en `DATOS_LIVE_CALENDARIO/calendario_economico/...`
   (`calendario...py:76-80`). El monitor reportará siempre "ARCHIVO NO ENCONTRADO" para el
   calendario. Los shell scripts también usan la ruta antigua `DATOS_LIVE/calendario_economico`.

3. **`readme.md` desactualizado respecto al código.**
   Describe `scraper_live_tradingview_v3.py` y `calendario_tradingview_live_v3.py`, y campos
   del calendario normalizados (`fecha_humana`, `titulo`, `pais`, `importancia`,
   `sorpresa`, etc.) que **no** existen en la V4 (que guarda campos raw como `title`,
   `country`, `importance`, sin `sorpresa`). El README no refleja la captura raw.

4. **Pausas del scraper modificadas sin actualizar docstrings.**
   La V4 usa `random.uniform(0.4, 1.2)` s, pero el `readme.md` afirma 2.5–5.0 s. Además el
   README dice que el scraper corre "cada 5 minutos" mientras el cron real es cada 3.

5. **Intervalo del monitor vs. cron del scraper.**
   El monitor asume un ciclo de 5 min para los activos (`intervalo_minutos=5`), mientras el
   cron los captura cada 3 min. Esto sesga el cálculo de `ciclos_perdidos` (los datos
   parecerán más frescos de lo que la fórmula sugiere o, por el contrario, el WARNING a
   1.5 ciclos equivale a 7.5 min con 5, cuando el ciclo real es 3).

6. **Anti-spam del monitor.**
   `TIEMPO_ESPERA_MIN_EVITAR_SPAM = 60` segundos, pero el comentario y el README afirman
   30 minutos (`1800`). Posible regresión de valor.

7. **Prefijo de directorio de datos.**
   El docstring del scraper menciona `DATOS_LIVE_2/{SYMBOL}` y archivos
   `DATOS_LIVE_2/{SYMBOL}_{YYYYMM}/historico_{SYMBOL}_{YYYYMM}.csv`, pero la constante real
   `BASE_DIR` es `"DATOS_LIVE"`. Los ejemplos del docstring están obsoletos.

8. **Conteo de activos inconsistente.**
   El shell del scraper imprime "118 activos"; el `readme.md` dice "34+ activos" y
   "113 primarios+respaldos" en el docstring del scraper. El conteo verificado es **110
   símbolos únicos** (93 claves).

9. **`fetch_from_scanner` maneja 429 solo vía valor de retorno.**
   Cualquier `status_code` distinto de 200/429 (500, 403, etc.) devuelve `None` y se trata
   como fallo genérico, sin diferenciar de errores de red. No hay reintento específico para
   5xx.

10. **`capturar_eventos` acota silenciosamente la ventana.**
    `main` pasa `dias_adelante=min(args.dias, 2)`, por lo que valores mayores de `--dias` se
    ignoran sin aviso al usuario.

11. **`timestamp_captura` duplica el momento de captura.**
    `evento_a_dict` asigna `timestamp_captura` **por evento**, de modo que todos los
    eventos del mismo lote comparten un timestamp con diferencias de microsegundos, lo que
    no constituye un identificador de lote estable.

12. **Lock del scraper nunca elimina el archivo `.lock`.**
    Se abre en `"w"` y no se hace `unlink`; no es un problema funcional (el `flock` se
    libera al cerrar el proceso) pero puede confundir a operadores.

13. **Manejo de `None` en `evento_a_dict`.**
    Convierte `None` a `''`, lo que impide distinguir "sin dato" de "dato vacío" en el CSV
    raw. Es una decisión de diseño documentada (raw), pero relevante para la posterior
    normalización.

14. **`tabulate` declarado pero no usado** en los tres scripts principales; probable
    dependencia heredada.

15. **Columna `symbol` en consolidados.** El módulo lee `df.iloc[-1:]` de cada CSV; dado
    que el CSV no incluye `symbol` como columna separada (solo `simbolo`), el consolidado
    no agrega el identificador de archivo, por lo que podría resultar difícil de trazar si
    `simbolo` faltara.

---

## 15. Apéndices (muestras reales)

### 15.1 CSV de activo (NASDAQ-QQQ)

```csv
ADX,BBPower,CCI20,Perf.W,Pivot.M.Camarilla.R3,RSI,change,close,volume,timestamp_utc,fecha_iso,simbolo
9.093774192295202,2.141676372458278,-4.260033047897424,-0.6207035567078428,730.169,50.76704987100507,0.8734425489282959,714.88,26646503,1789323133,2026-09-13T18:12:13Z,NASDAQ:QQQ
```

### 15.2 CSV de calendario (2 primeras filas de datos)

```csv
id,title,country,indicator,ticker,comment,category,period,referenceDate,source,source_url,actual,previous,forecast,actualRaw,previousRaw,forecastRaw,currency,unit,importance,date,timestamp_captura
421311,RBA Hunter Speech,AU,Interest Rate,ECONOMICS:AUINTR,"In Australia...",mny,,,Reserve Bank,http://www.rba.gov.au/,,,,,,,AUD,,0,2026-09-14T02:30:00.000Z,2026-09-13T18:10:47.976743+00:00
401456,Capacity Utilization MoM,JP,Capacity Utilization,ECONOMICS:JPCU,"In Japan...",bsnss,Jul,2026-07-31T00:00:00Z,Ministry of Economy Trade and Industry (METI),https://www.meti.go.jp,,4.1,,,4.1,,JPY,%,-1,2026-09-14T04:30:00.000Z,2026-09-13T18:10:47.976806+00:00
```

### 15.3 `checkpoint.json`

```json
{
  "ultimo_timestamp": 1789491600,
  "ultima_fecha": "2026-09-15T17:00:00+00:00",
  "eventos_acumulados": 66,
  "eventos_encontrados": 66,
  "fecha_ultima_revision": "2026-09-13T18:10:48.017528+00:00"
}
```

### 15.4 Log del calendario (ejecución 2026-09-13)

```
2026-09-13 13:10:47,462 - INFO - Rango: 2026-09-12 18:10 a 2026-09-15 18:10
2026-09-13 13:10:47,462 - INFO - Paises: US,GB,DE,FR,IT,ES,CN,JP,AU,CA,CH
2026-09-13 13:10:47,974 - INFO - Eventos obtenidos de API: 66
2026-09-13 13:10:47,978 - INFO - Eventos a guardar: 66 (sin filtro de importancia)
2026-09-13 13:10:47,998 - INFO - Archivo principal creado: 66 eventos
2026-09-13 13:10:48,016 - INFO - No hay eventos antiguos para rotar (todos dentro de ultimos 7 dias)
2026-09-13 13:10:48,017 - INFO - Checkpoint guardado - Revision: 2026-09-13 18:10:48 UTC, Encontrados: 66, Nuevos: 66
2026-09-13 13:10:48,017 - INFO - Captura completada: 66 eventos nuevos de 66 encontrados
```

### 15.5 Inventario de archivos fuente

| Archivo | Líneas | Descripción |
|---|---|---|
| `config.py` | 186 | Universo de activos y metadatos |
| `scraper_live_tradingview_v4.py` | 284 | Scraper de activos V4 |
| `calendario_tradingview_live_v4.py` | 498 | Calendario económico V4 |
| `monitor_tradingview_live_v3.py` | 663 | Monitor de procesos V3 |
| `run_scraper_tradingview.sh` | 229 | Wrapper shell del scraper |
| `run_calendario_tradingview.sh` | 225 | Wrapper shell del calendario |
| `readme.md` | 461 | Documentación del autor (desactualizada) |
| `readme_crontab.md` | 47 | Referencia de crontab |
| `requirements.txt` | 6 | Dependencias |

---

*Fin del informe — `documentacion_scrapper_2026-09-13.md`*
