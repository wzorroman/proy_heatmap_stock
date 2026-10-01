# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Evolución del score de mercado: la línea pasa a **smoothed con puntos visibles** (`symbol: circle`, `symbolSize: 5`), en **azul cian vivo** `#00d4ff` con **borde oscuro** `#0b1220` para resaltar sobre el relleno del área; hover con escala ×1.5 y `#5ee7ff`.
- Evolución del score de mercado: se agregan **separadores verticales naranjas punteados** en la medianoche de la zona de visualización (`APP_TIMEZONE`) y **sombreado gris claro de la sesión NY 09:30–16:00 ET** con DST correcto (markArea con `z: 3` sobre la serie, para que no lo tape el área azul de la línea). Los datos siguen en UTC en la BD; la conversión es **puramente visual**.
- Evolución del score de mercado: **línea vertical gris sólida con etiqueta `APERTURA`** en la primera muestra de cada sesión NY 09:30 ET.
- Versión **1.0.20 → 1.0.21** (`core/settings.py`, `pyproject.toml`): el cache-buster de estáticos (`app.css?v=`) no cambiaba y servía CSS viejo al navegador; subir la versión invalida la caché.
- Velas 15 min: al seleccionar un símbolo en el screener, el card de velas hace un **fade suave** (~0.3 s salida + 0.5 s entrada) en lugar del swap instantáneo (`hx-swap="innerHTML swap:0.3s settle:0.5s"` + clases `htmx-swapping`/`htmx-settling` de HTMX sobre `#trading-velas-card`).
- Screener 15 min: se elimina el scroll interno; ahora muestra hasta 20 señales COMPRAR/VENDER y, si hay menos de 5, completa con los top movimientos hasta 15 filas.
- Velas 15 min: el símbolo por defecto ya no es fijo (`NASDAQ:NVDA`); ahora toma el primer símbolo del screener 15 min. Sigue permitiendo `?symbol=...`.
- Velas 15 min: se mantiene un único gráfico (se descarta la vista de 3 comparativas).
- Screener 15 min: las filas son clicables y recargan el panel de velas con el símbolo seleccionado.
- Screener 15 min: valores de columna **centrados** (antes a la derecha) y más separación horizontal (`padding 9px`), para que `Vol ratio` no quede pegado a `Señal`. Aplica igual a la última columna (`Señal`/`Ruptura`) en `ib_acciones`.
- Fila Trading 15 min movida debajo de Alcistas/Bajistas del día, reorganizada en **dos filas**: `Screener (5) + Rango inicial por acción (4) + Confluencia (3)` y `Velas 15m (7) + Mapa de calor 15m (5)`.
- Confluencia 5m/15m/1D: ahora usa exactamente los mismos símbolos y el mismo orden visual que el screener 15 min (eje Y invertido y datos del heatmap transpuestos correctamente).
- Fila del screener: los 3 cards mantienen la misma altura (clase `card-trading` + `.chart-fill`); velas y mapa sectorial también comparten fila con altura uniforme.
- Fila del screener: el alto lo manda el screener; rango inicial y confluencia se anclan a ese alto (`.cell.altura-screener`, `@media (min-width: 1101px)`) para quedar alineados.
- Selección sincronizada: al elegir un símbolo en el screener se resalta también su fila en el rango inicial y su fila (3 círculos) en el heatmap de confluencia. El borde del resaltado toma el **tono vivo del propio círculo** (verde `#7ee787` / rojo `#ff9492` / gris `#9fb3c8`), **nítido** (`shadowBlur: 0`) y con una **banda sutil** sobre la fila; se elimina el borde celeste y el glow difuminado.
- Screener y Rango inicial: vuelven a ser **cards separados** (se descarta la tabla paralela en un solo card); el card **Rango inicial — por acción** se sube junto al screener y ahora lista **los mismos símbolos en el mismo orden que el screener** (`evaluar_lote()`; los símbolos sin IB aparecen con `—`).
- Rango inicial: etiquetas de ruptura en inglés corto — `UP` / `DOWN` / `IN` (antes ALCISTA/BAJISTA/DENTRO).
- Screener 15 min: etiqueta de señal en inglés — `BUY` / `SELL` / `NEUTRAL` (antes COMPRAR/VENDER).
- Confluencia 5m/15m/1D: celdas del heatmap convertidas en **círculos** (scatter `symbol: circle`) y card más ancho (3 grid) con etiquetas del eje Y legibles. Se elimina la leyenda visible y se mueve al `title` del encabezado (tooltip).
- Velas 15 min: el símbolo se muestra ahora como etiqueta destacada (`velas-symbol-badge`) sobre el título, con estilo azul tipo `zona-NEUTRAL` (`--azul` + `--azul-soft`) y brillo sutil.
- Screener 15 min: la fila del símbolo seleccionado se resalta (`selected`) y se sincroniza con el gráfico de velas.
- Velas 15 min: etiquetas y valores de `precio-meta` separados (`.meta-label` claro/atenuado vs `.meta-value` más claro y bold) para mejorar el contraste.
- Screener 15 min: la vista compacta agrega 3 columnas relevantes (Dist VWAP, RSI15, ADX15); la etiqueta de señal se reduce con `.zona-sm`.
- Screener 15 min: mejor distribución de filas (mayor padding vertical, separación entre filas, zebra sutil, hover azul, números tabulares alineados a la derecha y encabezado en mayúsculas).
- Cálculo 15m: todos los valores numéricos (OHLC, SMA, Bollinger, VWAP, vol ratio) se normalizan a máximo 4 decimales con `_r4()` para estandarizar la salida; el screener 15m usa el mismo helper.
- Screener 15 min: se agrega el logo de cada acción junto al símbolo (`.slogo`); si no hay logo se muestra un cuadro negro (`.slogo-empty`) para no distorsionar la alineación. `_screener_filas()` ahora enriquece cada fila con `logo_url(symbol)`.
- Confluencia 5m/15m/1D: colores del heatmap suavizados a tonos pastel (`VERDE_PASTEL #8fd19e`, `ROJO_PASTEL #e79a9a`, neutral `#2f3844`), manteniendo la semántica alcista/bajista.
- Layout: **primera fila con 5 tarjetas** (`score` 3 · `termómetro` 2 · `FX/Macro` 3 · `histograma score` 2 · `health` 2); el histograma se mueve entre FX/Macro y health. Fila **alcistas 5 · bajistas 5 · divergencias 2** (nueva clase `.cell.cinco`). Fila `IB acción` 3 · `sectorial 15m` 6 (3 reservadas). El IB de mercado se integra en las tarjetas de precio.
- Layout: primera fila con **altura uniforme** (clase `.fila1`): todas las tarjetas toman la altura de la más alta ("Distribución score").
- Mapa de calor 15m por sector: escala de color **dinámica** (`±máx|cambio|`, mínimo 0.05) con colores `VERDE`/`ROJO`; antes el rango fijo (−3..3) dejaba todos los sectores en gris.

### Added

- **Deploy contenedorizado (Podman/Docker, rootless)**: nuevo `Containerfile` (python:3.13-slim, usuario no-root `appuser` uid 10001, `HEALTHCHECK` sobre `/api/health`, puerto 8100), `compose.yml` con **solo el servicio web** — los cron jobs de escritura (`persist_score`, watchdog) **siguen en el crontab del servidor** y el contenedor marca `DB_WRITE_ENABLED=false` de forma explícita — y `.dockerignore` que excluye `.env`, `venv/` y `logs/` de la imagen.
- **README: checklist de despliegue en producción** (`Deploy en producción — pasos iniciales`): 8 fases con casos de prueba y comandos — prerequisitos del servidor (rootless/subuid/red/puerto), `.env` y permisos, estado de migraciones, Opción A Podman (build/compose/health), Opción B systemd, sección dedicada al **cron del servidor que permanece igual**, verificación final y update/rollback.
- **Favicon del dashboard**: `web/static/favicon.svg` (+ `favicon.png`/`favicon.ico` de respaldo) con el motivo de marca — diamante ◈ azul/cian sobre fondo `#0d1117`; enlazado en `base.html` con cache-buster `?v=`.
- `charts.line_option()` acepta `mark_lines` (separadores de día), `market_hours` (ventanas de sesión), `market_open_lines` + `market_open_label` (apertura NY) y el helper `charts._vertical_markline()` — markLine vertical por par de coordenadas `[idx, y0]→[idx, y1]`, formato que sí respeta el eje de categorías.
- Nota del panel *Evolución del score de mercado*: **leyenda con muestras de color** — `n ciclos · ▮ medianoche · ▮ apertura NY HH:MM <TZ>`; la hora de apertura se convierte dinámicamente a `APP_TIMEZONE` (p. ej. `08:30 PE` con NY en EDT).
- **Mapa de calor 15m por sector (5.5)**: nuevo `services/sector_15m_service.py` (cambio medio 15m por sector), `charts.sector_15m_option()` (treemap pastel, área = nº de acciones), endpoint `/partials/sector_15m` y test de agregación.
- **Histograma del score 15m (5.6)**: `ScoreService.distribucion_15min()`/`histograma_de_scores()` (distribución por acción, media, percentil, zonas y descripción), `charts.score_hist_option()` (barras por zona + marca de media) y endpoint `/partials/score_15m`. El título indica la temporalidad (`Distribución score 15m`) y la nota describe/recomienda. Tests en `tests/test_score_service.py`.
- **Initial Balance (rango inicial 09:30–10:00 NY)**:
  - 5.4a **por acción**: `/partials/ib_acciones` (tabla de rupturas, filas clicables que actualizan velas).
  - 5.4b **mercado**: integrado como **pastilla `IB`** en las tarjetas de precio QQQ/SPY/IWM (ORO `---`); el card independiente `/partials/ib_mercado` fue **eliminado**.
  - Nuevo `services/initial_balance_service.py` (`scan_por_accion`, `evaluar_symbol`, `evaluar`), wiring en `container.py`, claves `ib_*` en `config_dashboard.json`, estilos `.ib-time` / `.ib-badge` y tests en `tests/test_trading_15m.py`.
- **Cuarta tarjeta de precio IWM (Russell 2000)** en `precio.tarjetas`; `.precios-grid` pasa a 4 columnas (2 en ≤1500 px, 1 en ≤1100 px).
- Tarjetas de precio: se elimina la palabra "Precio" y la reemplaza el **logo/icono** del instrumento (`.precio-logo`, o emoji `.precio-icono` si no hay logo); el subnombre (`(S&P 500)`, etc.) se muestra en azul (`.precio-sub`). Config con `titulo`/`subtitulo`/`icono`/`icono_url`.
- Histograma del score 15m: la **interpretación se muestra debajo del gráfico** (plantilla `score_15m.html`), con encabezado de métricas (zona, media, percentil, %COMPRAR/%VENDER). La línea de la media pasa a **amarillo** punteado (width 2) con etiqueta resaltada.
- Histograma del score 15m: el texto del análisis ahora es **solo la sugerencia accionable** (ya no repite media/percentil/%), elegida de un **catálogo de 11 combinaciones** (`ScoreService.catalogo_analisis()` / `_opcion_analisis()`).
- Histograma del score 15m: grid con `containLabel` y márgenes mínimos (`left 6 · right 8 · top 18 · bottom 6`) para que el gráfico use el **100% del ancho** del card.
- Health: se reemplaza la tabla por **filas** (`.health-list`), con el **módulo como label destacable** (`.health-mod`) y luego **estado + detalle** con el mismo formato/color (estado `pos/neu/neg`, detalle muted); sin scroll horizontal.
- Health: los timestamps del detalle se muestran en **hora de Lima (America/Lima)** y formato legible `dd/mm HH:MM` (sin `T` ni `+00:00`), para lectura directa.
- Ícono de ORO reemplazado por un **lingote de oro** (`web/static/iconos_mercado/oro_lingote.svg`, config `icono_url`).
- Docs: anexo de implementación y análisis del screener en `docs/informe_graficos_2026-09-30.md`.
- Docs: sección 5 renombrada a “propuestos e implementados”, con estado por gráfico, **diseño ASCII** y **algoritmo de cálculo** (pseudocódigo) en cada ficha; secciones 1, 4, 6 y 8 alineadas al estado real.
- Docs: sección **5.8** con la decisión de alcance del Initial Balance: implementar **ambas opciones como subgráficos 5.4a + 5.4b**, con bocetos ASCII y ventana horaria; el total de fichas pasa de 7 a **8** (+1 gráfico).
- **Watchdog de frescura del score**: nuevo `jobs/check_score_freshness.py` y launcher `run_check_score_freshness.sh` (cron cada 10 min). Falla con exit `5` si `now() - max(timestamp_utc)` en `fact_market_score_agg` supera `panels.score_max_age_min` (default 20 min); tabla vacía cuenta como rancio. Exit `4` para precondiciones locales (falta `.env`, falta `venv`, `logs/` no escribible), que hasta ahora fallaban en silencio. Nuevo `ScoreRepository.fetch_agg_edad_minutos()` y clave `panels.score_max_age_min` en `config_dashboard.json`. Tests en `tests/test_check_score_freshness.py`.
- **Zona horaria explícita en el rango inicial**: la hora de ruptura se muestra con su etiqueta de zona (`09:00 PE`). Nuevos `core.timezone.tz_label()` (etiqueta corta) y `format_hora()` (ISO UTC → `HH:MM` en la zona pedida); `evaluar()` devuelve `hora_utc` y cada vista la formatea.
- Nueva constante `core.timezone.MARKET_TZ` (`America/New_York`): zona fija de la lógica de mercado, separada de `APP_TIMEZONE`, que queda como preferencia de visualización.
- Nuevo `core.timezone.rango_dia_utc(momento, tz)`: ventana UTC semiabierta `[inicio, fin)` del día local, para filtrar columnas `timestamptz` por día local. Lo usa el calendario económico.
- **Zona horaria visible en el subtítulo**: el encabezado muestra la zona de visualización activa (`America/Lima · PE`), tomada de `APP_TIMEZONE`, para que las horas del dashboard se lean sin ambigüedad. Nuevo badge `.tz-badge`.

### Fixed

- `run_check_score_freshness.sh` falla ruidosamente si falta `.env` en lugar de continuar sin configuración (era el modo de fallo que dejó el score 16 h sin actualizarse).
- Docs: los bloques de cron de `proy_dashboard` incluyen la redirección `>> logs/... 2>&1`; sin ella y sin `MAILTO`, cron descarta la salida y cualquier fallo queda invisible.
- **Rango inicial: la ventana 09:30–10:00 se ancla a NY aunque `APP_TIMEZONE` sea otra zona.** `initial_balance_service` y `session_service` usaban `settings.timezone` para la lógica de mercado: con `APP_TIMEZONE=America/Lima` el rango se calculaba sobre 09:30–10:00 Lima (10:30–11:00 NY) y daba `IB low/high` incorrectos. Ahora ambos usan `MARKET_TZ`.
- **Calendario: `APP_TIMEZONE` inválido ya no degrada a UTC.** `core.settings._get_tz()` valida el nombre y cae a `America/New_York` (zona de mercado) si falta o no existe, en lugar del fallback a UTC de `get_tz()`.
- **Calendario: la ventana del día local ahora es semiabierta.** `EventsRepository.fetch_eventos` filtra con `event_timestamp < until` en vez de `<=`, para que un evento en la medianoche exacta no aparezca en dos días consecutivos.

- CSS: nueva clase `.screener-table` para tabla sin scroll y fuente más compacta.
- CSS: se define la variable faltante `--azul: #58a6ff` (afectaba `.brand` y `.velas-symbol-badge`).

## [1.0.20] - 2026-09-30

### Added

- **Trading a 15 min — fila de decisión** en el dashboard:
  - Gráfico de velas 15m con volumen, SMA 9/21, Bollinger 20/2, VWAP y señal COMPRAR/VENDER/NEUTRAL.
  - Screener 15 min de acciones equity con cambio %, volumen relativo, distancia al VWAP, RSI15 y ADX15.
  - Heatmap de confluencia multi-timeframe 5m / 15m / 1D.
- Nuevos servicios de negocio:
  - `services/bar_15m_service.py`
  - `services/screener_15m_service.py`
  - `services/confluencia_service.py`
- Nuevo repositorio SQL:
  - `repositories/bar_15m_repo.py` (barras 15m y fallback a ticks).
- Nuevos parciales y templates:
  - `web/templates/partials/velas_15m.html`
  - `web/templates/partials/screener_15m.html`
  - `web/templates/partials/confluencia.html`
- Nuevas opciones de ECharts en `web/charts.py`:
  - `candlestick_option()`
  - `confluencia_option()`
- Nuevos endpoints JSON en `api/routers/trading15m.py`:
  - `GET /api/trading15m/velas?symbol=...`
  - `GET /api/trading15m/screener`
  - `GET /api/trading15m/confluencia`
- Configuración de trading 15m en `config_dashboard.json`:
  - `default_symbol`, horas de ventana, umbrales RSI/ADX y volumen relativo.
- Tests unitarios del backend en `tests/test_trading_15m.py`:
  - SMA, Bollinger, VWAP, ensamblaje de ticks.
  - Lógica de señales del screener.
  - Interpretación de timeframe y score de confluencia.

### Changed

- `dashboard.html`: nueva fila de 3 columnas (`cell.cuarto`) para los paneles de trading 15m.
- `web/static/app.css`: nueva clase `.cell.cuarto` (span 4 en desktop, span 12 en móvil).
- `core/container.py`: wiring de `Bar15mRepository`, `Bar15mService`, `Screener15mService` y `ConfluenciaService`.
- `web/app.py`: se monta el router `trading15m`.

### Fixed

- Manejo de barras 15m con volumen cero: VWAP conserva el valor acumulado anterior en lugar de volverse `None`.

### Removed

- Se eliminó la sección "Interpretación de riesgo" del card `riesgo_fx.html` porque duplicaba la información del termómetro de riesgo. Ahora el card solo muestra movimiento FX/Macro.

### Notes

- Los datos de `fact_market_bar_15m` están actualizados hasta el momento del deploy; el fallback a ticks de `fact_market_series` permanece activo por si el pipeline se retrasa.

## [1.0.0] - 2026-09-18

### Added

- Dashboard inicial de contexto de mercado conectado a PostgreSQL `heatmap_stock`.
- Score de mercado 0–10 (momentum + radar intermarket).
- Paneles de riesgo intermarket, precio QQQ/SPY/ORO, momentum top/bottom, sectorial, calendario económico y health.
- Arquitectura en capas: `repositories/`, `services/`, `api/`, `web/`.
- Tests por capa con pytest.

[Unreleased]: #unreleased
[1.0.20]: #100---2026-09-30
[1.0.0]: #100---2026-09-18
