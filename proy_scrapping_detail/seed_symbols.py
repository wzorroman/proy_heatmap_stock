#!/usr/bin/env python3
# file: proy_scrapping_detail/seed_symbols.py
"""
SEED de dim_asset desde CONFIG_ACTIVOS — proy_scrapping_detail
==============================================================
Sincroniza el universo del radar (primarios + respaldos) hacia dim_asset
con SOLO ALTAS NUEVAS (criterio primer-gana, D5). No re-etiqueta ni
sobreescribe símbolos existentes.

Verificado 2026-09-13: los 110 símbolos del radar ya existen en dim_asset,
por lo que hoy este script es idempotente/no-op y cubre altas futuras.

Uso:
    python seed_symbols.py             # altas nuevas en PostgreSQL (idempotente)
    python seed_symbols.py --dry-run   # reporta faltantes sin escribir
    python seed_symbols.py --check     # reporta faltantes y sale != 0 si hay alguno
"""
import argparse
import sys
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# CLASS_MAP y ETF_TICKERS: duplicado local del patrón del heatmap para autonomía.
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
    'TVC':      'index',
    'AMEX':     'etf',
    'NASDAQ':   'equity',
    'NYSE':     'equity',
}

ETF_TICKERS = ('QQQ', 'SPY', 'VOO', 'VGT', 'SHY', 'IEI', 'IEF', 'TLT', 'SLV',
               'USO', 'XLE', 'XOP', 'UUP')

# F4.5b: mapeo canónico de claves lógicas (espejo de la migración alembic 0006).
#   logical_key  = clave F2.5 (VIX|DXY|TLT|US10Y|ORO|OIL)
#   role         = primary (canónico) | fallback (respaldo del radar)
MAPEO_LOGICAL = {
    'TVC:VIX':      {'logical_key': 'VIX',   'role': 'primary',  'is_canonical': True,  'feed_delay_s': 0},
    'CBOE:VX1!':    {'logical_key': 'VIX',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 600},
    'TVC:DXY':      {'logical_key': 'DXY',   'role': 'primary',  'is_canonical': True,  'feed_delay_s': 0},
    'ICEUS:DX1!':   {'logical_key': 'DXY',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 600},
    'AMEX:UUP':     {'logical_key': 'DXY',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 900},
    'OANDA:XAUUSD': {'logical_key': 'ORO',   'role': 'primary',  'is_canonical': True,  'feed_delay_s': 0},
    'SAXO:XAUUSD':  {'logical_key': 'ORO',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 0},
    'AMEX:USO':     {'logical_key': 'OIL',   'role': 'primary',  'is_canonical': True,  'feed_delay_s': 900},
    'NYMEX:CL1!':   {'logical_key': 'OIL',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 600},
    'NASDAQ:TLT':   {'logical_key': 'TLT',   'role': 'primary',  'is_canonical': True,  'feed_delay_s': 900},
    'CBOT:ZB1!':    {'logical_key': 'TLT',   'role': 'fallback', 'is_canonical': False, 'feed_delay_s': 600},
    'TVC:US10Y':    {'logical_key': 'US10Y', 'role': 'primary',  'is_canonical': True,  'feed_delay_s': 0},
}

FEED_DELAY_CLASE = {
    'equity': 900, 'etf': 900,
    'future': 600,
    'crypto': 0, 'forex': 0, 'commodity': 0, 'index': 0, 'yield': 0,
}


def classify_symbol(symbol):
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


def radar_rows():
    import config
    rows = []
    for categoria, activos in config.CONFIG_ACTIVOS.items():
        for clave, fuentes in activos.items():
            for tipo_fuente in ('primario', 'respaldo'):
                symbol = fuentes.get(tipo_fuente)
                if not symbol:
                    continue
                exchange, ticker = symbol.split(':', 1)
                row = {
                    'symbol': symbol,
                    'ticker': ticker,
                    'exchange': exchange,
                    'asset_class': classify_symbol(symbol),
                    'source_discovered_by': 'radar_v4',
                    'source_category': categoria,
                }
                meta = MAPEO_LOGICAL.get(symbol)
                row['logical_key'] = (meta or {}).get('logical_key')
                row['role'] = (meta or {}).get('role')
                row['is_canonical'] = bool((meta or {}).get('is_canonical'))
                row['feed_delay_s'] = (meta or {}).get(
                    'feed_delay_s',
                    FEED_DELAY_CLASE.get(row['asset_class'], 0),
                )
                rows.append(row)
    return rows


def get_faltantes(db, rows):
    symbols = [r['symbol'] for r in rows]
    result = db.execute_query(
        "SELECT symbol FROM dim_asset WHERE is_active"
    )
    existentes = {row['symbol'] for row in result} if result else set()
    faltantes = [r for r in rows if r['symbol'] not in existentes]
    return faltantes


def main():
    parser = argparse.ArgumentParser(description="Seed dim_asset desde CONFIG_ACTIVOS")
    parser.add_argument('--dry-run', action='store_true',
                        help="Reporta faltantes sin escribir en BD")
    parser.add_argument('--check', action='store_true',
                        help="Reporta faltantes y sale con código != 0 si hay alguno")
    args = parser.parse_args()

    rows = radar_rows()
    unique_by_symbol = {}
    for r in rows:
        unique_by_symbol.setdefault(r['symbol'], r)
    rows = list(unique_by_symbol.values())

    print(f"Radar: {len(rows)} símbolos únicos "
          f"({len(unique_by_symbol)}) desde CONFIG_ACTIVOS")
    classes = Counter(r['asset_class'] for r in rows)
    print("  asset_class:", dict(classes))

    import config
    from db.postgresql_connection import PostgreSQLConnector

    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT,
        config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
    )
    if not db.connect():
        print("❌ No se pudo conectar a PostgreSQL")
        sys.exit(2)

    try:
        faltantes = get_faltantes(db, rows)

        if args.dry_run or args.check:
            print(f"\nFaltantes en dim_asset: {len(faltantes)}")
            for r in faltantes:
                print(f"  - {r['symbol']}  ({r['asset_class']}, cat={r['source_category']})")
            if args.check and faltantes:
                db.disconnect()
                sys.exit(1)
            db.disconnect()
            return

        # Altas nuevas (no-op si no falta ninguno)
        if not faltantes:
            print("\nSeed no-op: los símbolos del radar ya existen en dim_asset.")
        else:
            insert_query = """
                INSERT INTO dim_asset (
                    symbol, ticker, exchange, asset_class,
                    source_discovered_by, source_category,
                    logical_key, is_canonical, role, feed_delay_s,
                    is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s,
                          TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (symbol) DO NOTHING
            """
            n = 0
            for r in faltantes:
                n += db.execute_batch(insert_query, [(
                    r['symbol'], r['ticker'], r['exchange'], r['asset_class'],
                    r['source_discovered_by'], r['source_category'],
                    r.get('logical_key'), r.get('is_canonical'),
                    r.get('role'), r.get('feed_delay_s'),
                )])
            print(f"{n} altas nuevas realizadas en dim_asset")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()