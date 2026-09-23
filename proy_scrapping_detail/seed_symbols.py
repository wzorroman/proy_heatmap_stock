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
                rows.append({
                    'symbol': symbol,
                    'ticker': ticker,
                    'exchange': exchange,
                    'asset_class': classify_symbol(symbol),
                    'source_discovered_by': 'radar_v4',
                    'source_category': categoria,
                })
    return rows


def get_faltantes(db, rows):
    symbols = [r['symbol'] for r in rows]
    result = db.execute_query(
        "SELECT symbol FROM dim_asset WHERE is_active AND current_version"
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
                    is_active, valid_from, valid_to, current_version,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s,
                          TRUE, CURRENT_TIMESTAMP, 'infinity', TRUE,
                          CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (symbol) DO NOTHING
            """
            n = 0
            for r in faltantes:
                n += db.execute_batch(insert_query, [(
                    r['symbol'], r['ticker'], r['exchange'], r['asset_class'],
                    r['source_discovered_by'], r['source_category'],
                )])
            print(f"{n} altas nuevas realizadas en dim_asset")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()