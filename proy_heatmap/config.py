import os
import pytz
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv('.env')

# =============================================================================
# VERSIONES Y APLICACIÓN
# =============================================================================
VERSION = "1.0.2"
TIMEZONE = pytz.timezone("America/Lima")

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================
# Ruta donde se guardarán los logs (por defecto ./LOGS)
FILE_PATH_LOG = os.getenv('FILE_PATH_LOG', './LOGS')
RETRANSMISOR_ID = os.getenv('RETRANSMISOR_ID', '101')

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================
# El logger se obtiene desde utils.config_logging para mantener la separación
# Aquí solo definimos el nombre de la aplicación para el log
APP_NAME = "heatmap_stock"

# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================
try:
    PG_HOST = os.getenv('BD_HEATMAP_HOST')
    PG_PORT = int(os.getenv('BD_HEATMAP_PORT'))
    PG_DATABASE = os.getenv('BD_HEATMAP_DATABASE')
    PG_USER = os.getenv('BD_HEATMAP_USER')
    PG_PASSWORD = os.getenv('BD_HEATMAP_PASSWORD')

    # Validación básica
    if not all([PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD]):
        raise ValueError("Faltan variables de entorno para la conexión a PostgreSQL")

except KeyError as e:
    print(f"Falta la clave {e} en las variables de entorno")
    os._exit(1)
except ValueError as e:
    print(f"Error en variables de entorno: {e}")
    os._exit(1)


# =============================================================================
# CONFIGURACIÓN DEL SCRAPER HEATMAP
# =============================================================================

# Endpoint del heatmap (mismo que en la captura)
HEATMAP_URL = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"

# Headers de la solicitud (simulan un navegador)
HEATMAP_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://es.tradingview.com",
    "referer": "https://es.tradingview.com/heatmap/stock/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}

# Columnas del endpoint (las que el scanner acepta y devuelve en d[])
HEATMAP_COLUMNS = [
    "typespecs", "change", "change_abs",
    "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y", "Perf.YTD",
    "Volatility.D", "price_52_week_high", "price_52_week_low",
    "market_cap_basic", "average_volume_30d_calc", "average_volume_10d_calc",
    "volume", "total_shares_outstanding", "total_shares_outstanding_fundamental",
    "number_of_employees", "earnings_per_share_basic_ttm",
    "revenue_per_employee_ttm", "gross_profit_1Y_growth_fq",
    "sector", "logoid", "close", "pricescale",
    "name", "update_mode", "currency",
]

# Payload explícito (requerido; sin columns el endpoint devuelve d[] vacío)
HEATMAP_BODY = {
    "columns": HEATMAP_COLUMNS,
    "markets": ["america"],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
}

# Cantidad máxima de símbolos a insertar (top por market cap)
HEATMAP_MAX_SYMBOLS = 1000

# Timeout de la solicitud (segundos)
HEATMAP_TIMEOUT = 30


# # --- Fallback (deshabilitado, mantener para referencia) ---
# # Si es True, se ignora el API y se usa solo el archivo local.
# # Útil para testing cuando el mercado está cerrado.
# HEATMAP_USE_FALLBACK_ONLY = os.getenv(
#     'HEATMAP_USE_FALLBACK_ONLY', 'false'
# ).strip().lower() in ('1', 'true', 'yes', 'on')
#
# # Ruta del JSON de respaldo (relativa a la raíz del proyecto o absoluta)
# HEATMAP_FALLBACK_PATH = os.getenv(
#     'HEATMAP_FALLBACK_PATH',
#     'db/heatmap_symbols_v2_raw_20260909_170409Z.csv'
# )

