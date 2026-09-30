"""core/timezone.py — utilidades de zona horaria.

Los datos de la BD están en UTC; las fases de sesión de mercado se calculan en
``APP_TIMEZONE`` (default ``America/New_York``). UTC es la referencia para
frescura/staleness.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional

UTC = timezone.utc


def get_tz(name: str) -> ZoneInfo:
    """Zona horaria por nombre; cae a UTC si el nombre es inválido."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo("UTC")


def now_utc() -> datetime:
    """Instante actual con tzinfo=UTC."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return now_utc().isoformat()


def ensure_utc(dt: datetime) -> datetime:
    """Normaliza un datetime a UTC (asume UTC si es naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_tz(dt: datetime, name: str) -> datetime:
    """Convierte un datetime (naive=UTC) a la zona indicada."""
    return ensure_utc(dt).astimezone(get_tz(name))


def to_market_tz(dt: datetime, settings) -> datetime:
    """Convierte a la zona de mercado definida en Settings."""
    return to_tz(dt, settings.timezone)


def age_seconds(dt: datetime) -> float:
    """Antigüedad de un instante respecto a ahora (segundos)."""
    return (now_utc() - ensure_utc(dt)).total_seconds()


def is_stale(dt: datetime, max_age_seconds: float) -> bool:
    """True si el instante supera la antigüedad máxima permitida."""
    return age_seconds(dt) > max_age_seconds


def fase_sesion(
    dt: datetime,
    opens_at: Optional[datetime],
    closes_at: Optional[datetime],
) -> str:
    """Fase simple de sesión: PRE | OPEN | POST | CLOSED | SIN_DATOS."""
    if opens_at is None or closes_at is None:
        return "SIN_DATOS"
    momento = ensure_utc(dt)
    apertura = ensure_utc(opens_at)
    cierre = ensure_utc(closes_at)
    if momento < apertura:
        return "PRE"
    if momento <= cierre:
        return "OPEN"
    if momento <= cierre + timedelta(hours=4):
        return "POST"
    return "CLOSED"
