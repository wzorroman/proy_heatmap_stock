"""crear fact_market_score + fact_market_score_agg (prototipo dashboard)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-30

Fase 1 del dashboard `proy_dashboard` (decisión D8):
  - `fact_market_score`      → detalle por activo y ciclo (particionada mensual UTC + BRIN).
  - `fact_market_score_agg`  → agregado de mercado por ciclo (1 fila; BRIN).

Se separa el agregado del detalle para evitar redundancia (la tabla única
repetiría los agregados de mercado en cada activo), mantener integridad
atómica por ciclo y permitir recalcular el agregado sin re-scrapear.

Convención de particiones/fronteras UTC idéntica a 0003 (`fact_market_indicator_tf`)
y BRIN como en el baseline (`*_ts_brin`): 2026_09 … 2027_12.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _particiones():
    """Particiones mensuales UTC 2026_09 … 2027_12 + BRIN por partición."""
    bloques = []
    for anio in (2026, 2027):
        for mes in range(1, 13):
            if (anio, mes) < (2026, 9):
                continue
            nombre = f"fact_market_score_{anio}_{mes:02d}"
            desde = f"{anio}-{mes:02d}-01 00:00:00+00"
            fin_anio, fin_mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
            fin = f"{fin_anio}-{fin_mes:02d}-01 00:00:00+00"
            bloques.append(
                f"CREATE TABLE public.{nombre} PARTITION OF public.fact_market_score "
                f"FOR VALUES FROM ('{desde}') TO ('{fin}');"
            )
            bloques.append(
                f"CREATE INDEX {nombre}_ts_brin ON public.{nombre} USING brin (timestamp_utc);"
            )
    return "\n".join(bloques)


_DDL = f"""
-- ==== 0009 · fact_market_score (detalle por activo/ciclo) ====

CREATE TABLE public.fact_market_score (
    asset_id      integer      NOT NULL,
    timestamp_utc timestamptz  NOT NULL,
    score_general numeric(8,4),
    zona          text,
    componentes   jsonb,
    ingested_at   timestamptz  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fact_market_score_pkey PRIMARY KEY (asset_id, timestamp_utc)
) PARTITION BY RANGE (timestamp_utc);

COMMENT ON TABLE public.fact_market_score IS
    'Score por activo y ciclo (prototipo dashboard). Detalle para drill-down/backtest y re-agregación.';
COMMENT ON COLUMN public.fact_market_score.asset_id IS 'FK a dim_asset.';
COMMENT ON COLUMN public.fact_market_score.timestamp_utc IS 'Instante del ciclo del radar.';
COMMENT ON COLUMN public.fact_market_score.score_general IS 'PASO 1 por símbolo, rango [0,10].';
COMMENT ON COLUMN public.fact_market_score.zona IS 'COMPRAR | NEUTRAL | VENDER (umbrales de config).';
COMMENT ON COLUMN public.fact_market_score.componentes IS
    'JSON con la contribución por indicador ({{nombre, valor, norm, peso}}).';

{_particiones()}

-- ==== 0009 · fact_market_score_agg (agregado de mercado por ciclo) ====

CREATE TABLE public.fact_market_score_agg (
    timestamp_utc   timestamptz  NOT NULL,
    score_momentum  numeric(8,4),
    score_15min     numeric(8,4),
    score_radar     numeric(8,4),
    score_market    numeric(8,4),
    zona            text,
    n_simbolos      smallint,
    source_checksum varchar(64),
    audit_id        bigint,
    ingested_at     timestamptz  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fact_market_score_agg_pkey PRIMARY KEY (timestamp_utc)
);

CREATE INDEX fact_market_score_agg_ts_brin
    ON public.fact_market_score_agg USING brin (timestamp_utc);

COMMENT ON TABLE public.fact_market_score_agg IS
    'Agregado de mercado por ciclo del radar (score momentum/15min/radar), 1 fila por timestamp.';
COMMENT ON COLUMN public.fact_market_score_agg.score_momentum IS 'PASO 2: media ponderada del score por símbolo (equity/etf).';
COMMENT ON COLUMN public.fact_market_score_agg.score_15min IS 'PASO 2b: media de los últimos N registros por temporalidad.';
COMMENT ON COLUMN public.fact_market_score_agg.score_radar IS 'PASO 3: blend intermarket (VIX/US10Y/DXY/TLT).';
COMMENT ON COLUMN public.fact_market_score_agg.score_market IS 'Agregado final de mercado.';
COMMENT ON COLUMN public.fact_market_score_agg.n_simbolos IS 'Activos con score en el ciclo.';

-- ==== Vistas de presentación ====

CREATE VIEW public.vw_market_score_history AS
    SELECT * FROM public.fact_market_score_agg ORDER BY timestamp_utc;

CREATE VIEW public.vw_market_score_latest AS
    SELECT * FROM public.fact_market_score_agg ORDER BY timestamp_utc DESC LIMIT 1;

COMMENT ON VIEW public.vw_market_score_history IS 'Histórico del agregado de mercado ordenado por timestamp.';
COMMENT ON VIEW public.vw_market_score_latest IS 'Último agregado de mercado (header del dashboard).';
"""

_DOWN = r"""
-- ============ downgrade: revierte la Fase 1 del dashboard ============
DROP VIEW IF EXISTS public.vw_market_score_latest;
DROP VIEW IF EXISTS public.vw_market_score_history;
DROP TABLE IF EXISTS public.fact_market_score_agg CASCADE;
DROP TABLE IF EXISTS public.fact_market_score CASCADE;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)
