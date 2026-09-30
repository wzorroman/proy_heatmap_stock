# file: proy_bd_heatmap/tests/test_migraciones.py
"""Pruebas de las migraciones de alembic del proyecto proy_bd_heatmap.

Cubren:
- La cadena de revisiones (0001 baseline → 0002 seed → 0003 F4.2 →
  0004 F4.3 → 0005 F4.4 → 0006 F4.5/F4.5b → 0007 seed dim_country) es lineal
  y completa.
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
  `TVC:DXY` (dim_asset 1668 → 1669) y `feed_delay_s` por clase; 0008 completa el
  universo a 1.679 símbolos con los ids 4702-4711.
- Seed `dim_country`: los 11 países del calendario económico quedan poblados y
  `fact_economic_event.country` puede insertar sin violar FK.
- 0008: `dim_asset` cierra en 1.679 con los ids 4702-4711, secuencia en 4711 y
  `feed_delay_s` sin NULL, de modo que `upsert_market_series` acepta cualquier
  símbolo del universo.

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
    assert "0007 -> 0006" in r.stdout or "0006 -> 0007" in r.stdout
    assert "0008 -> 0007" in r.stdout or "0007 -> 0008" in r.stdout
    assert "0009 -> 0008" in r.stdout or "0008 -> 0009" in r.stdout
    # head == 0009 (0001 baseline → 0002 seed → 0003 F4.2 → 0004 F4.3 → 0005 F4.4 →
    #              0006 F4.5/F4.5b → 0007 seed dim_country → 0008 alta dim_asset → 0009 score dashboard)
    r = _run([ALEMBIC, "current"])
    assert "0009 (head)" in r.stdout


def test_esquema_baseline(bd_scratch):
    """Las tablas base y particiones existen tras upgrade head."""
    tablas = _psql(
        "SELECT string_agg(table_name, ',') FROM information_schema.tables "
        "WHERE table_schema='public';\n"
    )
    for t in ("dim_asset", "dim_time", "dim_trading_session", "dim_country",
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
    assert _count("dim_asset") == 1679
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
    assert int(n900.strip()) == 1087 + 25 + 537  # equity + etf + common (527 de 0002 + 10 de 0008)
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
    """dim_asset/dim_time/dim_trading_session/dim_country quedan poblados."""
    assert _count("dim_asset") == 1679
    assert _count("dim_time") == 730
    assert _count("dim_trading_session") == 630
    assert _count("dim_country") == 11


def test_seed_dim_country(bd_scratch):
    """0007: los 11 países del calendario económico con sus datos completos."""
    out = _psql(
        "SELECT string_agg(country_code, ',' ORDER BY country_code) "
        "FROM dim_country;\n"
    )
    assert out.strip() == "AU,CA,CH,CN,DE,ES,FR,GB,IT,JP,US"
    # country_name, region y currency_code no pueden quedar nulos
    nulos = _psql(
        "SELECT count(*) FROM dim_country "
        "WHERE country_name IS NULL OR region IS NULL OR currency_code IS NULL;\n"
    )
    assert nulos.strip() == "0"


def test_seed_dim_country_idempotente(bd_scratch):
    """downgrade+upgrade de 0007 no duplica ni desalinea el catálogo."""
    _run([ALEMBIC, "downgrade", "0006"])
    assert _count("dim_country") == 0
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_country") == 11
    # re-ejecución sobre la BD ya sembrada no cambia nada
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_country") == 11


def test_dim_asset_alta_universo(bd_scratch):
    """0008: los 10 símbolos discoveries por el scraper con id 4702-4711."""
    out = _psql(
        "SELECT string_agg(symbol, ',' ORDER BY asset_id) FROM dim_asset "
        "WHERE asset_id BETWEEN 4702 AND 4711;\n"
    )
    assert out.strip() == (
        "NASDAQ:FRHC,NYSE:FR,NYSE:NEU,NYSE:ADC,NYSE:WAL,"
        "NYSE:RHP,NASDAQ:AVT,NASDAQ:WYNN,NYSE:KMX,NASDAQ:MXL"
    )
    # id explícito y contiguo: los hechos son comparables entre BDs
    n = _psql("SELECT count(*) FROM dim_asset WHERE asset_id=4702;\n")
    assert n.strip() == "1"
    # atributos de catálogo rellenos
    vacios = _psql(
        "SELECT count(*) FROM dim_asset WHERE asset_id BETWEEN 4702 AND 4711 "
        "AND (ticker IS NULL OR exchange IS NULL OR sector IS NULL "
        "     OR company_name IS NULL OR logo_id IS NULL "
        "     OR source_discovered_by IS NULL OR NOT is_active);\n"
    )
    assert vacios.strip() == "0"


def test_dim_asset_alta_universo_ingestable(bd_scratch):
    """0008: upsert_market_series acepta un símbolo del alta (antes fallaba)."""
    _psql(
        "SELECT upsert_market_series('NYSE:WAL', "
        "    TIMESTAMPTZ '2026-09-29 15:00:00+00', "
        "    77.7, 10, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL, 'ck0008');\n"
    )
    out = _psql("SELECT count(*) FROM fact_market_series WHERE close=77.7;\n")
    assert out.strip() == "1"
    _psql("DELETE FROM fact_market_series WHERE source_checksum='ck0008';\n")


def test_dim_asset_alta_universo_idempotente(bd_scratch):
    """downgrade+upgrade de 0008 no duplica y resincroniza la secuencia."""
    _run([ALEMBIC, "downgrade", "0007"])
    assert _count("dim_asset") == 1669
    n = _psql(
        "SELECT count(*) FROM dim_asset WHERE asset_id BETWEEN 4702 AND 4711;\n"
    )
    assert n.strip() == "0"
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_asset") == 1679
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_asset") == 1679
    seq = _psql("SELECT last_value FROM dim_asset_asset_id_seq;\n")
    assert seq.strip() == "4711"


def test_universo_completo_sin_huecos(bd_scratch):
    """La BD limpia cubre los símbolos de la BD en uso.

    `TVC:DXY` (el único alta de 0006) queda excluido del conteo: 0006 lo
    inserta con `now()`, así que su `created_at`/`updated_at` no es
    reproducible entre entornos. Es la única diferencia esperada frente a la
    BD en uso.
    """
    out = _psql(
        "SELECT count(*) FROM dim_asset "
        "WHERE symbol IN ('NASDAQ:FRHC','NYSE:FR','NYSE:NEU','NYSE:ADC',"
        "  'NYSE:WAL','NYSE:RHP','NASDAQ:AVT','NASDAQ:WYNN','NYSE:KMX',"
        "  'NASDAQ:MXL');\n"
    )
    assert out.strip() == "10"
    # ninguna fila de catálogo queda con feed_delay_s sin definir
    nn = _psql("SELECT count(*) FROM dim_asset WHERE feed_delay_s IS NULL;\n")
    assert nn.strip() == "0"


def test_fk_fact_economic_event_pais(bd_scratch):
    """Con dim_country poblada, un evento económico inserta sin violar FK."""
    _psql(
        "INSERT INTO fact_economic_event "
        "    (event_id, title, country, event_timestamp) "
        "VALUES (999000001, 'F3 seed FK', 'US', "
        "        TIMESTAMPTZ '2026-09-29 14:30:00+00');\n"
    )
    out = _psql("SELECT count(*) FROM fact_economic_event WHERE country='US';\n")
    assert int(out.strip()) == 1
    _psql("DELETE FROM fact_economic_event WHERE event_id=999000001;\n")
    # el catálogo sigue íntegro tras la prueba
    assert _count("dim_country") == 11


def test_seed_idempotente(bd_scratch):
    """Downgrade+upgrade de 0002 no duplica filas (ON CONFLICT DO NOTHING)."""
    _run([ALEMBIC, "downgrade", "0001"])
    _run([ALEMBIC, "upgrade", "head"])
    assert _count("dim_asset") == 1679
    assert _count("dim_time") == 730
    assert _count("dim_trading_session") == 630
    assert _count("dim_country") == 11


def test_seq_dim_asset_sincronizada(bd_scratch):
    out = _psql(
        "SELECT last_value, (SELECT max(asset_id) FROM dim_asset) "
        "FROM dim_asset_asset_id_seq;\n"
    )
    assert out.strip() == "4711|4711"


def test_fact_market_score_schema(bd_scratch):
    """0009: fact_market_score particionada por RANGE(timestamp_utc) con BRIN."""
    out = _psql("SELECT pg_get_partkeydef('public.fact_market_score'::regclass);\n")
    assert out.strip() == "RANGE (timestamp_utc)"
    parts = _psql(
        "SELECT count(*) FROM pg_inherits i "
        "JOIN pg_class c ON i.inhrelid = c.oid "
        "JOIN pg_class p ON i.inhparent = p.oid "
        "WHERE p.relname = 'fact_market_score';\n"
    )
    assert int(parts.strip()) >= 10
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='fact_market_score';\n"
    )
    for c in ("asset_id", "timestamp_utc", "score_general", "zona",
              "componentes", "ingested_at"):
        assert c in cols, f"falta columna {c}"
    pk = _psql(
        "SELECT string_agg(a.attname, ',') FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = 'public.fact_market_score'::regclass AND i.indisprimary;\n"
    )
    assert pk.strip() == "asset_id,timestamp_utc"
    brin = _psql(
        "SELECT count(*) FROM pg_indexes WHERE tablename='fact_market_score_2026_09' "
        "AND indexdef ILIKE '%USING brin (timestamp_utc)%';\n"
    )
    assert int(brin.strip()) == 1


def test_fact_market_score_agg_schema(bd_scratch):
    """0009: fact_market_score_agg no particionada, PK timestamp_utc y BRIN."""
    rango = _psql("SELECT pg_get_partkeydef('public.fact_market_score_agg'::regclass);\n")
    assert rango.strip() == ""
    cols = _psql(
        "SELECT string_agg(column_name, ',') FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='fact_market_score_agg';\n"
    )
    for c in ("timestamp_utc", "score_momentum", "score_15min", "score_radar",
              "score_market", "zona", "n_simbolos", "source_checksum",
              "audit_id", "ingested_at"):
        assert c in cols, f"falta columna {c}"
    pk = _psql(
        "SELECT string_agg(a.attname, ',') FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = 'public.fact_market_score_agg'::regclass AND i.indisprimary;\n"
    )
    assert pk.strip() == "timestamp_utc"
    brin = _psql(
        "SELECT count(*) FROM pg_indexes WHERE tablename='fact_market_score_agg' "
        "AND indexdef ILIKE '%USING brin (timestamp_utc)%';\n"
    )
    assert int(brin.strip()) == 1


def test_vistas_score(bd_scratch):
    """0009: las vistas de presentación del score existen."""
    views = _psql(
        "SELECT coalesce(string_agg(table_name, ','), '') FROM information_schema.views "
        "WHERE table_schema='public';\n"
    )
    assert "vw_market_score_history" in views
    assert "vw_market_score_latest" in views


def test_score_upsert_y_reversion(bd_scratch):
    """UPSERT idempotente en detalle/agg, lectura por vista y reversión de 0009."""
    _psql(
        "INSERT INTO fact_market_score "
        "    (asset_id, timestamp_utc, score_general, zona, componentes) "
        "VALUES (1011, TIMESTAMPTZ '2026-09-30 14:00:00+00', 7.25, 'COMPRAR', "
        "        jsonb_build_object('rsi', 70)) "
        "ON CONFLICT (asset_id, timestamp_utc) DO UPDATE "
        "    SET score_general = EXCLUDED.score_general;\n"
    )
    _psql(
        "INSERT INTO fact_market_score "
        "    (asset_id, timestamp_utc, score_general, zona, componentes) "
        "VALUES (1011, TIMESTAMPTZ '2026-09-30 14:00:00+00', 7.50, 'COMPRAR', "
        "        jsonb_build_object('rsi', 72)) "
        "ON CONFLICT (asset_id, timestamp_utc) DO UPDATE "
        "    SET score_general = EXCLUDED.score_general;\n"
    )
    n = _psql("SELECT count(*) FROM fact_market_score WHERE asset_id=1011;\n")
    assert n.strip() == "1"
    val = _psql("SELECT score_general FROM fact_market_score WHERE asset_id=1011;\n")
    assert val.strip() == "7.5000"

    _psql(
        "INSERT INTO fact_market_score_agg "
        "    (timestamp_utc, score_momentum, score_radar, n_simbolos) "
        "VALUES (TIMESTAMPTZ '2026-09-30 14:00:00+00', 6.10, 5.20, 123) "
        "ON CONFLICT (timestamp_utc) DO UPDATE "
        "    SET score_momentum = EXCLUDED.score_momentum;\n"
    )
    latest = _psql("SELECT score_momentum FROM vw_market_score_latest;\n")
    assert latest.strip() == "6.1000"

    # downgrade 0009 revierte tablas y vistas
    _run([ALEMBIC, "downgrade", "0008"])
    tablas = _psql(
        "SELECT coalesce(string_agg(table_name, ','), '') FROM information_schema.tables "
        "WHERE table_schema='public';\n"
    )
    assert "fact_market_score" not in tablas
    assert "fact_market_score_agg" not in tablas
    vistas = _psql(
        "SELECT coalesce(string_agg(table_name, ','), '') FROM information_schema.views "
        "WHERE table_schema='public';\n"
    )
    assert "vw_market_score_latest" not in vistas
    # re-upgrade deja la BD lista para el resto de la suite
    _run([ALEMBIC, "upgrade", "head"])


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