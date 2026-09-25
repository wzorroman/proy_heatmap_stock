# file: proy_scrapping_detail/db/create_dim_trading_session.py
"""F2.1 · Crea y puebla dim_trading_session con exchange_calendars (XNYS).

Cubre 2026-01-01 hasta el límite del calendario XNYS (2027-09-22 en
exchange_calendars 4.13.2). Idempotente: ON CONFLICT DO UPDATE.

Uso:
    python3 -m db.create_dim_trading_session
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import exchange_calendars as xcals
import pandas as pd

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.postgresql_connection import PostgreSQLConnector

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS dim_trading_session (
    session_date   DATE        NOT NULL,
    is_session     BOOLEAN     NOT NULL DEFAULT FALSE,
    is_early_close BOOLEAN     NOT NULL DEFAULT FALSE,
    opens_at       TIMESTAMPTZ,
    closes_at      TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dim_trading_session_pkey PRIMARY KEY (session_date)
);

COMMENT ON TABLE  dim_trading_session
    IS 'Sesiones de trading XNYS (exchange_calendars), fuente del gate F2.2 (E-BD-01, E-BD-06, E-OPS-01).';
COMMENT ON COLUMN dim_trading_session.session_date   IS 'Fecha de sesión (ET, sin tz).';
COMMENT ON COLUMN dim_trading_session.is_session     IS 'True si la Bolsa de NY está abierta ese día (lun-vie sin feriados).';
COMMENT ON COLUMN dim_trading_session.is_early_close IS 'True si cierra antes de las 16:00 ET (post-Navidad, día antes de feriados).';
COMMENT ON COLUMN dim_trading_session.opens_at       IS 'Horario de apertura en UTC.';
COMMENT ON COLUMN dim_trading_session.closes_at      IS 'Horario de cierre en UTC (respeta cierres anticipados).';
"""

UPSERT = """
INSERT INTO dim_trading_session
    (session_date, is_session, is_early_close, opens_at, closes_at, updated_at)
VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
ON CONFLICT (session_date) DO UPDATE SET
    is_session     = EXCLUDED.is_session,
    is_early_close = EXCLUDED.is_early_close,
    opens_at       = EXCLUDED.opens_at,
    closes_at      = EXCLUDED.closes_at,
    updated_at     = CURRENT_TIMESTAMP
"""

NORMAL_CLOSE_NY = pd.Timestamp("16:00").time()


def rows_para(cal) -> list:
    """Genera las filas para TODOS los días 2026-01-01 → fin del calendario,
    con is_session=True solo en días hábiles del XNYS."""
    idx = cal.schedule.index
    rango = idx[(idx >= "2026-01-01") & (idx <= idx[-1])]
    sesiones = {d.strftime("%Y-%m-%d") for d in rango}
    start, end = pd.Timestamp("2026-01-01"), idx[-1]
    filas = []
    for d in pd.date_range(start, end, freq="D"):
        key = d.strftime("%Y-%m-%d")
        if key in sesiones:
            row = cal.schedule.loc[pd.Timestamp(key)]
            open_utc = row["open"].to_pydatetime()
            close_utc = row["close"].to_pydatetime()
            close_ny = row["close"].tz_convert("America/New_York").time()
            filas.append((d.date(), True, close_ny < NORMAL_CLOSE_NY, open_utc, close_utc))
        else:
            filas.append((d.date(), False, False, None, None))
    return filas


def main():
    cal = xcals.get_calendar("XNYS")
    filas = rows_para(cal)
    n_total = sum(1 for f in filas if f[1])
    print(f"XNYS: {len(filas)} días en el rango, {n_total} sesiones "
          f"(2026-01-01 → {cal.schedule.index[-1].date()})")

    conf = PostgreSQLConnector(
        os.getenv("BD_HEATMAP_HOST", "localhost"),
        int(os.getenv("BD_HEATMAP_PORT", "5432")),
        os.getenv("BD_HEATMAP_DATABASE", "heatmap_stock"),
        os.getenv("BD_HEATMAP_USER", "postgres"),
        os.getenv("BD_HEATMAP_PASSWORD", ""),
    )
    conf.connect()
    conf.execute_query(CREATE_TABLE)
    conf.execute_batch(UPSERT, filas)

    n = conf.execute_query(
        "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_session) AS sesiones, "
        "COUNT(*) FILTER (WHERE is_early_close) AS early FROM dim_trading_session"
    )[0]
    print("dim_trading_session:", n)

    # Verificación "Hecho cuando" F2.1
    cur = conf.connection.cursor()
    cur.execute(
        "SELECT session_date, is_session, is_early_close, opens_at, closes_at "
        "FROM dim_trading_session WHERE session_date IN ('2026-11-26', '2026-11-27') "
        "ORDER BY session_date"
    )
    for r in cur.fetchall():
        abre = r[3].strftime('%H:%M UTC') if r[3] else None
        cierra = r[4].strftime('%H:%M UTC') if r[4] else None
        print("  verificación:", r[0], "sesion=", r[1], "early=", r[2],
              "abre=", abre, "cierra=", cierra)
    cur.close()
    conf.disconnect()


if __name__ == "__main__":
    main()