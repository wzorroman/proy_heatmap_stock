"""proy_dashboard — prototipo de dashboard de contexto de mercado."""

try:
    from core.settings import VERSION as __version__
except Exception:  # pragma: no cover - fallback si se importa como paquete
    __version__ = "1.0.20"
