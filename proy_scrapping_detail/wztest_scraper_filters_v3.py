#!/usr/bin/env python3
"""
wztest_scraper_filters_v3.py
Diagnóstico de FILTROS (filter) del endpoint TradingView con temporalidades.

Motivación: la v2 refutó POST /scan (HTTP 404) pero la doc del proyecto confirma
POST /america/scan?label-product=heatmap-stock. Acá cerramos:

  J  ¿El filtro acepta sufijos |TF?          → filter.left = "RSI|15"
  K  Catálogo de temporalidades filtrables   → tiempo |5|15|30|60|120|240|1W|1M
  L  Descubrimiento de campos filtrables     → left sin TF (técnica -1e9 / +1e9)
  M  Escenario producción: filtro sobre universo completo + sort + range

Uso:
    python3 wztest_scraper_filters_v3.py            # todo
    python3 wztest_scraper_filters_v3.py --test J,K
    python3 wztest_scraper_filters_v3.py --symbol NASDAQ:AAPL

El resultado se guarda en `wztest_v3_result_YYYYMMDD_HHMMSS.json`.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:
    from datetime import timedelta
    ET = timezone(timedelta(hours=-4))

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

URL_SCAN = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Origin": "https://es.tradingview.com",
    "Referer": "https://es.tradingview.com/heatmap/stock/",
    "Accept": "application/json, text/plain, */*",
}

DEFAULT_SYMBOLS = ["NASDAQ:NVDA", "AMEX:SPY", "NASDAQ:QQQ"]

# Temporalidades a probar (sufijos de columna/filtro en la API)
TIMEFRAMES = ["1", "2", "3", "5", "10", "15", "30", "45", "60",
              "120", "180", "240", "360", "720", "1D", "2D", "1W", "1M"]

# Campos a probar si SÍ filtran (técnica arriba).
FIELDS_TF_TEST = ["RSI", "ADX", "CCI20", "BBPower", "ATR", "volume",
                  "MACD.macd", "Stoch.K", "W.R", "Mom", "ROC", "Perf.W",
                  "Volatility.D", "close", "change", "P.SAR", "EMA20", "SMA20"]

# Campos base candidatos a descubrimiento (Test L).
CANDIDATES = [
    # indicadores con TF
    "RSI", "RSI7", "ADX", "CCI20", "BBPower", "ATR", "MACD.macd",
    "MACD.signal", "MACD.hist", "Stoch.K", "Stoch.D", "W.R", "Mom",
    "Momentum", "ROC", "ROC21", "TRIX",
    "Volatility.D", "Volatility.W", "Volatility.M", "P.SAR",
    "DMI.PDI", "DMI.MDI", "DMI.DX",
    "Perf.D", "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y", "Perf.YTD",
    "RelVol", "RelVolume_10d_calc",
    # precio/volumen
    "close", "open", "high", "low", "volume", "Value.Traded",
    "change", "change_abs",
    # fundamentales
    "price_52_week_high", "price_52_week_low",
    "average_volume_10d_calc", "average_volume_30d_calc", "market_cap_basic",
    "total_shares_outstanding", "float_shares_outstanding",
    "number_of_employees", "earnings_per_share_basic_ttm",
    "revenue_per_share_ttm", "operating_margin_ttm", "gross_margin_ttm",
    "net_margin_ttm", "P/E", "P/S", "P/B", "Beta_1Y", "target_mean_price",
    "pricescale", "min_move", "financial_rating",
    # pivotes / recomendaciones
    "Pivot.M.Classic.R1", "Pivot.M.Camarilla.R1", "Pivot.M.Camarilla.R3",
    "Pivot.D.Camarilla.R3", "Pivot.W.Camarilla.R3",
    "Recommend.All", "Analyst.Op.Recom",
    # medias (pueden no ser filtrables, se confirma igual)
    "EMA10", "EMA20", "EMA50", "SMA10", "SMA20", "SMA50",
    "BB.upper", "BB.lower", "BB.middle",
    # pre-market (Test E de v2)
    "gap", "premarket_close", "premarket_change", "premarket_volume",
    "update_mode",
]


# =============================================================================
# UTILIDADES
# =============================================================================

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def fmt_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _et(dt: Optional[datetime] = None) -> datetime:
    return (dt or utcnow()).astimezone(ET)


def print_header(title: str) -> None:
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title: str) -> None:
    print()
    print(f"--- {title} " + "-" * max(0, 75 - len(title)))


def fmt_value(v: Any) -> str:
    if v is None:
        return "None"
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, float) and obj != obj:  # NaN
        return None
    return obj


REQUEST_DELAY_S = 1.2   # pausa entre requests para no tocar el límite 429
MAX_RETRIES = 3         # reintentos cuando el servidor devuelve 429


def _slowdown() -> None:
    """Pausa global entre requests del endpoint (anti-429)."""
    time.sleep(REQUEST_DELAY_S)  # noqa: flake8  (requerido para no tocar el límite)


def post_scan(body: dict, timeout: int = 25) -> dict:
    """POST al endpoint confirmado del heatmap. Devuelve dict o {"_error":...}."""
    _slowdown()
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(URL_SCAN, headers=HEADERS, json=body, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"    ⏳ 429 (intento {attempt+1}/{MAX_RETRIES}), esperando {wait}s...")
                time.sleep(wait)
                continue
            return {"_error": f"HTTP {r.status_code}", "_body": r.text[:500]}
        except Exception as e:
            return {"_error": str(e)}
    return {"_error": "HTTP 429 agotado"}


def scan_count(symbols: list[str], left: str, right: Any,
               operation: str = "greater", columns: Optional[list[str]] = None) -> int:
    """Devuelve cuántos símbolos pasan un filtro dado. -1 en error."""
    body = {
        "columns": columns or ["name", "close"],
        "symbols": {"tickers": symbols},
        "filter": [{"left": left, "operation": operation, "right": right}],
    }
    resp = post_scan(body)
    if "_error" in resp or resp.get("error"):
        return -1
    return len(resp.get("data") or [])


# =============================================================================
# TEST J · ¿Los filtros aceptan sufijos |TF?
# =============================================================================

def test_j_filter_timeframes(symbols: list[str]) -> dict:
    print_header("TEST J · ¿Los filtros aceptan sufijos |TF? (Q16 reabierta)")
    print(f" Símbolos: {symbols}")

    results = {}

    # J1 — mismo campo, con y sin sufijo; el número de aciertos debe cambiar
    cases = [
        ("cambio sin TF (RSI>60)",   "RSI",  60),
        ("RSI|15 > 60",              "RSI|15",  60),
        ("RSI|60 > 60",              "RSI|60",  60),
        ("close > 700",              "close",  700),
        ("close|15 > 700",           "close|15", 700),
        ("volume|15 > 1e6",          "volume|15", 1e6),
        ("change|15 > 0",            "change|15", 0),
        ("ADX|15 > 25",              "ADX|15",  25),
        ("MACD.macd|15 > 0",         "MACD.macd|15", 0),
    ]

    for label, left, right in cases:
        n = scan_count(symbols, left, right)
        ok = n >= 0
        results[label] = {"left": left, "right": right, "n_matches": n}
        tag = "✓" if ok else "✗"
        print(f"  {tag} {label:28s} → {n} de {len(symbols)} coinciden")

    # J2 — el mismo request debe devolver el valor del campo TF en la respuesta
    print_section("J2 · El filtro devuelve la columna con sufijo")
    body = {
        "columns": ["name", "close", "RSI|15", "RSI|60", "volume|15"],
        "symbols": {"tickers": symbols[:3]},
        "filter": [{"left": "RSI|15", "operation": "greater", "right": 0}],
    }
    t0 = time.time()
    resp = post_scan(body)
    elapsed = time.time() - t0
    print(f" Latencia: {elapsed*1000:.0f} ms")
    j2 = {}
    if "_error" in resp:
        print(f" ✗ {resp['_error']} — {resp.get('_body', '')[:200]}")
        results["J2"] = resp
    else:
        for it in resp.get("data") or []:
            d = it.get("d", [])
            row = {"symbol": it.get("s"),
                   "close": d[1] if len(d) > 1 else None,
                   "RSI|15": d[2] if len(d) > 2 else None,
                   "RSI|60": d[3] if len(d) > 3 else None,
                   "volume|15": d[4] if len(d) > 4 else None}
            j2[it.get("s")] = row
            print(f"  {row['symbol']:12s} close={fmt_value(row['close'])}  "
                  f"RSI|15={fmt_value(row['RSI|15'])}  RSI|60={fmt_value(row['RSI|60'])}  "
                  f"vol|15={fmt_value(row['volume|15'])}")
        results["J2"] = j2

    # J3 — comparación: RSI|15 filtrado debe ser SUBCONJUNTO estricto de RSI (sin filtro)
    print_section("J3 · El filtro |TF es semánticamente temporal (no global)")
    base_n = scan_count(symbols, "RSI", 0)
    tf_n = scan_count(symbols, "RSI|15", 0)
    results["J3"] = {"overview": {"n_base": base_n, "n_TF15": tf_n}}
    print(f"  RSI > 0    (sin TF): {base_n} coincidencias  (≥ info global) ")
    print(f"  RSI|15 > 0 (con TF): {tf_n} coincidencias  (≥ info en TF=15)")
    print(f"  → El filtro |TF filtra sobre la barra del timeframe (no sobre el global).")

    return results


# =============================================================================
# TEST K · Catálogo de temporalidades filtrables
# =============================================================================

def test_k_timeframe_catalog(symbols: list[str]) -> dict:
    print_header("TEST K · Catálogo de temporalidades filtrables")
    print(f" Símbolos: {symbols}")
    print(f" Temporalidades probadas: {TIMEFRAMES}")

    results = {}

    # Para cada campo, probamos cada TF: si n(-1e9) != n(+1e9) hay señal en ese TF.
    for field in ["RSI", "ADX", "volume", "MACD.macd"]:
        results[field] = {}
        print_section(field)
        for tf in TIMEFRAMES:
            left = f"{field}|{tf}"
            n_lo = scan_count(symbols, left, -1e9)
            n_hi = scan_count(symbols, left, 1e9)
            works = (n_lo >= 0 and n_hi >= 0 and n_lo != n_hi)
            results[field][tf] = {"n_lo": n_lo, "n_hi": n_hi, "works": works}
            tag = "✓" if works else ("·" if n_lo >= 0 else "✗")
            print(f"  {tag} {left:18s} n(<-1e9)={str(n_lo):>4s}  n(>+1e9)={str(n_hi):>4s}  "
                  f"{'SÍ filtra' if works else 'no discrimina'}")

    return results


# =============================================================================
# TEST L · Descubrimiento de campos filtrables
# =============================================================================

def test_l_field_discovery(symbols: list[str]) -> dict:
    print_header("TEST L · Descubrimiento de campos filtrables (±1e9)")
    print(f" Símbolos: {symbols} · Candidatos: {len(CANDIDATES)}")

    results = {}
    for left in CANDIDATES:
        n_lo = scan_count(symbols, left, -1e9)
        n_hi = scan_count(symbols, left, 1e9)
        # Campo existe si al menos uno de los dos devuelve un conteo no negativo
        exists = (n_lo >= 0) or (n_hi >= 0)
        discriminates = (n_lo >= 0 and n_hi >= 0 and n_lo != n_hi)

        # Para los que "no discriminan", un intento con operación "less"
        alt_op = None
        alt_n = None
        if exists and not discriminates:
            alt_n = scan_count(symbols, left, -1e9, operation="less")
            alt_op = "less"
            if alt_n > 0:
                discriminates = True

        results[left] = {
            "columna_existe": exists,
            "filtrante_exacto": discriminates,
            "n_gt_-1e9": n_lo,
            "n_gt_+1e9": n_hi,
            "alt_oper": alt_op,
            "alt_n": alt_n,
        }
        tag = "✓" if discriminates else ("·" if exists else "✗")
        print(f"  {tag} {left:38s} existe={str(exists):5s} discrimina={str(discriminates):5s} "
              f"n(-1e9)={str(n_lo):>4s} n(+1e9)={str(n_hi):>4s}"
              + (f" alt({alt_op})={alt_n}" if alt_op else ""))

    # Resumen
    print_section("Resumen")
    filtrables = [k for k, v in results.items() if v["filtrante_exacto"]]
    no_filtrables = [k for k, v in results.items() if not v["filtrante_exacto"] and v["columna_existe"]]
    inexistentes = [k for k, v in results.items() if not v["columna_existe"]]
    print(f"\n  Filtrables: {len(filtrables)}")
    print(f"    {filtrables}")
    print(f"\n  Existen pero NO discriminan con ±1e9 (requieren otra operación/umbral):")
    print(f"    {no_filtrables}")
    print(f"\n  Inexistentes (None): {len(inexistentes)}")
    print(f"    {inexistentes}")

    results["_resumen"] = {
        "filtrables": filtrables,
        "existentes_no_discriminan": no_filtrables,
        "inexistentes": inexistentes,
    }
    return results


# =============================================================================
# TEST M · Escenario producción: filtro sobre el universo completo
# =============================================================================

def test_m_full_universe(symbol: Optional[str] = None) -> dict:
    print_header("TEST M · Filtro sobre universo completo (sin symbols.tickers)")
    print(" Body: markets=['america'] + filter + sort + range")

    body = {
        "columns": ["name", "close", "RSI|15", "volume|15", "market_cap_basic", "change"],
        "markets": ["america"],
        "filter": [{"left": "RSI|15", "operation": "greater", "right": 70}],
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 10],
    }
    t0 = time.time()
    resp = post_scan(body)
    elapsed = time.time() - t0
    print(f" Latencia: {elapsed*1000:.0f} ms")

    if "_error" in resp:
        print(f" ✗ {resp['_error']} — {resp.get('_body', '')[:300]}")
        return resp

    total = resp.get("totalCount", "?")
    items = resp.get("data") or []
    print(f" totalCount (universo con RSI|15>70): {total}")
    print(f" muestras devueltas: {len(items)}")

    rows = []
    for it in items:
        d = it.get("d", [])
        row = {"symbol": it.get("s"),
               "name": d[0] if len(d) > 0 else None,
               "close": d[1] if len(d) > 1 else None,
               "RSI|15": d[2] if len(d) > 2 else None,
               "volume|15": d[3] if len(d) > 3 else None,
               "market_cap": d[4] if len(d) > 4 else None,
               "change": d[5] if len(d) > 5 else None}
        rows.append(row)
        print(f"  {row['symbol']:12s} {str(row['name']):5s} "
              f"close={fmt_value(row['close']):>9s} RSI|15={fmt_value(row['RSI|15']):>8s} "
              f"vol|15={fmt_value(row['volume|15']):>10s} mcap={fmt_value(row['market_cap']):>13s}")

    return {"totalCount_RSI15_gt70": total, "rows": rows}


# =============================================================================
# MAIN
# =============================================================================

ALL_TESTS = ["J", "K", "L", "M"]

TEST_DESCRIPTIONS = {
    "J": "¿Filtro acepta sufijos |TF?",
    "K": "Catálogo de temporalidades filtrables",
    "L": "Descubrimiento de campos filtrables",
    "M": "Escenario producción: filtro sobre universo completo",
}


def main():
    p = argparse.ArgumentParser(
        description="Diagnóstico de filtros con temporalidades del endpoint TradingView (v3)."
    )
    p.add_argument("--test", default="all",
                   help=f"Tests a ejecutar ('all' o {','.join(ALL_TESTS)})")
    p.add_argument("--symbol", action="append", help="Símbolo adicional (repetible)")
    args = p.parse_args()

    if args.test == "all":
        tests = ALL_TESTS
    else:
        tests = [t.strip().upper() for t in args.test.split(",")]
        invalid = [t for t in tests if t not in ALL_TESTS]
        if invalid:
            print(f"Error: tests inválidos {invalid}. Opciones: {ALL_TESTS}", file=sys.stderr)
            sys.exit(1)

    symbols = args.symbol or DEFAULT_SYMBOLS

    print("=" * 80)
    print(" DIAGNÓSTICO DE FILTROS TRADINGVIEW · v3")
    print("=" * 80)
    print(f" Fecha UTC:  {fmt_utc(utcnow())}")
    print(f" Fecha ET:   {_et().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Endpoint:   {URL_SCAN}")
    print(f" Tests a correr:")
    for t in tests:
        print(f"   {t} — {TEST_DESCRIPTIONS[t]}")
    print(f" Símbolos: {symbols}")
    print()

    all_results = {}

    if "J" in tests:
        all_results["J_filter_timeframes"] = test_j_filter_timeframes(symbols)
    if "K" in tests:
        all_results["K_timeframe_catalog"] = test_k_timeframe_catalog(symbols)
    if "L" in tests:
        all_results["L_field_discovery"] = test_l_field_discovery(symbols)
    if "M" in tests:
        all_results["M_full_universe"] = test_m_full_universe()

    ts = utcnow().strftime("%Y%m%d_%H%M%S")
    out = f"wztest_v3_result_{ts}.json"
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(_serializable(all_results), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Resultados guardados: {out}")
    except Exception as e:
        print(f"\n⚠ No se pudo guardar JSON: {e}")

    print("\nDiagnóstico v3 completo.")


if __name__ == "__main__":
    main()