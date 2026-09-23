#!/usr/bin/env python3
"""
wztest_scraper_timeframes_v2.py
Diagnóstico extendido del endpoint TradingView para correr en horas de mercado NYSE.

Objetivo: cerrar las dudas del Informe Técnico v3 que exigen datos en vivo.

Cobertura (por test):
  A  Consistencia intra-minuto       → H19, H24 (refresco real en acciones)
  B  Variación por timeframe         → confirma sufijos |TF
  C  Cruce de frontera de barra      → H19, H21 (repintado y vela en formación)
  D  update_mode por símbolo         → H1, H7b
  E  Campos de pre-market            → H6, H20, H7b
  F  Equivalencia de FX              → Q23, Q24
  G  POST /scan con sufijos          → Q16, H7b
  H  Variantes de pivote             → H22, Q17
  I  Gate por clase de activo        → Q22, H4

Uso:
    # Todo (≈25-45 min según dónde caiga el Test C)
    python3 wztest_scraper_timeframes_v2.py

    # Solo algunos tests
    python3 wztest_scraper_timeframes_v2.py --test A,B,D
    python3 wztest_scraper_timeframes_v2.py --test D,F,G,H

    # Rápido (pocos samples)
    python3 wztest_scraper_timeframes_v2.py --test A --iters 6 --gap 5

    # Con símbolos propios
    python3 wztest_scraper_timeframes_v2.py --symbol NASDAQ:NVDA --symbol AMEX:SPY

    # Forzar aunque NYSE esté cerrada
    python3 wztest_scraper_timeframes_v2.py --force

El resultado se guarda en `wztest_v2_result_YYYYMMDD_HHMMSS.json`.
"""

import argparse
import json
import sys
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                     # Python < 3.9 o sin tzdata
    ET = timezone(timedelta(hours=-4))  # aproximación EDT


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

URL_SYMBOL = "https://scanner.tradingview.com/symbol"
URL_SCAN = "https://scanner.tradingview.com/scan"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Content-Type": "application/json",
}

BASE_FIELDS = [
    "close", "volume", "RSI", "CCI20", "BBPower", "ADX",
    "Pivot.M.Camarilla.R3", "Perf.W", "change",
]

TIMEFRAMES = [None, "5", "15", "30", "60"]

DEFAULT_SYMBOLS = [
    "NASDAQ:NVDA",
    "AMEX:SPY",
    "NASDAQ:QQQ",
]

FX_VARIANTS = [
    "FX:EURUSD",
    "FX_IDC:EURUSD",
    "OANDA:EURUSD",
]

PIVOT_VARIANTS = [
    "Pivot.M.Camarilla.R3",
    "Pivot.M.Camarilla.R3|5",
    "Pivot.M.Camarilla.R3|15",
    "Pivot.M.Camarilla.R3|30",
    "Pivot.M.Camarilla.R3|60",
    "Pivot.D.Camarilla.R3",
    "Pivot.W.Camarilla.R3",
    "Pivot.D.Camarilla.R3|15",
    "Pivot.W.Camarilla.R3|15",
]

PREMARKET_FIELDS = [
    "close", "close|5", "close|15",
    "premarket_close", "premarket_change", "premarket_volume",
    "gap", "update_mode", "change",
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


def is_nyse_open(dt: Optional[datetime] = None) -> bool:
    """Aproximación: NYSE abierta lun-vie 09:30–16:00 ET. No considera feriados."""
    d = _et(dt)
    if d.weekday() >= 5:
        return False
    if (d.hour, d.minute) < (9, 30):
        return False
    if (d.hour, d.minute) >= (16, 0):
        return False
    return True


def in_premarket(dt: Optional[datetime] = None) -> bool:
    """09:00–09:30 ET en día hábil."""
    d = _et(dt)
    if d.weekday() >= 5:
        return False
    return d.hour == 9 and 0 <= d.minute < 30


def seconds_until_next_bar(tf_minutes: int) -> float:
    """Segundos hasta la próxima frontera de barra del TF dado."""
    now = utcnow()
    minutes_since_midnight = now.hour * 60 + now.minute
    next_boundary = ((minutes_since_midnight // tf_minutes) + 1) * tf_minutes
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    target = base + timedelta(minutes=next_boundary)
    return (target - now).total_seconds()


def fetch_symbol(symbol: str, fields: list[str], timeout: int = 12) -> Any:
    """GET /symbol. Devuelve dict, '429' o None."""
    params = {"symbol": symbol, "fields": ",".join(fields), "no_404": "true"}
    try:
        r = requests.get(URL_SYMBOL, params=params, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            return "429"
        return None
    except Exception:
        return None


def post_scan(tickers: list[str], columns: list[str], timeout: int = 15) -> dict:
    """POST /scan con múltiples tickers y columnas."""
    body = {"symbols": {"tickers": tickers}, "columns": columns}
    try:
        r = requests.post(URL_SCAN, headers=HEADERS, json=body, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return {"_error": f"HTTP {r.status_code}", "_body": r.text[:500]}
    except Exception as e:
        return {"_error": str(e)}


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


# =============================================================================
# TEST A · Consistencia intra-minuto
# =============================================================================

def test_a_consistency(symbols: list[str], iters: int = 12, gap: float = 5.0) -> dict:
    print_header("TEST A · Consistencia intra-minuto (refresco real)")
    print(f" Símbolos: {symbols}")
    print(f" Iteraciones: {iters} · gap: {gap}s · duración ≈ {iters * gap:.0f}s por símbolo")
    print(f" Hora UTC: {fmt_utc(utcnow())} · ET: {_et().strftime('%H:%M:%S')}")

    results = {}

    for symbol in symbols:
        print_section(f"{symbol}")
        samples = []
        for i in range(iters):
            t0 = utcnow()
            data = fetch_symbol(symbol, BASE_FIELDS)
            if isinstance(data, dict):
                samples.append((t0, data))
                print(f"  [{i+1:02d}/{iters}] {t0.strftime('%H:%M:%S')} "
                      f"close={fmt_value(data.get('close'))} "
                      f"vol={fmt_value(data.get('volume'))} "
                      f"RSI={fmt_value(data.get('RSI'))}")
            elif data == "429":
                print(f"  [{i+1:02d}/{iters}] {t0.strftime('%H:%M:%S')} 429")
            else:
                print(f"  [{i+1:02d}/{iters}] {t0.strftime('%H:%M:%S')} sin datos")
            if i < iters - 1:
                time.sleep(gap)

        if len(samples) < 2:
            results[symbol] = {"error": "muestras insuficientes"}
            continue

        analysis = {"n_samples": len(samples), "fields": {}}
        for field in BASE_FIELDS:
            values = [s[1].get(field) for s in samples if s[1].get(field) is not None]
            if not values:
                analysis["fields"][field] = {"n_unique": 0, "note": "todos None"}
                continue
            unique = list(dict.fromkeys([str(v) for v in values]))
            analysis["fields"][field] = {
                "n_unique": len(unique),
                "sample_values": unique[:4],
            }

        # Deltas entre valores distintos para campos clave
        analysis["deltas"] = {}
        for field in ["close", "volume"]:
            changes = []
            last = object()
            for ts, data in samples:
                v = data.get(field)
                if v != last:
                    changes.append(ts)
                    last = v
            if len(changes) >= 2:
                deltas = [(changes[i] - changes[i-1]).total_seconds()
                          for i in range(1, len(changes))]
                analysis["deltas"][field] = {
                    "n_changes": len(deltas),
                    "min_s": min(deltas),
                    "max_s": max(deltas),
                    "avg_s": sum(deltas) / len(deltas),
                }

        results[symbol] = analysis

        print(f"\n  Resumen {symbol}:")
        for field, info in analysis["fields"].items():
            if info.get("n_unique", 0) <= 1:
                vals = info.get("sample_values") or ["None"]
                print(f"    ✓ {field:28s} estable → {vals[0]}")
            else:
                vals = info.get("sample_values", [])[:3]
                print(f"    ⚠ {field:28s} cambia ({info['n_unique']} únicos): {vals}")
        if analysis["deltas"]:
            print(f"\n  Deltas entre valores distintos:")
            for field, d in analysis["deltas"].items():
                print(f"    {field:10s}: {d['n_changes']} cambios · "
                      f"min={d['min_s']:.1f}s avg={d['avg_s']:.1f}s max={d['max_s']:.1f}s")

    return results


# =============================================================================
# TEST B · Variación por timeframe
# =============================================================================

def test_b_timeframes(symbols: list[str]) -> dict:
    print_header("TEST B · Variación por timeframe")
    print(f" Símbolos: {symbols}")

    all_fields = list(BASE_FIELDS)
    for tf in TIMEFRAMES:
        if tf is None:
            continue
        for f in BASE_FIELDS:
            all_fields.append(f"{f}|{tf}")

    results = {}

    for symbol in symbols:
        print_section(f"{symbol}")
        data = fetch_symbol(symbol, all_fields)
        if not isinstance(data, dict):
            print(f"  Error: {data}")
            results[symbol] = {"error": str(data)}
            continue

        row = {}
        for f in BASE_FIELDS:
            entry = {"base": data.get(f)}
            for tf in TIMEFRAMES:
                if tf is None:
                    continue
                entry[f"|{tf}"] = data.get(f"{f}|{tf}")
            row[f] = entry
            print(f"  {f:25s} base={fmt_value(entry['base']):>14s}  " +
                  " ".join(f"{tf}={fmt_value(entry.get(f'|{tf}'))}"
                           for tf in TIMEFRAMES if tf is not None))
        results[symbol] = row

    return results


# =============================================================================
# TEST C · Cruce de frontera de barra
# =============================================================================

def test_c_bar_boundary(symbol: str, tf_minutes: int = 15) -> dict:
    print_header(f"TEST C · Cruce de frontera de barra · {symbol} · TF={tf_minutes}m")

    if not is_nyse_open():
        print(f" ⚠ NYSE parece cerrada ({_et().strftime('%H:%M')} ET).")

    fields = [
        "close", "volume", "change",
        f"RSI|{tf_minutes}", f"volume|{tf_minutes}", f"change|{tf_minutes}",
        f"ADX|{tf_minutes}", f"CCI20|{tf_minutes}", f"BBPower|{tf_minutes}",
        "RSI", "ADX",
    ]

    wait_s = seconds_until_next_bar(tf_minutes)
    print(f" Hora actual: {fmt_utc(utcnow())} UTC · {_et().strftime('%H:%M:%S')} ET")
    print(f" Próxima frontera en {wait_s:.1f}s · muestreo desde T-40s a T+40s")

    target = wait_s - 40
    if target > 0:
        time.sleep(target)

    samples = []
    for i in range(16):
        t0 = utcnow()
        data = fetch_symbol(symbol, fields)
        if isinstance(data, dict):
            samples.append((t0, data))
            print(f"  [{i+1:02d}] {t0.strftime('%H:%M:%S')} "
                  f"close={fmt_value(data.get('close'))} "
                  f"vol|{tf_minutes}={fmt_value(data.get(f'volume|{tf_minutes}'))} "
                  f"RSI|{tf_minutes}={fmt_value(data.get(f'RSI|{tf_minutes}'))} "
                  f"chg|{tf_minutes}={fmt_value(data.get(f'change|{tf_minutes}'))}")
        else:
            print(f"  [{i+1:02d}] {t0.strftime('%H:%M:%S')} error: {data}")
        time.sleep(5)

    return {"symbol": symbol, "tf_minutes": tf_minutes, "samples": samples}


# =============================================================================
# TEST D · update_mode
# =============================================================================

def test_d_update_mode(symbols: list[str]) -> dict:
    print_header("TEST D · update_mode por símbolo")
    print(f" Símbolos: {symbols}")

    results = {}
    for symbol in symbols:
        data = fetch_symbol(symbol, ["close", "update_mode"])
        if isinstance(data, dict):
            mode = data.get("update_mode")
            close = data.get("close")
            results[symbol] = {"update_mode": mode, "close": close}
            tag = "⏱" if mode and "delayed" in str(mode) else ("✓" if mode == "streaming" else "?")
            print(f"  {tag} {symbol:35s} update_mode={str(mode):30s} close={fmt_value(close)}")
        else:
            print(f"  ✗ {symbol:35s} error: {data}")
            results[symbol] = {"error": str(data)}
    return results


# =============================================================================
# TEST E · Pre-market
# =============================================================================

def test_e_premarket(symbols: list[str]) -> dict:
    print_header("TEST E · Campos de pre-market")
    print(f" Símbolos: {symbols}")

    if not in_premarket():
        print(f" ⚠ No estamos en 09:00–09:30 ET ({_et().strftime('%H:%M')} ET).")
        print(f"   Los campos premarket_* solo tendrán valor real en pre-apertura.")

    results = {}
    for symbol in symbols:
        data = fetch_symbol(symbol, PREMARKET_FIELDS)
        if isinstance(data, dict):
            row = {}
            print(f"\n  {symbol}:")
            for f in PREMARKET_FIELDS:
                present = f in data
                val = data.get(f)
                row[f] = val
                mark = "✓" if present else "·"
                print(f"    {mark} {f:25s} = {fmt_value(val)}")
            results[symbol] = row
        else:
            print(f"  ✗ {symbol}: {data}")
            results[symbol] = {"error": str(data)}
    return results


# =============================================================================
# TEST F · Equivalencia de FX
# =============================================================================

def test_f_fx_equivalence() -> dict:
    print_header("TEST F · Equivalencia de símbolos FX (Q23)")
    print(f" Variantes: {FX_VARIANTS}")

    fields = ["close", "volume", "update_mode", "change"]
    results = {}

    for symbol in FX_VARIANTS:
        data = fetch_symbol(symbol, fields)
        if isinstance(data, dict):
            row = {f: data.get(f) for f in fields}
            results[symbol] = row
            print(f"  {symbol:20s} " +
                  " | ".join(f"{f}={fmt_value(row[f])}" for f in fields))
        else:
            print(f"  {symbol:20s} error: {data}")
            results[symbol] = {"error": str(data)}

    valid = {k: v for k, v in results.items() if isinstance(v, dict) and "close" in v}
    if len(valid) >= 2:
        keys = list(valid.keys())
        same_close = len(set(str(valid[k].get("close")) for k in keys)) == 1
        same_vol = len(set(str(valid[k].get("volume")) for k in keys)) == 1
        same_mode = len(set(str(valid[k].get("update_mode")) for k in keys)) == 1
        print(f"\n  close idéntico:    {same_close}")
        print(f"  volume idéntico:   {same_vol}")
        print(f"  update_mode igual: {same_mode}")
        if same_close and same_mode:
            print(f"  → Probablemente MISMO feed subyacente")
        else:
            print(f"  → Feeds DISTINTOS · elegir uno como canónico en producción")

    return results


# =============================================================================
# TEST G · POST /scan con sufijos
# =============================================================================

def test_g_scan_post(tickers: list[str]) -> dict:
    print_header("TEST G · POST /scan con sufijos (Q16)")
    print(f" Tickers: {tickers}")

    columns = [
        "close", "volume", "RSI",
        "RSI|15", "ADX|15", "CCI20|15", "BBPower|15",
        "change|15", "volume|15",
        "Pivot.M.Camarilla.R3", "Pivot.M.Camarilla.R3|15",
        "Perf.W", "update_mode",
    ]

    t0 = time.time()
    resp = post_scan(tickers, columns)
    elapsed = time.time() - t0
    print(f" Latencia: {elapsed*1000:.0f} ms")

    if "_error" in resp:
        print(f" ✗ {resp['_error']}")
        print(f"   Body: {resp.get('_body', '')[:400]}")
        return resp

    data = resp.get("data", [])
    print(f" Símbolos devueltos: {len(data)}")
    results = {}
    for item in data:
        sym = item.get("s")
        d = item.get("d", [])
        if len(d) != len(columns):
            print(f"  ⚠ {sym}: {len(d)} valores vs {len(columns)} columnas")
        row = dict(zip(columns, d))
        results[sym] = row
        print(f"\n  {sym}:")
        for c in columns:
            print(f"    {c:30s} = {fmt_value(row.get(c))}")

    return results


# =============================================================================
# TEST H · Variantes de pivote
# =============================================================================

def test_h_pivots(symbols: list[str]) -> dict:
    print_header("TEST H · Variantes de pivote Camarilla (H22, Q17)")
    print(f" Símbolos: {symbols}")

    results = {}
    for symbol in symbols:
        print_section(f"{symbol}")
        data = fetch_symbol(symbol, PIVOT_VARIANTS)
        if isinstance(data, dict):
            row = {}
            for f in PIVOT_VARIANTS:
                v = data.get(f)
                row[f] = v
                mark = "✓" if v is not None else "✗"
                print(f"    {mark} {f:35s} = {fmt_value(v)}")
            results[symbol] = row
        else:
            print(f"  Error: {data}")
            results[symbol] = {"error": str(data)}

    print("\n  Agrupación de pares (|5 vs |15 y |30 vs |60):")
    for symbol, row in results.items():
        if "error" in row:
            continue
        v5, v15 = row.get("Pivot.M.Camarilla.R3|5"), row.get("Pivot.M.Camarilla.R3|15")
        v30, v60 = row.get("Pivot.M.Camarilla.R3|30"), row.get("Pivot.M.Camarilla.R3|60")
        pair1 = "IGUALES" if (v5 is not None and v15 is not None and str(v5) == str(v15)) else "DISTINTOS"
        pair2 = "IGUALES" if (v30 is not None and v60 is not None and str(v30) == str(v60)) else "DISTINTOS"
        print(f"    {symbol}: |5 vs |15 → {pair1} · |30 vs |60 → {pair2}")

    return results


# =============================================================================
# TEST I · Gate por clase de activo
# =============================================================================

def test_i_gate_by_class() -> dict:
    print_header("TEST I · Gate por clase de activo (Q22, H4)")
    print(f" Hora UTC: {fmt_utc(utcnow())} · ET: {_et().strftime('%H:%M:%S')}")
    print(f" NYSE abierta (aprox): {is_nyse_open()}")

    sample = {
        "equity":  "NASDAQ:NVDA",
        "etf":     "AMEX:SPY",
        "fx":      "FX_IDC:EURUSD",
        "crypto":  "BINANCE:BTCUSDT",
        "future":  "CME_MINI:NQ1!",
    }

    results = {}
    print("\n  3 muestras separadas por 5s por clase:")
    for klass, symbol in sample.items():
        closes, vols = [], []
        for _ in range(3):
            data = fetch_symbol(symbol, ["close", "volume"])
            if isinstance(data, dict):
                closes.append(data.get("close"))
                vols.append(data.get("volume"))
            time.sleep(5)
        close_moves = len(set(str(c) for c in closes if c is not None)) > 1
        vol_moves = len(set(str(v) for v in vols if v is not None)) > 1
        icon = "✓" if (close_moves or vol_moves) else "✗"
        results[klass] = {
            "symbol": symbol,
            "close_moves": close_moves,
            "vol_moves": vol_moves,
            "closes": closes,
            "volumes": vols,
        }
        print(f"    {icon} {klass:8s} {symbol:22s} "
              f"close_mueve={close_moves} vol_mueve={vol_moves}")

    return results


# =============================================================================
# MAIN
# =============================================================================

ALL_TESTS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

TEST_DESCRIPTIONS = {
    "A": "Consistencia intra-minuto (H24, H19)",
    "B": "Variación por timeframe",
    "C": "Cruce de frontera de barra (H19, H21)",
    "D": "update_mode (H1)",
    "E": "Pre-market (H6, H20)",
    "F": "Equivalencia FX (Q23, Q24)",
    "G": "POST /scan con sufijos (Q16)",
    "H": "Pivotes (H22, Q17)",
    "I": "Gate por clase (Q22)",
}


def main():
    p = argparse.ArgumentParser(
        description="Diagnóstico extendido endpoint TradingView (v2)."
    )
    p.add_argument("--test", default="all",
                   help=f"Tests a ejecutar, coma-separado ({','.join(ALL_TESTS)}) o 'all'")
    p.add_argument("--symbol", action="append",
                   help="Símbolo adicional (repetible)")
    p.add_argument("--iters", type=int, default=12,
                   help="Iteraciones del Test A (default 12)")
    p.add_argument("--gap", type=float, default=5.0,
                   help="Segundos entre muestras del Test A (default 5.0)")
    p.add_argument("--force", action="store_true",
                   help="Ignorar gate de horario NYSE")
    args = p.parse_args()

    # Parsear tests
    if args.test == "all":
        tests = ALL_TESTS
    else:
        tests = [t.strip().upper() for t in args.test.split(",")]
        invalid = [t for t in tests if t not in ALL_TESTS]
        if invalid:
            print(f"Error: tests inválidos {invalid}. Opciones: {ALL_TESTS}", file=sys.stderr)
            sys.exit(1)

    symbols = args.symbol or DEFAULT_SYMBOLS

    # Cabecera
    print("=" * 80)
    print(" DIAGNÓSTICO EXTENDIDO ENDPOINT TRADINGVIEW · v2")
    print("=" * 80)
    print(f" Fecha UTC:  {fmt_utc(utcnow())}")
    print(f" Fecha ET:   {_et().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" NYSE abierta (aprox): {is_nyse_open()}")
    print(f" Pre-market (aprox):   {in_premarket()}")
    print(f" Tests a correr:")
    for t in tests:
        print(f"   {t} — {TEST_DESCRIPTIONS[t]}")
    print(f" Símbolos: {symbols}")
    print()

    if not args.force and not is_nyse_open():
        print(" ⚠ NYSE parece cerrada.")
        print("   Test C (frontera de barra) y Test E (pre-market) rinden menos fuera de sesión.")
        print("   Ejecutá igual con --force, o esperá a la ventana 09:30–16:00 ET.")

    all_results = {}

    if "A" in tests:
        all_results["A_consistency"] = test_a_consistency(symbols, args.iters, args.gap)

    if "B" in tests:
        all_results["B_timeframes"] = test_b_timeframes(symbols)

    if "C" in tests:
        all_results["C_bar_boundary"] = test_c_bar_boundary(symbols[0], tf_minutes=15)

    if "D" in tests:
        extras = ["TVC:VIX", "CBOE:VX1!", "CME_MINI:ES1!", "CME_MINI:NQ1!", "BINANCE:BTCUSDT"]
        universe_d = list(dict.fromkeys(symbols + extras))
        all_results["D_update_mode"] = test_d_update_mode(universe_d)

    if "E" in tests:
        all_results["E_premarket"] = test_e_premarket(symbols)

    if "F" in tests:
        all_results["F_fx_equivalence"] = test_f_fx_equivalence()

    if "G" in tests:
        all_results["G_scan_post"] = test_g_scan_post(symbols[:5])

    if "H" in tests:
        all_results["H_pivots"] = test_h_pivots(symbols[:3])

    if "I" in tests:
        all_results["I_gate_by_class"] = test_i_gate_by_class()

    # Guardar JSON
    ts = utcnow().strftime("%Y%m%d_%H%M%S")
    out = f"wztest_v2_result_{ts}.json"
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(_serializable(all_results), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Resultados guardados: {out}")
    except Exception as e:
        print(f"\n⚠ No se pudo guardar JSON: {e}")

    print("\nDiagnóstico v2 completo.")


if __name__ == "__main__":
    main()
    # Cómo usarlo mañana
    # Antes de la apertura (12:45 UTC = 08:45 ET)
    # bash
    # # Test D y F — rápidos, no requieren mercado abierto
    # python3 wztest_scraper_timeframes_v2.py --test D,F,G,H
    # Esto te cierra H1 (update_mode), Q16 (/scan), H22 (pivotes) y Q23 (FX) sin esperar la apertura.

    # En pre-market (13:00–13:30 UTC = 09:00–09:30 ET)
    # bash
    # # Test E — pre-market real
    # python3 wztest_scraper_timeframes_v2.py --test E --force
    # Esto cierra H6 y H20.

    # Justo antes de la apertura (13:25 UTC)
    # bash
    # # Test A — consistencia con mercado abierto
    # python3 wztest_scraper_timeframes_v2.py --test A --iters 18 --gap 5
    # 18 muestras × 5 s × 3 símbolos ≈ 4.5 min. Cubre el minuto previo a la campana y los primeros minutos de sesión. Cierra H24.

    # Al cruzar los :15, :30, :45 (durante toda la sesión)
    # bash
    # # Test C — cruce de frontera
    # python3 wztest_scraper_timeframes_v2.py --test C
    # Correlo tres veces (una por cada frontera). Cierra H19 y H21 definitivamente.

    # Una corrida completa al mediodía (17:00 UTC = 13:00 ET)
    # bash
    # # Todo, con el mercado en plena actividad
    # python3 wztest_scraper_timeframes_v2.py
    # Duración total ≈ 25–45 min (depende de dónde caiga la frontera del Test C).

    # Qué resuelve cada test (mapeo directo al informe v3)
    # Test	Hipótesis / Dudas cerradas
    # A	H24 (refresco real acciones), H19 (parcial)
    # B	Confirmación sufijos |TF
    # C	H19 ✅, H21 ✅ (repintado y frontera)
    # D	H1 ✅, H7b (parcial)
    # E	H6 ✅, H20 ✅, H7b
    # F	Q23 ✅, Q24 (parcial)
    # G	Q16 ✅, H7b ✅
    # H	H22 ✅, Q17 ✅
    # I	Q22 ✅, H4 ✅
    # Con una corrida completa en horario de mercado, el informe v3 se cierra al 90%: de las 24 hipótesis, 
    # quedan pendientes solo H13 y H14 (que requieren semanas de datos, no una jornada).