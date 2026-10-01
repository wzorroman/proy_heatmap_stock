"""core/timezone.py — utilidades de zona horaria.

Los datos de la BD están en UTC. Hay que distinguir dos zonas:

- ``MARKET_TZ`` (``America/New_York``, NYSE): fija, define la **lógica de
  mercado** — apertura 09:30, rango inicial, fases de sesión. No depende de la
  configuración.
- ``APP_TIMEZONE`` (``settings.timezone``): **preferencia de visualización** del
  usuario (p. ej. ``America/Lima``). Solo afecta a cómo se muestran las horas,
  nunca a los cálculos de sesión.

UTC es la referencia para frescura/staleness.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional

UTC = timezone.utc

# Zona del mercado (NYSE). Ancla de toda la lógica de sesión, independiente de
# APP_TIMEZONE, que es solo preferencia de visualización.
MARKET_TZ = "America/New_York"


def get_tz(name: str) -> ZoneInfo:
    """Zona horaria por nombre; cae a UTC si el nombre es inválido."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo("UTC")


# Etiqueta corta y estable para mostrar junto a una hora. No es la abreviatura
# oficial del tzdata (EDT/EST cambia con el DST), sino una referencia legible.
_TZ_LABEL = {
    "America/New_York": "NY",
    "America/Lima": "PE",
    "UTC": "UTC",
}


def tz_label(name: str) -> str:
    """Etiqueta corta de zona horaria (ej. 'America/New_York' → 'NY')."""
    if name in _TZ_LABEL:
        return _TZ_LABEL[name]
    return name.rsplit("/", 1)[-1].replace("_", " ")


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


def format_hora(iso: Optional[str], name: str) -> str:
    """ISO UTC → ``'HH:MM'`` en la zona indicada. ``''`` si no hay instante."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    return to_tz(dt, name).strftime("%H:%M")


def rango_dia_utc(momento: datetime, name: str) -> tuple[datetime, datetime]:
    """Ventana UTC semiabierta ``[inicio, fin)`` del día local de ``momento``.

    Sirve para filtrar por *día local* contra columnas ``timestamptz`` que se
    guardan en UTC: se toma la fecha en la zona pedida, se convierte su medianoche
    a UTC y se devuelve el día completo. El fin es **exclusivo**, para que un
    evento en la medianoche exacta no aparezca en dos días consecutivos.
    """
    tz = get_tz(name)
    local = ensure_utc(momento).astimezone(tz)
    inicio = datetime.combine(local.date(), time.min, tzinfo=tz).astimezone(UTC)
    return inicio, inicio + timedelta(days=1)


def to_market_tz(dt: datetime) -> datetime:
    """Convierte a la zona del mercado (NYSE).

    Independiente de ``APP_TIMEZONE``: la lógica de sesión siempre es NY.
    """
    return to_tz(dt, MARKET_TZ)


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
