# Roadmap — proy_bd_heatmap (Alembic) — 2026-09-23

> Control de versiones del esquema PostgreSQL `heatmap_stock` con **Alembic**.
> Objetivo: convertir los scripts SQL sueltos en un historial versionado,
> reproducible y con rollback, integrado al ecosistema heatmap_stock.

## 1. Objetivo y motivación

Hoy el esquema se mantiene con scripts SQL dispersos:
`proy_heatmap/scripts/*.sql`, `proy_scrapping_detail/db/*.sql`, DDL generados
por Python (`create_dim_trading_session.py`, `create_partitions.py`,
`partitions.py`) y cambios aplicados a mano contra la BD viva.

Problemas actuales:

| Problema | Efecto |
|---|---|
| Sin historial versionado | No se sabe exactamente qué cambios se aplicaron ni en qué orden |
| Sin rollback | Un DDL erróneo no se puede revertir de forma segura |
| Doble fuente de verdad | `02_init_database.sql` se desvía de la BD real (drift) |
| Particiones con convenciones mixtas | `fact_market_series`/`fact_heatmap_snapshot` a `-05`, `fact_market_bar_15m` a `00:00+00` (F2.3 pendiente) |
| Onboarding lento | Levantar una BD desde cero requiere ejecutar scripts en el orden correcto a mano |

Alembic resuelve esto: cada cambio de esquema es una **revisión** versionada,
con `upgrade()`/`downgrade()`; la BD queda siempre en un estado conocido
(`alembic current`), y una BD nueva se construye con un solo comando
(`alembic upgrade head`).

## 2. Estado actual de la BD (`heatmap_stock`, PostgreSQL 17.10)

Inventario medido el 2026-09-23:

**Tablas base (10):** `dim_asset`, `dim_country`, `dim_time`,
`dim_trading_session`, `fact_market_series`, `fact_heatmap_snapshot`,
`fact_economic_event`, `fact_market_bar_15m`, `audit_sync_run`,
`sync_checkpoint`.

**Particiones (27):**

| Tabla madre | Particiones | Frontera |
|---|---|---|
| `fact_market_series` | 2026_03 → 2026_12 (10) | `-05` (legacy, F2.3 pendiente) |
| `fact_heatmap_snapshot` | 2026_09 → 2026_12 (4) | `-05` (legacy) |
| `fact_market_bar_15m` | 2026_09 → 2027_12 (16) | `00:00+00` (UTC) |

**Vistas (3):** `vw_heatmap_enriched`, `vw_heatmap_event_impact`,
`vw_market_live`.

**Funciones (2):** `upsert_heatmap_snapshot`, `upsert_market_series`.

**Extensiones (2):** `plpgsql` (builtin), `pg_trgm` 1.6.

**Secuencias (3):** `dim_asset_asset_id_seq`, `audit_sync_run_run_id_seq`,
`sync_checkpoint_checkpoint_id_seq`.

**Datos (pg_stat_user_tables):**

| Tabla | Filas |
|---|---|
| `fact_heatmap_snapshot_2026_09` | 7.000 |
| `dim_asset` | 1.669 |
| `fact_economic_event` | 699 |
| `fact_market_series_2026_09` | 647 |
| `dim_trading_session` | 630 |
| `audit_sync_run` | 28 |
| `sync_checkpoint` | 1 |

## 3. Ventajas del enfoque baseline

Un **baseline** es la primera migración que fija el esquema tal como está
hoy, para que alembic "arranque" desde un estado conocido. Ventajas:

1. **Cero drift** — se genera con `pg_dump --schema-only` de la BD viva y se
   embebe vía `op.execute`: es una foto exacta (tablas, particiones, índices,
   constraints, funciones, vistas, extensión, comentarios), sin reescritura
   manual que pueda omitir algo.
2. **Autogenerate no captura todo** — `alembic revision --autogenerate` no
   maneja correctamente funciones, vistas, extensiones, CHECK constraints ni
   el `pg_get_expr` de las particiones; el baseline embebido sí las conserva.
3. **Adopción no destructiva** — la BD real ya tiene el esquema: se marca con
   `alembic stamp head` (no re-ejecuta DDL sobre datos vivos).
4. **Reproducible** — una BD nueva (scratch/test/staging) se construye con
   `alembic upgrade head` y queda idéntica a producción.
5. **Verificable** — `pg_dump --schema-only` de scratch vs producción debe ser
   idéntico (salvo owner/search_path), cerrando la prueba del baseline.
6. **Rollback completo** — el `downgrade()` revierte en orden inverso
   (vistas → funciones → extensión → particiones → tablas → secuencias).

## 4. Diseño del proyecto `proy_bd_heatmap/`

```
proy_bd_heatmap/
├── alembic.ini              # sqlalchemy.url vacío; URL se arma en env.py
├── requirements.txt         # alembic, psycopg2-binary, python-dotenv
├── .env                     # BD_HEATMAP_* (gitignored)
├── .env.example             # plantilla committed
├── README.md                # cómo migrar, correr, importancia
├── venv/                    # venv propio (Python 3.13) — gitignored
└── alembic/
    ├── env.py               # carga .env, arma URL, target_metadata=None
    ├── script.py.mako
    └── versions/
        ├── 0001_baseline_2026_09_23.py
        ├── 0002_seed_catalogos_2026_09_23.py
        ├── 0003_fact_market_indicator_tf_2026_09_23.py
        ├── 0004_latest_market_tick_2026_09_23.py
        ├── 0005_fact_heatmap_snapshot_columnas_2026_09_23.py
        └── 0006_dim_asset_mapeo_canonico_2026_09_23.py
```

**Decisiones de diseño:**

- **Venv propio** en `proy_bd_heatmap/venv` (Python 3.13.14), independiente de
  los otros proyectos del ecosistema.
- **`env.py`** lee `BD_HEATMAP_*` del `.env` local y compone la URL
  `postgresql://user:pass@host:port/db`. `target_metadata = None`: las
  revisiones son DDL explícito (no autogenerate sobre metadata de modelos).
- **Baseline embebido** desde `pg_dump --schema-only` (ver §3).

## 5. Fases de ejecución

### F0 · Bootstrap
- Instalar alembic en `proy_bd_heatmap/venv`.
- `alembic init alembic` + personalizar `env.py`, `alembic.ini`,
  `requirements.txt`, `.env`/`.env.example`.

### F1 · Baseline
- Capturar `pg_dump --schema-only` de la BD viva.
- Generar `0001_baseline_2026_09_23.py` con `upgrade()` (DDL embebido) y
  `downgrade()` (reverso).

### F2 · Adopción y verificación
- Crear BD scratch (ej. `heatmap_stock_test`), `alembic upgrade head`.
- Comparar `pg_dump --schema-only` scratch vs producción → idéntico.
- Marcar producción con `alembic stamp head`.

### F3 · Seed de catálogos (dimensiones)
- Cargar en **revisiones seed separadas** (o script idempotente bajo alembic):
  - `dim_asset` (1.669 símbolos) — origen: `seed_symbols.py` + `seed_dim_asset.py`.
  - `dim_time` (2026–2027) — origen: `seed_dim_asset.py`.
  - `dim_trading_session` (630 días) — origen: `create_dim_trading_session.py`.
- **Decisión:** el baseline F1 contiene SOLO esquema; el seed va en
  revisiones/scripts posteriores idempotentes (no mezclar DDL con datos).

### F4 · Flujo de trabajo hacia adelante
- Toda migración nueva del ecosistema pasa por alembic:
  - ✅ **F4.2 `fact_market_indicator_tf`** → revisión **`0003`**
    (implementada 2026-09-23, aplicada en `heatmap_stock`).
  - ✅ **F4.3 `latest_market_tick`** → revisión **`0004`** (idem).
  - ✅ **F4.4 columnas explícitas de `fact_heatmap_snapshot`** → revisión
    **`0005`** (idem; ALTER sobre padre particionado propaga a particiones).
  - ✅ **F4.5/F4.5b `dim_asset` SCD2 → Tipo 1 + mapeo canónico** → revisión
    **`0006`** (aplicada 2026-09-23 en `heatmap_stock`): `dim_asset` pasa a
    Tipo 1 (se dropean `valid_from`, `valid_to`, `current_version`) y se añaden
    `logical_key`, `is_canonical`, `role`, `feed_delay_s`; mapeo canónico de las
    6 claves lógicas F2.5 (VIX|DXY|TLT|US10Y|ORO|OIL) con alta de `TVC:DXY`;
    índice único parcial `uq_dim_asset_canonical_logical_key` (1 canónico por
    clave); funciones/vistas/índices reconstruidos sin `current_version`;
    `idx_dim_asset_symbol` (duplicado) eliminado. `dim_asset`: 1.668 → 1.669.
  - F4.1 `fact_market_bar_15m` no requiere DDL nuevo (agregación sobre tablas
    ya existentes; particiones se crean en runtime). Se materializa con el job
    `scripts/build_market_bar_15m.py` sin revisión propia.
  - **🛑 F4.7 descartado (2026-09-23, directiva del usuario):** se obvian los
    **históricos**; el ecosistema **inicia desde cero con BD en blanco**
    (`alembic upgrade head` sobre una BD nueva). El reempaquetado de CSV a
    `fact_daily_context`/barras retroactivas **no se construye**; no requiere
    revisión alembic.
  - **F4.8 ✅** suite nocturna de calidad = **script independiente**
    `scripts/suite_calidad_nocturna.py` (cron; solo psycopg2 + python-dotenv),
    sin revisión alembic. Detalle en el README (§ F4.8).
  - F2.3 particiones a fronteras UTC (`fact_market_series`,
    `fact_heatmap_snapshot`).

## 6. Criterios de salida

1. `alembic current` en producción = `head` (sin migraciones pendientes).
2. `alembic upgrade head` en BD scratch → `pg_dump --schema-only` idéntico a
   producción (salvo owner/search_path).
3. `alembic history` muestra la cadena completa de revisiones.
4. README documenta migrar/correr y los scripts legacy quedan como referencia
   histórica.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Rol BD sin permisos para `CREATE EXTENSION` / `pg_trgm` | Documentar en README; ejecutar upgrade con rol con privilegios |
| Migraciones que tocan datos | Separar DDL (revisiones) de seed (scripts idempotentes) |
| Drift entre alembic y scripts legacy | Alembic pasa a ser la única fuente de verdad; legacy se congela |
| Baseline embebido con DDL no idempotente | El baseline se ejecuta una sola vez (alembic lo marca); la verificación scratch lo valida |
| Fronteras de particiones mixtas (`-05` vs UTC) | F2.3 se convierte en migración alembic dedicada |