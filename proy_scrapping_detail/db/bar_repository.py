# file: proy_scrapping_detail/db/bar_repository.py
"""F4.1b · Regla de cierre de barra y agregación de barras de 15 min.

Cierra: H21, E-RAD-15 (M-CAP-03 reformulada en el roadmap v2.3).

Regla de cierre (F4.1b):
    - Último tick en [T_cierre − 20 s, T_cierre − 5 s] → 'definitive'
    - Último tick en [T_cierre − 5 s,  T_cierre + 15 s] → 'provisional'
    - Fuera de ambos rangos                                   → 'unknown'

El endpoint tarda 7–12 s en reflejar el cambio de vela y el caché añade
15–40 s (Test C): un tick capturado en la ventana ciega es ambiguo. El
`last_tick_offset_s` mide (bar_cierre − último_tick) en segundos: positivo si
el tick precede al cierre (semántica de la columna en el DDL).

Agregación: agrupa ticks de `fact_market_series` en buckets de 15 min
alineados a UTC (:00/:15/:30/:45) y produce las barras OHLCV de
`fact_market_bar_15m`. Implementa también `is_regular` para equity/ETF
usando `dim_trading_session` (XNYS).
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.bar_repository')

BARRA_MINUTOS = 15
BARRA_SEGUNDOS = BARRA_MINUTOS * 60          # 900 s

CALIDAD_DEFINITIVA = 'definitive'
CALIDAD_PROVISIONAL = 'provisional'
CALIDAD_DESCONOCIDA = 'unknown'

# Clases que operan contra la sesión regular XNYS (F4.1 DDL: "XNYS para
# equity/ETF"). El resto (fx, crypto, futures, yield, index, commodity)
# opera fuera de ese horario → is_regular = True por defecto.
_CLASES_SESION_NYSE = {"equity", "etf"}

_TZ_NY = ZoneInfo("America/New_York")

_COLUMNAS_BARRA = (
    "asset_id, bar_start_utc, session_date, open, high, low, close, "
    "volume_delta, n_ticks, is_regular, close_quality, last_tick_offset_s"
)


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def bucket_15m_utc(ts: datetime) -> datetime:
    """Inicio de la barra de 15 min UTC que contiene a `ts`."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts_utc = ts.astimezone(timezone.utc)
    epoch = int(ts_utc.timestamp())
    inicio = epoch - (epoch % BARRA_SEGUNDOS)
    return datetime.fromtimestamp(inicio, tz=timezone.utc)


def bar_cierre_utc(bar_start_utc: datetime) -> datetime:
    """T_cierre de la barra: bar_start + 15 min."""
    return bar_start_utc + timedelta(seconds=BARRA_SEGUNDOS)


def ultimo_tick_offset_s(bar_cierre: datetime, ultimo_tick: datetime) -> int:
    """Segundos desde el cierre hasta el último tick (positivo si el tick
    precede al cierre, negativo si es posterior). Semántica de la columna
    `last_tick_offset_s`."""
    return int(round((bar_cierre - ultimo_tick).total_seconds()))


def close_quality_para_offset(offset_s: int) -> str:
    """F4.1b · Etiqueta de calidad según el desplazamiento del último tick.

    Desempate en la frontera [T_cierre − 5 s] (pertenece a ambas ventanas
    del roadmap): se marca 'provisional', pues la ambigüedad del endpoint
    arranca ahí (E-RAD-15).
    """
    if -15 <= offset_s <= 5:
        return CALIDAD_PROVISIONAL
    if 5 < offset_s <= 20:
        return CALIDAD_DEFINITIVA
    return CALIDAD_DESCONOCIDA


def session_date_para(bar_start_utc: datetime) -> date:
    """Fecha de sesión de la barra (UTC, semántica del DDL). Para barras de
    la sesión regular de equity/ETF coincide con la fecha ET del día."""
    return bar_start_utc.date()


def fecha_ny_iso(dt: datetime) -> str:
    return dt.astimezone(_TZ_NY).strftime("%Y-%m-%d")


def es_barra_regular(clase: str, bar_start_utc: datetime,
                     sesiones_por_dia: Dict[str, Dict]) -> bool:
    """True si la barra cae dentro de la sesión regular del activo.

    - equity/ETF: session XNYS de `dim_trading_session` por fecha ET.
    - resto de clases: True (operan 24/5 o 24/7).
    - equity/ETF sin fila de sesión (BD caída o día fuera de rango): True
      (fallback, no se pierde la barra; la calidad la da close_quality).
    """
    if clase not in _CLASES_SESION_NYSE:
        return True
    sesion = sesiones_por_dia.get(fecha_ny_iso(bar_start_utc))
    if not sesion:
        return True
    if not sesion.get("is_session"):
        return False
    abre = sesion.get("opens_at")
    cierra = sesion.get("closes_at")
    if abre is None or cierra is None:
        return False
    return abre <= bar_start_utc < cierra


def agrupar_barras(ticks: Iterable[Dict],
                   sesiones_por_dia: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Agrega ticks de `fact_market_series` en barras de 15 min.

    Cada tick: {asset_id, timestamp_utc (tz-aware), close, volume,
    asset_class}.

    Retorna lista de filas listas para `fact_market_bar_15m`:
    asset_id, bar_start_utc, session_date, open, high, low, close,
    volume_delta, n_ticks, is_regular, close_quality, last_tick_offset_s.
    """
    sesiones_por_dia = sesiones_por_dia or {}
    ticks_por_asset: Dict[int, List[Dict]] = defaultdict(list)
    clase_por_asset: Dict[int, str] = {}

    for t in ticks:
        aid = t.get("asset_id")
        if aid is None or t.get("timestamp_utc") is None:
            continue
        ticks_por_asset[aid].append(t)
        clase = t.get("asset_class") or "equity"
        clase_por_asset.setdefault(aid, clase)

    barras: List[Dict] = []
    for aid, serie in ticks_por_asset.items():
        serie.sort(key=lambda t: t["timestamp_utc"])
        clase = clase_por_asset[aid]

        # Buckets en orden: [(bar_start, [ticks])]
        buckets: List[tuple] = []
        for tick in serie:
            inicio = bucket_15m_utc(tick["timestamp_utc"])
            if buckets and buckets[-1][0] == inicio:
                buckets[-1][1].append(tick)
            else:
                buckets.append((inicio, [tick]))

        for bar_start, ticks_bar in buckets:
            cierres = [t.get("close") for t in ticks_bar if t.get("close") is not None]
            vols = [t.get("volume") for t in ticks_bar if t.get("volume") is not None]

            if not cierres:
                # Barra sin valores de mercado → solo se cuenta n_ticks.
                open_v = high_v = low_v = close_v = None
            else:
                open_v = cierres[0]
                high_v = max(cierres)
                low_v = min(cierres)
                close_v = cierres[-1]

            if len(vols) >= 1 and vols[0] is not None and vols[-1] is not None:
                volume_delta = vols[-1] - vols[0]
            else:
                volume_delta = None

            ultimo = ticks_bar[-1]["timestamp_utc"]
            cierre = bar_cierre_utc(bar_start)
            offset = ultimo_tick_offset_s(cierre, ultimo)

            barras.append({
                "asset_id": aid,
                "bar_start_utc": bar_start,
                "session_date": session_date_para(bar_start),
                "open": open_v,
                "high": high_v,
                "low": low_v,
                "close": close_v,
                "volume_delta": volume_delta,
                "n_ticks": len(ticks_bar),
                "is_regular": es_barra_regular(clase, bar_start, sesiones_por_dia),
                "close_quality": close_quality_para_offset(offset),
                "last_tick_offset_s": offset,
            })

    barras.sort(key=lambda b: (b["asset_id"], b["bar_start_utc"]))
    return barras


def resumen_calidad(barras: List[Dict]) -> Dict:
    """Distribución de close_quality y n_ticks para el reporte del job."""
    conteo: Dict[str, int] = {"definitive": 0, "provisional": 0, "unknown": 0}
    n_ticks_ge3 = 0
    total = len(barras)
    for b in barras:
        conteo[b["close_quality"]] = conteo.get(b["close_quality"], 0) + 1
        if b["n_ticks"] >= 3:
            n_ticks_ge3 += 1
    pct = lambda n: round(100.0 * n / total, 1) if total else 0.0
    return {
        "total": total,
        "definitive": conteo[CALIDAD_DEFINITIVA],
        "provisional": conteo[CALIDAD_PROVISIONAL],
        "unknown": conteo[CALIDAD_DESCONOCIDA],
        "pct_definitive": pct(conteo[CALIDAD_DEFINITIVA]),
        "pct_provisional": pct(conteo[CALIDAD_PROVISIONAL]),
        "pct_n_ticks_ge3": pct(n_ticks_ge3),
    }


# ---------------------------------------------------------------------------
# Acceso a BD
# ---------------------------------------------------------------------------

def leer_ticks(db: PostgreSQLConnector, desde_utc: datetime, hasta_utc: datetime) -> List[Dict]:
    """Lee los ticks de fact_market_series en [desde, hasta) + asset_class."""
    query = """
        SELECT t.asset_id, t.timestamp_utc, t.close, t.volume,
               COALESCE(d.asset_class, 'equity') AS asset_class
        FROM fact_market_series t
        LEFT JOIN dim_asset d
               ON d.asset_id = t.asset_id
        WHERE t.timestamp_utc >= %s AND t.timestamp_utc < %s
        ORDER BY t.asset_id, t.timestamp_utc
    """
    return db.execute_query(query, (desde_utc, hasta_utc))


def leer_sesiones(db: PostgreSQLConnector, desde_utc: datetime,
                  hasta_utc: datetime) -> Dict[str, Dict]:
    """Carga las sesiones XNYS de `dim_trading_session` para el rango de la
    corrida (por fecha ET, con un día de margen por el desfase UTC)."""
    desde_ny = fecha_ny_iso(desde_utc - timedelta(days=1))
    hasta_ny = fecha_ny_iso(hasta_utc + timedelta(days=1))
    query = """
        SELECT session_date, is_session, opens_at, closes_at
        FROM dim_trading_session
        WHERE session_date BETWEEN %s AND %s
    """
    rows = db.execute_query(query, (desde_ny, hasta_ny))
    sesiones = {}
    for row in rows:
        dia = row.get("session_date")
        if dia is None:
            continue
        iso = dia.strftime("%Y-%m-%d") if isinstance(dia, date) else str(dia)[:10]
        sesiones[iso] = {
            "is_session": bool(row.get("is_session")),
            "opens_at": row.get("opens_at"),
            "closes_at": row.get("closes_at"),
        }
    return sesiones


def _inicio_mes_utc(dt: datetime) -> datetime:
    """Primer instante del mes UTC de `dt` (tz-aware)."""
    return dt.astimezone(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)


def asegurar_particion(db: PostgreSQLConnector, bar_start_utc: datetime) -> bool:
    """Garantiza la partición mensual de fact_market_bar_15m (fronteras UTC).

    Las particiones viven hasta 2027_12 en el baseline; solo se crea una
    cuando falta (p. ej. un backfill a meses anteriores). Las fronteras se
    pasan como timestamptz a 00:00 UTC — misma convención que el baseline
    (que las declara `-05` pero por instante coinciden con los inicios de
    mes UTC).
    """
    mes = _inicio_mes_utc(bar_start_utc)
    if mes.month == 12:
        fin = mes.replace(year=mes.year + 1, month=1)
    else:
        fin = mes.replace(month=mes.month + 1)
    particion = f"fact_market_bar_15m_{mes.strftime('%Y_%m')}"

    existe = db.execute_query(
        "SELECT 1 AS ok FROM pg_class WHERE relname = %s", (particion,)
    )
    if existe:
        return False

    db.execute_query(
        f"CREATE TABLE {particion} PARTITION OF fact_market_bar_15m "
        "FOR VALUES FROM (%s) TO (%s)",
        (mes, fin),
    )
    logger.info("Partición %s creada (%s / %s)", particion, mes.date(), fin.date())
    return True


def upsert_barras(db: PostgreSQLConnector, barras: List[Dict]) -> int:
    """Upsert de barras en fact_market_bar_15m (revisión idempotente).

    Inserta por mes (commit por partición): si un mes se cae por datos
    inválidos, los demás meses ya escritos persisten. Garantiza la
    partición de cada mes del lote antes de insertar.
    """
    if not barras:
        return 0

    por_mes: Dict[datetime, List[Dict]] = defaultdict(list)
    for b in barras:
        por_mes[_inicio_mes_utc(b["bar_start_utc"])].append(b)

    query = f"""
        INSERT INTO fact_market_bar_15m (
            {_COLUMNAS_BARRA}
        ) VALUES %s
        ON CONFLICT (asset_id, bar_start_utc) DO UPDATE SET
            session_date       = EXCLUDED.session_date,
            open               = EXCLUDED.open,
            high               = EXCLUDED.high,
            low                = EXCLUDED.low,
            close              = EXCLUDED.close,
            volume_delta       = EXCLUDED.volume_delta,
            n_ticks            = EXCLUDED.n_ticks,
            is_regular         = EXCLUDED.is_regular,
            close_quality      = EXCLUDED.close_quality,
            last_tick_offset_s = EXCLUDED.last_tick_offset_s
    """
    template = "(" + ", ".join(["%s"] * 12) + ")"

    total = 0
    for mes in sorted(por_mes):
        grupo = por_mes[mes]
        asegurar_particion(db, grupo[0]["bar_start_utc"])
        params = [
            (
                b["asset_id"], b["bar_start_utc"], b["session_date"],
                b["open"], b["high"], b["low"], b["close"],
                b["volume_delta"], int(b["n_ticks"]), bool(b["is_regular"]),
                b["close_quality"], b["last_tick_offset_s"],
            )
            for b in grupo
        ]
        db.execute_values(query, params, template=template)
        total += len(params)

    logger.info("Barras escritas: %d (fact_market_bar_15m)", total)
    return total