#!/usr/bin/env python3
"""Versión v3 del exportador del heatmap de TradingView.

Descarga datos reales del endpoint del scanner usando requests puro.
No requiere Playwright ni fallback.

Uso:
    . .venv/bin/activate && python heatmap/export_heatmap_v3.py
    . .venv/bin/activate && python heatmap/export_heatmap_v3.py --output heatmap/heatmap_v3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
URL = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://es.tradingview.com",
    "referer": "https://es.tradingview.com/heatmap/stock/",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
}

COLUMNS = [
    "typespecs",
    "change",
    "change_abs",
    "Perf.1M",
    "Perf.3M",
    "Perf.6M",
    "Perf.Y",
    "Perf.YTD",
    "Volatility.D",
    "price_52_week_high",
    "price_52_week_low",
    "market_cap_basic",
    "average_volume_30d_calc",
    "average_volume_10d_calc",
    "volume",
    "total_shares_outstanding",
    "total_shares_outstanding_fundamental",
    "number_of_employees",
    "earnings_per_share_basic_ttm",
    "revenue_per_employee_ttm",
    "gross_profit_1Y_growth_fq",
    "sector",
    "logoid",
    "close",
    "pricescale",
    "name",
    "update_mode",
    "currency",
]

POST_BODY = {
    "columns": COLUMNS,
    "markets": ["america"],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def fetch_heatmap() -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch real data from the scanner endpoint.

    Returns (payload, timing_info).
    """
    t0 = time.perf_counter()
    response = requests.post(URL, headers=HEADERS, json=POST_BODY, timeout=60)
    t_fetch = time.perf_counter() - t0
    response.raise_for_status()

    t0_parse = time.perf_counter()
    payload = response.json()
    t_parse = time.perf_counter() - t0_parse

    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError(f"Respuesta inesperada: {payload}")

    items = payload.get("data", []) or []
    has_data = any(
        isinstance(it, dict) and isinstance(it.get("d"), list) and len(it["d"]) > 0
        for it in items
    )
    if not has_data:
        raise ValueError(
            f"El endpoint devolvió {len(items)} items pero todos con d[] vacío"
        )

    timing = {
        "fetch_seconds": round(t_fetch, 3),
        "parse_seconds": round(t_parse, 3),
        "total_seconds": round(t_fetch + t_parse, 3),
        "items_count": len(items),
        "total_count": payload.get("totalCount"),
    }
    return payload, timing


def safe(raw: list[Any], idx: int, default: Any = "") -> Any:
    if not isinstance(raw, list) or len(raw) <= idx:
        return default
    return raw[idx]


def direction_from_value(value: Any) -> str:
    if value in (None, "", "nan"):
        return "neutral"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if num > 0:
        return "buy"
    if num < 0:
        return "sell"
    return "neutral"


def normalize_symbol(item: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    symbol = item.get("s", "")
    raw = item.get("d", [])

    field_map = {col: safe(raw, idx) for idx, col in enumerate(columns)}

    exchange = ""
    base_ticker = symbol
    if ":" in symbol:
        exchange, base_ticker = symbol.split(":", 1)

    typespecs = field_map.get("typespecs", "")
    security_type = ""
    if isinstance(typespecs, list) and typespecs:
        security_type = str(typespecs[0])

    change_pct = field_map.get("change", "")
    market_cap = field_map.get("market_cap_basic", "")
    price = field_map.get("close", "")

    market_cap_trillions = ""
    if market_cap not in (None, ""):
        try:
            market_cap_trillions = round(float(market_cap) / 1_000_000_000_000, 4)
        except (TypeError, ValueError):
            pass

    return {
        "symbol": symbol,
        "exchange": exchange,
        "ticker": field_map.get("name", ""),
        "company_name": field_map.get("description", ""),
        "security_type": security_type,
        "sector": field_map.get("sector", ""),
        "currency": field_map.get("currency", ""),
        "price": price,
        "pricescale": field_map.get("pricescale", ""),
        "market_cap": market_cap,
        "market_cap_trillions": market_cap_trillions,
        "daily_change_pct": change_pct,
        "daily_change_abs": field_map.get("change_abs", ""),
        "perf_1m": field_map.get("Perf.1M", ""),
        "perf_3m": field_map.get("Perf.3M", ""),
        "perf_6m": field_map.get("Perf.6M", ""),
        "perf_y": field_map.get("Perf.Y", ""),
        "perf_ytd": field_map.get("Perf.YTD", ""),
        "volatility_d": field_map.get("Volatility.D", ""),
        "price_52w_high": field_map.get("price_52_week_high", ""),
        "price_52w_low": field_map.get("price_52_week_low", ""),
        "avg_volume_30d": field_map.get("average_volume_30d_calc", ""),
        "avg_volume_10d": field_map.get("average_volume_10d_calc", ""),
        "volume": field_map.get("volume", ""),
        "shares_outstanding": field_map.get("total_shares_outstanding", ""),
        "shares_outstanding_fund": field_map.get("total_shares_outstanding_fundamental", ""),
        "employees": field_map.get("number_of_employees", ""),
        "eps_ttm": field_map.get("earnings_per_share_basic_ttm", ""),
        "revenue_per_employee": field_map.get("revenue_per_employee_ttm", ""),
        "gross_profit_1y_growth": field_map.get("gross_profit_1Y_growth_fq", ""),
        "logoid": field_map.get("logoid", ""),
        "update_mode": field_map.get("update_mode", ""),
        "market_direction": direction_from_value(change_pct),
    }


def export_csv(rows: list[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Sin registros para exportar")

    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_raw_csv(payload: dict[str, Any], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    items = payload.get("data", []) or []

    fieldnames = ["symbol", "raw_d_json", "raw_d_len", "exported_at_utc"]
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            if not isinstance(item, dict):
                continue
            d = item.get("d", [])
            writer.writerow({
                "symbol": item.get("s", ""),
                "raw_d_json": json.dumps(d, ensure_ascii=False),
                "raw_d_len": len(d) if isinstance(d, list) else 0,
                "exported_at_utc": now_str,
            })
    return len(items)


def export_raw_json(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta datos reales del heatmap de TradingView (v3)."
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "heatmap" / "heatmap_v3.csv"),
        help="Ruta del CSV normalizado",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    timestamp = utc_timestamp()

    print(f"Descargando datos del endpoint...")
    payload, timing = fetch_heatmap()
    print(f"  Descarga: {timing['fetch_seconds']}s")
    print(f"  Parse:    {timing['parse_seconds']}s")
    print(f"  Total:    {timing['total_seconds']}s")
    print(f"  Items:    {timing['items_count']} (totalCount: {timing['total_count']})")

    print(f"\nNormalizando registros...")
    t0 = time.perf_counter()
    items = payload.get("data", []) or []
    normalized = [normalize_symbol(item, COLUMNS) for item in items if isinstance(item, dict)]
    t_norm = time.perf_counter() - t0
    print(f"  Normalizados: {len(normalized)} en {round(t_norm, 3)}s")

    csv_path = output_path
    raw_csv_path = output_path.with_name(f"heatmap_v3_raw_{timestamp}.csv")
    raw_json_path = output_path.with_name(f"heatmap_v3_raw_{timestamp}.json")

    print(f"\nExportando CSV normalizado...")
    t0 = time.perf_counter()
    csv_count = export_csv(normalized, csv_path)
    t_csv = time.perf_counter() - t0
    print(f"  {csv_count} filas -> {csv_path.name} ({round(t_csv, 3)}s)")

    print(f"Exportando CSV raw...")
    t0 = time.perf_counter()
    raw_csv_count = export_raw_csv(payload, raw_csv_path)
    t_raw_csv = time.perf_counter() - t0
    print(f"  {raw_csv_count} filas -> {raw_csv_path.name} ({round(t_raw_csv, 3)}s)")

    print(f"Exportando JSON crudo...")
    t0 = time.perf_counter()
    export_raw_json(payload, raw_json_path)
    t_raw_json = time.perf_counter() - t0
    print(f"  -> {raw_json_path.name} ({round(t_raw_json, 3)}s)")

    total_export = t_csv + t_raw_csv + t_raw_json
    total_all = timing["total_seconds"] + t_norm + total_export

    print(f"\n=== RESUMEN ===")
    print(f"  Fetch + parse:  {timing['total_seconds']}s")
    print(f"  Normalizacion:  {round(t_norm, 3)}s")
    print(f"  Export total:   {round(total_export, 3)}s")
    print(f"  TOTAL:          {round(total_all, 3)}s")
    print(f"  Simbolos:       {csv_count}")
    print(f"  CSV:            {csv_path}")
    print(f"  Raw CSV:        {raw_csv_path}")
    print(f"  Raw JSON:       {raw_json_path}")


if __name__ == "__main__":
    main()
