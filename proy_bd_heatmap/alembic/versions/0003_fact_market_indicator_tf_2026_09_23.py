"""crear fact_market_indicator_tf (F4.2, formato largo)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-23 20:40 UTC

F4.2 · `fact_market_indicator_tf` (formato largo) — cierra E-RAD-01 y D12.

Crea la tabla en formato largo (una fila por activo × timestamp × timeframe)
para los indicadores multi-TF capturados del batch `POST /america/scan`
(bloque `|5`, `|15`, `|60` del `CAMPOS` de F3.2 más
`Pivot.M.Camarilla.R3|15`). Particionada por RANGE (timestamp_utc) con
fronteras mensuales UTC (2026_09 → 2027_12), la misma convención que
`fact_market_bar_15m` (a diferencia de la `-05` legacy de F3/F4, pendiente
en F2.3).

El `rsi`/`cci20`/etc. de base (timeframe 1D de régimen) sigue viviendo en
`fact_market_series`; esta tabla guarda solo los bloques explícitos por TF.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _particiones():
    """Particiones mensuales UTC 2026_09 … 2027_12 (convención bar 15m)."""
    meses = []
    for anio in (2026, 2027):
        for mes in range(1, 13):
            if (anio, mes) < (2026, 9):
                continue
            nombre = f"fact_market_indicator_tf_{anio}_{mes:02d}"
            desde = f"{anio}-{mes:02d}-01 00:00:00+00"
            fin_anio, fin_mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
            fin = f"{fin_anio}-{fin_mes:02d}-01 00:00:00+00"
            meses.append(
                f"CREATE TABLE public.{nombre} PARTITION OF public.fact_market_indicator_tf "
                f"FOR VALUES FROM ('{desde}') TO ('{fin}');"
            )
    return "\n".join(meses)


_DDL = f"""
-- ==== F4.2 · fact_market_indicator_tf (formato largo) ====

CREATE TABLE public.fact_market_indicator_tf (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    tf character varying(3) NOT NULL,
    rsi numeric(12,6),
    cci20 numeric(14,6),
    bbpower numeric(20,8),
    adx numeric(12,6),
    change_pct numeric(12,8),
    volume numeric(30,8),
    pivot_r3 numeric(20,8),
    CONSTRAINT fact_market_indicator_tf_pkey
        PRIMARY KEY (asset_id, timestamp_utc, tf)
)
PARTITION BY RANGE (timestamp_utc);

COMMENT ON TABLE public.fact_market_indicator_tf IS
    'Indicadores multi-TF en formato largo (por activo × timestamp × tf). Un TF no exige cambiar el esquema (D12).';

COMMENT ON COLUMN public.fact_market_indicator_tf.asset_id IS 'FK a dim_asset.';
COMMENT ON COLUMN public.fact_market_indicator_tf.timestamp_utc IS 'Instante de captura del ciclo del radar (contrae al origen de la barra del TF).';
COMMENT ON COLUMN public.fact_market_indicator_tf.tf IS 'Timeframe del bloque de indicadores: ''5'', ''15'', ''30'' o ''60'' (catálogo T12).';
COMMENT ON COLUMN public.fact_market_indicator_tf.rsi IS 'RSI|tf del bloque (TradingView, vela del TF en formación; definitivo solo al cierre, F4.1b).';
COMMENT ON COLUMN public.fact_market_indicator_tf.cci20 IS 'CCI20|tf del bloque.';
COMMENT ON COLUMN public.fact_market_indicator_tf.bbpower IS 'BBPower|tf del bloque.';
COMMENT ON COLUMN public.fact_market_indicator_tf.adx IS 'ADX|tf del bloque.';
COMMENT ON COLUMN public.fact_market_indicator_tf.change_pct IS 'change|tf (cambio % dentro de la vela del TF).';
COMMENT ON COLUMN public.fact_market_indicator_tf.volume IS 'volume|tf (contador de volumen acumulado de la vela del TF, se reinicia en la frontera).';
COMMENT ON COLUMN public.fact_market_indicator_tf.pivot_r3 IS 'Pivot.M.Camarilla.R3|tf (pivote diario en |15, Test H/T6); solo existe en bloque |5/|15.';

{_particiones()}
"""

_DOWN = r"""
-- ============ downgrade: revierte F4.2 ============
DROP TABLE IF EXISTS public.fact_market_indicator_tf CASCADE;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)