"""
Consultas SQL para el heatmap.
Solo contiene funciones que ejecutan queries y retornan datos.
"""
from typing import List, Dict

from db.postgresql_connection import PostgreSQLConnector


# Taxonomía visible en el heatmap (excluye activos del radar V4: crypto, fx, futuros…)
ASSET_CLASSES_HEATMAP = ('equity', 'etf')


def get_heatmap_last_hour(conn: PostgreSQLConnector) -> List[Dict]:
    query = """
        SELECT
            symbol, ticker, sector, company_name,
            price_heatmap, daily_change_pct, market_cap, timestamp_utc
        FROM (
            SELECT DISTINCT ON (a.symbol)
                a.symbol,
                a.ticker,
                a.sector,
                a.company_name,
                h.price_heatmap,
                h.daily_change_pct,
                h.market_cap,
                h.timestamp_utc
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a ON h.asset_id = a.asset_id
            WHERE h.timestamp_utc >= (SELECT MAX(timestamp_utc) - INTERVAL '15 minutes' FROM fact_heatmap_snapshot)
              AND a.is_active = TRUE
              AND a.asset_class IN ('equity', 'etf')
            ORDER BY a.symbol, h.timestamp_utc DESC
        ) latest
        ORDER BY market_cap DESC NULLS LAST;
    """
    return conn.execute_query(query)


def get_sectors(conn: PostgreSQLConnector) -> List[str]:
    query = """
        SELECT DISTINCT sector
        FROM dim_asset
        WHERE sector IS NOT NULL
          AND is_active = TRUE
          AND asset_class IN ('equity', 'etf')
        ORDER BY sector;
    """
    result = conn.execute_query(query)
    return [row['sector'] for row in result]


def get_heatmap_stats(conn: PostgreSQLConnector) -> Dict:
    query = """
        SELECT
            COUNT(*) AS total_stocks,
            COUNT(*) FILTER (WHERE daily_change_pct > 0) AS stocks_up,
            COUNT(*) FILTER (WHERE daily_change_pct < 0) AS stocks_down,
            COUNT(*) FILTER (WHERE daily_change_pct = 0) AS stocks_neutral,
            ROUND(AVG(price_heatmap)::numeric, 2) AS avg_price,
            ROUND(AVG(daily_change_pct)::numeric, 4) AS avg_change_pct
        FROM (
            SELECT DISTINCT ON (a.symbol)
                h.price_heatmap, h.daily_change_pct
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a ON h.asset_id = a.asset_id
            WHERE h.timestamp_utc >= (SELECT MAX(timestamp_utc) - INTERVAL '15 minutes' FROM fact_heatmap_snapshot)
              AND a.is_active = TRUE
              AND a.asset_class IN ('equity', 'etf')
            ORDER BY a.symbol, h.timestamp_utc DESC
        ) latest;
    """
    result = conn.execute_query(query)
    return result[0] if result else {}


def get_price_evolution(conn: PostgreSQLConnector, lookback_hours: int = 24, max_snapshots: int = 6) -> List[Dict]:
    query = """
        WITH ranked AS (
            SELECT
                a.symbol, a.ticker, a.sector, a.company_name,
                h.price_heatmap, h.daily_change_pct, h.market_cap, h.timestamp_utc,
                ROW_NUMBER() OVER (
                    PARTITION BY a.symbol
                    ORDER BY h.timestamp_utc DESC
                ) AS rn
            FROM fact_heatmap_snapshot h
            JOIN dim_asset a ON h.asset_id = a.asset_id
            WHERE h.timestamp_utc >= NOW() - make_interval(hours => %s)
              AND a.is_active = TRUE
              AND a.asset_class IN ('equity', 'etf')
        )
        SELECT symbol, ticker, sector, company_name,
               price_heatmap, daily_change_pct, market_cap, timestamp_utc, rn
        FROM ranked
        WHERE rn <= %s
        ORDER BY market_cap DESC NULLS LAST, symbol, rn;
    """
    return conn.execute_query(query, (lookback_hours, max_snapshots))
