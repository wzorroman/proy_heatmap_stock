"""fact_heatmap_snapshot: columnas explícitas (F4.4)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-23 21:40 UTC

F4.4 · Snapshots con columnas explícitas — cierra E-HM-08 y E-HM-10
(M-DAT-05).

`fact_heatmap_snapshot` guardaba el vector `d` del endpoint completo en
`raw_vector` (JSONB con GIN, ~1,8 kB/fila) sin columnas para lo que el
dashboard consulta. Esta migración añade las columnas explícitas
(M-DAT-05), rellenadas por el scraper en cada capture:

    volume, avg_vol_10d, avg_vol_30d, volatility_d, change_abs,
    high_52w, low_52w, update_mode, fetched_at

- `update_mode` queda como columna canónica (E-HM-10); `stream_status`
  existente se conserva como alias legacy.
- `fetched_at` guarda el instante real del fetch (E-HM-10: antes no se
  registraba; timestamp_utc era after-proceso).
- `raw_vector` se conserva (B.4) pero deja de ser la fuente principal de
  lectura: las columnas nuevas cumplen «tamaño por fila < 1 kB» al
  consultar solo lo filtrable.

`ALTER TABLE` sobre el padre particionado propaga automáticamente las
columnas nuevas a las particiones adjuntas (PostgreSQL 12+). El
`downgrade` las retira de todas.

Uso: `cd proy_bd_heatmap && ./venv/bin/alembic upgrade head`.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


_DDL = r"""
-- ==== F4.4 · fact_heatmap_snapshot: columnas explícitas (M-DAT-05) ====

ALTER TABLE public.fact_heatmap_snapshot
    ADD COLUMN volume numeric(30,8),
    ADD COLUMN avg_vol_10d numeric(30,8),
    ADD COLUMN avg_vol_30d numeric(30,8),
    ADD COLUMN volatility_d numeric(12,6),
    ADD COLUMN change_abs numeric(12,6),
    ADD COLUMN high_52w numeric(18,6),
    ADD COLUMN low_52w numeric(18,6),
    ADD COLUMN update_mode character varying(30),
    ADD COLUMN fetched_at timestamp with time zone;

COMMENT ON COLUMN public.fact_heatmap_snapshot.volume IS 'volume del vector d (M-DAT-05).';
COMMENT ON COLUMN public.fact_heatmap_snapshot.avg_vol_10d IS 'average_volume_10d_calc del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.avg_vol_30d IS 'average_volume_30d_calc del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.volatility_d IS 'Volatility.D del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.change_abs IS 'change_abs (cambio absoluto del día) del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.high_52w IS 'price_52_week_high del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.low_52w IS 'price_52_week_low del vector d.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.update_mode IS 'update_mode del vector d (columna canónica, E-HM-10); stream_status queda como alias legacy.';
COMMENT ON COLUMN public.fact_heatmap_snapshot.fetched_at IS 'Instante real del fetch del scan (antes no se registraba, E-HM-10).';
"""

_DOWN = r"""
-- ============ downgrade: revierte F4.4 ============
ALTER TABLE public.fact_heatmap_snapshot
    DROP COLUMN volume,
    DROP COLUMN avg_vol_10d,
    DROP COLUMN avg_vol_30d,
    DROP COLUMN volatility_d,
    DROP COLUMN change_abs,
    DROP COLUMN high_52w,
    DROP COLUMN low_52w,
    DROP COLUMN update_mode,
    DROP COLUMN fetched_at;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)