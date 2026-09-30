"""api/routers/__init__.py — routers JSON del dashboard."""

from api.routers import events, health, heatmap, indicators, momentum, risk, score

__all__ = ["health", "score", "momentum", "heatmap", "indicators", "events", "risk"]
