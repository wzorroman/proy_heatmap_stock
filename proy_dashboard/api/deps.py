"""api/deps.py — dependencias compartidas de los routers."""

from __future__ import annotations

from fastapi import Request

from core.container import Container


def get_container(request: Request) -> Container:
    """Devuelve el contenedor construido en el lifespan de la app."""
    return request.app.state.container
