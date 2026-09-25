# file: proy_scrapping_detail/scripts/verificar_endpoints.py
"""Verificación de endpoints en vivo para la FASE 3 (F3.1/F3.2/F3.12).

Sin escribir BD. Comprueba que los endpoints siguen devolviendo los datos
correctos/esperados:

1. CAMPOS_LIST (33) en POST /america/scan sobre equity/ETF (batch).
2. GET /symbol de muestra: equity (NASDAQ:QQQ), ETF (AMEX:SPY), futuro
   (CME_MINI:ES1!, CBOT:ZB1!) y un ticker no válido (debe devolver None).
3. Verificación del payload según BATCH_PREFIJOS (unicidad de símbolos).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PARENT = Path(__file__).resolve().parents[1]
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import requests

from scraper_live_tradingview_v5 import (
    BATCH_PREFIJOS,
    CAMPOS,
    CAMPOS_LIST,
    HEADERS,
    URL_SCAN,
    URL_SYMBOL,
)

OK = []
FALLO = []


def reportar(nombre, condicion, detalle=None):
    if condicion:
        OK.append(f"[OK] {nombre}")
    else:
        FALLO.append(f"[FALLO] {nombre}: {detalle}")


def scan_batch(symbols):
    body = {"symbols": {"tickers": symbols}, "columns": CAMPOS_LIST}
    r = requests.post(URL_SCAN, json=body, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def symbol(s):
    params = {"symbol": s, "fields": CAMPOS, "no_404": "true"}
    r = requests.get(URL_SYMBOL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    print(f"[verificar_endpoints] {datetime.now(timezone.utc).isoformat()}Z")

    # 1. Batch equity/ETF: 33 campos, sin "_error", símbolos únicos
    batch = ["NASDAQ:QQQ", "AMEX:SPY", "NASDAQ:NVDA", "NYSE:JPM", "AMEX:UUP"]
    data = scan_batch(batch)
    reportar("batch /america/scan responde", isinstance(data, dict) and "data" in data,
             str(data)[:120])
    filas = data.get("data", [])
    reportar("batch devuelve filas", len(filas) == len(batch), f"filas={len(filas)}")
    simbolos = []
    for fila in filas:
        s = fila.get("s")
        d = fila.get("d", [])
        simbolos.append(s)
        reportar(f"batch {s} tiene 33 campos", isinstance(d, list) and len(d) == 33,
                 f"len(d)={len(d)}")
        mapeo = dict(zip(CAMPOS_LIST, d))
        reportar(f"batch {s} sin _error", "_error" not in mapeo, str(mapeo.get("_error")))
        reportar(f"batch {s} con update_mode", bool(mapeo.get("update_mode")),
                 mapeo.get("update_mode"))
        reportar(f"batch {s} RSI|15 poblado (puede ser 0)", mapeo.get("RSI|15") is not None,
                 mapeo.get("RSI|15"))
    reportar("batch sin duplicados de símbolo", len(simbolos) == len(set(simbolos)),
             str(simbolos))

    # 2. GET /symbol por clase de activo (respuesta con claves nombradas, SHA)
    casos = {
        "NASDAQ:QQQ": "equity",
        "AMEX:SPY": "equity/ETF",
        "CME_MINI:ES1!": "futuro (F3.12)",
        "CBOT:ZB1!": "futuro bono (F3.12)",
    }
    for s, clase in casos.items():
        data = symbol(s)
        reportar(f"symbol {s} ({clase}) es dict",
                 isinstance(data, dict) and bool(data), repr(data)[:100])
        if isinstance(data, dict) and data:
            reportar(f"symbol {s} sin _error", "_error" not in data, str(data.get("_error")))
            reportar(f"symbol {s} update_mode", bool(data.get("update_mode")),
                     data.get("update_mode"))
            reportar(f"symbol {s} close", data.get("close") is not None, data.get("close"))

    # 3. Ticker no válido -> None (fetch_from_scanner lo usa como "no capturar")
    r = requests.get(URL_SYMBOL, params={"symbol": "XXX:FAKETICKER", "fields": CAMPOS, "no_404": "true"},
                     headers=HEADERS, timeout=15)
    r.raise_for_status()
    reportar("symbol ticker inválido devuelve null", r.json() is None, r.text[:80])

    # 4. BATCH_PREFIJOS coherente: equity/ETF en batch, futuros fuera
    for s in batch:
        reportar(f"prefijo de {s} en BATCH_PREFIJOS", s.split(":")[0] in BATCH_PREFIJOS)
    for s in ("CME_MINI:ES1!", "CBOT:ZB1!"):
        reportar(f"prefijo de {s} fuera de batch", s.split(":")[0] not in BATCH_PREFIJOS)

    print("\n--- RESULTADO ---")
    print("\n".join(OK))
    if FALLO:
        print("\n".join(FALLO))
        sys.exit(1)
    print("\nTodo OK: los endpoints siguen devolviendo datos correctos.")


if __name__ == "__main__":
    main()