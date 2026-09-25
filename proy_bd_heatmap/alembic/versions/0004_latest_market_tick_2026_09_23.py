"""crear latest_market_tick (F4.3, último tick por activo)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-23 21:30 UTC

F4.3 · `latest_market_tick` — cierra E-DSH-04 (M-DAT-04).

Una fila por activo (`asset_id` como PK), actualizada por UPSERT en cada
ciclo del radar. Permite que el dashboard lea ~110 filas (=== universo)
para el panel de mercado sin escanear `fact_market_series` (decenas de
miles de ticks), que pasa a ser la historia.

Cada ciclo reescribe la fila con la última marca: close/change/volume,
los indicadores de régimen (base 1D) y el bloque `|15` que el dashboard
usa para el etiquetado (RSI 15m, CCI20, BBPower, ADX, pivote camarilla R3),
más la trazabilidad temporal (`update_mode`, `feed_delay_s`, `cycle_id`,
`fetched_at`).

No es particionada: el objetivo es una fila por activo (tamaño fijo,
crece solo con el universo), no un histórico.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


_DDL = r"""
-- ==== F4.3 · latest_market_tick (último tick por activo) ====

CREATE TABLE public.latest_market_tick (
    asset_id integer NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    close numeric(18,6),
    change_pct numeric(12,6),
    volume numeric(30,8),
    rsi numeric(12,6),
    rsi_15 numeric(12,6),
    cci20_15 numeric(14,6),
    bbpower_15 numeric(20,8),
    adx_15 numeric(12,6),
    pivot_r3_15 numeric(20,8),
    update_mode character varying(30),
    feed_delay_s integer,
    cycle_id uuid,
    fetched_at timestamp with time zone,
    ingested_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT latest_market_tick_pkey PRIMARY KEY (asset_id)
);

COMMENT ON TABLE public.latest_market_tick IS
    'Último tick de mercado por activo (1 fila/asset_id), reescrito por UPSERT en cada ciclo del radar (F4.3 · E-DSH-04).';

COMMENT ON COLUMN public.latest_market_tick.asset_id IS 'FK a dim_asset (PK).';
COMMENT ON COLUMN public.latest_market_tick.timestamp_utc IS 'Instante de captura del ciclo del radar.';
COMMENT ON COLUMN public.latest_market_tick.close IS 'Último close capturado.';
COMMENT ON COLUMN public.latest_market_tick.change_pct IS 'change del bloque base (cambio % día).';
COMMENT ON COLUMN public.latest_market_tick.volume IS 'volume del bloque base (acumulado 1D).';
COMMENT ON COLUMN public.latest_market_tick.rsi IS 'RSI del bloque base (régimen 1D).';
COMMENT ON COLUMN public.latest_market_tick.rsi_15 IS 'RSI|15 del bloque multi-TF (etiquetado 15m del dashboard).';
COMMENT ON COLUMN public.latest_market_tick.cci20_15 IS 'CCI20|15 del bloque multi-TF.';
COMMENT ON COLUMN public.latest_market_tick.bbpower_15 IS 'BBPower|15 del bloque multi-TF.';
COMMENT ON COLUMN public.latest_market_tick.adx_15 IS 'ADX|15 del bloque multi-TF.';
COMMENT ON COLUMN public.latest_market_tick.pivot_r3_15 IS 'Pivot.M.Camarilla.R3|15 del bloque multi-TF.';
COMMENT ON COLUMN public.latest_market_tick.update_mode IS 'update_mode reportado por el endpoint (streaming/delayed_streaming_900/…).';
COMMENT ON COLUMN public.latest_market_tick.feed_delay_s IS 'Retraso derivado de update_mode (streaming→0, delayed_streaming_900→900).';
COMMENT ON COLUMN public.latest_market_tick.cycle_id IS 'Ciclo de radar que produjo esta marca (uuid, trazabilidad F3.10).';
COMMENT ON COLUMN public.latest_market_tick.fetched_at IS 'Instante real del fetch del símbolo (puede diferir de timestamp_utc del ciclo).';
COMMENT ON COLUMN public.latest_market_tick.ingested_at IS 'Instante de escritura en BD (default CURRENT_TIMESTAMP).';
"""

_DOWN = r"""
-- ============ downgrade: revierte F4.3 ============
DROP TABLE IF EXISTS public.latest_market_tick CASCADE;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)