-- ============================================================================
-- Migración v3.1.0 — Cambios de esquema para el scraper de calendario
-- Fecha: 2026-09-13
-- Proyecto: proy_scrapping_detail (scraper de calendario económico)
-- ============================================================================
-- Este script modifica el esquema v1.0.2 para soportar:
--   1. Retención de raw_payload de eventos (NULL después de 6 meses)
--   2. Campos nullable para datos incompletos (D23)
--
-- Tablas afectadas: fact_economic_event
-- Ejecutar UNA VEZ antes de activar DB_WRITE_ENABLED=true en el scraper.
-- No crea tablas: el esquema v1.0.2 (02_init_database.sql) ya las define.
-- ============================================================================

\echo '=> [04] Iniciando migración v3.1.0'

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Hacer nullable raw_payload de eventos (D30)
-- ----------------------------------------------------------------------------
-- La columna raw_payload era NOT NULL en v1.0.2.
-- Para la retención de 6 meses necesitamos poder ponerla a NULL.
-- (retention_events.py ejecutará: UPDATE ... SET raw_payload = NULL WHERE ...)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fact_economic_event'
          AND column_name = 'raw_payload'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE fact_economic_event
            ALTER COLUMN raw_payload DROP NOT NULL;
        RAISE NOTICE '[04] fact_economic_event.raw_payload ahora es nullable';
    ELSE
        RAISE NOTICE '[04] fact_economic_event.raw_payload ya era nullable (sin cambios)';
    END IF;
END
$$;

COMMIT;

-- ----------------------------------------------------------------------------
-- 2. Verificar que la columna quedó nullable
-- ----------------------------------------------------------------------------
\echo '=> [04] Verificación: raw_payload nullable'
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'fact_economic_event'
  AND column_name = 'raw_payload';
-- Esperado: is_nullable = 'YES'

-- ----------------------------------------------------------------------------
-- 3. Verificar que las tablas de auditoría existen
-- ----------------------------------------------------------------------------
\echo '=> [04] Verificación: tablas de auditoría'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('audit_sync_run', 'sync_checkpoint')
ORDER BY table_name;
-- Esperado: 2 filas

-- ----------------------------------------------------------------------------
-- 4. Confirmar raw_payload nullable en fact_market_series (radar V4)
-- ----------------------------------------------------------------------------
\echo '=> [04] Verificación: fact_market_series.raw_payload nullable'
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'fact_market_series'
  AND column_name = 'raw_payload';
-- Esperado: is_nullable = 'YES'

\echo '=> [04] Migración v3.1.0 finalizada'
-- ============================================================================
-- FIN migración v3.1.0
-- ============================================================================
