#!/usr/bin/env python3
"""Consulta el endpoint del heatmap de TradingView y exporta los datos a CSV.

Uso:
    python heatmap/export_heatmap_csv.py
    python heatmap/export_heatmap_csv.py --output heatmap/output/heatmap_symbols.csv
"""

from __future__ import annotations

import argparse
import csv
import json
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


def normalize_symbol(item: dict[str, Any]) -> dict[str, Any]:
    """Normaliza cada símbolo del arreglo data para exportar a CSV."""
    symbol = item.get("s", "")
    raw = item.get("d", [])

    security_type = ""
    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list) and len(raw[0]) > 0:
        security_type = raw[0][0]

    result: dict[str, Any] = {
        "symbol": symbol,
        "ticker": raw[27] if isinstance(raw, list) and len(raw) > 27 else "",
        "company_name": raw[28] if isinstance(raw, list) and len(raw) > 28 else "",
        "security_type": security_type,
        "sector": raw[22] if isinstance(raw, list) and len(raw) > 22 else "",
        "sector_es": raw[23] if isinstance(raw, list) and len(raw) > 23 else "",
        "logo": json.dumps(raw[24], ensure_ascii=False) if isinstance(raw, list) and len(raw) > 24 and isinstance(raw[24], dict) else "",
        "stream_status": raw[29] if isinstance(raw, list) and len(raw) > 29 else "",
        "price": raw[25] if isinstance(raw, list) and len(raw) > 25 else "",
        "market_cap": raw[15] if isinstance(raw, list) and len(raw) > 15 else "",
        "daily_change_pct": raw[3] if isinstance(raw, list) and len(raw) > 3 else "",
    }

    for idx in range(1, 22):
        result[f"heatmap_metric_{idx}"] = raw[idx] if isinstance(raw, list) and len(raw) > idx else ""

    return result


def export_csv(payload: dict[str, Any], output_path: Path) -> int:
    """Guarda los datos normalizados en CSV."""
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
    """Guarda una copia raw del payload con el arreglo `d` serializado en JSON como respaldo."""
    rows = payload.get("data", [])
    raw_rows = [
        {
            "symbol": item.get("s", "") if isinstance(item, dict) else "",
            "raw_d": json.dumps(item.get("d", []), ensure_ascii=False) if isinstance(item, dict) else "",
        }
        for item in rows if isinstance(item, dict)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not raw_rows:
        raise ValueError("No se encontraron registros en 'data' para exportar la copia raw")

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["symbol", "raw_d"])
        writer.writeheader()
        writer.writerows(raw_rows)

    return len(raw_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta el endpoint de heatmap a CSV.")
    parser.add_argument("--url", default=URL, help="Endpoint del scanner")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "heatmap_symbols.csv"), help="Ruta del archivo CSV")
    args = parser.parse_args()

    payload = resolve_payload(args.url, HEADERS)
    output_path = Path(args.output)
    raw_output_path = output_path.with_name(output_path.stem + "_raw.csv")
    count = export_csv(payload, output_path)
    raw_count = export_raw_csv(payload, raw_output_path)

    print(json.dumps({
        "url": args.url,
        "rows_exported": count,
        "output_csv": str(output_path),
        "raw_output_csv": str(raw_output_path),
        "raw_rows_exported": raw_count,
        "total_count": payload.get("totalCount"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
