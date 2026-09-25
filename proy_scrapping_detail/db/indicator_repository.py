# file: proy_scrapping_detail/db/indicator_repository.py
"""F4.2 · Persistencia de indicadores multi-TF en formato largo
(`fact_market_indicator_tf`).

Cierra E-RAD-01 y D12: los indicadores capturados por el batch
`POST /america/scan` (CAMPOS de F3.2) incluyen bloques `|5`, `|15` y
`|60` además del bloque base (1D de régimen). Esta tabla larga guarda una
fila por (asset, timestamp, tf) con los campos del bloque:

    rsi, cci20, bbpower, adx, change_pct, volume, pivot_r3

- `volume|tf` es el contador de volumen acumulado de la vela del TF (se
  reinicia en la frontera, Test C).
- `Pivot.M.Camarilla.R3|tf` solo se captura en el bloque `|15` (pivote
  diario, Test H / T6); para `|5`/`|60` se deja NULL.
- `timestamp_utc` es el instante de captura del ciclo, no el del barrido
  del TF (el valor definitivo del bloque solo existe al cierre, F4.1b).
- El bloque base (1D) sigue viviendo en `fact_market_series`.

El radar persiste estas filas en cada ciclo (mismo `timestamp_utc` que la
serie); `scripts/build_indicator_tf.py` permite re-materializar/verificar un
rango (modo `--from-scan` para la ventana actual).

"El esquema de indicadores migra a tabla larga `fact_market_indicator_tf`
empezando por `15` y `5` (D12); `30`/`60` solo si M-VAL-02 los usa."
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.indicator_repository')

# D12: empezamos por 15 y 5 (M-VAL-02 aún no usa 30/60).
TFS_INDICADOR = ("15", "5")

# Campos de cada bloque |TF (clave en la respuesta del scan -> columna).
_CAMPOS_BLOQUE = {
    "RSI": "rsi",
    "CCI20": "cci20",
    "BBPower": "bbpower",
    "ADX": "adx",
    "change": "change_pct",
    "volume": "volume",
}

# Pivote de camarilla: solo existe la variante |15 en CAMPOS (F3.2).
_PIVOTE_TFS = ("15",)

_COLUMNAS = (
    "asset_id, timestamp_utc, tf, rsi, cci20, bbpower, adx, "
    "change_pct, volume, pivot_r3"
)


def proyectar_item(item: Dict, asset_id: int, tfs: Iterable[str]) -> List[Dict]:
    """Proyecta una fila cruda del scan (claves `CAMPOS_LIST`, incl. `|TF`)
    a filas largas de `fact_market_indicator_tf` (una por tf).

    `timestamp_utc` puede venir como epoch int (scraper) o datetime.
    Retorna [] si no hay ningún valor del bloque para ningún tf.
    """
    ts = item.get('timestamp_utc')
    if ts is None:
        return []
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    filas = []
    for tf in tfs:
        valores = {
            columna: item.get(f"{campo}|{tf}")
            for campo, columna in _CAMPOS_BLOQUE.items()
        }
        pivot = None
        if tf in _PIVOTE_TFS:
            pivot = item.get(f"Pivot.M.Camarilla.R3|{tf}")
        # Solo emitir la fila si al menos un valor del bloque o del pivote
        # existe (evita filas vacías en activos fuera del universo del batch).
        if not any(v is not None and v != '' for v in valores.values()) \
                and pivot is None:
            continue
        filas.append({
            "asset_id": int(asset_id),
            "timestamp_utc": ts,
            "tf": tf,
            "rsi": valores["rsi"],
            "cci20": valores["cci20"],
            "bbpower": valores["bbpower"],
            "adx": valores["adx"],
            "change_pct": valores["change_pct"],
            "volume": valores["volume"],
            "pivot_r3": pivot,
        })
    return filas


def _inicio_mes_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)


def asegurar_particion(db: PostgreSQLConnector, timestamp_utc: datetime) -> bool:
    """Garantiza la partición mensual UTC que contiene `timestamp_utc`.

    Solo crea cuando falta (las particiones 2026_09→2027_12 viven en la
    migración 0003); fronteras a 00:00 UTC como `fact_market_bar_15m`.
    """
    mes = _inicio_mes_utc(timestamp_utc)
    if mes.month == 12:
        fin = mes.replace(year=mes.year + 1, month=1)
    else:
        fin = mes.replace(month=mes.month + 1)
    particion = f"fact_market_indicator_tf_{mes.strftime('%Y_%m')}"

    existe = db.execute_query(
        "SELECT 1 AS ok FROM pg_class WHERE relname = %s", (particion,)
    )
    if existe:
        return False

    db.execute_query(
        f"CREATE TABLE {particion} PARTITION OF fact_market_indicator_tf "
        "FOR VALUES FROM (%s) TO (%s)",
        (mes, fin),
    )
    logger.info("Partición %s creada (%s / %s)", particion, mes.date(), fin.date())
    return True


def insert_indicator_tf_batch(db: PostgreSQLConnector, items: List[Dict],
                              asset_cache: Dict[str, int],
                              tfs: Iterable[str] = TFS_INDICADOR) -> int:
    """Upsert de filas largas de indicadores para una lista de items crudos
    del scan. `asset_cache`: {symbol: asset_id} (reutiliza el del ciclo).

    Inserta por mes (commit por partición) y por lote; ON CONFLICT
    (asset_id, timestamp_utc, tf) DO UPDATE para revisar filas del mismo ciclo.
    Retorna el número de filas largas escritas.
    """
    if not items:
        return 0

    tfs = tuple(tfs)
    filas_aplanadas: List[Dict] = []
    simbolos_ausentes = set()
    for item in items:
        symbol = item.get('simbolo') or item.get('symbol')
        if not symbol:
            continue
        asset_id = asset_cache.get(symbol)
        if asset_id is None:
            simbolos_ausentes.add(symbol)
            continue
        filas_aplanadas.extend(proyectar_item(item, asset_id, tfs))

    if simbolos_ausentes:
        logger.warning(
            f"Indicadores TF: {len(simbolos_ausentes)} símbolos sin asset_id — omitidos")

    if not filas_aplanadas:
        logger.info("Indicadores TF: sin filas válidas para escribir")
        return 0

    # Agrupar por mes para asegurar partición y commit por mes.
    por_mes: Dict[datetime, List[Dict]] = defaultdict(list)
    for f in filas_aplanadas:
        por_mes[_inicio_mes_utc(f["timestamp_utc"])].append(f)

    query = f"""
        INSERT INTO fact_market_indicator_tf ({_COLUMNAS}) VALUES %s
        ON CONFLICT (asset_id, timestamp_utc, tf) DO UPDATE SET
            rsi        = EXCLUDED.rsi,
            cci20      = EXCLUDED.cci20,
            bbpower    = EXCLUDED.bbpower,
            adx        = EXCLUDED.adx,
            change_pct = EXCLUDED.change_pct,
            volume     = EXCLUDED.volume,
            pivot_r3   = EXCLUDED.pivot_r3
    """
    template = "(" + ", ".join(["%s"] * 10) + ")"

    total = 0
    for mes in sorted(por_mes):
        grupo = por_mes[mes]
        asegurar_particion(db, grupo[0]["timestamp_utc"])
        params = [
            (
                f["asset_id"], f["timestamp_utc"], f["tf"],
                f["rsi"], f["cci20"], f["bbpower"], f["adx"],
                f["change_pct"], f["volume"], f["pivot_r3"],
            )
            for f in grupo
        ]
        db.execute_values(query, params, template=template)
        total += len(params)

    logger.info("Indicadores TF: %d filas largas en fact_market_indicator_tf", total)
    return total