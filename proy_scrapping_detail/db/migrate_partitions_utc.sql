-- ============================================================================
-- F2.3 · Migración de particiones a fronteras UTC (00:00+00)
-- Generado el 2026-09-22 por generate_migrate_partitions_utc.py
-- Backup previo: /tmp/opencode/backup_f2/heatmap_stock_pre_F2.3_20260922_224433.dump
-- Ejecutar con: docker exec -i pg_db psql -U postgres heatmap_stock < migrate_partitions_utc.sql
-- ============================================================================
BEGIN;
SET search_path = public;

-- ###########################################################################
-- fact_market_series
-- ###########################################################################
-- partición existente fact_market_series_2026_03 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_03;
ALTER TABLE fact_market_series_2026_03 RENAME TO fact_market_series_2026_03_legacy;
CREATE TABLE fact_market_series_2026_03 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_03_pkey ON fact_market_series_2026_03 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_03_timestamp_utc_idx ON fact_market_series_2026_03 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_03_close_idx ON fact_market_series_2026_03 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_03_rsi_idx ON fact_market_series_2026_03 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_03_timezone_idx ON fact_market_series_2026_03 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_03_ts_brin ON fact_market_series_2026_03 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_03_legacy;
DROP TABLE fact_market_series_2026_03_legacy;

-- partición existente fact_market_series_2026_04 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_04;
ALTER TABLE fact_market_series_2026_04 RENAME TO fact_market_series_2026_04_legacy;
CREATE TABLE fact_market_series_2026_04 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_04_pkey ON fact_market_series_2026_04 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_04_timestamp_utc_idx ON fact_market_series_2026_04 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_04_close_idx ON fact_market_series_2026_04 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_04_rsi_idx ON fact_market_series_2026_04 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_04_timezone_idx ON fact_market_series_2026_04 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_04_ts_brin ON fact_market_series_2026_04 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_04_legacy;
DROP TABLE fact_market_series_2026_04_legacy;

-- partición existente fact_market_series_2026_05 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_05;
ALTER TABLE fact_market_series_2026_05 RENAME TO fact_market_series_2026_05_legacy;
CREATE TABLE fact_market_series_2026_05 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_05_pkey ON fact_market_series_2026_05 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_05_timestamp_utc_idx ON fact_market_series_2026_05 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_05_close_idx ON fact_market_series_2026_05 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_05_rsi_idx ON fact_market_series_2026_05 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_05_timezone_idx ON fact_market_series_2026_05 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_05_ts_brin ON fact_market_series_2026_05 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_05_legacy;
DROP TABLE fact_market_series_2026_05_legacy;

-- partición existente fact_market_series_2026_06 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_06;
ALTER TABLE fact_market_series_2026_06 RENAME TO fact_market_series_2026_06_legacy;
CREATE TABLE fact_market_series_2026_06 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_06_pkey ON fact_market_series_2026_06 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_06_timestamp_utc_idx ON fact_market_series_2026_06 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_06_close_idx ON fact_market_series_2026_06 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_06_rsi_idx ON fact_market_series_2026_06 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_06_timezone_idx ON fact_market_series_2026_06 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_06_ts_brin ON fact_market_series_2026_06 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_06_legacy;
DROP TABLE fact_market_series_2026_06_legacy;

-- partición existente fact_market_series_2026_07 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_07;
ALTER TABLE fact_market_series_2026_07 RENAME TO fact_market_series_2026_07_legacy;
CREATE TABLE fact_market_series_2026_07 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_07_pkey ON fact_market_series_2026_07 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_07_timestamp_utc_idx ON fact_market_series_2026_07 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_07_close_idx ON fact_market_series_2026_07 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_07_rsi_idx ON fact_market_series_2026_07 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_07_timezone_idx ON fact_market_series_2026_07 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_07_ts_brin ON fact_market_series_2026_07 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_07_legacy;
DROP TABLE fact_market_series_2026_07_legacy;

-- partición existente fact_market_series_2026_08 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_08;
ALTER TABLE fact_market_series_2026_08 RENAME TO fact_market_series_2026_08_legacy;
CREATE TABLE fact_market_series_2026_08 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_08_pkey ON fact_market_series_2026_08 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_08_timestamp_utc_idx ON fact_market_series_2026_08 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_08_close_idx ON fact_market_series_2026_08 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_08_rsi_idx ON fact_market_series_2026_08 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_08_timezone_idx ON fact_market_series_2026_08 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_08_ts_brin ON fact_market_series_2026_08 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_08_legacy;
DROP TABLE fact_market_series_2026_08_legacy;

-- partición existente fact_market_series_2026_09 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_09;
ALTER TABLE fact_market_series_2026_09 RENAME TO fact_market_series_2026_09_legacy;
CREATE TABLE fact_market_series_2026_09 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_09_pkey ON fact_market_series_2026_09 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_09_timestamp_utc_idx ON fact_market_series_2026_09 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_09_close_idx ON fact_market_series_2026_09 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_09_rsi_idx ON fact_market_series_2026_09 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_09_timezone_idx ON fact_market_series_2026_09 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_09_ts_brin ON fact_market_series_2026_09 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_09_legacy;
DROP TABLE fact_market_series_2026_09_legacy;

-- partición existente fact_market_series_2026_10 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_10;
ALTER TABLE fact_market_series_2026_10 RENAME TO fact_market_series_2026_10_legacy;
CREATE TABLE fact_market_series_2026_10 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_10_pkey ON fact_market_series_2026_10 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_10_timestamp_utc_idx ON fact_market_series_2026_10 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_10_close_idx ON fact_market_series_2026_10 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_10_rsi_idx ON fact_market_series_2026_10 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_10_timezone_idx ON fact_market_series_2026_10 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_10_ts_brin ON fact_market_series_2026_10 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_10_legacy;
DROP TABLE fact_market_series_2026_10_legacy;

-- partición existente fact_market_series_2026_11 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_11;
ALTER TABLE fact_market_series_2026_11 RENAME TO fact_market_series_2026_11_legacy;
CREATE TABLE fact_market_series_2026_11 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_11_pkey ON fact_market_series_2026_11 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_11_timestamp_utc_idx ON fact_market_series_2026_11 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_11_close_idx ON fact_market_series_2026_11 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_11_rsi_idx ON fact_market_series_2026_11 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_11_timezone_idx ON fact_market_series_2026_11 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_11_ts_brin ON fact_market_series_2026_11 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_11_legacy;
DROP TABLE fact_market_series_2026_11_legacy;

-- partición existente fact_market_series_2026_12 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_market_series DETACH PARTITION fact_market_series_2026_12;
ALTER TABLE fact_market_series_2026_12 RENAME TO fact_market_series_2026_12_legacy;
CREATE TABLE fact_market_series_2026_12 PARTITION OF fact_market_series
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2026_12_pkey ON fact_market_series_2026_12 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2026_12_timestamp_utc_idx ON fact_market_series_2026_12 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2026_12_close_idx ON fact_market_series_2026_12 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2026_12_rsi_idx ON fact_market_series_2026_12 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2026_12_timezone_idx ON fact_market_series_2026_12 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2026_12_ts_brin ON fact_market_series_2026_12 USING brin (timestamp_utc);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_market_series SELECT * FROM fact_market_series_2026_12_legacy;
DROP TABLE fact_market_series_2026_12_legacy;

CREATE TABLE fact_market_series_2027_01 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-01-01 00:00:00+00') TO ('2027-02-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_01_pkey ON fact_market_series_2027_01 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_01_timestamp_utc_idx ON fact_market_series_2027_01 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_01_close_idx ON fact_market_series_2027_01 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_01_rsi_idx ON fact_market_series_2027_01 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_01_timezone_idx ON fact_market_series_2027_01 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_01_ts_brin ON fact_market_series_2027_01 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_02 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-02-01 00:00:00+00') TO ('2027-03-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_02_pkey ON fact_market_series_2027_02 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_02_timestamp_utc_idx ON fact_market_series_2027_02 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_02_close_idx ON fact_market_series_2027_02 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_02_rsi_idx ON fact_market_series_2027_02 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_02_timezone_idx ON fact_market_series_2027_02 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_02_ts_brin ON fact_market_series_2027_02 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_03 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-03-01 00:00:00+00') TO ('2027-04-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_03_pkey ON fact_market_series_2027_03 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_03_timestamp_utc_idx ON fact_market_series_2027_03 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_03_close_idx ON fact_market_series_2027_03 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_03_rsi_idx ON fact_market_series_2027_03 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_03_timezone_idx ON fact_market_series_2027_03 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_03_ts_brin ON fact_market_series_2027_03 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_04 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-04-01 00:00:00+00') TO ('2027-05-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_04_pkey ON fact_market_series_2027_04 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_04_timestamp_utc_idx ON fact_market_series_2027_04 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_04_close_idx ON fact_market_series_2027_04 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_04_rsi_idx ON fact_market_series_2027_04 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_04_timezone_idx ON fact_market_series_2027_04 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_04_ts_brin ON fact_market_series_2027_04 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_05 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-05-01 00:00:00+00') TO ('2027-06-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_05_pkey ON fact_market_series_2027_05 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_05_timestamp_utc_idx ON fact_market_series_2027_05 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_05_close_idx ON fact_market_series_2027_05 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_05_rsi_idx ON fact_market_series_2027_05 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_05_timezone_idx ON fact_market_series_2027_05 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_05_ts_brin ON fact_market_series_2027_05 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_06 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-06-01 00:00:00+00') TO ('2027-07-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_06_pkey ON fact_market_series_2027_06 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_06_timestamp_utc_idx ON fact_market_series_2027_06 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_06_close_idx ON fact_market_series_2027_06 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_06_rsi_idx ON fact_market_series_2027_06 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_06_timezone_idx ON fact_market_series_2027_06 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_06_ts_brin ON fact_market_series_2027_06 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_07 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-07-01 00:00:00+00') TO ('2027-08-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_07_pkey ON fact_market_series_2027_07 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_07_timestamp_utc_idx ON fact_market_series_2027_07 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_07_close_idx ON fact_market_series_2027_07 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_07_rsi_idx ON fact_market_series_2027_07 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_07_timezone_idx ON fact_market_series_2027_07 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_07_ts_brin ON fact_market_series_2027_07 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_08 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-08-01 00:00:00+00') TO ('2027-09-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_08_pkey ON fact_market_series_2027_08 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_08_timestamp_utc_idx ON fact_market_series_2027_08 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_08_close_idx ON fact_market_series_2027_08 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_08_rsi_idx ON fact_market_series_2027_08 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_08_timezone_idx ON fact_market_series_2027_08 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_08_ts_brin ON fact_market_series_2027_08 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_09 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-09-01 00:00:00+00') TO ('2027-10-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_09_pkey ON fact_market_series_2027_09 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_09_timestamp_utc_idx ON fact_market_series_2027_09 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_09_close_idx ON fact_market_series_2027_09 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_09_rsi_idx ON fact_market_series_2027_09 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_09_timezone_idx ON fact_market_series_2027_09 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_09_ts_brin ON fact_market_series_2027_09 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_10 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-10-01 00:00:00+00') TO ('2027-11-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_10_pkey ON fact_market_series_2027_10 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_10_timestamp_utc_idx ON fact_market_series_2027_10 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_10_close_idx ON fact_market_series_2027_10 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_10_rsi_idx ON fact_market_series_2027_10 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_10_timezone_idx ON fact_market_series_2027_10 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_10_ts_brin ON fact_market_series_2027_10 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_11 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-11-01 00:00:00+00') TO ('2027-12-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_11_pkey ON fact_market_series_2027_11 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_11_timestamp_utc_idx ON fact_market_series_2027_11 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_11_close_idx ON fact_market_series_2027_11 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_11_rsi_idx ON fact_market_series_2027_11 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_11_timezone_idx ON fact_market_series_2027_11 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_11_ts_brin ON fact_market_series_2027_11 USING brin (timestamp_utc);

CREATE TABLE fact_market_series_2027_12 PARTITION OF fact_market_series
    FOR VALUES FROM ('2027-12-01 00:00:00+00') TO ('2028-01-01 00:00:00+00');
CREATE UNIQUE INDEX fact_market_series_2027_12_pkey ON fact_market_series_2027_12 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_market_series_2027_12_timestamp_utc_idx ON fact_market_series_2027_12 USING btree (timestamp_utc DESC);
CREATE INDEX fact_market_series_2027_12_close_idx ON fact_market_series_2027_12 USING btree (close) WHERE (close IS NOT NULL);
CREATE INDEX fact_market_series_2027_12_rsi_idx ON fact_market_series_2027_12 USING btree (rsi) WHERE (rsi IS NOT NULL);
CREATE INDEX fact_market_series_2027_12_timezone_idx ON fact_market_series_2027_12 USING btree ((((timestamp_utc AT TIME ZONE 'UTC'::text))::date));
CREATE INDEX fact_market_series_2027_12_ts_brin ON fact_market_series_2027_12 USING brin (timestamp_utc);


-- ###########################################################################
-- fact_heatmap_snapshot
-- ###########################################################################
-- partición existente fact_heatmap_snapshot_2026_09 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_heatmap_snapshot DETACH PARTITION fact_heatmap_snapshot_2026_09;
ALTER TABLE fact_heatmap_snapshot_2026_09 RENAME TO fact_heatmap_snapshot_2026_09_legacy;
CREATE TABLE fact_heatmap_snapshot_2026_09 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2026_09_pkey ON fact_heatmap_snapshot_2026_09 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2026_09_timestamp_utc_idx ON fact_heatmap_snapshot_2026_09 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2026_09_daily_change_pct_idx ON fact_heatmap_snapshot_2026_09 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_09_market_cap_idx ON fact_heatmap_snapshot_2026_09 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_09_raw_vector_idx ON fact_heatmap_snapshot_2026_09 USING gin (raw_vector);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_heatmap_snapshot SELECT * FROM fact_heatmap_snapshot_2026_09_legacy;
DROP TABLE fact_heatmap_snapshot_2026_09_legacy;

-- partición existente fact_heatmap_snapshot_2026_10 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_heatmap_snapshot DETACH PARTITION fact_heatmap_snapshot_2026_10;
ALTER TABLE fact_heatmap_snapshot_2026_10 RENAME TO fact_heatmap_snapshot_2026_10_legacy;
CREATE TABLE fact_heatmap_snapshot_2026_10 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2026_10_pkey ON fact_heatmap_snapshot_2026_10 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2026_10_timestamp_utc_idx ON fact_heatmap_snapshot_2026_10 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2026_10_daily_change_pct_idx ON fact_heatmap_snapshot_2026_10 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_10_market_cap_idx ON fact_heatmap_snapshot_2026_10 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_10_raw_vector_idx ON fact_heatmap_snapshot_2026_10 USING gin (raw_vector);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_heatmap_snapshot SELECT * FROM fact_heatmap_snapshot_2026_10_legacy;
DROP TABLE fact_heatmap_snapshot_2026_10_legacy;

-- partición existente fact_heatmap_snapshot_2026_11 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_heatmap_snapshot DETACH PARTITION fact_heatmap_snapshot_2026_11;
ALTER TABLE fact_heatmap_snapshot_2026_11 RENAME TO fact_heatmap_snapshot_2026_11_legacy;
CREATE TABLE fact_heatmap_snapshot_2026_11 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2026_11_pkey ON fact_heatmap_snapshot_2026_11 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2026_11_timestamp_utc_idx ON fact_heatmap_snapshot_2026_11 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2026_11_daily_change_pct_idx ON fact_heatmap_snapshot_2026_11 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_11_market_cap_idx ON fact_heatmap_snapshot_2026_11 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_11_raw_vector_idx ON fact_heatmap_snapshot_2026_11 USING gin (raw_vector);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_heatmap_snapshot SELECT * FROM fact_heatmap_snapshot_2026_11_legacy;
DROP TABLE fact_heatmap_snapshot_2026_11_legacy;

-- partición existente fact_heatmap_snapshot_2026_12 (límites -05): DETACH + rename + recreate
ALTER TABLE fact_heatmap_snapshot DETACH PARTITION fact_heatmap_snapshot_2026_12;
ALTER TABLE fact_heatmap_snapshot_2026_12 RENAME TO fact_heatmap_snapshot_2026_12_legacy;
CREATE TABLE fact_heatmap_snapshot_2026_12 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2026_12_pkey ON fact_heatmap_snapshot_2026_12 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2026_12_timestamp_utc_idx ON fact_heatmap_snapshot_2026_12 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2026_12_daily_change_pct_idx ON fact_heatmap_snapshot_2026_12 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_12_market_cap_idx ON fact_heatmap_snapshot_2026_12 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2026_12_raw_vector_idx ON fact_heatmap_snapshot_2026_12 USING gin (raw_vector);
-- 3) la madre enruta cada fila por timestamp_utc (00:00 UTC)
INSERT INTO fact_heatmap_snapshot SELECT * FROM fact_heatmap_snapshot_2026_12_legacy;
DROP TABLE fact_heatmap_snapshot_2026_12_legacy;

CREATE TABLE fact_heatmap_snapshot_2027_01 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-01-01 00:00:00+00') TO ('2027-02-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_01_pkey ON fact_heatmap_snapshot_2027_01 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_01_timestamp_utc_idx ON fact_heatmap_snapshot_2027_01 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_01_daily_change_pct_idx ON fact_heatmap_snapshot_2027_01 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_01_market_cap_idx ON fact_heatmap_snapshot_2027_01 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_01_raw_vector_idx ON fact_heatmap_snapshot_2027_01 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_02 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-02-01 00:00:00+00') TO ('2027-03-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_02_pkey ON fact_heatmap_snapshot_2027_02 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_02_timestamp_utc_idx ON fact_heatmap_snapshot_2027_02 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_02_daily_change_pct_idx ON fact_heatmap_snapshot_2027_02 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_02_market_cap_idx ON fact_heatmap_snapshot_2027_02 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_02_raw_vector_idx ON fact_heatmap_snapshot_2027_02 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_03 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-03-01 00:00:00+00') TO ('2027-04-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_03_pkey ON fact_heatmap_snapshot_2027_03 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_03_timestamp_utc_idx ON fact_heatmap_snapshot_2027_03 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_03_daily_change_pct_idx ON fact_heatmap_snapshot_2027_03 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_03_market_cap_idx ON fact_heatmap_snapshot_2027_03 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_03_raw_vector_idx ON fact_heatmap_snapshot_2027_03 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_04 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-04-01 00:00:00+00') TO ('2027-05-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_04_pkey ON fact_heatmap_snapshot_2027_04 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_04_timestamp_utc_idx ON fact_heatmap_snapshot_2027_04 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_04_daily_change_pct_idx ON fact_heatmap_snapshot_2027_04 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_04_market_cap_idx ON fact_heatmap_snapshot_2027_04 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_04_raw_vector_idx ON fact_heatmap_snapshot_2027_04 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_05 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-05-01 00:00:00+00') TO ('2027-06-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_05_pkey ON fact_heatmap_snapshot_2027_05 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_05_timestamp_utc_idx ON fact_heatmap_snapshot_2027_05 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_05_daily_change_pct_idx ON fact_heatmap_snapshot_2027_05 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_05_market_cap_idx ON fact_heatmap_snapshot_2027_05 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_05_raw_vector_idx ON fact_heatmap_snapshot_2027_05 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_06 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-06-01 00:00:00+00') TO ('2027-07-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_06_pkey ON fact_heatmap_snapshot_2027_06 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_06_timestamp_utc_idx ON fact_heatmap_snapshot_2027_06 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_06_daily_change_pct_idx ON fact_heatmap_snapshot_2027_06 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_06_market_cap_idx ON fact_heatmap_snapshot_2027_06 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_06_raw_vector_idx ON fact_heatmap_snapshot_2027_06 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_07 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-07-01 00:00:00+00') TO ('2027-08-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_07_pkey ON fact_heatmap_snapshot_2027_07 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_07_timestamp_utc_idx ON fact_heatmap_snapshot_2027_07 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_07_daily_change_pct_idx ON fact_heatmap_snapshot_2027_07 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_07_market_cap_idx ON fact_heatmap_snapshot_2027_07 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_07_raw_vector_idx ON fact_heatmap_snapshot_2027_07 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_08 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-08-01 00:00:00+00') TO ('2027-09-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_08_pkey ON fact_heatmap_snapshot_2027_08 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_08_timestamp_utc_idx ON fact_heatmap_snapshot_2027_08 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_08_daily_change_pct_idx ON fact_heatmap_snapshot_2027_08 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_08_market_cap_idx ON fact_heatmap_snapshot_2027_08 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_08_raw_vector_idx ON fact_heatmap_snapshot_2027_08 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_09 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-09-01 00:00:00+00') TO ('2027-10-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_09_pkey ON fact_heatmap_snapshot_2027_09 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_09_timestamp_utc_idx ON fact_heatmap_snapshot_2027_09 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_09_daily_change_pct_idx ON fact_heatmap_snapshot_2027_09 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_09_market_cap_idx ON fact_heatmap_snapshot_2027_09 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_09_raw_vector_idx ON fact_heatmap_snapshot_2027_09 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_10 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-10-01 00:00:00+00') TO ('2027-11-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_10_pkey ON fact_heatmap_snapshot_2027_10 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_10_timestamp_utc_idx ON fact_heatmap_snapshot_2027_10 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_10_daily_change_pct_idx ON fact_heatmap_snapshot_2027_10 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_10_market_cap_idx ON fact_heatmap_snapshot_2027_10 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_10_raw_vector_idx ON fact_heatmap_snapshot_2027_10 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_11 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-11-01 00:00:00+00') TO ('2027-12-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_11_pkey ON fact_heatmap_snapshot_2027_11 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_11_timestamp_utc_idx ON fact_heatmap_snapshot_2027_11 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_11_daily_change_pct_idx ON fact_heatmap_snapshot_2027_11 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_11_market_cap_idx ON fact_heatmap_snapshot_2027_11 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_11_raw_vector_idx ON fact_heatmap_snapshot_2027_11 USING gin (raw_vector);

CREATE TABLE fact_heatmap_snapshot_2027_12 PARTITION OF fact_heatmap_snapshot
    FOR VALUES FROM ('2027-12-01 00:00:00+00') TO ('2028-01-01 00:00:00+00');
CREATE UNIQUE INDEX fact_heatmap_snapshot_2027_12_pkey ON fact_heatmap_snapshot_2027_12 USING btree (asset_id, timestamp_utc);
CREATE INDEX fact_heatmap_snapshot_2027_12_timestamp_utc_idx ON fact_heatmap_snapshot_2027_12 USING btree (timestamp_utc DESC);
CREATE INDEX fact_heatmap_snapshot_2027_12_daily_change_pct_idx ON fact_heatmap_snapshot_2027_12 USING btree (daily_change_pct) WHERE (daily_change_pct IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_12_market_cap_idx ON fact_heatmap_snapshot_2027_12 USING btree (market_cap DESC) WHERE (market_cap IS NOT NULL);
CREATE INDEX fact_heatmap_snapshot_2027_12_raw_vector_idx ON fact_heatmap_snapshot_2027_12 USING gin (raw_vector);


-- ============================================================================
-- Verificación final (A5): límites contiguos a 00:00+00
-- ============================================================================

SELECT pa.relname AS tabla, ch.relname AS particion,
       pg_get_expr(ch.relpartbound, ch.oid) AS bounds
FROM pg_class ch
JOIN pg_namespace n ON n.oid = ch.relnamespace
JOIN pg_inherits i ON i.inhrelid = ch.oid
JOIN pg_class pa ON i.inhparent = pa.oid
WHERE n.nspname='public'
  AND pa.relname IN ('fact_market_series','fact_heatmap_snapshot')
ORDER BY pa.relname, ch.relname;

-- Alerta: partición del mes siguiente ausente (debe existir AL MENOS el mes+1)
SELECT 'ALERTA: falta partición ' || to_char((CURRENT_DATE + INTERVAL '1 month'), 'YYYY_MM')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname='public'
      AND c.relname = 'fact_market_series_' || to_char((CURRENT_DATE + INTERVAL '1 month'), 'YYYY_MM')
);


COMMIT;
