# Playbook — Gestión de Activos del Radar V5

> **Ubicación:** `proy_scrapping_detail/playbooks/gestion_activos.md`  
> **Proyecto:** `proy_scrapping_detail` — Radar Intermarket V5  
> **Fecha:** 2026-10-07  
> **Estado:** documentación de procedimiento; automatización pendiente de aprobación.

---

## 1. Propósito

Este playbook describe el procedimiento estándar para **agregar, modificar o eliminar activos** del radar V5 de forma que:

- El scraper los capture en el siguiente ciclo (cada 3 minutos).
- `dim_asset` refleje correctamente la categoría y el exchange.
- Los datos sean compatibles con el heatmap y el dashboard.
- Se minimicen errores humanos al tocar múltiples archivos.

> **Regla de oro:** la fuente única del universo del radar es `config.py::CONFIG_ACTIVOS`. Todo lo demás (`dim_asset`, archivos CSV, tablas de BD) se deriva de ahí.

---

## 2. Requisitos mínimos para insertar un activo

Antes de agregar un símbolo, asegúrate de que cumpla **todos** estos requisitos:

| # | Requisito | Cómo verificar |
|---|---|---|
| R1 | **Formato correcto** | `EXCHANGE:TICKER` (p. ej. `NASDAQ:MU`). El exchange debe existir en `CLASS_MAP` de `seed_symbols.py`. |
| R2 | **Símbolo válido en TradingView** | Probar `GET https://scanner.tradingview.com/symbol?symbol=NASDAQ:MU&fields=close` y confirmar que devuelve datos. |
| R3 | **Exchange soportado por el batch** | Si es `NASDAQ`, `NYSE` o `AMEX`, se captura por `POST /america/scan` (eficiente). Otros exchanges usan `GET /symbol` individual. |
| R4 | **Liquidez / datos recientes** | El símbolo debe tener volumen y cotización activa. Activos sin cotización generarán filas vacías o `update_mode` inconsistente. |
| R5 | **Categoría lógica definida** | Debe existir una categoría en `CONFIG_ACTIVOS` coherente con el sector del activo (o crear una nueva justificada). |
| R6 | **Sin duplicados** | El símbolo (y su ticker) no debe existir ya en `CONFIG_ACTIVOS` bajo otra categoría. |
| R7 | **Impacto en dashboard evaluado** | Si el activo es para contexto (radar) o para trading (equity), debe quedar claro en `METADATOS_ACTIVOS` cuando aplique. |

---

## 3. Formato de entrada recomendado

Para automatizar el proceso, se propone un archivo YAML centralizado:

```yaml
# activos_cambios.yaml
altas:
  - clave: "SPCX"
    categoria: "TELECOM_MEDIA"
    primario: "NASDAQ:SPCX"
    respaldo: "NASDAQ:SPCX"
    nota: "Añadido para seguimiento de comunicaciones/spacex"

  - clave: "SKHY"
    categoria: "SEMICONDUCTORES"
    primario: "NASDAQ:SKHY"
    respaldo: "NASDAQ:SKHY"
    nota: "Añadido como proxy semiconductor adicional"

bajas:
  - clave: "VZ"
    razon: "Baja liquidez / datos inconsistentes"
    mantener_historico: true

modificaciones:
  - clave: "MU"
    categoria: "SEMICONDUCTORES"
    # cambiar respaldo si fuera necesario
    respaldo_nuevo: "NYSE:MU"
```

---

## 4. Procedimiento manual paso a paso

### 4.1 Agregar un activo

1. **Validar el símbolo en TradingView**
   ```bash
   curl -s "https://scanner.tradingview.com/symbol?symbol=NASDAQ:SPCX&fields=close,volume,RSI"
   ```
   Debe devolver JSON con valores numéricos.

2. **Editar `config.py`**
   - Añadir la entrada en la categoría correspondiente dentro de `CONFIG_ACTIVOS`.
   - Si el activo es un componente del radar (VIX, DXY, TLT, US10Y, ORO, OIL), actualizar `METADATOS_ACTIVOS`.

3. **Sincronizar `dim_asset`**
   ```bash
   cd /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_scrapping_detail
   ./venv/bin/python seed_symbols.py --dry-run
   ./venv/bin/python seed_symbols.py
   ```
   > ⚠️ `seed_symbols.py` solo hace **altas nuevas**. Si el símbolo ya existía en `dim_asset` (por ejemplo, descubierto por el heatmap), no actualiza `source_category`. En ese caso, actualizar manualmente:
   > ```sql
   > UPDATE dim_asset
   > SET source_category = 'NOMBRE_CATEGORIA', updated_at = CURRENT_TIMESTAMP
   > WHERE symbol = 'EXCHANGE:TICKER';
   > ```

4. **Poblar datos**

   **Opción A — dentro del horario bursátil NYSE:**
   Esperar al próximo ciclo del cron (cada 3 minutos) o ejecutar manualmente:
   ```bash
   ./venv/bin/python scraper_live_tradingview_v5.py
   ```

   **Opción B — fuera del horario bursátil (prueba/manual):**
   El scraper omite equity/ETF fuera de la ventana NYSE. Para forzar la captura del último tick e indicadores usar:
   ```bash
   ./venv/bin/python scripts/build_latest_tick.py --prime
   ./venv/bin/python scripts/build_indicator_tf.py --from-scan
   ```
   > ⚠️ Estos scripts **no** escriben `fact_market_series`; solo `latest_market_tick` e `indicator_tf`. La serie histórica (`fact_market_series`) se poblará en el próximo ciclo dentro del horario bursátil.

5. **Verificar captura**
   ```bash
   ./venv/bin/python scripts/build_latest_tick.py --status
   ./venv/bin/python scripts/build_indicator_tf.py --status --days 1
   ```

6. **Verificar en BD**
   ```sql
   SELECT a.symbol,
          (SELECT count(*) FROM fact_market_series s WHERE s.asset_id = a.asset_id) AS ticks,
          (SELECT count(*) FROM latest_market_tick l WHERE l.asset_id = a.asset_id) AS latest,
          (SELECT count(*) FROM fact_market_indicator_tf i WHERE i.asset_id = a.asset_id) AS tf
   FROM dim_asset a
   WHERE a.symbol IN ('NASDAQ:SPCX', 'NASDAQ:SKHY');
   ```

### 4.2 Modificar un activo

1. Editar `config.py`.
2. Si cambia la categoría, ejecutar `seed_symbols.py` para actualizar `source_category` en `dim_asset`.
3. Si cambia el símbolo primario/respaldo, el scraper lo aplicará en el siguiente ciclo. Los datos antiguos bajo el símbolo anterior quedarán en `fact_market_series` (no se migran automáticamente).
4. Verificar con `build_latest_tick.py --status`.

### 4.3 Eliminar un activo

1. **Quitar de `CONFIG_ACTIVOS`**.
2. **(Opcional pero recomendado)** Marcar inactivo en `dim_asset`:
   ```sql
   UPDATE dim_asset
   SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
   WHERE symbol = 'NASDAQ:XYZ';
   ```
3. Los datos históricos en `fact_market_series`, `fact_market_indicator_tf` y `fact_heatmap_snapshot` **no se borran** automáticamente. Si se requiere borrado, hacerlo manualmente con criterio de retención.
4. Verificar que el dashboard ya no lo muestre (filtra por `is_active = TRUE`).

---

## 5. Validaciones posteriores

Después de cualquier alta/baja/modificación, ejecutar:

```bash
# 1. Verificar universo del radar
./venv/bin/python seed_symbols.py --check

# 2. Verificar últimos ticks
./venv/bin/python scripts/build_latest_tick.py --status

# 3. Verificar indicadores multi-TF
./venv/bin/python scripts/build_indicator_tf.py --status --days 1

# 4. Verificar health del dashboard
# (desde proy_dashboard)
curl -s http://localhost:8100/api/health | python3 -m json.tool
```

---

## 6. Rollback

| Cambio | Rollback |
|---|---|
| Alta | Revertir `config.py` + marcar inactivo en `dim_asset` + (opcional) borrar filas recientes de `fact_market_series`. |
| Modificación | Revertir `config.py`. Si cambió el símbolo, los datos históricos quedan bajo el símbolo anterior; no hay migración automática. |
| Baja | Recuperar la entrada en `config.py` + poner `is_active = TRUE` en `dim_asset`. |

---

## 7. Propuesta de automatización (script `gestion_activos.py`)

Para evitar tocar `config.py` a mano y ejecutar múltiples scripts, se propone crear:

```
proy_scrapping_detail/scripts/gestion_activos.py
```

### Funciones del script

1. **Leer** un archivo YAML (`activos_cambios.yaml`) con altas/bajas/modificaciones.
2. **Validar** cada símbolo contra TradingView (`GET /symbol`).
3. **Actualizar** `config.py` de forma idempotente:
   - Alta: añadir entrada si no existe.
   - Baja: eliminar entrada.
   - Modificación: actualizar primario/respaldo/categoría.
4. **Ejecutar** `seed_symbols.py` automáticamente.
5. **Opcionalmente** ejecutar `scraper_live_tradingview_v5.py` una vez para poblar datos inmediatos.
6. **Generar** un reporte de cambios aplicados.
7. **Registrar** en `audit_sync_run` (opcional).

### Requisitos del script

- Python 3.10+.
- Librerías: `pyyaml`, `requests` (ya disponibles en el venv).
- Backup automático de `config.py` antes de modificarlo.
- Modo `--dry-run` para previsualizar cambios sin escribir.
- Validación de formato `EXCHANGE:TICKER`.
- Validación de que la categoría existe o se crea explícitamente.

### Ejemplo de uso futuro

```bash
# Previsualizar
./venv/bin/python scripts/gestion_activos.py --file activos_cambios.yaml --dry-run

# Aplicar
./venv/bin/python scripts/gestion_activos.py --file activos_cambios.yaml --apply

# Aplicar + capturar datos ahora
./venv/bin/python scripts/gestion_activos.py --file activos_cambios.yaml --apply --capture-now
```

---

## 8. Ejemplo completo: alta de SPCX y SKHY

### Entrada YAML

```yaml
# activos_cambios_2026-10-07.yaml
altas:
  - clave: "SPCX"
    categoria: "TELECOM_MEDIA"
    primario: "NASDAQ:SPCX"
    respaldo: "NASDAQ:SPCX"
  - clave: "SKHY"
    categoria: "SEMICONDUCTORES"
    primario: "NASDAQ:SKHY"
    respaldo: "NASDAQ:SKHY"
```

### Resultado esperado en `CONFIG_ACTIVOS`

```python
"TELECOM_MEDIA": {
    "DIS": {"primario": "NYSE:DIS", "respaldo": "NYSE:DIS"},
    "VZ":  {"primario": "NYSE:VZ",  "respaldo": "NYSE:VZ"},
    "SPCX": {"primario": "NASDAQ:SPCX", "respaldo": "NASDAQ:SPCX"},
},
"SEMICONDUCTORES": {
    ...
    "MU":   {"primario": "NASDAQ:MU",   "respaldo": "NASDAQ:MU"},
    "SKHY": {"primario": "NASDAQ:SKHY", "respaldo": "NASDAQ:SKHY"},
},
```

### Verificación en BD (tras `prime` / `from-scan` fuera de horario)

```sql
SELECT a.symbol, a.asset_class, a.source_category, a.is_active,
       (SELECT count(*) FROM fact_market_series s WHERE s.asset_id = a.asset_id) AS ticks,
       (SELECT count(*) FROM latest_market_tick l WHERE l.asset_id = a.asset_id) AS latest,
       (SELECT count(*) FROM fact_market_indicator_tf i WHERE i.asset_id = a.asset_id) AS tf,
       (SELECT count(*) FROM fact_heatmap_snapshot h WHERE h.asset_id = a.asset_id) AS heatmap
FROM dim_asset a
WHERE a.symbol IN ('NASDAQ:SPCX', 'NASDAQ:SKHY', 'NASDAQ:MU');
```

Resultado observado (2026-10-07, fuera de horario NYSE):

| symbol | asset_class | source_category | ticks | latest | tf | heatmap |
|---|---|---|---:|---:|---:|---:|
| NASDAQ:MU | equity | SEMICONDUCTORES | 8447 | 1 | 10 | 9 |
| NASDAQ:SPCX | equity | TELECOM_MEDIA | 0 | 1 | 4 | 9 |
| NASDAQ:SKHY | equity | SEMICONDUCTORES | 0 | 1 | 2 | 9 |

- `ticks = 0` para SPCX/SKHY porque el scraper aún no ha corrido dentro del horario bursátil; se poblará en la próxima ventana NYSE.
- `latest = 1` y `tf > 0` confirman que `prime` / `from-scan` funcionaron correctamente.

---

## 9. Checklist antes de dar por terminado un cambio

- [ ] El símbolo está en `CONFIG_ACTIVOS` con `primario` y `respaldo` correctos.
- [ ] La categoría es coherente con el sector en `dim_asset`.
- [ ] `seed_symbols.py --check` no reporta faltantes.
- [ ] El activo aparece en `latest_market_tick` tras un ciclo del cron.
- [ ] El activo aparece en `fact_market_indicator_tf` (tf 5 y 15).
- [ ] El dashboard `/api/health` sigue OK.
- [ ] Se documentó el cambio en el changelog/playbook.

---

*Fin del playbook — 2026-10-07. Pendiente de aprobación para codificar `scripts/gestion_activos.py`.*
