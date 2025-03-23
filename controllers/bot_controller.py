from telegram import Update, error as telegram_error
from telegram.ext import ContextTypes
from models.command_executor import CommandExecutor
from models.system_info import SystemInfo
from utils.logger import logger
from config.config import TELEGRAM_GROUP
from functools import wraps
import psutil
import os
from datetime import datetime
import socket
import platform
import asyncio

class BotController:
    def __init__(self):
        self.command_executor = CommandExecutor()
        self.system_info = SystemInfo()
        self.modo_terminal = False
        self.max_retries = 3
        self.welcome_sent = False
        
    async def send_welcome_message(self, bot):
        """Envía mensaje de bienvenida al iniciar el bot"""
        if not self.welcome_sent:
            welcome_text = (
                "🚀 *¡Bot Iniciado!*\n\n"
                "El bot está listo para recibir comandos.\n\n"
                "📌 *Comandos de Terminal:*\n"
                "/run - 🖥️ Activar modo terminal\n"
                "/exit - ⛔ Desactivar modo terminal\n\n"
                "📊 *Comandos de Monitoreo:*\n"
                "/info - 📋 Información del sistema\n"
                "/ps - 📈 Lista de procesos activos\n"
                "/net - 🌐 Estado de la red\n"
                "/disk - 💾 Uso detallado del disco\n\n"
            )
            try:
                if TELEGRAM_GROUP:
                    await bot.send_message(chat_id=TELEGRAM_GROUP, text=welcome_text, parse_mode='Markdown')
                    self.welcome_sent = True
                    logger.info("Mensaje de bienvenida enviado")
            except Exception as e:
                logger.error(f"Error al enviar mensaje de bienvenida: {e}")

    async def send_message_with_retry(self, message, text, parse_mode=None):
        """Envía un mensaje con reintentos en caso de timeout"""
        for attempt in range(self.max_retries):
            try:
                return await message.reply_text(text, parse_mode=parse_mode)
            except telegram_error.TimedOut:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)

    async def edit_message_with_retry(self, message, text, parse_mode=None):
        """Edita un mensaje con reintentos en caso de timeout"""
        for attempt in range(self.max_retries):
            try:
                return await message.edit_text(text, parse_mode=parse_mode)
            except telegram_error.TimedOut:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
            except telegram_error.BadRequest:
                return await self.send_message_with_retry(message.chat, text, parse_mode)

    def validate_access(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = str(update.effective_user.id)
            username = update.effective_user.username or "Sin username"
            
            if not TELEGRAM_GROUP or user_id != TELEGRAM_GROUP:
                logger.warning(f"Acceso denegado - Usuario: {username} (ID: {user_id})")
                await self.send_message_with_retry(update.message, "Acceso denegado")
                return
            
            logger.info(f"Comando ejecutado por admin {username} (ID: {user_id})")
            
            # Mostrar mensaje de espera con reintentos
            try:
                wait_message = await self.send_message_with_retry(
                    update.message,
                    "⏳ *Procesando su solicitud...*",
                    parse_mode='Markdown'
                )
                
                try:
                    result = await func(self, update, context, *args, **kwargs)
                    await wait_message.delete()
                    return result
                except telegram_error.TimedOut:
                    # Reintento del comando
                    for attempt in range(self.max_retries - 1):
                        try:
                            result = await func(self, update, context, *args, **kwargs)
                            await wait_message.delete()
                            return result
                        except telegram_error.TimedOut:
                            continue
                    await self.edit_message_with_retry(
                        wait_message,
                        "❌ Error: Tiempo de espera agotado. Intenta nuevamente."
                    )
                except Exception as e:
                    logger.error(f"Error en comando: {str(e)}")
                    await self.edit_message_with_retry(
                        wait_message,
                        f"❌ Error: {str(e)}"
                    )
            except telegram_error.TimedOut:
                logger.error("Error al enviar mensaje de espera")
                await self.send_message_with_retry(
                    update.message,
                    "❌ Error de conexión. Intenta nuevamente."
                )
        return wrapper

    @validate_access
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 *Bot - Comandos Disponibles*\n\n"
            "\n📌 *Comandos de Terminal:*\n"
            "/run - 🖥️ Activar modo terminal\n"
            "/exit - ⛔ Desactivar modo terminal\n\n"
            "📊 *Comandos de Monitoreo:*\n"
            "/info - 📋 Información del sistema\n"
            "/ps - 📈 Lista de procesos activos\n"
            "/net - 🌐 Estado de la red\n"
            "/disk - 💾 Uso detallado del disco"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    @validate_access
    async def run_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.modo_terminal = True
        await update.message.reply_text(
            "🖥️ *Modo Terminal Activado*\n"
            "Puedes ejecutar comandos directamente.\n"
            "Usa /exit para salir.",
            parse_mode='Markdown'
        )

    @validate_access
    async def exit_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.modo_terminal = False
        await update.message.reply_text(
            "🚫 *Modo Terminal Desactivado*",
            parse_mode='Markdown'
        )

    @validate_access
    async def info_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            uname = platform.uname()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            info = self.system_info.get_system_info()
            
            if info:
                message = (
                    "🖥️ *Información Detallada del Sistema*\n\n"
                    f"*Sistema:* `{uname.system} {uname.release}`\n"
                    f"*Hostname:* `{uname.node}`\n"
                    f"*Arquitectura:* `{uname.machine}`\n"
                    f"*CPU:* `{psutil.cpu_count()} cores ({info['cpu_usage']} uso)`\n"
                    f"*RAM Total:* `{info['memory_total']}`\n"
                    f"*RAM Usada:* `{info['memory_used']}` ({info['memory_percent']})\n"
                    f"*Disco Total:* `{info['disk_total']}`\n"
                    f"*Disco Usado:* `{info['disk_used']}` ({info['disk_percent']})\n"
                    f"*Tiempo Activo:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                    f"*Inicio Sistema:* `{boot_time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                    f"*Dir Actual:* `{info['current_dir']}`"
                )
            else:
                message = "❌ Error obteniendo información del sistema"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    @validate_access
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.modo_terminal:
            await self.send_message_with_retry(
                update.message,
                "❌ Modo terminal no está activo. Usa /run para activarlo.",
                parse_mode='Markdown'
            )
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "Sin username"
        comando = update.message.text.strip()
        
        logger.info(f"Comando recibido de {username} (ID: {user_id}): {comando}")
        
        try:
            espera_message = await self.send_message_with_retry(
                update.message,
                "⏳ Ejecutando comando..."
            )

            result, error = self.command_executor.execute_command(comando)
            
            if error:
                logger.error(f"Error ejecutando comando de {username}: {error}")
                await self.edit_message_with_retry(espera_message, f"❌ {error}")
                return

            # Formatear el mensaje final
            output_message = f"$ {comando}\n{result if result else 'Comando ejecutado con éxito'}"
            
            if len(output_message) > 4000:
                output_message = output_message[:1500] + "\n...\n" + output_message[-1500:]

            logger.info(f"Comando ejecutado exitosamente para {username}")
            await self.edit_message_with_retry(espera_message, output_message)
        except telegram_error.TimedOut:
            logger.error(f"Error de timeout al procesar comando de {username}")
            await self.send_message_with_retry(
                update.message,
                "❌ Error de conexión. Intenta nuevamente."
            )

    @validate_access
    async def ps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Ordenar por uso de CPU
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            message = "📈 *Top 10 Procesos Activos*\n\n"
            message += "```\n"
            message += "🔵 PROCESO      CPU%   MEM%   ESTADO\n"
            message += "═" * 40 + "\n"
            
            for proc in processes[:10]:
                status_emoji = "🟢" if proc['status'] == 'running' else "⚪"
                message += f"{status_emoji} {proc['name'][:10]:<10} {proc['cpu_percent']:>5.1f} {proc['memory_percent']:>6.1f}  {proc['status'][:8]}\n"
            message += "\n📊 Total procesos: {}".format(len(processes))
            message += "```"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo procesos: {str(e)}")

    @validate_access
    async def net_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            interfaces = psutil.net_if_stats()
            io_counters = psutil.net_io_counters(pernic=True)
            addrs = psutil.net_if_addrs()
            
            message = "🌐 *Interfaces de Red*\n\n"
            
            for iface, stats in interfaces.items():
                status = '🟢 ACTIVO' if stats.isup else '🔴 INACTIVO'
                message += f"📡 *{iface}* ({status})\n"
                
                # Mostrar direcciones IP
                if iface in addrs:
                    for addr in addrs[iface]:
                        if addr.family.name == 'AF_INET':  # IPv4
                            message += f"└─ IP: `{addr.address}`\n"
                        elif addr.family.name == 'AF_INET6':  # IPv6
                            message += f"└─ IPv6: `{addr.address[:10]}...`\n"
                
                if iface in io_counters:
                    io = io_counters[iface]
                    # Convertir a unidades más legibles
                    sent = io.bytes_sent
                    recv = io.bytes_recv
                    
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if sent < 1024:
                            sent_str = f"{sent:.1f} {unit}"
                            break
                        sent /= 1024
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if recv < 1024:
                            recv_str = f"{recv:.1f} {unit}"
                            break
                        recv /= 1024
                        
                    message += f"└─ 📤 Enviado: `{sent_str}`\n"
                    message += f"└─ 📥 Recibido: `{recv_str}`\n"
                message += "\n"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estado de red: {str(e)}")

    @validate_access
    async def disk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            message = "💾 *Almacenamiento del Sistema*\n\n"
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    # Calcular porcentaje usado para la barra de progreso
                    used_percent = usage.percent
                    progress_bar = self._generate_progress_bar(used_percent)
                    
                    message += f"📂 *{partition.mountpoint}*\n"
                    message += f"└─ Tipo: `{partition.fstype}`\n"
                    message += f"└─ {progress_bar} {used_percent}%\n"
                    
                    # Convertir tamaños a la unidad más apropiada
                    total = self._format_size(usage.total)
                    used = self._format_size(usage.used)
                    free = self._format_size(usage.free)
                    
                    message += f"└─ Total: `{total}`\n"
                    message += f"└─ Usado: `{used}`\n"
                    message += f"└─ Libre: `{free}`\n\n"
                except Exception:
                    continue

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo información de disco: {str(e)}")

    def _generate_progress_bar(self, percent, length=10):
        filled = int(percent / 100 * length)
        empty = length - filled
        return f"[{'■' * filled}{'□' * empty}]"

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"



