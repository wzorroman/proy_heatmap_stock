"""web/templating.py — instancia compartida de Jinja2Templates."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from core.settings import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _chart_code(slug: str) -> str:
    """Código del gráfico (A1, A2, …) leído de config/charts/*.json."""
    return get_settings().chart_code(slug)


# Disponible en todas las plantillas sin hardcodear códigos.
templates.env.globals["chart_code"] = _chart_code
