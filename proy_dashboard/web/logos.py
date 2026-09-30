"""web/logos.py — resuelve el logo local de un símbolo.

Convención de archivo (misma que `proy_heatmap/static/iconos_mercado`):
    "NASDAQ:NVDA" → "nasdaq_nvda.svg|.png"

Se indexa la carpeta una sola vez (cacheado).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

LOGO_DIR = Path(__file__).resolve().parent / "static" / "iconos_mercado"
_EXTS = (".svg", ".png")


def _slug(symbol: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", symbol.lower().strip()).strip("_")
    return s or "activo"


@lru_cache(maxsize=1)
def _indice() -> dict[str, str]:
    if not LOGO_DIR.is_dir():
        return {}
    return {
        p.stem: p.name
        for p in LOGO_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in _EXTS
    }


@lru_cache(maxsize=8192)
def logo_url(symbol: str) -> str | None:
    """URL estática del logo (`/static/iconos_mercado/<archivo>`), o None."""
    if not symbol:
        return None
    nombre = _indice().get(_slug(symbol))
    return f"/static/iconos_mercado/{nombre}" if nombre else None
