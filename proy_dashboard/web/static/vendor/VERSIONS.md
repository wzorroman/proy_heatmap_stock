# VERSIONS — Librerías vendorizadas (offline)

Todas las librerías frontend se sirven **desde local** (`web/static/vendor/`), sin CDN.
No actualizar sin re-verificar `sha256` y registrar aquí la fecha.

| Librería | Versión | Licencia | Archivo | Fecha | sha256 |
|---|---|---|---|---|---|
| Apache ECharts | 6.1.0 | Apache-2.0 | `echarts/6.1.0/echarts.min.js` | 2026-09-30 | `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0` |
| HTMX | 2.0.11 | 0BSD | `htmx/2.0.11/htmx.min.js` | 2026-09-30 | `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717` |

## Origen
- ECharts: `https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js` (LICENSE y NOTICE desde el tag `6.1.0`).
- HTMX: `https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/dist/htmx.min.js` (LICENSE desde el tag `v2.0.11`).

## Verificación
```bash
cd proy_dashboard/web/static/vendor
sha256sum echarts/6.1.0/echarts.min.js htmx/2.0.11/htmx.min.js
```
