"""core/container.py — inyección de dependencias (wiring manual).

Un único contenedor construye settings, conector PostgreSQL, repositorios y
servicios, y los inyecta por constructor. Los repositorios funcionan sin conector
(degradan a vacío), lo que permite arrancar el dashboard aunque la BD no esté
configurada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.logging_config import get_logger
from core.settings import Settings, get_settings
from db.postgresql_connection import PostgreSQLConnector
from repositories import (
    EventsRepository,
    HeatmapRepository,
    IndicatorTfRepository,
    LatestTickRepository,
    ScoreRepository,
    SeriesRepository,
    SessionRepository,
)
from services.event_service import EventService
from services.health_service import HealthService
from services.heatmap_service import HeatmapService
from services.indicator_service import IndicatorService
from services.momentum_service import MomentumService
from services.precio_service import PrecioService
from services.score_service import ScoreService
from services.session_service import SessionService


@dataclass
class Container:
    """Contenedor de dependencias del dashboard."""

    settings: Settings
    connector: Optional[PostgreSQLConnector] = None

    # repositorios (solo SQL)
    latest_tick_repo: Optional[LatestTickRepository] = None
    score_repo: Optional[ScoreRepository] = None
    heatmap_repo: Optional[HeatmapRepository] = None
    events_repo: Optional[EventsRepository] = None
    series_repo: Optional[SeriesRepository] = None
    indicator_repo: Optional[IndicatorTfRepository] = None
    session_repo: Optional[SessionRepository] = None

    # servicios (negocio)
    score_service: Optional[ScoreService] = None
    momentum_service: Optional[MomentumService] = None
    heatmap_service: Optional[HeatmapService] = None
    indicator_service: Optional[IndicatorService] = None
    precio_service: Optional[PrecioService] = None
    event_service: Optional[EventService] = None
    session_service: Optional[SessionService] = None
    health_service: Optional[HealthService] = None

    name: str = field(default="container")

    # ── construcción ────────────────────────────────────────────────────────
    @classmethod
    def build(cls, settings: Optional[Settings] = None, connect: bool = False) -> "Container":
        settings = settings or get_settings()
        connector: Optional[PostgreSQLConnector] = None
        if settings.db_configurada:
            connector = PostgreSQLConnector(**settings.db_kwargs())
            if connect:
                connector.connect()

        container = cls(settings=settings, connector=connector)
        container._wire()
        return container

    def _wire(self) -> None:
        self.latest_tick_repo = LatestTickRepository(self.connector)
        self.score_repo = ScoreRepository(self.connector)
        self.heatmap_repo = HeatmapRepository(self.connector)
        self.events_repo = EventsRepository(self.connector)
        self.series_repo = SeriesRepository(self.connector)
        self.indicator_repo = IndicatorTfRepository(self.connector)
        self.session_repo = SessionRepository(self.connector)

        self.score_service = ScoreService(
            latest_tick_repo=self.latest_tick_repo,
            heatmap_repo=self.heatmap_repo,
            indicator_repo=self.indicator_repo,
            series_repo=self.series_repo,
            settings=self.settings,
        )
        self.momentum_service = MomentumService(self.latest_tick_repo, self.settings)
        self.heatmap_service = HeatmapService(self.heatmap_repo, self.settings)
        self.indicator_service = IndicatorService(
            self.latest_tick_repo, self.indicator_repo, self.settings
        )
        self.precio_service = PrecioService(
            self.series_repo, self.score_service, self.settings
        )
        self.event_service = EventService(self.events_repo, self.settings)
        self.session_service = SessionService(self.session_repo, self.settings)
        self.health_service = HealthService(
            self.settings,
            self.latest_tick_repo,
            self.heatmap_repo,
            self.events_repo,
            self.indicator_repo,
        )

    # ── utilidades ──────────────────────────────────────────────────────────
    def logger(self, name: str) -> logging.Logger:
        return get_logger(name)

    @property
    def db_habilitada(self) -> bool:
        return self.connector is not None

    def close(self) -> None:
        if self.connector is not None:
            self.connector.disconnect()

    def __enter__(self) -> "Container":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
