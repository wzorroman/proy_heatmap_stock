#!/usr/bin/env python3
"""Versión v2 del exportador del heatmap de TradingView.

Objetivo:
- consultar el endpoint real del scanner,
- preservar la copia raw con timestamp,
- exportar columnas con nombres semánticos descubiertos,
- incluir columnas derivadas sobre color/intensidad y geometría visual
  para documentar los campos relevantes del heatmap.

Uso:
    . .venv/bin/activate && python heatmap/export_heatmap_v2.py
    . .venv/bin/activate && python heatmap/export_heatmap_v2.py --output heatmap/heatmap_symbols_v2.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
URL = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"
CAPTURED_SCAN_PATH = ROOT_DIR / "raw" / "responses" / "0196_america_scan_bf8828f8dd_8f5b42c8c525.json"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://es.tradingview.com",
    "referer": "https://es.tradingview.com/heatmap/stock/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}


def utc_timestamp() -> str:
    """Devuelve una marca temporal UTC para nombrar archivos."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def fetch_heatmap_payload(url: str = URL, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Obtiene el payload JSON del endpoint de scan del heatmap."""
    response = requests.post(url, headers=headers or HEADERS, data=None, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Respuesta inesperada: {type(payload).__name__}")
    if "data" not in payload:
        raise KeyError("No se encontró la clave 'data' en la respuesta")
    return payload


def resolve_payload(url: str = URL, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Usa la respuesta en vivo y, si viene vacía, recurre a la captura local del proyecto."""
    payload = fetch_heatmap_payload(url, headers)
    items = payload.get("data", [])

    if isinstance(items, list) and items and any(
        isinstance(item, dict) and isinstance(item.get("d"), list) and len(item["d"]) > 0
        for item in items
    ):
        return payload

    if CAPTURED_SCAN_PATH.exists():
        with CAPTURED_SCAN_PATH.open("r", encoding="utf-8") as fh:
            captured_payload = json.load(fh)
        if isinstance(captured_payload, dict) and "data" in captured_payload:
            return captured_payload

    return payload


def safe_value(raw: list[Any], index: int, default: Any = "") -> Any:
    if not isinstance(raw, list):
        return default
    if len(raw) <= index:
        return default
    return raw[index]


def extract_security_type(raw: list[Any]) -> str:
    value = safe_value(raw, 0)
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def extract_symbol_meta(symbol: str) -> tuple[str, str]:
    if ":" in symbol:
        exchange, rest = symbol.split(":", 1)
        return exchange, rest
    return "", symbol


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


def color_from_change(value: Any) -> str:
    direction = direction_from_value(value)
    if direction == "buy":
        return "green"
    if direction == "sell":
        return "red"
    return "neutral"


def intensity_from_change(value: Any) -> float:
    if value in (None, "", "nan"):
        return 0.0
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return 0.0


def normalize_symbol(item: dict[str, Any]) -> dict[str, Any]:
    """Normaliza un registro del payload en columnas semánticas."""
    symbol = item.get("s", "")
    raw = item.get("d", [])
    exchange, base_ticker = extract_symbol_meta(symbol)

    price = safe_value(raw, 25)
    market_cap = safe_value(raw, 15)
    daily_change_pct = safe_value(raw, 3)

    row: dict[str, Any] = {
        # IDs y metadatos básicos
        "symbol": symbol,
        "exchange": exchange,
        "base_ticker": base_ticker,
        "ticker": safe_value(raw, 27),
        "company_name": safe_value(raw, 28),
        "security_type": extract_security_type(raw),
        "sector": safe_value(raw, 22),
        "sector_es": safe_value(raw, 23),
        "logo_json": json.dumps(safe_value(raw, 24), ensure_ascii=False) if isinstance(safe_value(raw, 24), dict) else "",
        "stream_status": safe_value(raw, 29),
        "raw_vector_len": len(raw) if isinstance(raw, list) else 0,

        # Campos descubiertos del payload
        "field_0_asset_class": safe_value(raw, 0),
        "field_3_daily_change_pct": daily_change_pct,
        "field_15_market_cap": market_cap,
        "field_22_sector": safe_value(raw, 22),
        "field_23_sector_es": safe_value(raw, 23),
        "field_24_logo": json.dumps(safe_value(raw, 24), ensure_ascii=False) if isinstance(safe_value(raw, 24), dict) else "",
        "field_25_price": price,
        "field_27_ticker": safe_value(raw, 27),
        "field_28_company_name": safe_value(raw, 28),
        "field_29_stream_status": safe_value(raw, 29),

        # Valores de negocio relevantes
        "price": price,
        "market_cap": market_cap,
        "daily_change_pct": daily_change_pct,
        "market_cap_in_trillions": float(market_cap) / 1_000_000_000_000 if market_cap not in (None, "") else "",

        # Semántica de dirección / color / fuerza visual
        "market_direction": direction_from_value(daily_change_pct),
        "heatmap_color": color_from_change(daily_change_pct),
        "heatmap_color_intensity": intensity_from_change(daily_change_pct),
        "heatmap_buy_sell_strength": intensity_from_change(daily_change_pct),

        # Geometría del cuadro: no viene en el payload; se deriva en el renderer del front-end
        "heatmap_tile_width_px": "",
        "heatmap_tile_height_px": "",
        "heatmap_tile_area_px2": "",
        "heatmap_render_source": "front-end layout; not present in scanner payload",

        # Mapeo de los 21 índices de métricas compactas
        "heatmap_metric_1": safe_value(raw, 1),
        "heatmap_metric_2": safe_value(raw, 2),
        "heatmap_metric_3": safe_value(raw, 3),
        "heatmap_metric_4": safe_value(raw, 4),
        "heatmap_metric_5": safe_value(raw, 5),
        "heatmap_metric_6": safe_value(raw, 6),
        "heatmap_metric_7": safe_value(raw, 7),
        "heatmap_metric_8": safe_value(raw, 8),
        "heatmap_metric_9": safe_value(raw, 9),
        "heatmap_metric_10": safe_value(raw, 10),
        "heatmap_metric_11": safe_value(raw, 11),
        "heatmap_metric_12": safe_value(raw, 12),
        "heatmap_metric_13": safe_value(raw, 13),
        "heatmap_metric_14": safe_value(raw, 14),
        "heatmap_metric_15": safe_value(raw, 15),
        "heatmap_metric_16": safe_value(raw, 16),
        "heatmap_metric_17": safe_value(raw, 17),
        "heatmap_metric_18": safe_value(raw, 18),
        "heatmap_metric_19": safe_value(raw, 19),
        "heatmap_metric_20": safe_value(raw, 20),
        "heatmap_metric_21": safe_value(raw, 21),
    }

    return row


def export_csv(payload: dict[str, Any], output_path: Path) -> int:
    """Guarda los datos normalizados en un CSV legible."""
    rows = payload.get("data", [])
    normalized_rows = [normalize_symbol(item) for item in rows if isinstance(item, dict)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not normalized_rows:
        raise ValueError("No se encontraron registros en 'data' para exportar")

    fieldnames = list(normalized_rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)

    return len(normalized_rows)


def export_raw_csv(payload: dict[str, Any], output_path: Path) -> int:
    """Guarda una copia raw del payload con el vector `d` como respaldo exacto."""
    rows = payload.get("data", [])
    raw_rows = [
        {
            "symbol": item.get("s", "") if isinstance(item, dict) else "",
            "raw_d_json": json.dumps(item.get("d", []), ensure_ascii=False) if isinstance(item, dict) else "",
            "raw_d_len": len(item.get("d", [])) if isinstance(item, dict) and isinstance(item.get("d"), list) else 0,
            "exported_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for item in rows if isinstance(item, dict)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_rows:
        raise ValueError("No se encontraron registros en 'data' para exportar la copia raw")

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["symbol", "raw_d_json", "raw_d_len", "exported_at_utc"])
        writer.writeheader()
        writer.writerows(raw_rows)

    return len(raw_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta el endpoint de heatmap a CSV v2.")
    parser.add_argument("--url", default=URL, help="Endpoint del scanner")
    parser.add_argument("--output", default=str(ROOT_DIR / "heatmap" / "heatmap_symbols_v2.csv"), help="Ruta del CSV normalizado")
    args = parser.parse_args()

    payload = resolve_payload(args.url, HEADERS)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = utc_timestamp()
    raw_timestamped_path = output_path.with_name(f"{output_path.stem}_raw_{timestamp}.csv")
    raw_static_path = output_path.with_name(output_path.stem.replace("_v2", "") + "_raw.csv")

    normalized_count = export_csv(payload, output_path)
    raw_count = export_raw_csv(payload, raw_timestamped_path)

    # preserva el raw clásico para compatibilidad
    if raw_static_path != raw_timestamped_path:
        with raw_timestamped_path.open("r", encoding="utf-8", newline="") as source, raw_static_path.open("w", encoding="utf-8", newline="") as target:
            target.write(source.read())

    print(json.dumps({
        "url": args.url,
        "rows_exported": normalized_count,
        "output_csv": str(output_path),
        "raw_timestamped_csv": str(raw_timestamped_path),
        "raw_compat_csv": str(raw_static_path),
        "raw_rows_exported": raw_count,
        "total_count": payload.get("totalCount"),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
