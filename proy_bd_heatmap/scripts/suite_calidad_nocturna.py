#!/usr/bin/env python3
# file: proy_bd_heatmap/scripts/suite_calidad_nocturna.py
"""F4.8 · Suite nocturna de calidad de datos (M-VAL-01) — script independiente.

================================================================================
¿POR QUÉ EXISTE ESTE SCRIPT? (justificación)
--------------------------------------------------------------------------------
Cierra la mitigación de E-RAD-05 (pérdida silenciosa de datos): el radar V4
tragaba excepciones y vaciaba el buffer con o sin SUCCESS, de modo que una BD
caída o un ciclo fallido pasaban SIN dejar rastro. F1.4 corrigió el contrato
de escritura; esta suite añade la VERIFICACIÓN INDEPENDIENTE (no atada a los
propios jobs) que se ejecuta cada noche y DEJA UN INFORME DIARIO.

Revisa sobre la BD `heatmap_stock` del ecosistema:
  · duplicados en las tablas de hechos (series, barras, indicadores TF, snapshots);
  · huecos de captura en activos 24/5 (forex, cripto, índices, yields, commodities),
    cadencia esperada de 3 min del radar → hueco > 15 min = alerta;
  · frescura global (última marca por clase 24/5);
  · nulos inesperados en columnas críticas (close, price, rsi);
  · ticks planos fuera de sesión (close repetido idéntico con el NYSE cerrado);
  · n_ticks por barra (0 ticks = FAIL; < umbral = WARN);
  · close_quality por barra (distribución definitive/provisional/unknown);
  · contigüidad de particiones mensuales de cada tabla particionada.

MODO DE USO (ejemplos)
--------------------------------------------------------------------------------
  # Inspección rápida (ventana de 24 h)
  cd proy_bd_heatmap
  ./venv/bin/python scripts/suite_calidad_nocturna.py

  # Ventana de 7 días + umbral de ticks planos más estricto
  ./venv/bin/python scripts/suite_calidad_nocturna.py --hours 168 --max-flat 5

  # Contra otra BD (p. ej. la de pruebas) y solo un cheque
  BD_HEATMAP_DATABASE=heatmap_stock_test ./venv/bin/python \
      scripts/suite_calidad_nocturna.py --check CHK-FRESCURA

  # Ejecución silenciosa para cron (solo exit code + archivos)
  ./venv/bin/python scripts/suite_calidad_nocturna.py --quiet

INFORMACIÓN ÚTIL
--------------------------------------------------------------------------------
  · Conexión: lee BD_HEATMAP_* del .env de proy_bd_heatmap (igual que
    alembic/env.py). Sobrescribibles también por flags --host/--port/--db.
  · Informe: escribe MD + JSON en proy_bd_heatmap/reports/
    (suite_calidad_<fecha>.md | .json); la ruta se muestra por stdout.
  · Exit codes (pensados para cron / monitoreo):
        0 = OK (ningún FAIL)
        1 = hay al menos un FAIL (alerta: revisar el informe)
        3 = error de conexión/ejecución (infraestructura)
    Los WARN no cambian el exit code; quedan señalados en el informe.
  · Comportamiento con BD recién creada (sin datos): los cheques de datos
    emiten INFO "sin datos/ventana vacía" y NO fallan, para no disparar
    alertas en un arranque desde cero.
  · Ejemplo de línea CRON (02:00 UTC, log a syslog propio):
    0 2 * * * /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_bd_heatmap/venv/bin/python \
        /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_bd_heatmap/scripts/suite_calidad_nocturna.py \
        >> /var/log/suite_calidad_nocturna.log 2>&1

  Hecho cuando (criterio del roadmap): corre a las 02:00 UTC y deja informe
  diario sin alertas abiertas.
================================================================================
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=False)

VERSION = "1.0.0"

CONTINUO = ["forex", "crypto", "index", "yield", "commodity"]
SESION = ["equity", "etf", "common", "preferred", "unit"]

HUECO_MAX_S = 900          # cadencia radar 3 min → hueco > 15 min = alerta
FRESCURA_MAX_S = 1800       # 30 min sin marca en 24/5 = obsoleto
FLAT_MAX = 20               # ticks planos fuera de sesión tolerados (ventana 7d)
N_TICKS_WARN = 2            # n_ticks < 2 → WARN
MIN_DEFINITIVE = 0.0        # % mínimo de barras definitive (F4.1c lo elevará)


@dataclass
class CheckResult:
    id: str
    nombre: str
    estado: str
    detalle: dict = field(default_factory=dict)
    sql: str = ""


def conectar(args):
    host = args.host or os.getenv("BD_HEATMAP_HOST", "localhost")
    port = args.port or os.getenv("BD_HEATMAP_PORT", "5432")
    db = args.db or os.getenv("BD_HEATMAP_DATABASE", "heatmap_stock")
    user = args.user or os.getenv("BD_HEATMAP_USER", "postgres")
    password = args.password if args.password is not None else os.getenv("BD_HEATMAP_PASSWORD", "")
    return psycopg2.connect(host=host, port=port, dbname=db,
                            user=user, password=password), db


def ejecutar(cur, sql, params=None):
    cur.execute(sql, params or {})
    if cur.description is None:
        return []
    columns = [c.name for c in cur.description]
    return [dict(zip(columns, r)) for r in cur.fetchall()]


def chk_dups(table, claves, ventana_h, col_ts="timestamp_utc"):
    """Duplicados por clave natural en una tabla de hechos."""
    where = f"WHERE {col_ts} >= now() - make_interval(hours => %(h)s)"
    keys = ", ".join(claves)
    sql = (f"SELECT {keys}, count(*) AS n FROM {table} "
           f"{where} GROUP BY {keys} HAVING count(*) > 1 "
           f"ORDER BY n DESC LIMIT 20")

    def run(cur, args):
        filas = ejecutar(cur, sql, {"h": ventana_h})
        return CheckResult(
            id=f"CHK-DUP-{table.upper()}",
            nombre=f"Duplicados en {table} (ventana {ventana_h} h)",
            estado="FAIL" if filas else "PASS",
            detalle={"duplicados": len(filas), "ejemplos": filas[:5]},
            sql=sql,
        )
    return run


def chk_nulos(table, columna, ventana_h, col_ts="timestamp_utc"):
    sql = f"""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE {columna} IS NULL) AS nulos
        FROM {table}
        WHERE {col_ts} >= now() - make_interval(hours => %(h)s)
    """

    def run(cur, args):
        filas = ejecutar(cur, sql, {"h": ventana_h})
        r = filas[0] if filas else {"total": 0, "nulos": 0}
        if r["total"] == 0:
            estado = "INFO"
        else:
            estado = "FAIL" if r["nulos"] > 0 else "PASS"
        return CheckResult(
            id=f"CHK-NULL-{columna.upper()}",
            nombre=f"Nulos en {table}.{columna} (ventana {ventana_h} h)",
            estado=estado,
            detalle=r,
            sql=sql,
        )
    return run


def chk_ciclos(args):
    sql = f"""
        WITH serie AS (
            SELECT a.asset_class, a.symbol, s.timestamp_utc,
                   extract(epoch FROM (s.timestamp_utc - lag(s.timestamp_utc)
                       OVER (PARTITION BY s.asset_id ORDER BY s.timestamp_utc)))
                       AS gap_s
            FROM fact_market_series s
            JOIN dim_asset a ON a.asset_id = s.asset_id AND a.is_active
            WHERE s.timestamp_utc >= now() - make_interval(hours => %(h)s)
              AND a.asset_class = ANY(%(cont)s)
        )
        SELECT count(*) AS gaps, count(DISTINCT symbol) AS activos_afectados
        FROM serie
        WHERE gap_s IS NOT NULL AND gap_s > %(max)s
    """

    def run(cur, args):
        filas = ejecutar(cur, sql, {"h": args.hours, "cont": CONTINUO,
                                    "max": HUECO_MAX_S})
        r = filas[0] if filas else {"gaps": 0, "activos_afectados": 0}
        estado = "FAIL" if r["gaps"] else "PASS"
        return CheckResult(
            id="CHK-CICLOS",
            nombre="Huecos de captura en activos 24/5 (> 15 min)",
            estado=estado,
            detalle={**r, "umbral_s": HUECO_MAX_S},
            sql=sql,
        )
    return run


def chk_frescura(args):
    sql = f"""
        SELECT a.asset_class,
               max(s.timestamp_utc) AS max_ts,
               extract(epoch FROM (now() - max(s.timestamp_utc))) AS edad_s
        FROM fact_market_series s
        JOIN dim_asset a ON a.asset_id = s.asset_id AND a.is_active
        WHERE a.asset_class = ANY(%(cont)s)
        GROUP BY 1 ORDER BY 1
    """

    def run(cur, args):
        filas = ejecutar(cur, sql, {"cont": CONTINUO})
        if not filas:
            return CheckResult("CHK-FRESCURA",
                               "Frescura global de clases 24/5",
                               "INFO", {"detalle": "sin datos de series 24/5"}, sql)
        malos = [f for f in filas if f["max_ts"] is None or f["edad_s"] > FRESCURA_MAX_S]
        estado = "FAIL" if malos else "PASS"
        return CheckResult(
            id="CHK-FRESCURA",
            nombre="Frescura global de clases 24/5",
            estado=estado,
            detalle={"clases": filas, "obsoletas": malos, "umbral_s": FRESCURA_MAX_S},
            sql=sql,
        )
    return run


def chk_ticks_planos(args):
    sql = f"""
        WITH serie AS (
            SELECT s.asset_id, s.timestamp_utc, s.close,
                   lag(s.close) OVER (PARTITION BY s.asset_id
                       ORDER BY s.timestamp_utc) AS prev_close,
                   d.opens_at, d.closes_at
            FROM fact_market_series s
            JOIN dim_asset a ON a.asset_id = s.asset_id AND a.is_active
            LEFT JOIN dim_trading_session d
                   ON d.session_date = (s.timestamp_utc AT TIME ZONE 'America/New_York')::date
                  AND d.is_session = true
            WHERE s.timestamp_utc >= now() - INTERVAL '7 days'
              AND s.close IS NOT NULL
              AND a.asset_class IN ('equity', 'etf')
        )
        SELECT count(*) AS planos
        FROM serie t
        WHERE t.prev_close = t.close
          AND (
                t.opens_at IS NULL
                OR t.timestamp_utc < t.opens_at
                OR t.timestamp_utc > t.closes_at
          )
    """

    def run(cur, args):
        filas = ejecutar(cur, sql)
        n = filas[0]["planos"] if filas else 0
        estado = "FAIL" if n > args.max_flat else ("WARN" if n > 0 else "PASS")
        return CheckResult(
            id="CHK-TICKS-PLANOS",
            nombre="Ticks planos fuera de sesión (7 días, equity/ETF)",
            estado=estado,
            detalle={"planos": n, "umbral": args.max_flat},
            sql=sql,
        )
    return run


def chk_n_ticks(args):
    sql = f"""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE n_ticks = 0) AS cero,
               count(*) FILTER (WHERE n_ticks > 0 AND n_ticks < %(warn)s) AS bajos
        FROM fact_market_bar_15m
        WHERE bar_start_utc >= now() - INTERVAL '7 days'
    """

    def run(cur, args):
        filas = ejecutar(cur, sql, {"warn": N_TICKS_WARN})
        r = filas[0] if filas else {"total": 0, "cero": 0, "bajos": 0}
        if r["total"] == 0:
            estado = "INFO"
        elif r["cero"] > 0:
            estado = "FAIL"
        elif r["bajos"] > 0:
            estado = "WARN"
        else:
            estado = "PASS"
        return CheckResult(
            id="CHK-NTICKS",
            nombre="n_ticks por barra (7 días)",
            estado=estado,
            detalle={**r, "umbral_warn": N_TICKS_WARN},
            sql=sql,
        )
    return run


def chk_close_quality(args):
    sql = f"""
        SELECT close_quality, count(*) AS n
        FROM fact_market_bar_15m
        WHERE bar_start_utc >= now() - INTERVAL '7 days'
        GROUP BY 1 ORDER BY 2 DESC
    """

    def run(cur, args):
        filas = ejecutar(cur, sql)
        if not filas:
            return CheckResult("CHK-CLOSE-QUALITY",
                               "close_quality por barra (7 días)",
                               "INFO", {"detalle": "sin barras en 7 días"}, sql)
        total = sum(f["n"] for f in filas)
        porq = {f["close_quality"]: f["n"] for f in filas}
        definitivo = porq.get("definitive", 0)
        pct = definitivo / total
        estado = "PASS" if pct >= args.min_definitive else ("WARN" if pct == 0 else "PASS")
        return CheckResult(
            id="CHK-CLOSE-QUALITY",
            nombre="close_quality por barra (7 días)",
            estado=estado,
            detalle={"distribucion": porq, "total": total, "pct_definitive": round(pct, 4)},
            sql=sql,
        )
    return run


def chk_particiones(args):
    sql = f"""
        SELECT c.relname AS tabla, i.inhrelid::regclass::text AS particion
        FROM pg_class c
        JOIN pg_inherits i ON i.inhparent = c.oid
        WHERE c.relkind = 'p'
        ORDER BY 1, 2
    """

    def run(cur, args):
        filas = ejecutar(cur, sql)
        por_tabla = {}
        for f in filas:
            por_tabla.setdefault(f["tabla"], []).append(f["particion"])

        ahora = datetime.now(timezone.utc)
        esperado = [f"{t}_{ahora:%Y_%m}" for t in por_tabla]
        falta = [p for p in esperado if not any(p == part.split('.')[-1]
                                                for part in por_tabla.get(p.rsplit('_', 2)[0], []))]

        resumen = {t: len(v) for t, v in sorted(por_tabla.items())}
        estado = "FAIL" if falta else "PASS"
        return CheckResult(
            id="CHK-PARTICIONES",
            nombre="Contigüidad de particiones mensuales",
            estado=estado,
            detalle={"tablas": resumen, "esperadas_mes_actual": esperado,
                     "faltantes": falta},
            sql=sql,
        )
    return run


def main():
    ap = argparse.ArgumentParser(description="Suite nocturna de calidad F4.8 (M-VAL-01).")
    ap.add_argument("--db", default=None, help="BD a comprobar (default $BD_HEATMAP_DATABASE)")
    ap.add_argument("--host", default=None)
    ap.add_argument("--port", default=None)
    ap.add_argument("--user", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--hours", type=int, default=24,
                    help="Ventana de horas para cheques de datos recientes")
    ap.add_argument("--max-flat", type=int, default=FLAT_MAX,
                    help="Ticks planos fuera de sesión tolerados")
    ap.add_argument("--min-definitive", type=float, default=MIN_DEFINITIVE,
                    help="Fracción mínima de barras definitive (p. ej. 0.5)")
    ap.add_argument("--check", default=None, help="Ejecutar un solo cheque por id")
    ap.add_argument("--quiet", action="store_true", help="No imprimir el resumen en stdout")
    args = ap.parse_args()

    try:
        conn, db = conectar(args)
    except psycopg2.Error as exc:
        print(f"[suicidad] error de conexion a BD: {exc}", file=sys.stderr)
        return 3

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    ahora = datetime.now(timezone.utc)
    resultados = []
    fallos = 0

    fabricas = [
        lambda c, a: chk_ciclos(a)(c, a),
        lambda c, a: chk_frescura(a)(c, a),
        lambda c, a: chk_ticks_planos(a)(c, a),
        lambda c, a: chk_n_ticks(a)(c, a),
        lambda c, a: chk_close_quality(a)(c, a),
        lambda c, a: chk_particiones(a)(c, a),
        lambda c, a: chk_dups("fact_market_series", ["asset_id", "timestamp_utc"], a.hours)(c, a),
        lambda c, a: chk_dups("fact_market_bar_15m", ["asset_id", "bar_start_utc"], a.hours, "bar_start_utc")(c, a),
        lambda c, a: chk_dups("fact_market_indicator_tf", ["asset_id", "timestamp_utc", "tf"], a.hours)(c, a),
        lambda c, a: chk_dups("fact_heatmap_snapshot", ["asset_id", "timestamp_utc"], a.hours * 7)(c, a),
        lambda c, a: chk_nulos("fact_market_series", "close", a.hours)(c, a),
        lambda c, a: chk_nulos("fact_market_bar_15m", "close", a.hours * 7, "bar_start_utc")(c, a),
        lambda c, a: chk_nulos("fact_heatmap_snapshot", "price_heatmap", a.hours * 7)(c, a),
    ]

    for fabrica in fabricas:
        try:
            res = fabrica(cur, args)
        except psycopg2.Error as exc:
            res = CheckResult(fabrica.__name__, fabrica.__name__, "ERROR",
                              {"error": str(exc)}, "")
        if args.check and args.check.upper() != res.id:
            continue
        resultados.append(res)

    for r in resultados:
        if r.estado == "FAIL":
            fallos += 1

    conn.close()

    REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = ahora.strftime("%Y%m%d_%H%M%S")
    fecha = ahora.strftime("%Y-%m-%d %H:%M UTC")
    md_path = REPORT_DIR / f"suite_calidad_{ahora:%Y%m%d}_{ahora:%H%M%S}.md"
    json_path = REPORT_DIR / f"suite_calidad_{ahora:%Y%m%d}_{ahora:%H%M%S}.json"

    lineas = [f"# Suite nocturna de calidad (F4.8) — {fecha}",
              f"BD: `{db}` · versión script {VERSION} · "
              f"ventana {args.hours} h · ticks planos umbral {args.max_flat}",
              "",
              f"**Exit code:** {1 if fallos else 0} · **FAIL:** {fallos}",
              "",
              "| Cheque | Estado | Detalle |",
              "|---|:---:|---|"]
    for r in sorted(resultados, key=lambda x: x.id):
        d = json.dumps(r.detalle, ensure_ascii=False, default=str)
        lineas.append(f"| {r.id} | {r.estado} | {d} |")
    md_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps({
            "fecha": fecha, "bd": db, "version_script": VERSION,
            "ventana_h": args.hours, "exit_code": 1 if fallos else 0,
            "resultados": [r.__dict__ for r in sorted(resultados, key=lambda x: x.id)],
        }, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    if not args.quiet:
        print(f"[suite] {fecha} | BD={db} | FAIL={fallos} | "
              f"informe: {md_path} | json: {json_path}")
        for r in sorted(resultados, key=lambda x: x.id):
            marca = {"FAIL": "!!", "WARN": "~", "PASS": "ok", "INFO": "··",
                     "ERROR": "XX"}[r.estado]
            print(f"[{marca}] {r.id:24s} {r.estado:5s} {r.nombre}")
            if r.estado in ("FAIL", "WARN", "ERROR"):
                print(f"      {json.dumps(r.detalle, ensure_ascii=False, default=str)[:300]}")

    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())