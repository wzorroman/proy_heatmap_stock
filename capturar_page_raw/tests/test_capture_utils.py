import pathlib

from capture_tradingview_heatmap import guess_extension, slugify_url


def test_slugify_url_removes_invalid_chars():
    value = "https://es.tradingview.com/heatmap/stock/?country=ES"
    slug = slugify_url(value)
    assert "heatmap" in slug
    assert "country" not in slug
    assert slug.startswith("heatmap")


def test_guess_extension_detects_js_and_json():
    assert guess_extension("https://example.com/app.js", "application/javascript") == ".js"
    assert guess_extension("https://example.com/data.json", "application/json") == ".json"
    assert guess_extension("https://example.com/file.bin", "application/octet-stream") == ".bin"
