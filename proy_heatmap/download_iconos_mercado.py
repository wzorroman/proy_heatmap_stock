#!/usr/bin/env python3
"""
DESCARGA DE ICONOS DE MERCADO
=============================
Para cada activo en dim_asset:
  1. Calcula `slug` a partir del symbol (sin caracteres especiales).
  2. Resuelve el logo (logoid de TradingView, fallback oro/plata y crypto
     vía CoinGecko) y arma `url_logo`.
  3. Guarda ambos en dim_asset (columnas slug y url_logo).
  4. Descarga el icono en static/iconos_mercado/{slug}.svg|.png.

Uso:
    python download_iconos_mercado.py                 # puebla BD + descarga
    python download_iconos_mercado.py --db-only       # solo puebla slug/url_logo
    python download_iconos_mercado.py --skip-db       # solo descarga
    python download_iconos_mercado.py --refresh       # fuerza re-descarga
    python download_iconos_mercado.py --parallel 8

Dependencias: requests, psycopg2, python-dotenv (ver requirements.txt).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402  (carga .env y expone PG_* y HEATMAP_*)

LOGO_DIR = BASE_DIR / "static" / "iconos_mercado"
HEATMAP_CSV = REPO_ROOT / "heatmap" / "heatmap_v3.csv"
LOGO_URL_TPL = "https://s3-symbol-logo.tradingview.com/{logoid}.svg"
HEATMAP_URL = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"
SCANNER_URL = "https://scanner.tradingview.com/{region}/scan"
LOG_COLUMNS = ["logoid", "name", "description"]
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/markets"

# logoid que TradingView sirve para commodities sin ticker de bolsa
FALLBACK_LOGOS: dict[str, str] = {
    "OANDA:XAUUSD": "gold",
    "SAXO:XAUUSD": "gold",
    "TVC:SILVER": "silver",
}


def slugify(symbol: str) -> str:
    """Convierte un symbol (ej. NASDAQ:NVDA) en un slug seguro para archivo."""
    s = re.sub(r"[^a-z0-9]+", "_", symbol.lower().strip()).strip("_")
    return s or "activo"


def _scanner_region(symbol: str) -> str:
    ex = symbol.split(":", 1)[0]
    if ex in ("BINANCE", "BITSTAMP", "BYBIT", "OKX", "COINBASE"):
        return "crypto"
    if ex in ("FX_IDC", "OANDA", "FXCM", "SAXO"):
        return "forex"
    if ex in ("CME", "CME_MINI", "CBOT", "NYMEX", "ICEUS", "CBOE"):
        return "futures"
    return "america"


def _ext(logo_url: str) -> str:
    base = logo_url.split("?", 1)[0].rstrip("/")
    return ".png" if base.lower().endswith(".png") else ".svg"


def _bad_logoid(logoid: str) -> bool:
    """Descartar pseudologos de TradingView (banderas de país) que no son iconos."""
    return bool(re.match(r"^country(/|$)", logoid))


def fetch_heatmap_logoid_map() -> dict[str, str]:
    """{symbol: logoid} descargando el heatmap real de TradingView."""
    res = requests.post(
        HEATMAP_URL, headers=config.HEATMAP_HEADERS,
        json=config.HEATMAP_BODY, timeout=config.HEATMAP_TIMEOUT,
    )
    res.raise_for_status()
    m: dict[str, str] = {}
    for item in res.json().get("data", []) or []:
        if not isinstance(item, dict):
            continue
        d = item.get("d", [])
        if isinstance(d, list) and len(d) > 23:
            logoid = d[22]
            if isinstance(logoid, str) and logoid and not _bad_logoid(logoid):
                m[item.get("s", "")] = logoid
    return m


def load_csv_logoid_map() -> dict[str, str]:
    """Fallback {symbol: logoid} desde el CSV local del heatmap."""
    m: dict[str, str] = {}
    with HEATMAP_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = (row.get("symbol") or "").strip()
            logoid = (row.get("logoid") or "").strip()
            if sym and logoid and not _bad_logoid(logoid):
                m[sym] = logoid
    return m


def fetch_symbol_logoid(symbol: str, headers: dict[str, str]) -> str:
    """logoid por ticker en el scanner regional."""
    region = _scanner_region(symbol)
    body = {"symbols": {"tickers": [symbol]}, "columns": LOG_COLUMNS, "no_404": True}
    res = requests.post(
        SCANNER_URL.format(region=region), headers=headers,
        json=body, timeout=config.HEATMAP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json().get("data", []) or []
    if data:
        d = data[0].get("d", [])
        if isinstance(d, list) and d and isinstance(d[0], str):
            return d[0] if not _bad_logoid(d[0]) else ""
    return ""


def fetch_crypto_logo_map(crypto_symbols: list[str], headers: dict[str, str]) -> dict[str, str]:
    """URL CoinGecko para pares crypto (mapa symbol -> image_url)."""
    m: dict[str, str] = {}
    if not crypto_symbols:
        return m
    try:
        res = requests.get(
            COINGECKO_API,
            params={"vs_currency": "usd", "per_page": 250},
            headers=headers, timeout=30,
        )
        res.raise_for_status()
        base_coin = {c["symbol"]: c["image"] for c in res.json()}
        for sym in crypto_symbols:
            ticker = sym.split(":", 1)[-1].lower()
            if ticker == "btcusd":
                ticker = "btc"
            if ticker == "btcusdt":
                ticker = "btc"
            img = base_coin.get(ticker)
            if img:
                m[sym] = img
    except Exception as e:
        print(f"[crypto] CoinGecko fallo: {e}")
    return m


def build_logo_map(symbols: list[str]) -> dict[str, str]:
    """Construye {symbol: url_logo} combinando heatmap, scanner y fallbacks.

    Orden de resolución:
      1. logoid del endpoint del heatmap (o CSV local si el endpoint falla)
      2. scanner regional por ticker (incluye acciones OTC y futuros)
      3. fallback manual (oro/plata en el bucket de TradingView)
      4. CoinGecko para crypto
    """
    url_map: dict[str, str] = {}

    logoid_map: dict[str, str] = {}
    try:
        logoid_map.update(fetch_heatmap_logoid_map())
        print(f"[heatmap] logoids del endpoint: {len(logoid_map)}")
    except Exception as e:
        print(f"[heatmap] fallo el endpoint ({e}); usando CSV local")
        logoid_map.update(load_csv_logoid_map())
        print(f"[heatmap] logoids desde CSV local: {len(logoid_map)}")

    for sym, logoid in logoid_map.items():
        if logoid and sym in symbols:
            url_map.setdefault(sym, LOGO_URL_TPL.format(logoid=logoid))

    pending = [s for s in symbols if s not in url_map]
    pend_region: dict[str, list[str]] = {}
    for s in pending:
        pend_region.setdefault(_scanner_region(s), []).append(s)

    for region, syms in sorted(pend_region.items()):
        ok = 0
        for s in syms:
            try:
                logoid = fetch_symbol_logoid(s, config.HEATMAP_HEADERS)
                if logoid:
                    url_map[s] = LOGO_URL_TPL.format(logoid=logoid)
                    ok += 1
            except Exception:
                continue
        print(f"[scanner:{region}] logoids extra: {ok}/{len(syms)}")

    for sym, logoid in FALLBACK_LOGOS.items():
        if sym not in url_map:
            url_map[sym] = LOGO_URL_TPL.format(logoid=logoid)

    pending_crypto = [s for s in symbols if s not in url_map
                      and _scanner_region(s) == "crypto"]
    if pending_crypto:
        crypto_map = fetch_crypto_logo_map(pending_crypto, config.HEATMAP_HEADERS)
        for sym, img in crypto_map.items():
            url_map[sym] = img
        print(f"[crypto] CoinGecko: {len(crypto_map)}/{len(pending_crypto)}")

    return url_map


def download_logo(slug: str, url: str, out_dir: Path, refresh: bool,
                  session: requests.Session) -> tuple[bool, str]:
    target = out_dir / f"{slug}{_ext(url)}"
    if target.exists() and not refresh:
        return True, "exists"
    s = session or requests
    try:
        with s.get(url, timeout=60) as r:
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}"
            target.write_bytes(r.content)
        return True, "ok"
    except requests.RequestException as e:
        return False, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description="Puebla slug/url_logo y descarga iconos.")
    parser.add_argument("--db-only", action="store_true", help="Solo actualizar BD")
    parser.add_argument("--skip-db", action="store_true", help="Solo descargar iconos")
    parser.add_argument("--refresh", action="store_true", help="Re-descargar iconos existentes")
    parser.add_argument("--parallel", type=int, default=4, help="Descargas concurrentes (default 4)")
    args = parser.parse_args()

    import psycopg2

    conn = psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT, dbname=config.PG_DATABASE,
        user=config.PG_USER, password=config.PG_PASSWORD,
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, COALESCE(url_logo,'') FROM dim_asset "
        "WHERE is_active ORDER BY asset_class, symbol"
    )
    rows = [(r[0], r[1] or "") for r in cur.fetchall()]
    symbols = [r[0] for r in rows]
    existing_urls = dict(rows)
    print(f"[bd] {len(symbols)} activos en dim_asset")

    t0 = time.perf_counter()
    url_map = build_logo_map(symbols)
    print(f"[logoid] mapa de logos en {round(time.perf_counter() - t0, 2)}s "
          f"({len(url_map)} resueltos)")

    if not args.skip_db:
        updated = 0
        for sym in symbols:
            slug = slugify(sym)
            new_url = url_map.get(sym)
            old_url = existing_urls.get(sym) or None
            if new_url != old_url:
                cur.execute(
                    "UPDATE dim_asset SET slug = %s, url_logo = %s, "
                    "updated_at = CURRENT_TIMESTAMP WHERE symbol = %s",
                    (slug, new_url, sym),
                )
                updated += 1
        cur.execute(
            "SELECT symbol FROM dim_asset WHERE slug IS NULL"
        )
        pend = [r[0] for r in cur.fetchall()]
        for sym in pend:
            cur.execute(
                "UPDATE dim_asset SET slug = %s, updated_at = CURRENT_TIMESTAMP "
                "WHERE symbol = %s",
                (slugify(sym), sym),
            )
        print(f"[bd] slug/url_logo actualizados: {updated}; slugs pendientes: {len(pend)}")
    conn.close()

    if args.db_only:
        return 0

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(config.HEATMAP_HEADERS)

    conn = psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT, dbname=config.PG_DATABASE,
        user=config.PG_USER, password=config.PG_PASSWORD,
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, url_logo FROM dim_asset "
        "WHERE is_active AND url_logo IS NOT NULL AND url_logo <> ''"
    )
    targets = cur.fetchall()
    conn.close()

    downloaded = skipped = 0
    sin_logo: list[str] = []
    for sym, url in targets:
        slug = slugify(sym)
        ok, reason = download_logo(slug, url, LOGO_DIR, refresh=args.refresh, session=session)
        if ok:
            downloaded += 1
        else:
            skipped += 1
            sin_logo.append(f"{sym} -> {reason}")

    missing = [s for s in symbols if s not in url_map]

    print("\n=== RESUMEN ===")
    print(f"  Iconos descargados:  {downloaded}")
    print(f"  Fallos de descarga:  {skipped}")
    print(f"  Sin logo disponible: {len(missing)}")
    if missing:
        for s in missing:
            print("    ", s)
    print(f"  Carpeta:            {LOGO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())