-- ============================================================================
-- Migración v1.0.3 — slug y url_logo en dim_asset
-- Fecha: 2026-09-18
-- Proyecto: proy_heatmap (heatmap_stock)
-- ============================================================================
-- Agrega a dim_asset:
--   1. slug      : identificador de archivo para el icono del activo
--                  (símbolo sin caracteres especiales, ej. "nasdaq_nvda")
--   2. url_logo  : URL remota del logo (TradingView, ej. .../{logoid}.svg)
--
-- El poblado lo realiza el script download_iconos_mercado.py.
-- ============================================================================

\echo '=> [08] Iniciando migración v1.0.3 (slug y url_logo)'

BEGIN;

ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS slug     TEXT;

ALTER TABLE dim_asset
    ADD COLUMN IF NOT EXISTS url_logo TEXT;

COMMENT ON COLUMN dim_asset.slug    IS 'Símbolo en slug (sin ":" ni ".") para nombrar el icono, ej. "nasdaq_nvda".';
COMMENT ON COLUMN dim_asset.url_logo IS 'URL remota del logo del activo (TradingView), NULL si no se resolvió.';

CREATE INDEX IF NOT EXISTS idx_dim_asset_slug ON dim_asset (slug);

COMMIT;

\echo '=> [08] Verificación: columnas dim_asset'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'dim_asset'
  AND column_name IN ('slug', 'url_logo')
ORDER BY column_name;

\echo '=> [08] Migración v1.0.3 finalizada'