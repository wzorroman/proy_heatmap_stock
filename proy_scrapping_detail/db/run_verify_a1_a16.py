# file: proy_scrapping_detail/db/run_verify_a1_a16.py
"""F0.1 · Ejecuta A1-A16 contra heatmap_stock y genera la planilla de resultados.

Uso:
    python3 -m db.run_verify_a1_a16 [--tz America/Lima|UTC]
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.postgresql_connection import PostgreSQLConnector

QUERIES_FILE = Path(__file__).parent / "verify_a1_a16.sql"

A5_EXTRA = {
    "UTC": "SET TIME ZONE 'UTC';",
    "America/Lima": "SET TIME ZONE 'America/Lima';",
}


def split_queries(text: str):
    lines = [ln.split("--", 1)[0] for ln in text.splitlines() if ln.strip()]
    return [q.strip() for q in "\n".join(lines).split(";") if q.strip()]


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tz", default="UTC", choices=["UTC", "America/Lima"])
    args = parser.parse_args()

    conf = PostgreSQLConnector(
        os.getenv("BD_HEATMAP_HOST", "localhost"),
        int(os.getenv("BD_HEATMAP_PORT", "5432")),
        os.getenv("BD_HEATMAP_DATABASE", "heatmap_stock"),
        os.getenv("BD_HEATMAP_USER", "postgres"),
        os.getenv("BD_HEATMAP_PASSWORD", ""),
    )
    conf.connect()
    cur = conf.connection.cursor()

    queries = split_queries(QUERIES_FILE.read_text())
    # A1-A4, A6-A10, A11, A12, A14, A15
    results = {}
    for idx, q in enumerate(queries, start=1):
        if idx == 5:
            continue  # A5 va aparte con SET TIME ZONE
        cur.execute(q)
        if cur.description is None:
            results[f"A{idx}"] = {"rows": [], "note": "sin resultado"}
            continue
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        results[f"A{idx}"] = {"columns": cols, "count": len(rows),
                              "sample": [list(r) for r in rows[:8]]}

    # A5 (dos veces)
    a5 = {}
    for tz, stmt in A5_EXTRA.items():
        cur.execute(stmt)
        cur.execute(queries[4])
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        a5[tz] = {"columns": cols, "count": len(rows),
                  "sample": [list(r) for r in rows[:8]]}

    results["A5"] = a5
    conf.disconnect()

    out = Path(__file__).parent / f"planilla_a1_a16_{args.tz.replace('/', '-')}.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"OK → {out}")
    for k, v in results.items():
        if k == "A5":
            print(f"  {k}: Lima={v['America/Lima']['count']} filas / UTC={v['UTC']['count']} filas")
        else:
            print(f"  {k}: {v['count']} filas")


if __name__ == "__main__":
    run()