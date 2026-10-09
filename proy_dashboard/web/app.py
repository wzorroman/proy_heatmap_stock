"""web/app.py — aplicación FastAPI del dashboard.

Monta:
  - ``/static`` con librerías vendorizadas (ECharts, HTMX) y assets propios.
  - routers JSON de ``api/`` (``/api/health``, ``/api/score``, …).
  - páginas Jinja2 y fragmentos HTMX (``/``, ``/partials/*``).

El contenedor de dependencias se construye una vez en el ``lifespan`` y se
expone en ``app.state.container`` (lo consumen ``api.deps`` y ``web.views``).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from api.routers import events, health, heatmap, indicators, momentum, risk, score, trading15m
from core.container import Container
from core.logging_config import get_logger, setup_global_logging
from core.settings import get_settings
from core.timezone import tz_label
from web import views
from web.templating import templates

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

logger = get_logger("web.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger, log_path = setup_global_logging(settings)
    container = Container.build(settings=settings)
    app.state.container = container
    app.state.log_path = log_path
    logger.info(
        "Dashboard arrancando — puerto %s, env=%s, BD=%s",
        settings.port,
        settings.app_env,
        "configurada" if container.db_habilitada else "no configurada",
    )
    yield
    container.close()
    logger.info("Dashboard detenido")


app = FastAPI(
    title="Radar Intermarket — Prototipo BD",
    version=get_settings().version,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

for _router in (health.router, score.router, momentum.router, heatmap.router,
                indicators.router, events.router, risk.router, trading15m.router,
                views.router):
    app.include_router(_router)


def _page_context(request: Request, active_tab: str) -> dict:
    """Contexto base común a las páginas (título, zona horaria, auto-refresh, tab activa)."""
    container = request.app.state.container
    settings = container.settings
    return {
        "settings": settings,
        "title": settings.business("app", "title", default="Radar Intermarket"),
        "refresh_ms": settings.business("app", "htmx_refresh_ms", default=30000),
        "version": settings.version,
        # Zona de visualización (APP_TIMEZONE) para mostrarla en el subtítulo.
        "timezone": settings.timezone,
        "tz_label": tz_label(settings.timezone),
        "fase": container.session_service.estado(),
        "active_tab": active_tab,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = _page_context(request, "dashboard")
    context["placeholders"] = [
        ("SMA20/50 de precio", context["settings"].business("data", "placeholder_msg", default="Histórico insuficiente.")),
        ("Percentil 60d de riesgo", context["settings"].business("data", "placeholder_msg", default="Histórico insuficiente.")),
        ("Performance semanal", context["settings"].business("data", "placeholder_msg", default="Histórico insuficiente.")),
        ("Distribución histórica / backtest", context["settings"].business("data", "placeholder_msg", default="Histórico insuficiente.")),
    ]
    return templates.TemplateResponse(request, "dashboard.html", context)


@app.get("/tmp1d", response_class=HTMLResponse)
def tmp1d(request: Request):
    """Pestaña 'Tmp 1D': aloja el gráfico B2 (Evolución del score de mercado)."""
    return templates.TemplateResponse(request, "tmp1d.html", _page_context(request, "tmp1d"))


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run("web.app:app", host="0.0.0.0", port=settings.port, reload=settings.is_dev)


if __name__ == "__main__":
    main()
