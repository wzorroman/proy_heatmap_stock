"""
Servicio de negocio para el heatmap.
Orquesta las consultas del repositorio y aplica logica de transformacion.
"""
import os
import sys
from typing import List, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import config
from db.postgresql_connection import PostgreSQLConnector
from application.db.heatmap_repository import (
    get_heatmap_last_hour,
    get_sectors,
    get_heatmap_stats,
    get_price_evolution,
)


def _get_connection() -> PostgreSQLConnector:
    db = PostgreSQLConnector(
        host=config.PG_HOST,
        port=config.PG_PORT,
        database=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )
    if not db.connect():
        raise ConnectionError("No se pudo conectar a PostgreSQL")
    return db


def fetch_heatmap_data() -> List[Dict]:
    db = _get_connection()
    try:
        return get_heatmap_last_hour(db)
    finally:
        db.disconnect()


def fetch_sectors() -> List[str]:
    db = _get_connection()
    try:
        return get_sectors(db)
    finally:
        db.disconnect()


def fetch_heatmap_stats() -> Dict:
    db = _get_connection()
    try:
        return get_heatmap_stats(db)
    finally:
        db.disconnect()


def _format_market_cap(value) -> Optional[str]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


def _build_asset_label(row: Dict) -> str:
    ticker = row.get('ticker') or ''
    company = row.get('company_name') or ''
    sector = row.get('sector') or ''

    parties = [company] if company and company != ticker else []
    label = '  '.join([ticker] + parties)
    if sector:
        label += f"  [{sector}]"
    return label


def fetch_price_evolution(lookback_hours: int = 1, max_snapshots: int = 6) -> List[Dict]:
    db = _get_connection()
    try:
        rows = get_price_evolution(db, lookback_hours, max_snapshots)
    finally:
        db.disconnect()

    from collections import defaultdict

    by_symbol = defaultdict(list)
    for row in rows:
        by_symbol[row['symbol']].append(row)

    result = []
    for symbol, snapshots in by_symbol.items():
        snapshots.sort(key=lambda r: r['timestamp_utc'], reverse=True)
        base = snapshots[0]
        prev_price = snapshots[1]['price'] if len(snapshots) > 1 else None

        arrow = ""
        direction = 0
        if prev_price is not None and base['price'] is not None:
            if base['price'] > prev_price:
                arrow = "\U0001F7E2 \u2191"
                direction = 1
            elif base['price'] < prev_price:
                arrow = "\U0001F534 \u2193"
                direction = -1
            else:
                arrow = "\u26AA"

        row_data = {
            'symbol': symbol,
            'asset': _build_asset_label(base),
            'price': base['price'],
            'arrow': arrow,
            'direction': direction,
            'daily_change_pct': base['daily_change_pct'],
            'market_cap': base['market_cap'],
            'mcap': _format_market_cap(base['market_cap']),
        }
        for snap in snapshots:
            label = snap['timestamp_utc'].strftime('%H:%M')
            row_data[label] = snap['price']
        result.append(row_data)
    return result
