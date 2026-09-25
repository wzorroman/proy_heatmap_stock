#!/usr/bin/env python3
# file: proy_bd_heatmap/scripts/generar_seed_catalogos.py
"""F3 · Genera la migración seed de catálogos (dim_asset, dim_time,
dim_trading_session) desde un pg_dump --data-only de la BD viva.

Convierte INSERT en INSERT ... ON CONFLICT DO NOTHING (idempotente) y
sincroniza dim_asset_asset_id_seq con el máximo asset_id.

Uso:
    docker exec pg_db pg_dump --data-only --column-inserts --no-owner \
        -U postgres heatmap_stock -t dim_asset -t dim_time \
        -t dim_trading_session > seed_catalogos.sql
    python scripts/generar_seed_catalogos.py seed_catalogos.sql \
        alembic/versions/0002_seed_catalogos_2026_09_23.py
"""
import re
import sys
from datetime import datetime, timezone

TABLAS = ("public.dim_asset", "public.dim_time", "public.dim_trading_session")


def limpiar(path: str) -> list:
    lineas = []
    for linea in open(path, encoding="utf-8"):
        s = linea.strip()
        if s.startswith("\\restrict") or s.startswith("\\unrestrict"):
            continue
        if s.startswith("--") or s.startswith("SET ") or not s:
            continue
        if s.startswith("SELECT pg_catalog.set_config"):
            lineas.append("SET search_path = public;\n")
            continue
        lineas.append(linea)
    return lineas


def generador(path: str) -> str:
    sql = limpiar(path)
    # INSERT idempotente
    out = []
    for linea in sql:
        linea = linea.rstrip("\n")
        if linea.startswith("INSERT INTO public.dim_asset"):
            linea = linea[:-1] + " ON CONFLICT DO NOTHING;"
        elif linea.startswith("INSERT INTO public.dim_time"):
            linea = linea[:-1] + " ON CONFLICT DO NOTHING;"
        elif linea.startswith("INSERT INTO public.dim_trading_session"):
            linea = linea[:-1] + " ON CONFLICT DO NOTHING;"
        out.append(linea)
    cuerpo = "\n".join(out)

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''"""seed catálogos - dim_asset + dim_time + dim_trading_session

Revision ID: 0002
Revises: 0001
Create Date: {ahora}

Carga idempotente de los catálogos del ecosistema (sin hechos):
- dim_asset              1.668 símbolos (asset_id explícito, ON CONFLICT DO NOTHING)
- dim_time               730 días 2026-2027
- dim_trading_session    630 sesiones XNYS
Sincroniza dim_asset_asset_id_seq con el máximo asset_id.

Uso en BD nueva: alembic upgrade head  (0001 esquema → 0002 seed).
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_DATOS = r"""
{cuerpo}
"""

_SEQ = r"""
SELECT setval(
    'public.dim_asset_asset_id_seq',
    (SELECT COALESCE(MAX(asset_id), 1) FROM public.dim_asset)
);
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DATOS)
        cur.execute(_SEQ)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE public.dim_trading_session CASCADE;")
        cur.execute("TRUNCATE TABLE public.dim_time CASCADE;")
        cur.execute("TRUNCATE TABLE public.dim_asset CASCADE;")
'''


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    dump_path, out_path = sys.argv[1], sys.argv[2]
    contenido = generador(dump_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"OK → {out_path} ({len(contenido)} bytes)")


if __name__ == "__main__":
    main()