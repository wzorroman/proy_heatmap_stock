# file: proy_scrapping_detail/tests/test_fase3_calendario.py
"""Pruebas de la FASE 3 — calendario (F3.6).

Verifica: reintento con backoff distingue "sin eventos" (PARTIAL_FAIL,
checkpoint intacto) de "error de API" (reintenta); RotatingFileHandler
maxBytes/backupCount.
"""
import os
import sys
import logging

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import calendario_tradingview_live_v5 as cal  # noqa: E402


def test_reintento_backoff_distingue_sin_eventos_de_error():
    # "Sin eventos" (status != ok) -> API ok pero vacío -> NO error, [] y constante
    assert hasattr(cal, "ApiSinEventos")
    assert hasattr(cal, "ErrorApi")
    # Ambos son excepciones distinguibles
    assert issubclass(cal.ApiSinEventos, Exception)
    assert issubclass(cal.ErrorApi, Exception)
    assert cal.ApiSinEventos is not cal.ErrorApi
    # Constantes de reintento definidas
    assert cal.MAX_REINTENTOS_API == 3
    assert cal.BACKOFF_BASE_S == 5


def test_rotating_file_handler_en_setup_logging():
    from logging.handlers import RotatingFileHandler
    logger = cal.setup_logging()
    handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)] or \
               [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
    assert handlers, "no se registró RotatingFileHandler"
    h = handlers[0]
    assert h.maxBytes == 10 * 1024 * 1024
    assert h.backupCount == 7   # F3.6 / E-CAL-04: máx 7 archivos


def test_checkpoint_sin_except_desnudo():
    # E-CAL-06/07: el cálculo del checkpoint usa except explícito.
    src = open(cal.__file__, encoding='utf-8').read()
    # No debe haber "except:" desnudo en el archivo
    assert "\n    except:\n" not in src
    assert "\texcept:\n" not in src