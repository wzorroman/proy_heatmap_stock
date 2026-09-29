"""dim_asset: alta de los 10 símbolos faltantes del universo

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-29 16:40 UTC

`0002` siembra `dim_asset` desde un `pg_dump` del 2026-09-23 (1.668 símbolos).
Desde entonces el scraper `heatmap` descubrió 10 símbolos más por sí solo
(`upsert_heatmap_snapshot` inserta en `dim_asset` cuando el símbolo no
existe), así que una **BD nueva cargada desde cero** quedaba con 1.669
símbolos mientras la BD en uso tiene 1.679.

Consecuencias de no sembrarlos:

1. `upsert_market_series` hace `RAISE EXCEPTION 'Activo no registrado en
   dim_asset: %'` ante un símbolo ausente: una BD limpia no puede escribir
   series de esos 10.
2. `dim_asset_asset_id_seq` queda en 4701 mientras la BD en uso está en 4711:
   los `asset_id` de los hechos se|numbrarían distinto en cada entorno, y los
   símbolos discoveries recibirían ids que en la otra BD pertenecen a otros
   (`upsert_heatmap_snapshot` auto-inserta en 4702+).
3. Los 10 rows quedaron con `feed_delay_s = NULL` en la BD en uso, porque el
   backfill por `asset_class` de `0006` (common → 900 s) corrió el 2026-09-23
   y estas filas se insertaron el 2026-09-29. Las otras 527 filas `common`
   tienen 900. Esta revisión también normaliza ese campo.

La revisión:

1. Inserta los 10 símbolos con `asset_id` explícito 4702-4711 (mismo
   identificador que en la BD en uso, para que los hechos sean comparables
   entre entornos).
2. `ON CONFLICT (symbol) DO UPDATE` sobre las 21 columnas: re-ejecutarla
   sincroniza la fila con el catálogo de referencia en vez de duplicarla, y
   en la BD en uso solo corrige `feed_delay_s`.
3. Normaliza `feed_delay_s = 900` (asset_class `common`).
4. `setval` de `dim_asset_asset_id_seq` a 4711 sin retroceder por debajo del
   `MAX(asset_id)` existente.

`downgrade()` borra solo los 10 símbolos de esta revisión que no tengan
hechos asociados (protege las FK de `fact_*` y `latest_market_tick`).

Los archivos 0001-0007 ya aplicados no se tocan.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# Fila de dim_asset en el esquema post-0006 (sin las columnas SCD2 dropeadas).
# (asset_id, symbol, ticker, exchange, asset_class, share_class, sector,
#  sector_es, company_name, logo_id, source_discovered_by, source_category,
#  is_active, created_at, updated_at, slug, url_logo, logical_key,
#  is_canonical, role, feed_delay_s)
_COLUMNAS = (
    "asset_id", "symbol", "ticker", "exchange", "asset_class", "share_class",
    "sector", "sector_es", "company_name", "logo_id", "source_discovered_by",
    "source_category", "is_active", "created_at", "updated_at", "slug",
    "url_logo", "logical_key", "is_canonical", "role", "feed_delay_s",
)

_ALTAS = (
    (4702, "NASDAQ:FRHC", "FRHC", "NASDAQ", "common", "common", "Finance",
     None, "Freedom Holding Corp.", "freedom-holding", "heatmap", None, True,
     "2026-09-29 13:00:24.288402+00", "2026-09-29 13:00:24.288402+00", None,
     None, None, False, None, 900),
    (4703, "NYSE:FR", "FR", "NYSE", "common", "common", "Finance", None,
     "First Industrial Realty Trust, Inc.", "first-industrial-realty-trust",
     "heatmap", None, True, "2026-09-29 13:00:24.288402+00",
     "2026-09-29 13:00:24.288402+00", None, None, None, False, None, 900),
    (4704, "NYSE:NEU", "NEU", "NYSE", "common", "common", "Process Industries",
     None, "NewMarket Corporation", "newmarket", "heatmap", None, True,
     "2026-09-29 13:00:24.288402+00", "2026-09-29 13:00:24.288402+00", None,
     None, None, False, None, 900),
    (4705, "NYSE:ADC", "ADC", "NYSE", "common", "common", "Finance", None,
     "Agree Realty Corporation",
     "agree-realty-depositary-shares-each-representing-1-1000th-of-a-4250-series-a-cumulative-redeemable-preferred-stock",
     "heatmap", None, True, "2026-09-29 13:00:24.288402+00",
     "2026-09-29 13:00:24.288402+00", None, None, None, False, None, 900),
    (4706, "NYSE:WAL", "WAL", "NYSE", "common", "common", "Finance", None,
     "Western Alliance Bancorp", "western-alliance-bancorp", "heatmap", None,
     True, "2026-09-29 13:00:24.288402+00", "2026-09-29 13:00:24.288402+00",
     None, None, None, False, None, 900),
    (4707, "NYSE:RHP", "RHP", "NYSE", "common", "common", "Finance", None,
     "Ryman Hospitality Properties, Inc.", "ryman-hospitality-properties-reit",
     "heatmap", None, True, "2026-09-29 13:00:24.288402+00",
     "2026-09-29 13:00:24.288402+00", None, None, None, False, None, 900),
    (4708, "NASDAQ:AVT", "AVT", "NASDAQ", "common", "common",
     "Distribution Services", None, "Avnet, Inc.", "avnet", "heatmap", None,
     True, "2026-09-29 13:00:24.288402+00", "2026-09-29 13:00:24.288402+00",
     None, None, None, False, None, 900),
    (4709, "NASDAQ:WYNN", "WYNN", "NASDAQ", "common", "common",
     "Consumer Services", None, "Wynn Resorts, Limited", "wynn-resorts",
     "heatmap", None, True, "2026-09-29 13:00:24.288402+00",
     "2026-09-29 13:00:24.288402+00", None, None, None, False, None, 900),
    (4710, "NYSE:KMX", "KMX", "NYSE", "common", "common", "Retail Trade", None,
     "CarMax, Inc.", "carmax", "heatmap", None, True,
     "2026-09-29 13:45:23.219834+00", "2026-09-29 13:45:23.219834+00", None,
     None, None, False, None, 900),
    (4711, "NASDAQ:MXL", "MXL", "NASDAQ", "common", "common",
     "Electronic Technology", None, "MaxLinear, Inc.", "maxlinear", "heatmap",
     None, True, "2026-09-29 13:45:23.219834+00",
     "2026-09-29 13:45:23.219834+00", None, None, None, False, None, 900),
)

_SIN_NULOS = {"sector_es", "source_category", "slug", "url_logo", "logical_key",
              "role"}


def _literal(valor, columna):
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int):
        return str(valor)
    if columna in _SIN_NULOS:
        return "NULL"
    return "'" + str(valor).replace("'", "''") + "'"


def _fila_sql(fila):
    return "    (" + ", ".join(
        _literal(v, c) for v, c in zip(fila, _COLUMNAS)
    ) + ")"


_DATOS = (
    "INSERT INTO public.dim_asset\n    ("
    + ", ".join(_COLUMNAS)
    + ")\nVALUES\n"
    + ",\n".join(_fila_sql(f) for f in _ALTAS)
    + "\nON CONFLICT (symbol) DO UPDATE SET\n    "
    + ",\n    ".join(
        "{} = EXCLUDED.{}".format(c, c) for c in _COLUMNAS if c != "asset_id"
    )
    + ";\n"
)

# setval sin retroceder: si la BD ya tiene asset_id > 4711 (altas posteriores),
# la secuencia queda en el máximo real y no en 4711.
_SEQ = """
SELECT setval(
    'public.dim_asset_asset_id_seq',
    GREATEST(
        (SELECT COALESCE(MAX(asset_id), 1) FROM public.dim_asset),
        4711
    )
);
"""

# Normaliza feed_delay_s de los 10 (NULL en la BD en uso por el backfill de
# 0006 anterior a su inserción); asset_class 'common' → 900 s.
_NORMALIZA = """
UPDATE public.dim_asset
   SET feed_delay_s = 900
 WHERE symbol = ANY(%s)
   AND (feed_delay_s IS NULL OR feed_delay_s <> 900);
"""

_SIMBOLOS = [f[1] for f in _ALTAS]

_DOWNGRADE = """
DELETE FROM public.dim_asset a
 WHERE a.symbol = ANY(%s)
   AND NOT EXISTS (SELECT 1 FROM public.fact_market_series f
                    WHERE f.asset_id = a.asset_id)
   AND NOT EXISTS (SELECT 1 FROM public.fact_heatmap_snapshot h
                    WHERE h.asset_id = a.asset_id)
   AND NOT EXISTS (SELECT 1 FROM public.fact_market_bar_15m b
                    WHERE b.asset_id = a.asset_id)
   AND NOT EXISTS (SELECT 1 FROM public.fact_market_indicator_tf i
                    WHERE i.asset_id = a.asset_id)
   AND NOT EXISTS (SELECT 1 FROM public.latest_market_tick l
                    WHERE l.asset_id = a.asset_id);
"""

_SEQ_DOWNGRADE = """
SELECT setval(
    'public.dim_asset_asset_id_seq',
    GREATEST(
        (SELECT COALESCE(MAX(asset_id), 1) FROM public.dim_asset),
        1
    )
);
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DATOS)
        cur.execute(_NORMALIZA, (_SIMBOLOS,))
        cur.execute(_SEQ)


def downgrade():
    """Retira los 10 símbolos de esta revisión sin referenciar y resincroniza la
    secuencia."""
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWNGRADE, (_SIMBOLOS,))
        cur.execute(_SEQ_DOWNGRADE)
