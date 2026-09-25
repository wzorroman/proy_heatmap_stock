#!/usr/bin/env python3
# file: proy_bd_heatmap/scripts/generar_baseline.py
"""F1 · Genera la migración baseline de alembic desde el pg_dump de la BD viva.

Uso:
    docker exec pg_db pg_dump --schema-only --no-owner --no-privileges \
        -U postgres heatmap_stock > schema_vivo.sql
    python scripts/generar_baseline.py schema_vivo.sql \
        alembic/versions/0001_baseline_2026_09_23.py
"""
import re
import sys
from datetime import datetime, timezone


def limpiar_dump(path: str) -> str:
    """Devuelve el SQL ejecutable, sin meta-comandos psql ni cabecera."""
    lineas = []
    for linea in open(path, encoding="utf-8"):
        s = linea.strip()
        if s.startswith("\\restrict") or s.startswith("\\unrestrict"):
            continue
        if s.startswith("-- PostgreSQL database dump") or s.startswith("-- Dumped"):
            continue
        lineas.append(linea)
    texto = "".join(lineas)
    # search_path vacío rompe objetos no calificados: fijarlo a public.
    texto = texto.replace(
        "SELECT pg_catalog.set_config('search_path', '', false);",
        "SET search_path = public;",
    )
    return texto


def generador(dump_path: str) -> str:
    ddl = limpiar_dump(dump_path)
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''"""baseline - esquema heatmap_stock (estado 2026-09-23)

Revision ID: 0001
Revises:
Create Date: {ahora}

Baseline generado desde pg_dump --schema-only de la BD viva
(10 tablas base + 27 particiones + 3 vistas + 2 funciones + pg_trgm).
Contiene SOLO esquema (sin datos). El seed de catálogos va en revisiones
posteriores.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_DDL = r"""
{ddl}
"""

_DOWN = r"""
-- ============ downgrade: revertir en orden inverso ============
DROP VIEW IF EXISTS public.vw_market_live CASCADE;
DROP VIEW IF EXISTS public.vw_heatmap_event_impact CASCADE;
DROP VIEW IF EXISTS public.vw_heatmap_enriched CASCADE;
DROP FUNCTION IF EXISTS public.text_to_tsvector_english(text) CASCADE;
DROP FUNCTION IF EXISTS public.upsert_heatmap_snapshot CASCADE;
DROP FUNCTION IF EXISTS public.upsert_market_series CASCADE;
DROP TABLE IF EXISTS public.fact_market_series CASCADE;
DROP TABLE IF EXISTS public.fact_heatmap_snapshot CASCADE;
DROP TABLE IF EXISTS public.fact_market_bar_15m CASCADE;
DROP TABLE IF EXISTS public.fact_economic_event CASCADE;
DROP TABLE IF EXISTS public.dim_asset CASCADE;
DROP TABLE IF EXISTS public.dim_trading_session CASCADE;
DROP TABLE IF EXISTS public.dim_time CASCADE;
DROP TABLE IF EXISTS public.dim_country CASCADE;
DROP TABLE IF EXISTS public.audit_sync_run CASCADE;
DROP TABLE IF EXISTS public.sync_checkpoint CASCADE;
DROP SEQUENCE IF EXISTS public.dim_asset_asset_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.audit_sync_run_run_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.sync_checkpoint_checkpoint_id_seq CASCADE;
DROP EXTENSION IF EXISTS pg_trgm;
"""


def upgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DDL)


def downgrade():
    conn = op.get_bind().connection
    with conn.cursor() as cur:
        cur.execute(_DOWN)
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