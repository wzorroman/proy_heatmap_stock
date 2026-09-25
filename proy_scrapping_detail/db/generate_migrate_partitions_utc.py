# file: proy_scrapping_detail/db/generate_migrate_partitions_utc.py
"""F2.3 · Genera el SQL (NO lo ejecuta) que migra las particiones de
fact_market_series y fact_heatmap_snapshot a fronteras UTC (00:00+00).

Estado actual de la BD: límites a medianoche Lima (-05 = 05:00 UTC) en las
particiones existentes. Objetivo: límites contiguos a 00:00 UTC, creando
hasta 2027_12.

Hay que conocer qué particiones YA EXISTEN (se migran DETACH+RENAME →
CREATE nuevo → INSERT desde _legacy → DROP). Las demás se crean nuevas.

Uso:
    python3 -m db.generate_migrate_partitions_utc > migrate_partitions_utc.sql
"""
from datetime import date

TABLAS = {
    "fact_market_series": ("2026_03", "2027_12"),
    "fact_heatmap_snapshot": ("2026_09", "2027_12"),
}

# Particiones que YA EXISTEN en la BD (2026-09-22, límites -05)
EXISTENTES = {
    "fact_market_series": [f"2026_{m:02d}" for m in range(3, 13)],
    "fact_heatmap_snapshot": [f"2026_{m:02d}" for m in range(9, 13)],
}

# Índices por partición (replican los de la partición modelo actual)
IDX = {
    "fact_market_series": [
        "CREATE UNIQUE INDEX {p}_pkey ON {p} USING btree (asset_id, timestamp_utc);",
        "CREATE INDEX {p}_timestamp_utc_idx ON {p} USING btree (timestamp_utc DESC);",
        "CREATE INDEX {p}_close_idx ON {p} USING btree (close) WHERE (close IS NOT NULL);",
        "CREATE INDEX {p}_rsi_idx ON {p} USING btree (rsi) WHERE (rsi IS NOT NULL);",
        "CREATE INDEX {p}_timezone_idx ON {p} USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));",
        "CREATE INDEX {p}_ts_brin ON {p} USING brin (timestamp_utc);",
    ],
    "fact_heatmap_snapshot": [
        "CREATE UNIQUE INDEX {p}_pkey ON {p} USING btree (asset_id, timestamp_utc);",
        "CREATE INDEX {p}_timestamp_utc_idx ON {p} USING btree (timestamp_utc DESC);",
        "CREATE INDEX {p}_daily_change_pct_idx ON {p} USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);",
        "CREATE INDEX {p}_market_cap_idx ON {p} USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);",
        "CREATE INDEX {p}_raw_vector_idx ON {p} USING gin (raw_vector);",
    ],
}


def meses(desde: str, hasta: str):
    a1, m1 = (int(x) for x in desde.split("_"))
    a2, m2 = (int(x) for x in hasta.split("_"))
    y, m = a1, m1
    while (y, m) <= (a2, m2):
        yield f"{y:04d}_{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def sig_mes(ym: str) -> str:
    y, m = (int(x) for x in ym.split("_"))
    m += 1
    if m > 12:
        m = 1
        y += 1
    return f"{y:04d}_{m:02d}"


def generador():
    yield "-- ============================================================================"
    yield "-- F2.3 · Migración de particiones a fronteras UTC (00:00+00)"
    yield "-- Generado el 2026-09-22 por generate_migrate_partitions_utc.py"
    yield "-- Backup previo: /tmp/opencode/backup_f2/heatmap_stock_pre_F2.3_20260922_224433.dump"
    yield "-- Ejecutar con: docker exec -i pg_db psql -U postgres heatmap_stock < migrate_partitions_utc.sql"
    yield "-- ============================================================================"
    yield "BEGIN;"
    yield "SET search_path = public;"
    yield ""

    for tabla, (desde, hasta) in TABLAS.items():
        yield f"-- ###########################################################################"
        yield f"-- {tabla}"
        yield f"-- ###########################################################################"
        exist = set(EXISTENTES[tabla])
        for ym in meses(desde, hasta):
            p = f"{tabla}_{ym}"
            sm = sig_mes(ym)
            bounds = (f"FOR VALUES FROM ('{ym.replace('_', '-')}-01 00:00:00+00') "
                      f"TO ('{sm.replace('_', '-')}-01 00:00:00+00')")
            if ym in exist:
                # 1) Liberar el nombre con el bloque legacy (conserva datos)
                yield f"-- partición existente {p} (límites -05): DETACH + rename + recreate"
                yield f"ALTER TABLE {tabla} DETACH PARTITION {p};"
                yield f"ALTER TABLE {p} RENAME TO {p}_legacy;"
                yield f"CREATE TABLE {p} PARTITION OF {tabla}"
                yield f"    {bounds};"
                for idx in IDX[tabla]:
                    yield idx.format(p=p)
                yield f"-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)"
                yield f"INSERT INTO {tabla} SELECT * FROM {p}_legacy;"
                yield f"DROP TABLE {p}_legacy;"
                yield ""
            else:
                yield f"CREATE TABLE {p} PARTITION OF {tabla}"
                yield f"    {bounds};"
                for idx in IDX[tabla]:
                    yield idx.format(p=p)
                yield ""
        yield ""

    yield "-- ============================================================================"
    yield "-- Verificación final (A5): límites contiguos a 00:00+00"
    yield "-- ============================================================================"
    yield """
SELECT pa.relname AS tabla, ch.relname AS particion,
       pg_get_expr(ch.relpartbound, ch.oid) AS bounds
FROM pg_class ch
JOIN pg_namespace n ON n.oid = ch.relnamespace
JOIN pg_inherits i ON i.inhrelid = ch.oid
JOIN pg_class pa ON i.inhparent = pa.oid
WHERE n.nspname='public'
  AND pa.relname IN ('fact_market_series','fact_heatmap_snapshot')
ORDER BY pa.relname, ch.relname;

-- Alerta: partición del mes siguiente ausente (debe existir AL MENOS el mes+1)
SELECT 'ALERTA: falta partición ' || to_char((CURRENT_DATE + INTERVAL '1 month'), 'YYYY_MM')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname='public'
      AND c.relname = 'fact_market_series_' || to_char((CURRENT_DATE + INTERVAL '1 month'), 'YYYY_MM')
);
"""

    yield ""
    yield "COMMIT;"


if __name__ == "__main__":
    print("\n".join(generador()))