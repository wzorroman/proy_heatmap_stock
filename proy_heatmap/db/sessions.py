# file: proy_heatmap/db/sessions.py
"""F2.2 · Gate NYSE del heatmap (M-CAP-01).

El heatmap solo captura equity/ETF, así que el gate es único NYSE, evaluado
una vez por corrida. Consulta dim_trading_session (poblada por
proy_scrapping_detail/db/create_dim_trading_session.py). Sin pandas.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger('db.sessions')


def en_ventana_nyse(conn, ahora: datetime | None = None,
                    pre_min: int = 30) -> bool:
    """True si `ahora` (tz-aware) está entre apertura−pre_min y cierre de la
    sesión XNYS de hoy, según dim_trading_session. Feriados y cierres
    anticipados ya quedan reflejados en la tabla."""
    ahora = ahora or datetime.now(timezone.utc)
    day = ahora.astimezone(timezone.utc)
    while True:
        try:
            from zoneinfo import ZoneInfo
            et = ahora.astimezone(ZoneInfo("America/New_York"))
            dia = et.date().isoformat()
            break
        except Exception:
            dia = (day - timedelta(hours=5)).date().isoformat()
            break

    rows = conn.execute_query(
        "SELECT is_session, opens_at, closes_at FROM dim_trading_session "
        "WHERE session_date = %s", (dia,)
    )
    if not rows or "is_session" not in rows[0]:
        logger.warning(f"dim_trading_session sin fila para {dia} — gate abierto "
                       "(fail-open para no romper el ciclo)")
        return True
    r = rows[0]
    if not r["is_session"]:
        return False
    if r["opens_at"] is None or r["closes_at"] is None:
        return False
    desde = (r["opens_at"] - timedelta(minutes=pre_min)).astimezone(timezone.utc)
    hasta = r["closes_at"].astimezone(timezone.utc)
    return desde <= ahora <= hasta