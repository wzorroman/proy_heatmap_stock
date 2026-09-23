"""
test_scraper_timeframes.py
Diagnóstico del endpoint /symbol de TradingView.

- NO escribe CSV, NO escribe BD, NO requiere config.py.
- Prueba A: consistencia intra-minuto (mismo request repetido).
- Prueba B: variación por timeframe usando el sufijo campo|TF.

Uso:
    python3 test_scraper_timeframes.py
    python3 test_scraper_timeframes.py --symbol NASDAQ:AAPL --iters 6 --gap 8
"""

import argparse
import time
from collections import OrderedDict
from datetime import datetime, timezone

import requests

URL = "https://scanner.tradingview.com/symbol"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}

# Campos del scraper v5 (sin sufijo => 1D / default)
BASE_FIELDS = [
    "close", "volume", "RSI", "CCI20", "BBPower", "ADX","Pivot.M.Camarilla.R3", "Perf.W", "change",
]

# Timeframes a probar con sufijo. None = sin sufijo (default 1D)
TIMEFRAMES = [None, "5", "15", "30", "60", "1D"]

# Símbolos representativos (modificalos si querés usar los de config.py)
DEFAULT_SYMBOLS = ["BINANCE:BTCUSDT", "NASDAQ:AAPL", "FX:EURUSD"]


def fetch(symbol, fields):
    """Un solo GET al endpoint /symbol. Devuelve dict o lanza excepción."""
    params = {"symbol": symbol, "fields": ",".join(fields), "no_404": "true"}
    r = requests.get(URL, params=params, headers=HEADERS, timeout=12)
    r.raise_for_status()
    return r.json()


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


# ---------------------------------------------------------------------------
# PRUEBA A — Consistencia intra-minuto
# ---------------------------------------------------------------------------
def test_intra_minute(symbol, iters, gap):
    print(f"\n=== TEST A · Consistencia intra-minuto — {symbol} ===")
    print(f"    {iters} requests, gap={gap}s (~{iters * gap}s total)\n")

    samples = []
    for i in range(iters):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        try:
            data = fetch(symbol, BASE_FIELDS)
        except Exception as e:
            print(f"  [{i+1}/{iters}] {ts}  ERROR: {e}")
            continue

        row = OrderedDict((f, data.get(f)) for f in BASE_FIELDS)
        samples.append((ts, row))

        printable = " | ".join(f"{k}={fmt(v)}" for k, v in row.items())
        print(f"  [{i+1}/{iters}] {ts}  {printable}")

        if i < iters - 1:
            time.sleep(gap)

    if len(samples) < 2:
        print("\n  ⚠  Menos de 2 muestras válidas. No se puede comparar.")
        return

    print("\n  Resumen de variación por campo:")
    print("  " + "-" * 78)
    for f in BASE_FIELDS:
        vals = [str(s[1][f]) for s in samples]
        uniq = list(dict.fromkeys(vals))          # preserva orden
        if len(uniq) == 1:
            print(f"    ✓ {f:28s} estable   → {fmt(uniq[0])}")
        else:
            print(f"    ⚠ {f:28s} CAMBIA    → {len(uniq)} valores únicos: {uniq[:5]}")
    print("  " + "-" * 78)


# ---------------------------------------------------------------------------
# PRUEBA B — Variación por timeframe (sufijo campo|TF)
# ---------------------------------------------------------------------------
def test_timeframes(symbol):
    print(f"\n=== TEST B · Variación por timeframe — {symbol} ===")
    print("    Cada fila es un request con TODOS los campos sufijados por TF.\n")

    # Guardamos las respuestas por TF para comparar después
    results = {}

    for tf in TIMEFRAMES:
        suffix = f"|{tf}" if tf else ""
        label = tf or "default"
        fields = [f"{f}{suffix}" for f in BASE_FIELDS]
        try:
            data = fetch(symbol, fields)
        except Exception as e:
            print(f"  TF={label:>7s}  ERROR: {e}")
            continue

        results[label] = {f: data.get(f"{f}{suffix}") for f in BASE_FIELDS}

        # Campos que el endpoint ignoró (no aparecen con sufijo)
        missing = [f for f in BASE_FIELDS if f"{f}{suffix}" not in data]

        printable = " | ".join(f"{f}={fmt(results[label][f])}" for f in BASE_FIELDS)
        print(f"  TF={label:>7s}  {printable}")
        if missing:
            print(f"              ⚠ el endpoint IGNORÓ el sufijo en: {missing}")

    # Comparativa: ¿qué campos responden realmente al TF?
    if len(results) < 2:
        return

    print("\n  ¿Qué campos cambian entre timeframes?")
    print("  " + "-" * 78)
    labels = list(results.keys())
    for f in BASE_FIELDS:
        vals = [str(results[l][f]) for l in labels]
        uniq = list(dict.fromkeys(vals))
        if len(uniq) == 1:
            print(f"    · {f:28s} CONSTANTE entre TFs → {fmt(uniq[0])}")
        else:
            pairs = "  ".join(f"{l}={fmt(v)}" for l, v in zip(labels, vals))
            print(f"    ⚠ {f:28s} VARÍA con TF     → {pairs}")
    print("  " + "-" * 78)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", action="append",
                    help="Símbolo a probar (repetible). Default: set interno.")
    ap.add_argument("--iters", type=int, default=5,
                    help="Iteraciones de TEST A (default 5).")
    ap.add_argument("--gap", type=int, default=10,
                    help="Segundos entre iteraciones de TEST A (default 10).")
    ap.add_argument("--skip-a", action="store_true", help="Omitir TEST A.")
    ap.add_argument("--skip-b", action="store_true", help="Omitir TEST B.")
    args = ap.parse_args()

    symbols = args.symbol or DEFAULT_SYMBOLS

    print("=" * 80)
    print(f" DIAGNÓSTICO ENDPOINT TRADINGVIEW · {datetime.now(timezone.utc).isoformat()}")
    print(f" Símbolos: {symbols}")
    print("=" * 80)

    for sym in symbols:
        if not args.skip_a:
            test_intra_minute(sym, args.iters, args.gap)
        if not args.skip_b:
            test_timeframes(sym)

    print("\nDiagnóstico completo.")


if __name__ == "__main__":
    main()
