# file: proy_scrapping_detail/db/event_repository.py
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from db.postgresql_connection import PostgreSQLConnector

logger = logging.getLogger('db.event_repository')


def safe_int(val: Any) -> Optional[int]:
    """Convierte a int si es posible, retorna None si no."""
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def safe_float(val: Any) -> Optional[float]:
    """Convierte a float si es posible, retorna None si no."""
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_text(val: Any) -> Optional[str]:
    """Convierte a str si existe, retorna None si no."""
    if val is None:
        return None
    return str(val)


def parse_iso(val: Any) -> Optional[datetime]:
    """Parsea ISO string a datetime UTC."""
    if not val:
        return None
    try:
        s = val.replace('Z', '+00:00')
        return datetime.fromisoformat(s)
    except Exception:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def sha256(data: str) -> str:
    """Calcula SHA-256 hex."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def insert_events_batch(db: PostgreSQLConnector, events: List[Dict]) -> int:
    """
    Inserta batch de eventos económicos en fact_economic_event.
    Dedup por event_id (BIGINT PK). Puebla las 29 columnas del esquema v1.0.2.
    """
    params = []
    for evento in events:
        # 1. Convertir event_id a BIGINT
        event_id = safe_int(evento.get('id'))
        if event_id is None:
            logger.warning(f"Evento sin id válido: {evento}")
            continue

        # 2. Calcular checksum canónico (sin timestamp_captura para estabilidad)
        # Nota: el raw_payload sí incluye todo el evento original
        checksum = sha256(json.dumps(evento, sort_keys=True, default=str))

        # 3. Preparar tupla (29 columnas, en el orden del esquema)
        params.append((
            event_id,                                   # 1. event_id (BIGINT PK)
            evento.get('title'),                        # 2. title
            evento.get('country'),                      # 3. country (FK dim_country)
            evento.get('indicator'),                    # 4. indicator
            evento.get('ticker'),                       # 5. event_ticker
            evento.get('comment'),                      # 6. comment
            evento.get('category'),                     # 7. category
            evento.get('period'),                       # 8. period
            parse_iso(evento.get('referenceDate')),     # 9. reference_date
            evento.get('source'),                       # 10. source
            evento.get('source_url'),                   # 11. source_url
            safe_float(evento.get('actual')),           # 12. actual
            safe_float(evento.get('previous')),         # 13. previous
            safe_float(evento.get('forecast')),         # 14. forecast
            safe_float(evento.get('actualRaw')),        # 15. actual_raw
            safe_float(evento.get('previousRaw')),      # 16. previous_raw
            safe_float(evento.get('forecastRaw')),      # 17. forecast_raw
            safe_text(evento.get('actual')),            # 18. actual_display
            safe_text(evento.get('previous')),          # 19. previous_display
            safe_text(evento.get('forecast')),          # 20. forecast_display
            evento.get('currency'),                     # 21. currency
            evento.get('unit'),                         # 22. unit
            safe_int(evento.get('importance')),         # 23. importance
            parse_iso(evento.get('date')),              # 24. event_timestamp
            parse_iso(evento.get('timestamp_captura')), # 25. captured_at
            now_utc(),                                   # 26. first_seen_at
            now_utc(),                                   # 27. last_updated_at
            json.dumps(evento, default=str),            # 28. raw_payload (JSONB)
            checksum                                     # 29. payload_checksum
        ))

    if not params:
        logger.info("No hay eventos válidos para insertar")
        return 0

    # 4. UPSERT batch (29 columnas)
    upsert_query = """
        INSERT INTO fact_economic_event (
            event_id, title, country, indicator, event_ticker, comment,
            category, period, reference_date, source, source_url,
            actual, previous, forecast,
            actual_raw, previous_raw, forecast_raw,
            actual_display, previous_display, forecast_display,
            currency, unit, importance, event_timestamp, captured_at,
            first_seen_at, last_updated_at, raw_payload, payload_checksum
        ) VALUES %s
        ON CONFLICT (event_id) DO UPDATE SET
            title             = EXCLUDED.title,
            country           = EXCLUDED.country,
            indicator         = COALESCE(EXCLUDED.indicator, fact_economic_event.indicator),
            event_ticker      = COALESCE(EXCLUDED.event_ticker, fact_economic_event.event_ticker),
            comment           = COALESCE(EXCLUDED.comment, fact_economic_event.comment),
            category          = COALESCE(EXCLUDED.category, fact_economic_event.category),
            period            = COALESCE(EXCLUDED.period, fact_economic_event.period),
            reference_date    = COALESCE(EXCLUDED.reference_date, fact_economic_event.reference_date),
            source            = COALESCE(EXCLUDED.source, fact_economic_event.source),
            source_url        = COALESCE(EXCLUDED.source_url, fact_economic_event.source_url),
            actual            = COALESCE(EXCLUDED.actual, fact_economic_event.actual),
            previous          = COALESCE(EXCLUDED.previous, fact_economic_event.previous),
            forecast          = COALESCE(EXCLUDED.forecast, fact_economic_event.forecast),
            actual_raw        = COALESCE(EXCLUDED.actual_raw, fact_economic_event.actual_raw),
            previous_raw      = COALESCE(EXCLUDED.previous_raw, fact_economic_event.previous_raw),
            forecast_raw      = COALESCE(EXCLUDED.forecast_raw, fact_economic_event.forecast_raw),
            actual_display    = COALESCE(EXCLUDED.actual_display, fact_economic_event.actual_display),
            previous_display  = COALESCE(EXCLUDED.previous_display, fact_economic_event.previous_display),
            forecast_display  = COALESCE(EXCLUDED.forecast_display, fact_economic_event.forecast_display),
            currency          = EXCLUDED.currency,
            unit              = EXCLUDED.unit,
            importance        = EXCLUDED.importance,
            event_timestamp   = EXCLUDED.event_timestamp,
            captured_at       = COALESCE(EXCLUDED.captured_at, fact_economic_event.captured_at),
            raw_payload       = EXCLUDED.raw_payload,
            last_updated_at   = CURRENT_TIMESTAMP,
            payload_checksum  = EXCLUDED.payload_checksum
    """
    # 27 placeholders + raw_payload (jsonb) + checksum = 29
    template = "(" + ", ".join(["%s"] * 27 + ["%s::jsonb", "%s"]) + ")"
    
    result = db.execute_values(upsert_query, params, template=template)
    inserted = len(result) if result and isinstance(result[0], dict) and 'rows_affected' not in result[0] else len(params)
    logger.info(f"BD: {inserted} eventos upserted en fact_economic_event")
    return inserted