# file: proy_heatmap/scripts/verificar_endpoints.py
"""Verificación de endpoints en vivo para el heatmap (F3.7/F3.8).

Sin escribir BD. Reutiliza fetch_from_api() y filter_top_by_market_cap()
reales y comprueba que los datos siguen siendo correctos/esperados:

1. El body HEATMAP_BODY filtra por exchange in_range (solo america).
2. Ningún símbolo OTC combinado con acciones preferentes ni volumen < 20M USD.
3. descripción (company_name) y logoid presentes en los vectores top.
4. El nº de símbolos filtrados es <= HEATMAP_MAX_SYMBOLS.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PARENT = Path(__file__).resolve().parents[1]
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import config
from scrapper_heatmap_v1 import COLUMN_INDEX, fetch_from_api, filter_top_by_market_cap, parse_vector

OK = []
FALLO = []


def reportar(nombre, condicion, detalle=None):
    if condicion:
        OK.append(f"[OK] {nombre}")
    else:
        FALLO.append(f"[FALLO] {nombre}: {detalle}")


def main():
    print(f"[verificar_endpoints_heatmap] {datetime.now(timezone.utc).isoformat()}Z")

    # 1. El body filtra por exchange con in_range (F3.7, D-manual)
    body = config.HEATMAP_BODY
    exchange_filter = body.get("filter", [])
    reportar("body trae filtro de exchange in_range",
             any(f.get("left") == "exchange" and f.get("operation") == "in_range"
                 for f in exchange_filter),
             str(exchange_filter))

    # 2. Fetch real desde config
    estado, rows = fetch_from_api()
    reportar("heatmap /america/scan responde 'ok'", estado == "ok", estado)
    if estado != "ok" or not rows:
        print("Sin datos válidos; el mercado puede estar cerrado. Fin.")
        print("\n".join(OK))
        sys.exit(1 if FALLO else 0)

    reportar("hay vectores 'd' con las 29 columnas", all(
        len(r.get("d", [])) >= len(config.HEATMAP_COLUMNS) for r in rows),
        f"fila0 len={len(rows[0].get('d', []))}")

    # 3. Aplicar el filtro real de app (F3.7)
    filtered = filter_top_by_market_cap(rows, config.HEATMAP_MAX_SYMBOLS)
    reportar("nº filtrado <= HEATMAP_MAX_SYMBOLS",
             len(filtered) <= config.HEATMAP_MAX_SYMBOLS,
             f"{len(filtered)} <= {config.HEATMAP_MAX_SYMBOLS}")

    otc = [r["s"] for r in filtered if "OTC" in r.get("s", "")]
    preferidas = []
    baja_liq = []
    sin_descripcion = 0
    sin_logo = []
    for r in filtered:
        p = parse_vector(r["d"])
        if p is None:
            continue
        share = p.get("share_class")
        # F3.7: typespecs vacío '' ('equity') o 'common' son admisibles; el
        # resto (preferred/unit/ADR pfd) queda fuera (igual que el filtro real).
        if share not in (None, "", "equity", "common"):
            preferidas.append(r["s"])
        if p.get("dollar_volume_30d") is not None and p["dollar_volume_30d"] < config.HEATMAP_MIN_USD_VOL:
            baja_liq.append(r["s"])
        if not p.get("company_name"):
            sin_descripcion += 1
        if p.get("logo") is None:
            sin_logo.append(r["s"])

    reportar("0 OTC en el conjunto final", otc == [], str(otc[:5]))
    reportar("0 acc. preferentes/unit/ADR-pfd en el conjunto final",
             preferidas == [], str(preferidas[:5]))
    reportar("todas con volumen 30d >= 20M USD o sin dato de volumen",
             baja_liq == [], str(baja_liq[:5]))
    reportar("todas con descripción (company_name)", sin_descripcion == 0, str(sin_descripcion))
    # logoid puede ser '' en TV para algunos símbolos (HON, OKE, HONA, DD);
    # lo importante es que nunca sea None (el parse siempre lo expone).
    reportar("ninguna con logoid None", sin_logo == [], str(sin_logo[:5]))
    print(f"    aviso: {len(sin_logo)} símbolos sin logoid en TV (vacío, normal):")
    for s in sin_logo:
        print(f"      - {s}")

    # 4. Muestra representativa
    for r in filtered[:5]:
        p = parse_vector(r["d"])
        print(f"    muestra: {p['ticker']:>8} | {p['company_name'][:30]:<30}"
              f" | $vol30d={p['dollar_volume_30d']!s:>14} | logo={p['logo']}")

    print("\n--- RESULTADO ---")
    print("\n".join(OK))
    if FALLO:
        print("\n".join(FALLO))
        sys.exit(1)
    print("\nTodo OK: el heatmap sigue devolviendo datos correctos.")


if __name__ == "__main__":
    main()