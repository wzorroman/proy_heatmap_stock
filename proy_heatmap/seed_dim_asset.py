#!/usr/bin/env python3
"""
SEED de dim_asset + dim_time — heatmap_stock v1.0.2
====================================================
Carga el catálogo base de activos por defecto:

  1. Catálogo del heatmap:   docs/dim_asset_202609112246.csv  (1.005 símbolos)
  2. Merge con el radar:     config/radar_activos.json        (110 símbolos)
  3. dim_time 2026–2027      (calendario generado)

Criterio primer-gana: el primer scraper que llegó deja su source_discovered_by;
los upserts usan COALESCE para no pisar asset_class/share_class/source_* previos.

Uso:
    python seed_dim_asset.py                # carga real en PostgreSQL
    python seed_dim_asset.py --dry-run      # solo conteos, sin tocar la BD
    python seed_dim_asset.py --csv-only     # omite el merge del radar
    python seed_dim_asset.py --skip-dim-time
    python seed_dim_asset.py --config config/radar_activos.json
"""

import argparse
import csv
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
CSV_DEFAULT = os.path.join(REPO_ROOT, "docs", "dim_asset_202609112246.csv")
RADAR_DEFAULT = os.path.join(BASE_DIR, "config", "radar_activos.json")

# Derivación de asset_class por prefijo del exchange (roadmap §13)
CLASS_MAP = {
    'BINANCE':  'crypto',
    'BITSTAMP': 'crypto',
    'OANDA':    'forex',
    'FX_IDC':   'forex',
    'SAXO':     'commodity',
    'CME':      'future',
    'CME_MINI': 'future',
    'CBOT':     'future',
    'NYMEX':    'future',
    'ICEUS':    'future',
    'CBOE':     'future',
    'TVC':      'index',      # se sobreescribe abajo para US02Y/US10Y
    'AMEX':     'etf',        # puede ser equity según ticker
    'NASDAQ':   'equity',
    'NYSE':     'equity',
}

ETF_TICKERS = ('QQQ', 'SPY', 'VOO', 'VGT', 'SHY', 'IEI', 'IEF', 'TLT', 'SLV',
               'USO', 'XLE', 'XOP', 'UUP')


def classify(symbol, category):
    ex, tk = symbol.split(':', 1)
    if ex == 'TVC' and tk.startswith('US') and tk.endswith('Y'):
        return 'yield'
    if ex == 'TVC' and tk == 'VIX':
        return 'index'
    if ex == 'TVC' and tk == 'SILVER':
        return 'commodity'
    if ex in ('NASDAQ', 'AMEX') and tk in ETF_TICKERS:
        return 'etf'
    return CLASS_MAP.get(ex, 'equity')


def all_symbols(radar_config):
    seen = set()
    for cat, data in radar_config.items():
        for entry in data.values():
            for key in ('primario', 'respaldo'):
                s = entry.get(key)
                if s and s not in seen:
                    seen.add(s)
                    yield s, cat


def _bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


def load_csv_rows(csv_path):
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            symbol = (r.get('symbol') or '').strip()
            if not symbol:
                continue
            exchange = symbol.split(':', 1)[0]
            ticker = (r.get('ticker') or '').strip() or symbol.split(':', 1)[-1]
            share_class = (r.get('asset_class') or '').strip() or None
            rows.append({
                'symbol': symbol,
                'ticker': ticker,
                'exchange': exchange,
                'asset_class': 'equity',
                'share_class': share_class,
                'sector': (r.get('sector') or '').strip() or None,
                'company_name': (r.get('company_name') or '').strip() or None,
                'source_discovered_by': 'heatmap',
                'source_category': None,
                'is_active': _bool(r.get('is_active')),
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
            })
    return rows


def load_radar_rows(radar_path):
    import json
    with open(radar_path, 'r', encoding='utf-8') as f:
        radar_config = json.load(f)
    rows = []
    for symbol, category in all_symbols(radar_config):
        exchange, ticker = symbol.split(':', 1)
        rows.append({
            'symbol': symbol,
            'ticker': ticker,
            'exchange': exchange,
            'asset_class': classify(symbol, category),
            'source_discovered_by': 'radar_v4',
            'source_category': category,
        })
    return rows


def show_dry_run(csv_rows, radar_rows, csv_only):
    csv_symbols = {r['symbol'] for r in csv_rows}
    radar_symbols = {r['symbol'] for r in radar_rows}

    print("=== DRY RUN — seed_dim_asset ===")
    print(f"CSV   ({CSV_DEFAULT}): {len(csv_rows)} filas")

    from collections import Counter
    share = Counter(r['share_class'] for r in csv_rows)
    print("  share_class:", dict(share))
    excl = Counter(r['exchange'] for r in csv_rows)
    print("  exchanges:  ", dict(excl))
    print(f"  con created_at: {sum(1 for r in csv_rows if r['created_at'])}")

    if not csv_only:
        print(f"RADAR ({RADAR_DEFAULT}): {len(radar_rows)} símbolos")
        classes = Counter(r['asset_class'] for r in radar_rows)
        print("  asset_class:", dict(classes))
        cats = Counter(r['source_category'] for r in radar_rows)
        print("  categorías: ", len(cats))
        overlap = sorted(csv_symbols & radar_symbols)
        print(f"  solapamientos CSV→radar: {len(overlap)} {overlap[:25]}...")
        print("  radios que ganan su asset_class (no en CSV):",
              len(radar_symbols - csv_symbols))

    print("---")
    print("Fuentes de símbolos (primer-gana):")
    mixes = Counter('heatmap' if s in csv_symbols else 'radar_v4' for s in (csv_symbols | radar_symbols))
    print(" ", dict(mixes))


def seed_dim_time(cur):
    cur.execute("""
        INSERT INTO dim_time (
            date_id, full_date, year, quarter, month, month_name,
            day_of_month, day_of_week, week_number, is_weekend, is_holiday,
            trading_session
        )
        SELECT
            (EXTRACT(YEAR FROM d)::int * 10000
             + EXTRACT(MONTH FROM d)::int * 100
             + EXTRACT(DAY FROM d)::int) AS date_id,
            d AS full_date,
            EXTRACT(YEAR FROM d)::smallint,
            EXTRACT(QUARTER FROM d)::smallint,
            EXTRACT(MONTH FROM d)::smallint,
            to_char(d, 'FMMonth'),
            EXTRACT(DAY FROM d)::smallint,
            EXTRACT(ISODOW FROM d)::smallint,
            EXTRACT(WEEK FROM d)::smallint,
            EXTRACT(ISODOW FROM d) IN (6, 7),
            FALSE,
            CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN NULL ELSE 'US' END
        FROM generate_series('2026-01-01'::date, '2027-12-31'::date, '1 day') AS d
        ON CONFLICT (date_id) DO NOTHING
    """)


def run_real(csv_rows, radar_rows, csv_only, skip_dim_time):
    sys.path.insert(0, BASE_DIR)
    import config
    import psycopg2

    with psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT, dbname=config.PG_DATABASE,
        user=config.PG_USER, password=config.PG_PASSWORD
    ) as conn:
        with conn.cursor() as cur:

            csv_sql = """
                INSERT INTO dim_asset (
                    symbol, ticker, exchange, asset_class, share_class,
                    sector, company_name, source_discovered_by, source_category,
                    is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    ticker          = EXCLUDED.ticker,
                    exchange        = EXCLUDED.exchange,
                    sector          = COALESCE(dim_asset.sector, EXCLUDED.sector),
                    company_name    = COALESCE(dim_asset.company_name, EXCLUDED.company_name),
                    updated_at      = CURRENT_TIMESTAMP
            """
            csv_params = [(
                r['symbol'], r['ticker'], r['exchange'], r['asset_class'],
                r['share_class'], r['sector'], r['company_name'],
                r['source_discovered_by'], r['source_category'],
                r['is_active'], r['created_at'], r['updated_at'],
            ) for r in csv_rows]
            cur.executemany(csv_sql, csv_params)
            print(f"dim_asset CSV sembrada: {len(csv_params)} filas")

            if not csv_only:
                radar_sql = """
                    INSERT INTO dim_asset (
                        symbol, ticker, exchange, asset_class,
                        source_discovered_by, source_category
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        asset_class     = COALESCE(dim_asset.asset_class, EXCLUDED.asset_class),
                        source_category = COALESCE(EXCLUDED.source_category, dim_asset.source_category),
                        updated_at      = CURRENT_TIMESTAMP
                """
                radar_params = [(
                    r['symbol'], r['ticker'], r['exchange'], r['asset_class'],
                    r['source_discovered_by'], r['source_category'],
                ) for r in radar_rows]
                cur.executemany(radar_sql, radar_params)
                print(f"dim_asset radar sembrada: {len(radar_params)} filas (primer-gana respetado)")

            if not skip_dim_time:
                seed_dim_time(cur)
                cur.execute("SELECT COUNT(*) FROM dim_time")
                print(f"dim_time sembrada: {cur.fetchone()[0]} días (2026-2027)")

            conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed de dim_asset + dim_time")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo mostrar conteos, sin tocar la BD")
    parser.add_argument("--csv-only", action="store_true",
                        help="Omitir el merge con los símbolos del radar")
    parser.add_argument("--skip-dim-time", action="store_true",
                        help="No sembrar dim_time 2026-2027")
    parser.add_argument("--config", default=RADAR_DEFAULT,
                        help=f"Ruta del volcado radar (default: {RADAR_DEFAULT})")
    args = parser.parse_args()

    csv_rows = load_csv_rows(CSV_DEFAULT)
    radar_rows = [] if args.csv_only else load_radar_rows(args.config)

    if args.dry_run:
        show_dry_run(csv_rows, radar_rows, args.csv_only)
        return

    run_real(csv_rows, radar_rows, args.csv_only, args.skip_dim_time)
    print("seed_dim_asset completado.")


if __name__ == "__main__":
    main()