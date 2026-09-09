#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

TARGET_URL = "https://es.tradingview.com/heatmap/stock/"


def slugify_url(url: str, max_length: int = 120) -> str:
    """Genera un nombre de archivo seguro a partir de la URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "root"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path)
    stem = stem.strip("._-") or "root"
    if parsed.query:
        query_hash = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:10]
        stem = f"{stem}_{query_hash}"
    return stem[:max_length]


def guess_extension(url: str, content_type: str = "") -> str:
    """Devuelve la extensión más adecuada para el contenido detectado."""
    lower = (content_type or "").lower()
    lower_url = url.lower()

    if "javascript" in lower or lower_url.endswith(".js"):
        return ".js"
    if "json" in lower or lower_url.endswith(".json"):
        return ".json"
    if "text/html" in lower or lower_url.endswith(".html"):
        return ".html"
    if "css" in lower or lower_url.endswith(".css"):
        return ".css"
    if "image/webp" in lower or lower_url.endswith(".webp"):
        return ".webp"
    if "image/png" in lower or lower_url.endswith(".png"):
        return ".png"
    if "image/jpeg" in lower or lower_url.endswith(".jpg") or lower_url.endswith(".jpeg"):
        return ".jpg"
    if "font/woff" in lower or lower_url.endswith(".woff"):
        return ".woff"
    if "font/woff2" in lower or lower_url.endswith(".woff2"):
        return ".woff2"
    if lower_url.endswith(".svg"):
        return ".svg"
    if lower_url.endswith(".map"):
        return ".map"
    return ".bin"


def save_response_file(base_dir: Path, response, index: int) -> dict:
    """Guarda el cuerpo y metadata de una respuesta de red."""
    url = response.url
    content_type = response.headers.get("content-type", "")
    body = response.body()
    ext = guess_extension(url, content_type)
    slug = slugify_url(url)
    resource_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    file_name = f"{index:04d}_{slug}_{resource_hash}{ext}"
    file_path = base_dir / "responses" / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(body)

    metadata = {
        "index": index,
        "url": url,
        "status": response.status,
        "resource_type": response.request.resource_type if response.request else None,
        "method": response.request.method if response.request else None,
        "content_type": content_type,
        "headers": dict(response.headers),
        "file": file_name,
    }
    meta_path = file_path.with_suffix(file_path.suffix + ".json")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def capture_page(url: str, output_dir: str, timeout_ms: int = 120000) -> dict:
    """Abre la URL con Playwright y guarda todos los artefactos descargados."""
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            ),
            record_har_path=str(base_dir / "network.har"),
        )
        page = context.new_page()

        def on_response(response):
            try:
                if not response or not response.url:
                    return
                request = response.request
                if request and request.resource_type in {"document", "script", "xhr", "fetch", "stylesheet", "image", "font", "other"}:
                    record = save_response_file(base_dir, response, len(manifest) + 1)
                    manifest.append(record)
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(url, wait_until="load", timeout=timeout_ms)
        page.wait_for_timeout(5000)

        page_html = page.content()
        (base_dir / "page.html").write_text(page_html, encoding="utf-8")
        try:
            page.screenshot(path=str(base_dir / "page.png"), full_page=True)
        except Exception:
            pass

        browser.close()

    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"url": url, "count": len(manifest), "records": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"url": url, "count": len(manifest), "directory": str(base_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga los artefactos crudos de una vista de TradingView.")
    parser.add_argument("--url", default=TARGET_URL, help="URL a capturar")
    parser.add_argument("--output-dir", default="raw", help="Directorio donde guardar los resultados")
    parser.add_argument("--timeout", type=int, default=120000, help="Tiempo máximo de carga en milisegundos")
    args = parser.parse_args()

    result = capture_page(args.url, args.output_dir, timeout_ms=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
