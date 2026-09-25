# proy_bd_heatmap — Migraciones de base de datos con Alembic

Control de versiones del esquema PostgreSQL **`heatmap_stock`** del ecosistema
heatmap_stock (radar, calendario, heatmap) usando **Alembic**.

> Fuente única de verdad del esquema hacia adelante. Los scripts SQL legacy
> (`proy_heatmap/scripts/*.sql`, `proy_scrapping_detail/db/*.sql`) quedan como
> referencia histórica; todo cambio de esquema nuevo debe ser una revisión
> alembic.

---

## Importancia para el ecosistema

| Beneficio | Detalle |
|---|---|
| Historial versionado | Cada cambio de esquema es una revisión con `upgrade()`/`downgrade()`; se sabe exactamente qué cambió, cuándo y en qué orden (`alembic history`) |
| Reproducible | Una BD nueva (scratch/test/staging) se construye con un solo comando: `alembic upgrade head` |
| Rollback | `alembic downgrade` revierte migraciones de forma segura |
| Cero drift | El baseline se generó desde `pg_dump --schema-only` de la BD viva: el esquema de la BD real quedó congelado fielmente |
| Adopción no destructiva | La BD existente se marcó con `alembic stamp head` sin re-ejecutar DDL sobre datos vivos |
| Desbloquea fases | F2.3 (particiones UTC) pendiente; F4.2→`0003`, F4.3→`0004`, F4.4→`0005` y F4.5/F4.5b→`0006` ya están |

---

## Requisitos

- Python 3.13 (venv propio en `venv/`)
- PostgreSQL 17 (Docker: contenedor `pg_db`, imagen `postgres:17-bookworm`)
- Dependencias: `requirements.txt` (alembic, psycopg2-binary, python-dotenv)

## Instalación

```bash
cd proy_bd_heatmap
./venv/bin/pip install -r requirements.txt

# Configurar credenciales (gitignored)
cp .env.example .env
# editar .env con BD_HEATMAP_HOST/PORT/DATABASE/USER/PASSWORD
```

## Estructura

```
proy_bd_heatmap/
├── alembic.ini                    # configuración (script_location, logging)
├── requirements.txt
├── .env / .env.example            # credenciales BD (BD_HEATMAP_*)
├── README.md
├── scripts/
│   ├── generar_baseline.py        # F1 · regenera la migración 0001 (pg_dump)
│   ├── generar_seed_catalogos.py  # F3 · regenera la migración 0002 (seed)
│   └── suite_calidad_nocturna.py  # F4.8 · suite nocturna de calidad (cron)
├── tests/test_migraciones.py      # suite de pruebas de las migraciones
└── alembic/
    ├── env.py                     # arma la URL desde .env; target_metadata=None
    ├── script.py.mako
    └── versions/
        ├── 0001_baseline_2026_09_23.py           # esquema completo (DDL)
        ├── 0002_seed_catalogos_2026_09_23.py     # seed dim_asset/dim_time/dim_trading_session
        ├── 0003_fact_market_indicator_tf_2026_09_23.py  # F4.2 · tabla larga multi-TF
        ├── 0004_latest_market_tick_2026_09_23.py        # F4.3 · último tick por activo
        ├── 0005_fact_heatmap_snapshot_columnas_2026_09_23.py  # F4.4 · snapshots columnas explícitas
        └── 0006_dim_asset_mapeo_canonico_2026_09_23.py  # F4.5/F4.5b · dim_asset Tipo 1 + mapeo canónico
```

---

## Cómo migrar

Todos los comandos se ejecutan desde `proy_bd_heatmap/`.

### Aplicar todas las migraciones (BD nueva)

```bash
./venv/bin/alembic upgrade head
```

Esto ejecuta:
1. `0001` — baseline: crea las 10 tablas base, 27 particiones, 3 vistas,
   2 funciones, extensión `pg_trgm` y 3 secuencias (solo esquema).
2. `0002` — seed idempotente: carga `dim_asset` (1.668), `dim_time` (730),
   `dim_trading_session` (630) y sincroniza `dim_asset_asset_id_seq`.
3. `0003` — `fact_market_indicator_tf` (F4.2): tabla larga multi-TF
   particionada por `RANGE (timestamp_utc)` (16 particiones mensuales UTC).
4. `0004` — `latest_market_tick` (F4.3): una fila por activo (PK `asset_id`),
   reescrita por UPSERT en cada ciclo del radar (E-DSH-04).
5. `0005` — `fact_heatmap_snapshot` (F4.4): columnas explícitas
   `volume, avg_vol_10d, avg_vol_30d, volatility_d, change_abs, high_52w,
   low_52w, update_mode, fetched_at` (M-DAT-05, E-HM-08/E-HM-10; ALTER sobre
   el padre particionado propaga a las particiones).
6. `0006` — `dim_asset` Tipo 1 + mapeo canónico (F4.5b): elimina SCD2
   (`valid_from`, `valid_to`, `current_version`) y añade `logical_key`,
   `is_canonical`, `role`, `feed_delay_s`; mapeo canónico de las 6 claves
   lógicas F2.5 con alta de `TVC:DXY`; índice único parcial
   `uq_dim_asset_canonical_logical_key`; funciones/vistas/índices
   reconstruidos sin `current_version`; elimina `idx_dim_asset_symbol`
   (duplicado). `dim_asset` pasa a 1.669 y la secuencia a 4.701.

### Ver estado actual

```bash
./venv/bin/alembic current          # en qué revisión está la BD
./venv/bin/alembic history          # cadena de revisiones
./venv/bin/alembic heads            # revisión(es) punta
```

### Subir/bajar una revisión concreta

```bash
./venv/bin/alembic upgrade +1       # una revisión hacia adelante
./venv/bin/alembic upgrade 0002     # a una revisión específica
./venv/bin/alembic downgrade -1     # una revisión hacia atrás
./venv/bin/alembic downgrade 0001   # a una revisión específica
./venv/bin/alembic downgrade base   # revertir todo (deja solo alembic_version)
```

### Crear una migración nueva

```bash
# 1. (opcional) con autogenerate si hay modelos con metadata
./venv/bin/alembic revision --autogenerate -m "descripcion"

# 2. manual (recomendado para DDL de particiones/funciones/vistas)
./venv/bin/alembic revision -m "descripcion"
#   editar alembic/versions/<rev>_descripcion.py: implementar upgrade()/downgrade()
```

### Adoptar una BD existente (sin re-ejecutar DDL)

```bash
./venv/bin/alembic stamp head
```

> ⚠️ El `stamp` NO ejecuta DDL: solo registra la revisión como aplicada. Usar
> cuando la BD ya tiene el esquema (como se hizo con `heatmap_stock`).

### Verificación de consistencia

```bash
# 1. Ejecutar la suite de pruebas (usa la BD scratch heatmap_stock_test)
./venv/bin/python3 -m pytest tests -q

# 2. Comparar esquema scratch vs producción
docker exec pg_db pg_dump --schema-only --no-owner --no-privileges \
    -U postgres heatmap_stock_test > /tmp/scratch.sql
docker exec pg_db pg_dump --schema-only --no-owner --no-privileges \
    -U postgres heatmap_stock > /tmp/prod.sql
diff <(grep -v '^\\restrict\|^-- Dumped\|^-- PostgreSQL database dump' /tmp/prod.sql) \
     <(grep -v '^\\restrict\|^-- Dumped\|^-- PostgreSQL database dump' /tmp/scratch.sql)
#   La única diferencia esperada es la tabla alembic_version.
```

---

## Migraciones existentes

### `0001` — baseline (2026-09-23)
- **Generada desde** `pg_dump --schema-only` de la BD viva (`scripts/generar_baseline.py`).
- Contiene **solo esquema** (sin datos): tablas, particiones, índices,
  constraints, funciones, vistas, extensión `pg_trgm`, comentarios.
- `downgrade()` revierte en orden inverso (vistas → funciones → tablas →
  secuencias → extensión).

### `0002` — seed de catálogos (2026-09-23)
- **Generada desde** `pg_dump --data-only` de las tablas de dimensión
  (`scripts/generar_seed_catalogos.py`).
- Idempotente: `INSERT ... ON CONFLICT DO NOTHING` (no duplica si se re-ejecuta).
- Sincroniza `dim_asset_asset_id_seq` con el `MAX(asset_id)`.
- `downgrade()` hace `TRUNCATE` de las tres tablas de dimensión.

### `0003` — `fact_market_indicator_tf` (F4.2, 2026-09-23)
- Crea la tabla larga de indicadores multi-TF (`asset_id`, `timestamp_utc`,
  `tf` + `rsi`, `cci20`, `bbpower`, `adx`, `change_pct`, `volume`, `pivot_r3`),
  **particionada por RANGE (`timestamp_utc`)** con particiones mensuales UTC
  `2026_09`…`2027_12` (fronteras a 00:00 UTC, convención de
  `fact_market_bar_15m`).
- Cierra **E-RAD-01** y **D12**; la puebla el radar (bloques `|5` y `|15`) y
  `proy_scrapping_detail/scripts/build_indicator_tf.py`.
- `downgrade()` hace `DROP TABLE ... CASCADE`.

### `0004` — `latest_market_tick` (F4.3, 2026-09-23)
- Una fila por activo (`asset_id` como PK, **no particionada**), reescrita por
  UPSERT en cada ciclo del radar con la última marca: bloque base (close,
  change_pct, volume, rsi), bloque `|15` (rsi_15, cci20_15, bbpower_15,
  adx_15, pivot_r3_15) y trazabilidad F3.3 (update_mode, feed_delay_s,
  cycle_id, fetched_at).
- Cierra **E-DSH-04** (el dashboard lee ~110 filas sin escanear
  `fact_market_series`); la escriben el radar y
  `proy_scrapping_detail/scripts/build_latest_tick.py`.
- `downgrade()` hace `DROP TABLE ... CASCADE`.

### `0005` — `fact_heatmap_snapshot` columnas explícitas (F4.4, 2026-09-23)
- Añade `volume, avg_vol_10d, avg_vol_30d, volatility_d, change_abs,
  high_52w, low_52w, update_mode, fetched_at` (M-DAT-05). El ALTER sobre el
  padre particionado propaga automáticamente a las particiones adjuntas.
- Cierra **E-HM-08** y **E-HM-10**; `raw_vector` se conserva pero deja de ser
  la fuente principal (tamaño por fila < 1 kB al leer las columnas).
- `downgrade()` retira las 9 columnas.

### `0006` — `dim_asset` Tipo 1 + mapeo canónico (F4.5/F4.5b, 2026-09-23)
- Elimina el SCD2 de `dim_asset`: se **dropean** `valid_from`, `valid_to`,
  `current_version` (E-DSH-02, E-DSH-03) — `symbol` era `UNIQUE` global, así
  que el SCD2 con `current_version` era una falsa promesa.
- Añade `logical_key` (6 claves F2.5), `is_canonical`, `role`
  (`primary`/`fallback`) y `feed_delay_s` (backfill por clase: 900 equidad/ETF,
  600 futuros, 0 el resto). Alta canónica de **`TVC:DXY`** (índice DXY).
- Índice único parcial `uq_dim_asset_canonical_logical_key (logical_key)
  WHERE logical_key IS NOT NULL AND is_canonical` → **1 canónico por clave**.
- Reconstruye funciones (`upsert_*`), vistas (`vw_heatmap_enriched`,
  `vw_market_live`) e índices `idx_dim_asset_active/class` sin
  `current_version`; elimina `idx_dim_asset_symbol` (duplicaba la UNIQUE
  `dim_asset_symbol_key`).
- `dim_asset`: 1.668 → **1.669**; `dim_asset_asset_id_seq` → **4.701**.
- `downgrade()` restaura columnas, mapeo/y alta y los índices legacy.

---

## F4.8 — Suite nocturna de calidad

Script **independiente** (`scripts/suite_calidad_nocturna.py`) pensado para
ejecutarse como cronjob nocturno contra la BD viva **`heatmap_stock`** (no usa
alembic ni depende de la suite de migraciones; solo necesita `psycopg2` y
`python-dotenv`, ambos en `requirements.txt`).

**Justificación.** Antes de reempaquetar histórico (F4.7, actualmente
descartada: se inicia desde cero con BD en blanco y sin históricos) la calidad
de lo capturado debe ser verificable de forma periódica y automatizada. La
suite audita coherencia, frescura y volumen de las fact tables que alimentan el
dashboard, y termina con un informe legible (MD) y otro técnico (JSON) en
`reports/` (gitignored).

### Uso

```bash
cd proy_bd_heatmap

# Ejecución completa (ventana por defecto 24 h)
./venv/bin/python scripts/suite_calidad_nocturna.py

# Ventana de horas distinta (p. ej. 6 h para una validación rápida)
./venv/bin/python scripts/suite_calidad_nocturna.py --hours 6

# Un único cheque (filtra por id, p. ej. CHK-FRESCURA)
./venv/bin/python scripts/suite_calidad_nocturna.py --check CHK-FRESCURA

# Ayuda
./venv/bin/python scripts/suite_calidad_nocturna.py --help
```

### Ejemplo de cron

```cron
# Todos los días 04:05 (ventana asiática, mercado cerrado en NY)
05 4 * * * cd /path/to/proy_bd_heatmap && ./venv/bin/python scripts/suite_calidad_nocturna.py >> logs/suite_calidad.log 2>&1 || echo "SUITE EXIT=$?" >> logs/suite_calidad.log
```

### Códigos de salida

| Código | Significado |
|---|---|
| `0` | Todo PASS (puede haber WARN) |
| `1` | Al menos un cheque FAIL |
| `3` | Error de conexión con la BD (no se emite informe) |

### Estado por cheque

| Estado | Significado |
|---|---|
| `PASS` | Sin incidencias |
| `WARN` | Bajo volumen pero dentro de umbral (p. ej. barras con `n_ticks < 2`) |
| `INFO` | Resultado informativo (p. ej. ventana vacía o BD aún sin datos; no es alerta) |
| `FAIL` | Incumplimiento: huecos de captura, frescura vencida, duplicados, nulos o ticks planos fuera del umbral |

> El estado `INFO` evita falsas alertas cuando se corre sobre una BD recién
> creada (`alembic upgrade head` desde cero, arranque F4.7) que aún no acumula
> datos en la ventana consultada.

### Cheques incluidos

| ID | Qué audita |
|---|---|
| `CHK-DUP-*` | Duplicados por clave natural en `fact_market_series`, `fact_market_bar_15m`, `fact_market_indicator_tf`, `fact_heatmap_snapshot` |
| `CHK-NULL-*` | Nulos en columnas críticas (`close`, `price_heatmap`) |
| `CHK-CICLOS` | Huecos de captura en activos 24/5 (radar de 3 min → alerta si hueco > 15 min) |
| `CHK-FRESCURA` | Frescura por clase 24/5 (`max(timestamp)` vs ahora; umbral 30 min) |
| `CHK-TICKS-PLANOS` | Ticks con precio plano fuera de sesión NYSE (equity/ETF, 7 días) |
| `CHK-NTICKS` | Distribución de `n_ticks` por barra (WARN si < 2) |
| `CHK-CLOSE-QUALITY` | `close_quality_definitive` por barra (7 días) |
| `CHK-PARTICIONES` | Contigüidad de particiones mensuales de las fact tables (incluye mes actual) |

### Salida

- Consola: resumen por cheque con detalle abreviado.
- `reports/suite_calidad_<AAAAmmdd_HHMMSS>.md` — informe legible (BD, ventana,
  exit code, tabla de cheques con su detalle).
- `reports/suite_calidad_<AAAAmmdd_HHMMSS>.json` — informe técnico para
  consumo de otras herramientas.

---

## Buenas prácticas

- **No mezclar DDL con datos**: las revisiones cambian esquema; los seeds van
  en revisiones idempotentes (como `0002`) o scripts dedicados.
- **Idempotencia**: usar `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` cuando sea
  posible; las revisiones deben poderse re-ejecutar sin romper.
- **Particiones**: las particiones mensuales se crean en el baseline; las
  nuevas tablas de hechos deben crearse particionadas desde el inicio y las
  particiones futuras se gestionan en revisiones dedicadas (F2.3 pendiente).
- **Permisos**: el `upgrade` de extensiones (`pg_trgm`) requiere un rol con
  privilegios de superusuario o de `CREATE EXTENSION`.
- **No editar revisiones aplicadas**: una revisión ya ejecutada en alguna BD
  es inmutable; los cambios se hacen en revisiones nuevas.
- **Revisar `autogenerate`**: siempre revisar lo que genera antes de aplicarlo;
  no captura funciones/vistas/extensión/CHECK constraints.
- **Probarlo en scratch primero**: antes de tocar `heatmap_stock`, ejecutar
  `upgrade head` en `heatmap_stock_test` y correr la suite.

---

## Notas

- La BD `heatmap_stock` está actualmente en revisión **`0006 (head)`**
  (0001 baseline → 0002 seed → 0003 F4.2 → 0004 latest_market_tick → 0005
  columnas explícitas de snapshot → 0006 dim_asset Tipo 1 + mapeo canónico).
- La tabla de bookkeeping `alembic_version` es la única tabla creada por alembic
  fuera del esquema de negocio.
- El roadmap y la justificación están en
  `docs/Roadmap proy_bd_heatmap - Alembic (2026-09-23).md`.