# file: proy_bd_heatmap/tests/test_migraciones.py
"""Pruebas de las migraciones de alembic del proyecto proy_bd_heatmap.

Cubren:
- La cadena de revisiones (0001 baseline → 0002 seed → 0003 F4.2 →
  0004 F4.3 → 0005 F4.4 → 0006 F4.5/F4.5b) es lineal y completa.
- El `upgrade head` sobre una BD scratch vacía crea el esquema y los catálogos.
- Idempotencia del seed: re-ejecutar 0002 no duplica filas.
- La migración baseline embebida tiene upgrade/downgrade ejecutables.
- F4.2 `fact_market_indicator_tf`: particionada por `RANGE(timestamp_utc)`,
  columnas, PK y cantidad de particiones.
- F4.3 `latest_market_tick`: una fila por activo (PK asset_id) con trazabilidad
  temporal.
- F4.4 `fact_heatmap_snapshot`: columnas explícitas (M-DAT-05) presentes en el
  padre y propagadas a las particiones.
- F4.5 `dim_asset` Tipo 1: columnas SCD2 removidas, funciones/vistas sin
  `current_version`, índices reconstruidos y `idx_dim_asset_symbol` eliminado.
- F4.5b mapeo canónico: 6 claves lógicas con 1 canónico cada una, alta de
  `TVC:DXY` (dim_asset 1668 → 1669) y `feed_delay_s` por clase.

Requiere una BD de prueba `heatmap_stock_test` (se crea/limpia por el test).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
VENV_BIN = PROJECT / "venv" / "bin"
ALEMBIC = VENV_BIN / "alembic"
PYTHON = VENV_BIN / "python3"
DB_TEST = "heatmap_stock_test"


def _run(cmd, env_extra=None, check=True):
    env = dict(os.environ)
    env["BD_HEATMAP_DATABASE"] = DB_TEST
    env.update(env_extra or {})
    r = subprocess.run(
        [str(c) for c in cmd], cwd=PROJECT, env=env,
        capture_output=True, text=True,
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd falló: {cmd}\n{r.stdout}\n{r.stderr}")
    return r


def _psql(script, db=DB_TEST):
    """Ejecuta SQL contra una BD vía psql dentro del contenedor pg_db."""
    r = subprocess.run(
        ["docker", "exec", "-i", "pg_db", "psql", "-U", "postgres",
         "-d", db, "-v", "ON_ERROR_STOP=1", "-t", "-A"],
        input=script, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"psql falló: {r.stdout}\n{r.stderr}")
    return r.stdout


def _recrear_bd_test():
    # DROP/CREATE se ejecutan contra la BD "postgres" (no se puede dropear la propia)
    _psql(f"DROP DATABASE IF EXISTS {DB_TEST};\n", db="postgres")
    _psql(f"CREATE DATABASE {DB_TEST};\n", db="postgres")


def _count(tabla):
    out = _psql(f"SELECT count(*) FROM {tabla};\n")
    return int(out.strip())


@pytest.fixture(scope="module")
def bd_scratch():
    _recrear_bd_test()
    _run([ALEMBIC, "upgrade", "head"])
    yield DB_TEST


def test_historial_lineal(bd_scratch):
    r = _run([ALEMBIC, "history"])
    assert "0002 -> 0001" in r.stdout or "0001 -> 0002" in r.stdout
    assert "0003 -> 0002" in r.stdout or "0002 -> 0003" in r.stdout
    assert "0004 -> 0003" in r.stdout or "0003 -> 0004" in r.stdout
    assert "0005 -> 0004" in r.stdout or "0004 -> 0005" in r.stdout
    assert "0006 -> 0005" in r.stdout or "0005 -> 0006" in r.stdout
    # head == 0006 (0001 baseline → 0002 seed → 0003 F4.2 → 0004 F4.3 → 0005 F4.4 → 0006 F4.5/F4.5b)
    r = _run([ALEMBIC, "current"])
    assert "0006 (head)" in r.stdout


def test_esquema_baseline(bd_scratch):
    """Las tablas base y particiones existen tras upgrade head."""
    tablas = _psql(
        "SELECT string_agg(table_name, ',') FROM information_schema.tables "
        "WHERE table_schema='public';\n"
    )
    for t in ("dim_asset", "dim_time", "dim_trading_session",
              "fact_market_series", "fact_heatmap_snapshot",
              "fact_market_bar_15m", "fact_market_indicator_tf",
              "latest_market_tick", "fact_economic_event",
              "audit_sync_run", "sync_checkpoint", "alembic_version"):
        assert t in tablas, f"falta tabla {t}"


def test_fact_market_indicator_tf(bd_scratch):
    """F4.2: fact_market_indicator_tf particionada por RANGE(timestamp_utc)."""
    out = _psql(
        "SELECT pg_get_partkeydef('public.fact_market_indicator_tf'::regclass);\n"
    )
    assert out.strip() == "RANGE (timestamp_utc)"
    parts = _psql(
        "SELECT count(*) FROM pg_inherits i "
        "JOIN pg_class c ON i.inhrelid = c.oid "
        "JOIN pg_class p ON i.inhparent = p.oid "
        "WHERE p.relname = 'fact_market_indicator_tf';\n"
    )
    assert int(parts.strip()) >= 10
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='fact_market_indicator_tf';\n"
    )
    for c in ("asset_id", "timestamp_utc", "tf", "rsi", "cci20", "bbpower",
              "adx", "change_pct", "volume", "pivot_r3"):
        assert c in cols, f"falta columna {c}"
    pk = _psql(
        "SELECT string_agg(a.attname, ',') FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = 'public.fact_market_indicator_tf'::regclass "
        "AND i.indisprimary;\n"
    )
    assert pk.strip() == "asset_id,timestamp_utc,tf"


def test_latest_market_tick(bd_scratch):
    """F4.3: latest_market_tick una fila por activo (PK asset_id)."""
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='latest_market_tick';\n"
    )
    for c in ("asset_id", "timestamp_utc", "close", "change_pct", "volume",
              "rsi", "rsi_15", "cci20_15", "bbpower_15", "adx_15",
              "pivot_r3_15", "update_mode", "feed_delay_s", "cycle_id",
              "fetched_at", "ingested_at"):
        assert c in cols, f"falta columna {c}"
    pk = _psql(
        "SELECT string_agg(a.attname, ',') FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = 'public.latest_market_tick'::regclass "
        "AND i.indisprimary;\n"
    )
    assert pk.strip() == "asset_id"
    # No particionada: una fila por activo (tamaño fijo, no histórico).
    rango = _psql(
        "SELECT pg_get_partkeydef('public.latest_market_tick'::regclass);\n"
    )
    assert rango.strip() == ""


def test_fact_heatmap_snapshot_columnas(bd_scratch):
    """F4.4: columnas explícitas en fact_heatmap_snapshot y sus particiones."""
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='fact_heatmap_snapshot';\n"
    )
    for c in ("volume", "avg_vol_10d", "avg_vol_30d", "volatility_d",
              "change_abs", "high_52w", "low_52w", "update_mode", "fetched_at"):
        assert c in cols, f"falta columna {c}"
    # ALTER sobre el padre particionado propaga las columnas a las particiones.
    part = _psql(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='fact_heatmap_snapshot_2026_09' "
        "AND column_name='fetched_at';\n"
    )
    assert int(part.strip()) == 1


def test_dim_asset_tipo1(bd_scratch):
    """F4.5 (D7): columnas SCD2 removidas; columnas de resolución presentes."""
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='dim_asset';\n"
    )
    for c in ("logical_key", "is_canonical", "role", "feed_delay_s"):
        assert c in cols, f"falta columna {c}"
    for c in ("valid_from", "valid_to", "current_version"):
        assert c not in cols, f"columna SCD2 {c} aún presente"
    # índice duplicado eliminado; invariantes e índices reconstruidos presentes
    idxs = _psql(
        "SELECT string_agg(indexname, ',') FROM pg_indexes "
        "WHERE tablename='dim_asset';\n"
    )
    assert "idx_dim_asset_symbol" not in idxs, "idx_dim_asset_symbol no eliminado"
    assert "uq_dim_asset_canonical_logical_key" in idxs
    assert "idx_dim_asset_active" in idxs
    assert "idx_dim_asset_class" in idxs
    chk = _psql("SELECT count(*) FROM pg_constraint WHERE conname='chk_dim_asset_role';\n")
    assert int(chk.strip()) == 1
    # funciones y vistas siguen existiendo (regeneradas sin current_version)
    funcs = _psql(
        "SELECT string_agg(proname, ',') FROM pg_proc "
        "WHERE pronamespace = 'public'::regnamespace AND prokind='f';\n"
    )
    assert "upsert_market_series" in funcs
    assert "upsert_heatmap_snapshot" in funcs


def test_mapeo_canonico(bd_scratch):
    """F4.5b: alta de TVC:DXY y 6 claves lógicas con 1 canónico cada una."""
    assert _count("dim_asset") == 1669
    n = _psql("SELECT count(*) FROM dim_asset WHERE symbol='TVC:DXY';\n")
    assert int(n.strip()) == 1
    # invariante del índice único: a lo sumo 1 canónico por logical_key
    dup = _psql(
        "SELECT count(*) FROM ("
        " SELECT logical_key FROM dim_asset "
        " WHERE is_canonical GROUP BY logical_key "
        " HAVING count(*) > 1) d;\n"
    )
    assert int(dup.strip()) == 0
    claves = _psql(
        "SELECT count(DISTINCT logical_key) FROM dim_asset "
        "WHERE logical_key IS NOT NULL;\n"
    )
    assert int(claves.strip()) == 6
    mapa = _psql(
        "SELECT symbol||'='||COALESCE(logical_key,'')||':'||COALESCE(role,'') "
        "FROM dim_asset "
        "WHERE logical_key IS NOT NULL ORDER BY logical_key, role;\n"
    )
    for esperado in (
        "TVC:VIX=VIX:primary", "CBOE:VX1!=VIX:fallback",
        "TVC:DXY=DXY:primary", "ICEUS:DX1!=DXY:fallback", "AMEX:UUP=DXY:fallback",
        "OANDA:XAUUSD=ORO:primary", "SAXO:XAUUSD=ORO:fallback",
        "AMEX:USO=OIL:primary", "NYMEX:CL1!=OIL:fallback",
        "NASDAQ:TLT=TLT:primary", "CBOT:ZB1!=TLT:fallback",
        "TVC:US10Y=US10Y:primary",
    ):
        assert esperado in mapa, f"falta {esperado}"


def test_feed_delay_backfill(bd_scratch):
    """F4.5b: feed_delay_s por clase (equity/etf/share_class→900, future→600, resto→0)."""
    n900 = _psql(
        "SELECT count(*) FROM dim_asset WHERE feed_delay_s=900 AND "
        "COALESCE(asset_class,'') IN ('equity','etf','common','preferred','unit');\n"
    )
    n600 = _psql(
        "SELECT count(*) FROM dim_asset WHERE feed_delay_s=600 AND asset_class='future';\n"
    )
    n0 = _psql(
        "SELECT count(*) FROM dim_asset WHERE feed_delay_s=0 AND "
        "(asset_class IS NULL OR asset_class NOT IN "
        "('equity','etf','common','preferred','unit','future'));\n"
    )
    assert int(n900.strip()) == 1087 + 25 + 527  # equity + etf + common
    assert int(n600.strip()) == 9                # futures
    assert int(n0.strip()) == 2 + 2 + 13 + 2 + 2  # commodity+crypto+forex+index(con TVC:DXY)+yield
    nn = _psql("SELECT count(*) FROM dim_asset WHERE feed_delay_s IS NULL;\n")
    assert int(nn.strip()) == 0


def test_particiones_market_series(bd_scratch):
    """fact_market_series tiene sus particiones mensuales."""
    out = _psql(
        "SELECT count(*) FROM pg_inherits i "
        "JOIN pg_class c ON i.inhrelid = c.oid "
        "JOIN pg_class p ON i.inhparent = p.oid "
        "WHERE p.relname = 'fact_market_series';\n"
    )
    assert int(out.strip()) >= 10


def test_extension_y_funciones(bd_scratch):
    ext = _psql("SELECT extname FROM pg_extension;\n")
    assert "pg_trgm" in ext
    funcs = _psql(
        "SELECT string_agg(proname, ',') FROM pg_proc "
        "WHERE pronamespace = 'public'::regnamespace AND prokind='f';\n"
    )
    assert "upsert_market_series" in funcs
    assert "upsert_heatmap_snapshot" in funcs


def test_seed_catalogos(bd_scratch):
    """dim_asset/dim_time/dim_trading_session quedan poblados."""
    assert _count("dim_asset") == 1669
    assert _count("dim_time") == 730
    assert _count("dim_trading_session") == 630


def test_seed_idempotente(bd_scratch):
    """Downgrade+upgrade de 0002 no duplica filas (ON CONFLICT DO NOTHING)."""
    _run([ALEMBIC, "downgrade", "0001"])
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_asset") == 1669
    assert _count("dim_time") == 730
    assert _count("dim_trading_session") == 630


def test_seq_dim_asset_sincronizada(bd_scratch):
    out = _psql(
        "SELECT last_value, (SELECT max(asset_id) FROM dim_asset) "
        "FROM dim_asset_asset_id_seq;\n"
    )
    assert out.strip() == "4701|4701"


def test_downgrade_base(bd_scratch):
    """downgrade base revierte todo; solo queda alembic_version."""
    _run([ALEMBIC, "downgrade", "base"])
    tablas = _psql(
        "SELECT string_agg(tablename, ',') FROM pg_tables "
        "WHERE schemaname='public';\n"
    )
    assert tablas.strip() == "alembic_version"
    # restaurar para no romper fixtures posteriores
    _run([ALEMBIC, "upgrade", "head"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))