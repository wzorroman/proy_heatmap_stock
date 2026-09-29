#!/usr/bin/env python3
"""
Notificador Telegram - Receptor de mensajes desde otros sistemas
Uso: ./notificador_telegram.py "Mensaje a enviar"

# ====================
#  -- USOS  --
# ====================
## Pruebas básicas
    # Mensaje simple
    ./notificador_telegram.py "Hola mundo desde consola"

    # Mensaje con título
    ./notificador_telegram.py -t "PRUEBA" "Este es un mensaje de prueba"

    # Mensaje largo (varias líneas)
    ./notificador_telegram.py "Línea 1 del mensaje
    Línea 2 del mensaje
    Línea 3 del mensaje"

    # Mensaje JSON estructurado
    ./notificador_telegram.py -j '{"estado": "OK", "cpu": "45%", "memoria": "2.3GB"}'

    # Mensaje sin formato
    ./notificador_telegram.py -s "Mensaje sin formato ni fecha"

## Pruebas con pipes
    echo "El sistema ha iniciado correctamente" | ./notificador_telegram.py --stdin -t "BOOT"
    cat /var/log/syslog | head -20 | ./notificador_telegram.py --stdin -t "Últimas 20 líneas"

# TODO(fase futura): reemplazar por el paquete compartido `wz_notify`
# (interfaz Notificador + backends pluggables + multi-canal: Slack, webhook,
# etc.). De momento se mantiene este módulo local por simplicidad.
"""

import asyncio
import sys
import argparse
import datetime
import json
import logging
from telegram import Bot
from telegram.constants import ParseMode
import os

logger = logging.getLogger("notificador_telegram")

# Configuración - usar variables de entorno para seguridad.
# Se aceptan TELEGRAM_TOKEN (nombre canónico del repo) y TELEGRAM_BOT_TOKEN.
DEFAULT_PARSE_MODE = "Markdown"


class TelegramNotificador:
    """Clase para manejar el envío de notificaciones a Telegram.

    Si no hay credenciales configuradas (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID), el
    notificador queda DESHABILITADO: cada llamada a `enviar` registra la alerta
    como WARNING en el log y devuelve False, sin lanzar ni abortar el proceso.
    """

    def __init__(self, token=None, chat_id=None, parse_mode=None):
        self.token = (
            token
            or os.getenv("TELEGRAM_TOKEN")
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or ""
        ).strip()

        raw_chat = chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID")
        raw_chat = "" if raw_chat is None else str(raw_chat).strip()

        self.parse_mode = (
            parse_mode
            or os.getenv("TELEGRAM_PARSE_MODE")
            or DEFAULT_PARSE_MODE
        ).strip() or DEFAULT_PARSE_MODE

        self.deshabilitado = False
        self.bot = None
        self.chat_id = None

        if not self.token or not raw_chat:
            self.deshabilitado = True
            logger.warning(
                "Notificador Telegram DESHABILITADO: faltan TELEGRAM_TOKEN/"
                "TELEGRAM_CHAT_ID. Las alertas solo se registrarán en el log."
            )
            return

        try:
            self.chat_id = int(raw_chat)
        except (TypeError, ValueError):
            self.chat_id = raw_chat

        self.bot = Bot(token=self.token)

    def _armar_mensaje(self, mensaje, titulo, parse_mode):
        """Compone el texto con la cabecera adecuada al parse_mode elegido."""
        fecha_formateada = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pm = (parse_mode or "").lower()
        if pm == "html":
            b_open, b_close, i_open, i_close = "<b>", "</b>", "<i>", "</i>"
        elif pm in ("markdown", "markdownv2"):
            b_open, b_close, i_open, i_close = "*", "*", "_", "_"
        else:
            b_open = b_close = i_open = i_close = ""

        if titulo:
            cabecera = f"🔔 {b_open}{titulo}{b_close}\n📅 {i_open}{fecha_formateada}{i_close}"
        else:
            cabecera = (
                f"📨 {b_open}NUEVA NOTIFICACIÓN{b_close}\n"
                f"📅 {i_open}{fecha_formateada}{i_close}"
            )

        return (
            f"{cabecera}\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"{mensaje}\n\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🤖 {i_open}Notificación automática{i_close}"
        )

    async def enviar(self, mensaje, titulo=None, formato=True, parse_mode=None):
        """Envía un mensaje. Nunca lanza: ante cualquier fallo devuelve False.

        - Si no hay credenciales, registra un WARNING y no envía.
        - `parse_mode` configurable (HTML / Markdown / MarkdownV2 / None).
        - Si el envío con formato falla (entidades no escapadas), reintenta una
          vez en texto plano para no perder la alerta.
        """
        if self.deshabilitado:
            logger.warning(
                f"[Telegram deshabilitado] {titulo or 'NOTIFICACIÓN'}: {mensaje}"
            )
            return False

        pm = parse_mode if parse_mode is not None else (self.parse_mode if formato else None)

        if formato:
            texto = self._armar_mensaje(mensaje, titulo, pm)
        else:
            fecha_formateada = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            texto = f"[{fecha_formateada}] {mensaje}"

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=texto.strip(),
                parse_mode=(pm or None),
            )
            logger.info("Mensaje enviado correctamente")
            return True

        except Exception as e:
            logger.error(f"Error al enviar (parse_mode={pm}): {e}")

            if pm:
                try:
                    plano = (
                        self._armar_mensaje(mensaje, titulo, None)
                        if formato
                        else texto
                    )
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=plano.strip(),
                        parse_mode=None,
                    )
                    logger.warning("Reenviado en texto plano (sin parse_mode)")
                    return True
                except Exception as e2:
                    logger.error(f"Error al reenviar en texto plano: {e2}")

            return False

    async def enviar_estructurado(self, datos):
        """Envía datos estructurados (diccionario/JSON)."""
        if isinstance(datos, str):
            try:
                datos = json.loads(datos)
            except Exception:
                return await self.enviar(datos)

        mensaje = ""
        for key, value in datos.items():
            emoji = self._get_emoji(key)
            mensaje += f"{emoji} {key}: {value}\n"

        return await self.enviar(mensaje.strip())

    def _get_emoji(self, key):
        """Asigna emojis según la clave."""
        emojis = {
            'status': '🔴' if 'error' in key.lower() else '🟢',
            'error': '❌',
            'warning': '⚠️',
            'success': '✅',
            'info': 'ℹ️',
            'precio': '💰',
            'cpu': '💻',
            'ram': '📊',
            'disco': '💾',
            'tiempo': '⏰',
            'fecha': '📅'
        }

        for palabra, emoji in emojis.items():
            if palabra in key.lower():
                return emoji
        return '•'


async def main():
    """Función principal con manejo de argumentos."""

    parser = argparse.ArgumentParser(
        description='Enviar notificaciones a Telegram',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s "El servidor ha iniciado"
  %(prog)s -t "ALERTA" "La CPU está al 90%"
  %(prog)s -j '{"status": "error", "cpu": "95%", "memoria": "80%"}'
  echo "Mensaje desde pipe" | %(prog)s
  cat log.txt | %(prog)s -t "LOG DEL SISTEMA"
        """
    )

    parser.add_argument('mensaje', nargs='*', help='Mensaje a enviar')
    parser.add_argument('-t', '--titulo', help='Título de la notificación')
    parser.add_argument('-j', '--json', action='store_true',
                        help='El mensaje es un JSON estructurado')
    parser.add_argument('-s', '--simple', action='store_true',
                        help='Enviar sin formato (solo texto)')
    parser.add_argument('--stdin', action='store_true',
                        help='Leer mensaje desde STDIN (pipe)')

    args = parser.parse_args()

    mensaje = None
    if not sys.stdin.isatty() or args.stdin:
        mensaje = sys.stdin.read().strip()
    elif args.mensaje:
        mensaje = ' '.join(args.mensaje)

    if not mensaje:
        parser.print_help()
        print("\n❌ Error: Debes proporcionar un mensaje")
        sys.exit(1)

    notificador = TelegramNotificador()
    if notificador.deshabilitado:
        print("❌ Error: Debes configurar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID")
        print("\nPuedes hacerlo de dos formas:")
        print("1. Editar el archivo .env del proyecto")
        print("2. Usar variables de entorno:")
        print("   export TELEGRAM_TOKEN='tu_token'")
        print("   export TELEGRAM_CHAT_ID='tu_chat_id'")
        sys.exit(1)

    if args.json:
        exito = await notificador.enviar_estructurado(mensaje)
    else:
        exito = await notificador.enviar(
            mensaje=mensaje,
            titulo=args.titulo,
            formato=not args.simple,
        )

    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
