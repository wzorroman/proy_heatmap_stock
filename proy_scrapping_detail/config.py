import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde el directorio del proyecto
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH, override=True)

VERSION = "3.1.0"

# Variables de BD (solo requeridas si DB_WRITE_ENABLED=true)
PG_HOST = os.getenv("BD_HEATMAP_HOST", "localhost")
PG_PORT = int(os.getenv("BD_HEATMAP_PORT", "5432"))
PG_DATABASE = os.getenv("BD_HEATMAP_DATABASE", "heatmap_stock")
PG_USER = os.getenv("BD_HEATMAP_USER", "postgres")
PG_PASSWORD = os.getenv("BD_HEATMAP_PASSWORD", "")

# Flag de escritura en BD (default false = modo legacy CSV)
DB_WRITE_ENABLED = os.getenv("DB_WRITE_ENABLED", "false").lower() == "true"

# Nombre del script para auditoría
SCRIPT_NAME_CALENDARIO = "calendario"
SCRIPT_NAME_SCRAPER = "radar_v4"

# Validación estricta solo si DB_WRITE_ENABLED=true
if DB_WRITE_ENABLED:
    required = {
        "BD_HEATMAP_HOST": PG_HOST,
        "BD_HEATMAP_PORT": PG_PORT,
        "BD_HEATMAP_DATABASE": PG_DATABASE,
        "BD_HEATMAP_USER": PG_USER,
        "BD_HEATMAP_PASSWORD": PG_PASSWORD,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Faltan variables de BD requeridas: {missing}")

CONFIG_ACTIVOS = {
    "NASDAQ_CORE": {"QQQ": {"primario": "NASDAQ:QQQ", "respaldo": "CME_MINI:NQ1!"}},
    "SENTIMIENTO": {
        "BTC":  {"primario": "BINANCE:BTCUSDT", "respaldo": "BITSTAMP:BTCUSD"},
        "VIX":  {"primario": "CBOE:VX1!",       "respaldo": "TVC:VIX"},
        "DXY":  {"primario": "AMEX:UUP",        "respaldo": "ICEUS:DX1!"},
        "MSTR": {"primario": "NASDAQ:MSTR",     "respaldo": "NASDAQ:MSTR"},
        "MARA": {"primario": "NASDAQ:MARA",     "respaldo": "NASDAQ:MARA"},
    },
    "FOREX_CENTINELA": {
        "EURUSD": {"primario": "FX_IDC:EURUSD", "respaldo": "OANDA:EURUSD"},
        "AUDUSD": {"primario": "OANDA:AUDUSD",  "respaldo": "CME:6A1!"},
        "USDJPY": {"primario": "OANDA:USDJPY",  "respaldo": "CME:6J1!"},
        "GBPUSD": {"primario": "OANDA:GBPUSD",  "respaldo": "OANDA:GBPUSD"},
    },
    "METALES_SPOT": {
        "ORO":   {"primario": "OANDA:XAUUSD", "respaldo": "SAXO:XAUUSD"},
        "PLATA": {"primario": "AMEX:SLV",     "respaldo": "TVC:SILVER"},
    },
    "BONOS_ETF_TEC": {
        "SHY": {"primario": "NASDAQ:SHY", "respaldo": "NASDAQ:IEI"},
        "IEF": {"primario": "NASDAQ:IEF", "respaldo": "CBOT:ZN1!"},
        "TLT": {"primario": "NASDAQ:TLT", "respaldo": "CBOT:ZB1!"},
    },
    "BONOS_YIELD": {
        "US02Y": {"primario": "TVC:US02Y", "respaldo": "TVC:US02Y"},
        "US10Y": {"primario": "TVC:US10Y", "respaldo": "TVC:US10Y"},
    },
    "ENERGIA": {
        "OIL": {"primario": "AMEX:USO", "respaldo": "NYMEX:CL1!"},
        "XLE": {"primario": "AMEX:XLE", "respaldo": "AMEX:XOP"},
    },
    "INDICES_ETF_USA": {
        "SPY": {"primario": "AMEX:SPY",   "respaldo": "AMEX:SPY"},
        "VOO": {"primario": "AMEX:VOO",   "respaldo": "AMEX:VOO"},
        "VGT": {"primario": "AMEX:VGT",   "respaldo": "AMEX:VGT"},
        "NDX": {"primario": "NASDAQ:NDX", "respaldo": "NASDAQ:NDX"},
    },
    "FOREX_EXTRA": {
        "USDCAD": {"primario": "OANDA:USDCAD", "respaldo": "FX_IDC:USDCAD"},
        "GBPJPY": {"primario": "OANDA:GBPJPY", "respaldo": "FX_IDC:GBPJPY"},
        "NZDUSD": {"primario": "OANDA:NZDUSD", "respaldo": "FX_IDC:NZDUSD"},
    },
    "FINANZAS_BANCOS": {
        "BRK.B": {"primario": "NYSE:BRK.B",  "respaldo": "NYSE:BRK.B"},
        "JPM":   {"primario": "NYSE:JPM",    "respaldo": "NYSE:JPM"},
        "V":     {"primario": "NYSE:V",      "respaldo": "NYSE:V"},
        "BAC":   {"primario": "NYSE:BAC",    "respaldo": "NYSE:BAC"},
        "MS":    {"primario": "NYSE:MS",     "respaldo": "NYSE:MS"},
        "BLK":   {"primario": "NYSE:BLK",    "respaldo": "NYSE:BLK"},
        "GS":    {"primario": "NYSE:GS",     "respaldo": "NYSE:GS"},      
    },
    "CONSUMO_DEFENSIVO": {
        "PG":   {"primario": "NYSE:PG",      "respaldo": "NYSE:PG"},
        "KO":   {"primario": "NYSE:KO",      "respaldo": "NYSE:KO"},
        "PEP":  {"primario": "NASDAQ:PEP",   "respaldo": "NASDAQ:PEP"},
        "COST": {"primario": "NASDAQ:COST",  "respaldo": "NASDAQ:COST"},
    },
    "RETAIL_CONSUMO": {
        "WMT":  {"primario": "NASDAQ:WMT",   "respaldo": "NASDAQ:WMT"},
        "HD":   {"primario": "NYSE:HD",      "respaldo": "NYSE:HD"},
        "MCD":  {"primario": "NYSE:MCD",     "respaldo": "NYSE:MCD"},
        "SBUX": {"primario": "NASDAQ:SBUX",  "respaldo": "NASDAQ:SBUX"},
        "BABA": {"primario": "NYSE:BABA",    "respaldo": "NYSE:BABA"},
        "TGT":  {"primario": "NYSE:TGT",     "respaldo": "NYSE:TGT"},
    },
    "SALUD_FARMACIA": {
        "LLY":  {"primario": "NYSE:LLY",     "respaldo": "NYSE:LLY"},
        "UNH":  {"primario": "NYSE:UNH",     "respaldo": "NYSE:UNH"},
        "JNJ":  {"primario": "NYSE:JNJ",     "respaldo": "NYSE:JNJ"},
        "ABBV": {"primario": "NYSE:ABBV",    "respaldo": "NYSE:ABBV"},
        "TMO":  {"primario": "NYSE:TMO",     "respaldo": "NYSE:TMO"},
    },
    "INDUSTRIAL_LOGISTICA": {
        "GE":  {"primario": "NYSE:GE",  "respaldo": "NYSE:GE"},
        "UPS": {"primario": "NYSE:UPS", "respaldo": "NYSE:UPS"},
        "DE":  {"primario": "NYSE:DE",  "respaldo": "NYSE:DE"},
        "WM":  {"primario": "NYSE:WM",  "respaldo": "NYSE:WM"},
    },
    "AEROESPACIAL_DEFENSA": {
        "BA":   {"primario": "NYSE:BA",     "respaldo": "NYSE:BA"},
        "LMT":  {"primario": "NYSE:LMT",    "respaldo": "NYSE:LMT"},
        "NOC":  {"primario": "NYSE:NOC",    "respaldo": "NYSE:NOC"},
    },
    "ENERGIA_ACCIONES": {
        "CCJ": {"primario": "NYSE:CCJ", "respaldo": "NYSE:CCJ"},
        "XOM": {"primario": "NYSE:XOM", "respaldo": "NYSE:XOM"},
    },
    "TELECOM_MEDIA": {
        "DIS": {"primario": "NYSE:DIS", "respaldo": "NYSE:DIS"},
        "VZ":  {"primario": "NYSE:VZ",  "respaldo": "NYSE:VZ"},
    },
    "TECNOLOGIA_GIGANTES": {
        "AAPL":  {"primario": "NASDAQ:AAPL",  "respaldo": "NASDAQ:AAPL"},
        "AMZN":  {"primario": "NASDAQ:AMZN",  "respaldo": "NASDAQ:AMZN"},
        "GOOGL": {"primario": "NASDAQ:GOOGL", "respaldo": "NASDAQ:GOOGL"},
        "META":  {"primario": "NASDAQ:META",  "respaldo": "NASDAQ:META"},
        "MSFT":  {"primario": "NASDAQ:MSFT",  "respaldo": "NASDAQ:MSFT"},
        "NFLX":  {"primario": "NASDAQ:NFLX",  "respaldo": "NASDAQ:NFLX"},
        "TSLA":  {"primario": "NASDAQ:TSLA",  "respaldo": "NASDAQ:TSLA"},
    },
    "SEMICONDUCTORES": {
        "NVDA": {"primario": "NASDAQ:NVDA", "respaldo": "NASDAQ:NVDA"},
        "ASML": {"primario": "NASDAQ:ASML", "respaldo": "NASDAQ:ASML"},
        "MU":   {"primario": "NASDAQ:MU",   "respaldo": "NASDAQ:MU"},
        "QCOM": {"primario": "NASDAQ:QCOM", "respaldo": "NASDAQ:QCOM"},
        "TSM":  {"primario": "NYSE:TSM",    "respaldo": "NYSE:TSM"},
        "AVGO": {"primario": "NASDAQ:AVGO", "respaldo": "NASDAQ:AVGO"},
        "ARM":  {"primario": "NASDAQ:ARM",  "respaldo": "NASDAQ:ARM"},
        "INTC": {"primario": "NASDAQ:INTC", "respaldo": "NASDAQ:INTC"},
        "SMCI": {"primario": "NASDAQ:SMCI", "respaldo": "NASDAQ:SMCI"},
        "TER":  {"primario": "NASDAQ:TER",  "respaldo": "NASDAQ:TER"},
        "TXN":  {"primario": "NASDAQ:TXN",  "respaldo": "NASDAQ:TXN"},
    },
    "SOFTWARE_SAAS": {
        "ADSK": {"primario": "NASDAQ:ADSK", "respaldo": "NASDAQ:ADSK"},
        "CRM":  {"primario": "NYSE:CRM",    "respaldo": "NYSE:CRM"},
        "DDOG": {"primario": "NASDAQ:DDOG", "respaldo": "NASDAQ:DDOG"},
        "FTNT": {"primario": "NASDAQ:FTNT", "respaldo": "NASDAQ:FTNT"},
        "NOW":  {"primario": "NYSE:NOW",    "respaldo": "NYSE:NOW"},
        "ORCL": {"primario": "NYSE:ORCL",   "respaldo": "NYSE:ORCL"},
        "PANW": {"primario": "NASDAQ:PANW", "respaldo": "NASDAQ:PANW"},
        "SHOP": {"primario": "NASDAQ:SHOP", "respaldo": "NASDAQ:SHOP"},
        "SPOT": {"primario": "NYSE:SPOT",   "respaldo": "NYSE:SPOT"},        
    },
    "HARDWARE_INFRAESTRUCTURA": {
        "IBM":  {"primario": "NYSE:IBM",    "respaldo": "NYSE:IBM"},
        "CSCO": {"primario": "NASDAQ:CSCO", "respaldo": "NASDAQ:CSCO"},
        "DELL": {"primario": "NYSE:DELL",   "respaldo": "NYSE:DELL"},
        "HPQ":  {"primario": "NYSE:HPQ",    "respaldo": "NYSE:HPQ"},
        "LOGI": {"primario": "NASDAQ:LOGI", "respaldo": "NASDAQ:LOGI"},
        "STX":  {"primario": "NASDAQ:STX",  "respaldo": "NASDAQ:STX"},
        "WDC":  {"primario": "NASDAQ:WDC",  "respaldo": "NASDAQ:WDC"},
    },
}

METADATOS_ACTIVOS = {
    "VIX":   {"categoria": "macro", "peso": 0.0, "peso_radar": 20, "direccion": "invertida"},
    "DXY":   {"categoria": "macro", "peso": 0.0, "peso_radar": 15, "direccion": "invertida"},
    "TLT":   {"categoria": "macro", "peso": 0.0, "peso_radar": 15, "direccion": "normal"},
    "US10Y": {"categoria": "macro", "peso": 0.0, "peso_radar": 15, "direccion": "invertida"},
    "ORO":   {"categoria": "macro", "peso": 0.0, "peso_radar": 15, "direccion": "invertida"},
    "OIL":   {"categoria": "macro", "peso": 0.0, "peso_radar": 10, "direccion": "invertida"},
    "US02Y": {"categoria": "macro", "peso": 0.0},
    "BTC":   {"categoria": "macro", "peso": 0.0},
    "EURUSD": {"categoria": "macro", "peso": 0.0},
    "AUDUSD": {"categoria": "macro", "peso": 0.0},
    "USDJPY": {"categoria": "macro", "peso": 0.0},
    "GBPUSD": {"categoria": "macro", "peso": 0.0},
    "USDCAD": {"categoria": "macro", "peso": 0.0},
    "GBPJPY": {"categoria": "macro", "peso": 0.0},
    "NZDUSD": {"categoria": "macro", "peso": 0.0},
}
CATEGORIA_DEFAULT = "equity"
PESO_DEFAULT = 1.0