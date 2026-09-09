import json

import csv

from heatmap.export_heatmap_csv import normalize_symbol


def test_normalize_symbol_handles_empty_d():
    item = {"s": "NASDAQ:TEST", "d": []}
    row = normalize_symbol(item)
    assert row["symbol"] == "NASDAQ:TEST"
    assert row["ticker"] == ""
    assert row["company_name"] == ""
    assert row["sector"] == ""


def test_export_raw_backup_csv_preserves_original_payload(tmp_path):
    payload = {
        "totalCount": 1,
        "data": [{
            "s": "NASDAQ:NVDA",
            "d": [["common"], 1.23, "Electronic Technology", {"logoid": "nvidia"}],
        }],
    }
    output_dir = tmp_path / "heatmap"
    output_dir.mkdir()
    output_path = output_dir / "heatmap_symbols.csv"
    raw_path = output_dir / "heatmap_symbols_raw.csv"

    from heatmap.export_heatmap_csv import export_raw_csv

    export_raw_csv(payload, raw_path)

    with raw_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert rows[0]["symbol"] == "NASDAQ:NVDA"
    assert '"common"' in rows[0]["raw_d"]
    assert 'Electronic Technology' in rows[0]["raw_d"]


def test_normalize_symbol_includes_price_and_market_cap_fields():
    item = {
        "s": "NASDAQ:NVDA",
        "d": [["common"], 0.20663853482402852, -0.17551462621885205, 0.8360691617421865,
             1.319493314567206, 6.225214424052384, 7.378921362979543, 28.091637010676163,
             21.34748597466221, 35.053057395790596, 1.1687458962573938, -0.20402847716618652,
             0.8472847761107444, 2.747898793711624, 1.1556139198949509, 5551675925838.097,
             131881678, 658126815, 533424155, 30380263344.08, 151606093103.4, 122879588345.8,
             "Electronic Technology", "Tecnología electrónica", {"logoid": "nvidia", "style": "single"},
             230.345, 100, "NVDA", "NVIDIA Corporation", "delayed_streaming_900"],
    }
    row = normalize_symbol(item)

    assert row["price"] == 230.345
    assert row["market_cap"] == 5551675925838.097
    assert row["daily_change_pct"] == 0.8360691617421865
    assert row["heatmap_metric_1"] == 0.20663853482402852
    assert row["heatmap_metric_3"] == 0.8360691617421865


def test_resolve_payload_uses_raw_capture_when_live_scan_is_empty(monkeypatch, tmp_path):
    fallback_file = tmp_path / "captured_scan.json"
    fallback_file.write_text(
        json.dumps({
            "totalCount": 1,
            "data": [{
                "s": "NASDAQ:NVDA",
                "d": [["common"], 1.23, "Electronic Technology", "Tecnología electrónica", {"logoid": "nvidia"}, 100, "NVDA", "NVIDIA Corporation", "delayed_streaming_900"],
            }],
        }),
        encoding="utf-8",
    )

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_post(url, headers=None, data=None, timeout=30):
        return FakeResponse({"totalCount": 1, "data": [{"s": "NASDAQ:EMPTY", "d": []}]})

    monkeypatch.setattr("heatmap.export_heatmap_csv.requests.post", fake_post)
    monkeypatch.setattr("heatmap.export_heatmap_csv.CAPTURED_SCAN_PATH", fallback_file)

    from heatmap.export_heatmap_csv import resolve_payload

    payload = resolve_payload("https://scanner.tradingview.com/america/scan?label-product=heatmap-stock")

    assert payload["data"][0]["s"] == "NASDAQ:NVDA"
    assert payload["data"][0]["d"][0][0] == "common"
