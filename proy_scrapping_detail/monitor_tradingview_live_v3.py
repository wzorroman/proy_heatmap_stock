#!/usr/bin/env python3
"""
MONITOR DE PROCESOS TRADINGVIEW - SCRAPER Y CALENDARIO V2
=========================================================
Script: monitor_tradingview_live_v2.py
Author: Wilson Zauma
Date: 2026-03-16

DESCRIPCIÓN:
    Monitorea que los procesos de scraping de TradingView estén funcionando correctamente.
    ENVÍA UNA SOLA NOTIFICACIÓN CONSOLIDADA con todas las alertas detectadas.

    - scraper_live_tradingview_v5.py (activos cada 5min)
    - calendario_tradingview_live_v1.py (calendario cada 15min)

    Verifica que los archivos se actualicen dentro de los ciclos esperados:
    - Activos: máx 10min sin actualizar (2 ciclos)
    - Calendario: máx 30min sin actualizar (2 ciclos)
"""

import json
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
import asyncio
import sys
from pathlib import Path
import glob

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"✅ Configuración cargada desde: {env_path}")
    else:
        load_dotenv()
        print("✅ Configuración cargada desde .env (directorio actual)")
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables de entorno del sistema.")
except Exception as e:
    print(f"⚠️  Error cargando .env: {e}")

# Importar notificador de Telegram
try:
    from notificador_telegram import TelegramNotificador
except ImportError:
    print("❌ Error: No se pudo importar TelegramNotificador")
    print("   Asegúrate de que notificador_telegram.py está en el mismo directorio")
    sys.exit(1)

# Configuración desde variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SERVER_ID = os.getenv('SERVER_ID', "WZAUMA")

# Validar configuración de Telegram
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Error: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID deben estar configurados")
    print("   Crea un archivo .env con:")
    print("   TELEGRAM_TOKEN=tu_token")
    print("   TELEGRAM_CHAT_ID=tu_chat_id")
    sys.exit(1)

# Convertir chat_id a entero si es necesario
try:
    TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    pass

MAX_CICLOS_ESPERAR = 2
CICLO_ALERTA_WARNING = 1.5
TIEMPO_ESPERA_MIN_EVITAR_SPAM = 60  # 30 MIN : 1800
# Directorio base
BASE_DIR = Path("DATOS_LIVE")
CALENDARIO_LOG_DIR = BASE_DIR / "calendario_economico" / "logs"

# Configuración de archivos a monitorear
ARCHIVOS_A_MONITOREAR = [
    # Activos del scraper (cada 5 minutos) - Usan timestamp_utc
    {
        'ruta': BASE_DIR / "NASDAQ-QQQ" / "NASDAQ-QQQ.csv",
        'intervalo_minutos': 5,
        'proceso': 'scraper_live_tradingview_v5.py (QQQ)',
        'nombre_archivo': 'NASDAQ-QQQ.csv',
        'tipo': 'activo',
        'campo_timestamp': 'timestamp_utc',
        'cron_config': '*/5 * * * *'
    },
    {
        'ruta': BASE_DIR / "OANDA-XAUUSD" / "OANDA-XAUUSD.csv",
        'intervalo_minutos': 5,
        'proceso': 'scraper_live_tradingview_v5.py (XAUUSD)',
        'nombre_archivo': 'OANDA-XAUUSD.csv',
        'tipo': 'activo',
        'campo_timestamp': 'timestamp_utc',
        'cron_config': '*/5 * * * *'
    },
    {
        'ruta': BASE_DIR / "OANDA-EURUSD" / "OANDA-EURUSD.csv",
        'intervalo_minutos': 5,
        'proceso': 'scraper_live_tradingview_v5.py (EURUSD)',
        'nombre_archivo': 'OANDA-EURUSD.csv',
        'tipo': 'activo',
        'campo_timestamp': 'timestamp_utc',
        'cron_config': '*/5 * * * *'
    },
    # Calendario económico (cada 15 minutos) - Usa timestamp_captura
     {
        'ruta': BASE_DIR / "calendario_economico" / "checkpoint.json",  # ← Cambiado a checkpoint.json
        'intervalo_minutos': 15,
        'proceso': 'calendario_tradingview_live_v2.py',
        'nombre_archivo': 'checkpoint.json',
        'tipo': 'calendario',
        'campo_timestamp': 'fecha_ultima_revision',  # ← Campo en el checkpoint
        'es_json': True,  # ← Nuevo: indica que es archivo JSON
        'log_dir': BASE_DIR / "calendario_economico" / "logs",
        'cron_config': '*/15 * * * *'
    }
]


class MonitorTradingView:
    def __init__(self):
        self.notificador = TelegramNotificador(
            token=TELEGRAM_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        self.alertas_previas = self.cargar_alertas_previas()
        self.archivo_estado = Path(__file__).parent / 'ultima_alerta_tradingview.json'

    def cargar_alertas_previas(self):
        """Carga el registro de alertas previas para evitar spam"""
        alertas_file = Path(__file__).parent / 'alertas_tradingview_previas.txt'
        alertas = {}

        if alertas_file.exists():
            with open(alertas_file, 'r') as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea:
                        continue

                    partes = linea.split('|')
                    if len(partes) >= 2:
                        proceso = partes[0]
                        timestamp = partes[-1]

                        if len(partes) > 2:
                            proceso = '|'.join(partes[:-1])

                        alertas[proceso] = timestamp

        return alertas

    def debe_enviar_alerta_agrupada(self):
        """Verifica si debe enviar una alerta agrupada (evita spam cada 30 minutos)"""
        if not self.archivo_estado.exists():
            return True

        try:
            with open(self.archivo_estado, 'r') as f:
                ultima_alerta = json.load(f)

            ultima_fecha = datetime.fromisoformat(ultima_alerta['fecha'])
            diferencia = datetime.now() - ultima_fecha

            # Solo enviar si pasaron más de 30 minutos desde la última alerta
            if diferencia.total_seconds() < TIEMPO_ESPERA_MIN_EVITAR_SPAM:
                print(f"  ⏰ Alerta reciente (hace {diferencia.total_seconds()/60:.1f} min) - No se envía notificación duplicada")
                return False
            return True
        except:
            return True

    def guardar_estado_alerta(self, alertas_data):
        """Guarda el estado de la última alerta enviada"""
        try:
            # Crear directorio si no existe
            self.archivo_estado.parent.mkdir(exist_ok=True)

            with open(self.archivo_estado, 'w') as f:
                json.dump({
                    'fecha': datetime.now().isoformat(),
                    'total_alertas': len(alertas_data),
                    'procesos': [a['nombre'] for a in alertas_data]
                }, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Error guardando estado: {e}")

    def obtener_ultimas_lineas_log(self, log_dir, n_lineas=50):
        """Obtiene las últimas n líneas del log más reciente"""
        if not log_dir or not os.path.exists(log_dir):
            return None, "Directorio de logs no encontrado"

        # Buscar archivos de log ordenados por fecha (más reciente primero)
        log_files = sorted(glob.glob(str(log_dir / "calendario_*.log")), reverse=True)

        if not log_files:
            return None, "No se encontraron archivos de log"

        try:
            with open(log_files[0], 'r') as f:
                lines = f.readlines()
                ultimas_lineas = lines[-n_lineas:] if len(lines) > n_lineas else lines
                return log_files[0], ''.join(ultimas_lineas)
        except Exception as e:
            return None, f"Error leyendo log: {str(e)}"

    def obtener_ultimo_timestamp(self, archivo, tipo='activo', campo_timestamp=None):
        """
        Lee el último timestamp del archivo CSV o JSON
        - Para activos: usa campo 'timestamp_utc' (momento de la captura del precio)
        - Para calendario: usa checkpoint.json con campo 'fecha_ultima_revision'
        """
        try:
            if not os.path.exists(archivo):
                return None, None, "Archivo no encontrado", None

            # Si es calendario y el archivo es checkpoint.json, usar método específico
            if tipo == 'calendario' and archivo.name == 'checkpoint.json':
                return self.obtener_ultimo_timestamp_checkpoint(archivo)

            # Para CSV (activos)
            df = pd.read_csv(archivo)

            if df.empty:
                return None, None, "Archivo vacío", None

            # Determinar qué campo de timestamp usar según el tipo
            if tipo == 'calendario':
                # Para calendario (eventos_calendario.csv) - mantener compatibilidad
                campo = 'timestamp_captura'
                if campo not in df.columns:
                    return None, None, f"Campo '{campo}' no encontrado en calendario", None
            else:
                # Para activos, usar timestamp_utc (campo por defecto)
                campo = campo_timestamp or 'timestamp_utc'
                if campo not in df.columns:
                    # Intentar con 'timestamp' como fallback
                    if 'timestamp' in df.columns:
                        campo = 'timestamp'
                    else:
                        return None, None, f"No se encontró campo de timestamp en activos", None

            ultimo_timestamp = df[campo].iloc[-1]

            # Convertir a numérico si es string
            try:
                ultimo_timestamp = float(ultimo_timestamp)
            except:
                pass

            # Buscar fecha legible si existe (solo para información)
            fecha_str = None
            if 'fecha_humana' in df.columns:
                fecha_str = df['fecha_humana'].iloc[-1]
            elif 'datetime' in df.columns:
                fecha_str = df['datetime'].iloc[-1]
            elif 'fecha_iso' in df.columns:
                fecha_str = df['fecha_iso'].iloc[-1]

            # Verificar timestamp futuro (solo para activos, en calendario puede ser normal)
            ahora = datetime.now(timezone.utc).timestamp()
            if tipo == 'activo' and isinstance(ultimo_timestamp, (int, float)) and ultimo_timestamp > ahora + 3600:
                return None, None, f"⚠️ Timestamp en el futuro: {datetime.fromtimestamp(ultimo_timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}", None

            return ultimo_timestamp, fecha_str, None, campo

        except Exception as e:
            return None, None, f"Error leyendo archivo: {str(e)}", None
    
    def obtener_ultimo_timestamp_checkpoint(self, archivo):
        """
        Lee el último timestamp del archivo checkpoint.json del calendario
        
        Args:
            archivo: Ruta al archivo checkpoint.json
            
        Returns:
            tuple: (ultimo_timestamp, fecha_str, error, campo_usado)
        """
        try:
            if not os.path.exists(archivo):
                return None, None, "Archivo checkpoint no encontrado", None

            with open(archivo, 'r') as f:
                checkpoint = json.load(f)
            
            # Obtener la fecha de última revisión
            fecha_ultima_revision = checkpoint.get('fecha_ultima_revision')
            
            if not fecha_ultima_revision:
                return None, None, "Campo 'fecha_ultima_revision' no encontrado en checkpoint", None
            
            # Convertir a datetime
            try:
                ultima_fecha = datetime.fromisoformat(fecha_ultima_revision)
                ultimo_timestamp = ultima_fecha.timestamp()
                fecha_str = ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')
                
                # También mostrar información adicional del checkpoint
                eventos_encontrados = checkpoint.get('eventos_encontrados', 0)
                eventos_acumulados = checkpoint.get('eventos_acumulados', 0)
                ultimo_evento = checkpoint.get('ultima_fecha', 'N/A')
                
                return ultimo_timestamp, fecha_str, None, 'fecha_ultima_revision'
                
            except Exception as e:
                return None, None, f"Error parseando fecha: {e}", None
                
        except json.JSONDecodeError as e:
            return None, None, f"Error decodificando JSON: {e}", None
        except Exception as e:
            return None, None, f"Error leyendo checkpoint: {e}", None
        
    async def enviar_alerta_agrupada(self, alertas_data, log_calendario=None):
        """Envía UNA SOLA notificación con todas las alertas agrupadas"""
        try:
            # Verificar si debemos enviar la alerta
            if not self.debe_enviar_alerta_agrupada():
                return

            # Construir mensaje agrupado
            lines = []
            lines.append(f"🚨 *[{SERVER_ID}] PROCESOS LIVE CAÍDOS* | [{len(alertas_data)}]")
            # lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            # lines.append(f"🔴 Total: {len(alertas_data)} procesos\n")

            # Agrupar por tipo para mejor organización
            activos_alerta = [a for a in alertas_data if a['tipo'] == 'activo']
            calendario_alerta = [a for a in alertas_data if a['tipo'] == 'calendario']

            if activos_alerta:
                lines.append("📈 * --- ACTIVOS --- (c/5min):*")
                for alerta in activos_alerta:
                    lines.append(f"  • *{alerta['nombre']}*")
                    lines.append(f"    ⚙️ {alerta['proceso']}")
                    lines.append(f"    📅 Último: {alerta['ultima_fecha']}")
                    lines.append(f"    ⏱️ hace {alerta['diferencia']:.1f} min | {alerta['ciclos_perdidos']:.1f} ciclos perdidos")
                    if alerta.get('error'):
                        lines.append(f"    ⚠️ {alerta['error']}")
                    lines.append("")

            if calendario_alerta:
                lines.append("📅 * --- CALENDARIO --- (c/15min):*")
                for alerta in calendario_alerta:
                    lines.append(f"  • *{alerta['nombre']}*")
                    lines.append(f"    ⚙️ {alerta['proceso']}")
                    if alerta.get('error'):
                        lines.append(f"    ⚠️ {alerta['error']}")
                    else:
                        lines.append(f"    📅 Última ejecución: {alerta['ultima_fecha']}")
                        lines.append(f"    ⏱️ hace {alerta['diferencia']:.1f} min | {alerta['ciclos_perdidos']:.1f} ciclos perdidos")
                        # 🔥 NUEVO: Mostrar información adicional del calendario
                        if alerta.get('eventos_encontrados') is not None:
                            lines.append(f"    📊 Eventos encontrados: {alerta['eventos_encontrados']}")
                        if alerta.get('ultimo_evento') and alerta['ultimo_evento'] != 'N/A':
                            lines.append(f"    🕒 Último evento: {alerta['ultimo_evento']}")
                    lines.append("")

            # Añadir últimas líneas del log del calendario si está disponible
            if log_calendario and log_calendario[0] and log_calendario[1]:
                log_file, log_content = log_calendario
                lines.append(f"📋 *Últimas líneas del log ({os.path.basename(log_file)}):*")
                lines.append("```")
                # Limitar a 1000 caracteres para no exceder límite de Telegram
                lines.append(log_content[:1000])
                if len(log_content) > 1000:
                    lines.append("...[truncado]")
                lines.append("```\n")

            lines.append("🔍 *Acciones recomendadas:*")
            lines.append("1. Verificar procesos manualmente")
            lines.append("2. Revisar logs completos en sus respectivas carpetas")
            lines.append("3. Reiniciar los procesos si es necesario")

            mensaje = "\n".join(lines)

            # Enviar notificación
            await self.notificador.enviar(
                mensaje=mensaje,
                titulo=f"⚠️ {len(alertas_data)} PROCESOS CAÍDOS"
            )

            print(f"\n   📱 Alerta agrupada enviada ({len(alertas_data)} procesos)")

            # Guardar estado
            self.guardar_estado_alerta(alertas_data)

        except Exception as e:
            print(f"   ❌ Error enviando alerta agrupada: {str(e)}")

    async def verificar_procesos(self):
        """Verifica todos los procesos configurados"""
        print(f"MONITOR DE PROCESOS TRADINGVIEW - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("=" * 100)

        hora_actual = datetime.now(timezone.utc)
        print(f"Hora actual UTC: {hora_actual.strftime('%Y-%m-%d %H:%M:%S')}\n")

        alertas_data = []  # Lista para almacenar datos de alertas
        warnings = []
        estados = []
        log_calendario = None

        for config in ARCHIVOS_A_MONITOREAR:
            ruta = config['ruta']
            intervalo = config['intervalo_minutos']
            proceso = config['proceso']
            nombre = config['nombre_archivo']
            tipo = config['tipo']

            print(f"\n📁 ANALIZANDO: {nombre}")
            print(f"   Proceso: {proceso}")
            print(f"   Tipo: {tipo} | Intervalo: cada {intervalo} min")

            # Verificar archivo
            if not os.path.exists(ruta):
                msg = f"❌ ERROR: Archivo no encontrado"
                print(f"   {msg}")
                alertas_data.append({
                    'nombre': nombre,
                    'proceso': proceso,
                    'tipo': tipo,
                    'error': 'ARCHIVO NO ENCONTRADO',
                    'diferencia': None,
                    'ciclos_perdidos': None,
                    'ultima_fecha': None
                })
                estados.append({
                    'nombre': nombre,
                    'proceso': proceso,
                    'estado': 'ERROR',
                    'ultima_fecha': None,
                    'diferencia': None
                })
                continue

            # Obtener último timestamp
            ultimo_timestamp, fecha_str, error, campo_usado = self.obtener_ultimo_timestamp(
                ruta, tipo, config.get('campo_timestamp')
            )

            if error:
                print(f"  ❌ ERROR: {error}")
                alertas_data.append({
                    'nombre': nombre,
                    'proceso': proceso,
                    'tipo': tipo,
                    'error': error,
                    'diferencia': None,
                    'ciclos_perdidos': None,
                    'ultima_fecha': None
                })
                estados.append({
                    'nombre': nombre,
                    'proceso': proceso,
                    'estado': 'ERROR',
                    'ultima_fecha': None,
                    'diferencia': None
                })
                continue

            # Mostrar qué campo estamos usando (útil para debugging)
            print(f"   📊 Usando campo: {campo_usado}")

            # Convertir timestamp a datetime
            if isinstance(ultimo_timestamp, (int, float)):
                ultima_fecha = datetime.fromtimestamp(ultimo_timestamp, tz=timezone.utc)
                fecha_str_formateada = ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Intentar parsear como string ISO
                try:
                    ultima_fecha = datetime.fromisoformat(str(ultimo_timestamp).replace('Z', '+00:00'))
                    fecha_str_formateada = ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    print(f"   ❌ ERROR: Formato de timestamp no reconocido: {ultimo_timestamp}")
                    continue

            # Calcular diferencia
            diferencia = hora_actual - ultima_fecha
            minutos_diferencia = diferencia.total_seconds() / 60
            ciclos_perdidos = minutos_diferencia / intervalo

            # Mostrar información
            print(f"   📅 Último dato: {fecha_str_formateada}")
            
            # 🔥 NUEVO: Si es calendario y es checkpoint.json, mostrar información adicional
            if tipo == 'calendario' and nombre == 'checkpoint.json':
                try:
                    with open(ruta, 'r') as f:
                        checkpoint = json.load(f)
                    
                    eventos_encontrados = checkpoint.get('eventos_encontrados', 0)
                    eventos_acumulados = checkpoint.get('eventos_acumulados', 0)
                    ultimo_evento = checkpoint.get('ultima_fecha', 'N/A')
                    
                    print(f"   📊 Eventos encontrados: {eventos_encontrados} | Nuevos: {eventos_acumulados}")
                    if ultimo_evento != 'N/A':
                        print(f"   🕒 Último evento capturado: {ultimo_evento}")
                except Exception as e:
                    print(f"   ⚠️ No se pudo leer info adicional del checkpoint: {e}")
            
            if fecha_str:
                print(f"   📅 Fecha registro: {fecha_str}")
            print(f"   ⏱️  Diferencia: {minutos_diferencia:.1f} min ({ciclos_perdidos:.1f} ciclos)")

            # Determinar estado
            if ciclos_perdidos > MAX_CICLOS_ESPERAR:  # Nota: Tiene typo en tu variable MAX_CICLOS_ESPERAR
                estado = "🔴 ALERTA"
                msg = f"❌ PROCESO CAÍDO: Sin datos por {minutos_diferencia:.1f} minutos"
                print(f"   {estado}: {msg}")

                # Agregar a lista de alertas
                alerta_info = {
                    'nombre': nombre,
                    'proceso': proceso,
                    'tipo': tipo,
                    'diferencia': minutos_diferencia,
                    'ciclos_perdidos': ciclos_perdidos,
                    'ultima_fecha': fecha_str_formateada,
                    'error': None
                }
                
                # 🔥 NUEVO: Agregar info del checkpoint a la alerta si es calendario
                if tipo == 'calendario' and nombre == 'checkpoint.json':
                    try:
                        with open(ruta, 'r') as f:
                            checkpoint = json.load(f)
                        alerta_info['eventos_encontrados'] = checkpoint.get('eventos_encontrados', 0)
                        alerta_info['ultimo_evento'] = checkpoint.get('ultima_fecha', 'N/A')
                    except:
                        pass
                
                alertas_data.append(alerta_info)

                # Obtener últimas líneas del log si es calendario
                if tipo == 'calendario' and 'log_dir' in config and not log_calendario:
                    log_calendario = self.obtener_ultimas_lineas_log(config['log_dir'], 50)
                    if log_calendario and log_calendario[1]:
                        print(f"   📋 Últimas líneas del log obtenidas")

            elif ciclos_perdidos > CICLO_ALERTA_WARNING:
                estado = "🟡 ADVERTENCIA"
                msg = f"⚠️  Sin datos por {minutos_diferencia:.1f} minutos "
                warnings.append(f"{proceso} - {nombre}: {msg}")
                print(f"   {estado}: {msg}")
            else:
                estado = "🟢 OK"
                msg = f"✅ Funcionando correctamente"
                print(f"   {estado}: {msg}")

            estados.append({
                'nombre': nombre,
                'proceso': proceso,
                'estado': 'ALERTA' if ciclos_perdidos > MAX_CICLOS_ESPERAR else 'WARNING' if ciclos_perdidos > CICLO_ALERTA_WARNING else 'OK',
                'ultima_fecha': fecha_str_formateada,
                'diferencia': minutos_diferencia,
                'ciclos_perdidos': ciclos_perdidos,
                'tipo': tipo
            })

        # Mostrar resumen
        self.mostrar_resumen(estados, alertas_data, warnings)

        # ENVIAR UNA SOLA ALERTA AGRUPADA si hay alertas
        if alertas_data:
            await self.enviar_alerta_agrupada(alertas_data, log_calendario)

        # Guardar log de ejecución
        self.guardar_log_ejecucion(alertas_data)

        return alertas_data

    def mostrar_resumen(self, estados, alertas_data, warnings):
        """Muestra un resumen formateado del estado de los procesos"""
        print("📊 RESUMEN DE ESTADO")
        print("=" * 40)

        # Agrupar por tipo
        activos = [e for e in estados if e.get('tipo') == 'activo']
        calendarios = [e for e in estados if e.get('tipo') == 'calendario']

        if activos:
            print("\n📈 --- ACTIVOS --- (c/5min):")
            for e in activos:
                emoji = "✅" if e['estado'] == 'OK' else "⚠️" if e['estado'] == 'WARNING' else "❌"
                fecha_str = e['ultima_fecha'] if e['ultima_fecha'] else "N/A"
                diff_str = f"{e['diferencia']:.1f} min" if e['diferencia'] else "N/A"
                print(f"  {emoji} {e['nombre']:<20} {e['estado']:<10} {fecha_str} ({diff_str})")

        if calendarios:
            print("\n📅 --- CALENDARIO --- (c/15min):")
            for e in calendarios:
                emoji = "✅" if e['estado'] == 'OK' else "⚠️" if e['estado'] == 'WARNING' else "❌"
                fecha_str = e['ultima_fecha'] if e['ultima_fecha'] else "N/A"
                diff_str = f"{e['diferencia']:.1f} min" if e['diferencia'] else "N/A"
                print(f"  {emoji} {e['nombre']:<20} {e['estado']:<10} {fecha_str} ({diff_str})")

        if warnings:
            print("\n" + "=" * 100)
            print("⚠️  ADVERTENCIAS")
            print("=" * 100)
            for warning in warnings:
                print(f"   {warning}")

        if alertas_data:
            print("\n" + "=" * 100)
            print(f"🚨 {len(alertas_data)} ALERTA(S) CRÍTICA(S) DETECTADA(S)")
            print("=" * 100)
            for alerta in alertas_data:
                if alerta.get('error'):
                    print(f"   ❌ {alerta['proceso']} - {alerta['nombre']}: {alerta['error']}")
                else:
                    print(f"   ❌ {alerta['proceso']} - {alerta['nombre']}: {alerta['diferencia']:.1f} min sin datos")
        else:
            print("\n✅ ¡FELICIDADES! Todos los procesos funcionando correctamente")

    def guardar_log_ejecucion(self, alertas_data):
        """Guarda un registro de la ejecución"""
        log_dir = Path(__file__).parent / 'logs_ejecucion'
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f'monitor_tradingview_{datetime.now().strftime("%Y%m%d")}.log'

        with open(log_file, 'a') as f:
            f.write(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Ejecución monitor\n")
            if alertas_data:
                for alerta in alertas_data:
                    if alerta.get('error'):
                        f.write(f"  ALERTA: {alerta['proceso']} - {alerta['nombre']}: {alerta['error']}\n")
                    else:
                        f.write(f"  ALERTA: {alerta['proceso']} - {alerta['nombre']}: {alerta['diferencia']:.1f} min sin datos\n")
            else:
                f.write("  OK: Todos los procesos funcionando\n")

        print(f"\n📝 Log guardado en: {log_file}")


async def main():
    """Función principal"""
    monitor = MonitorTradingView()

    try:
        print(f"\n🔍 [{SERVER_ID}] INICIANDO MONITOREO DE PROCESOS TRADINGVIEW...\n")
        alertas = await monitor.verificar_procesos()

        # Salir con código de error si hay alertas
        if alertas:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error en la ejecución: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())
