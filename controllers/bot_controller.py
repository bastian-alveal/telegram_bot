from telegram import Update, error as telegram_error, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from models.command_executor import CommandExecutor
from models.system_info import SystemInfo
from models.alert_system import AlertSystem
from models.user_manager import UserManager, UserRole
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
        self.alert_system = AlertSystem()
        self.user_manager = UserManager()
        self.modo_terminal = False
        self.max_retries = 3
        self.welcome_sent = False
        self._bot = None
        self._alert_check_task = None
        self._owner_id = None
        
    async def notify_owner(self, message: str):
        """Notifica al owner sobre eventos importantes"""
        try:
            if not self._owner_id:
                # Buscar al owner en la lista de usuarios
                users = self.user_manager.list_users()
                owner = next((user for user in users if user['role'].lower() == 'owner'), None)
                if owner:
                    self._owner_id = owner['id']
            
            if self._owner_id:
                await self._bot.send_message(
                    chat_id=self._owner_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error notificando al owner: {e}")
        
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
            
            # Verificar si el usuario está registrado
            permissions = self.user_manager.get_user_permissions(user_id)
            if not permissions:
                logger.warning(f"Acceso denegado - Usuario: {username} (ID: {user_id})")
                # Generar alerta de seguridad
                alert = self.alert_system.check_unauthorized_access(user_id, username)
                if alert:
                    await self._send_alert(context.bot, alert)
                await self.send_message_with_retry(update.message, "Acceso denegado")
                return
            
            # Verificar permisos específicos
            command = func.__name__
            if command in ['run_commands', 'handle_message'] and not permissions.can_execute_commands:
                await self.send_message_with_retry(update.message, "❌ No tienes permiso para ejecutar comandos")
                return
            elif command.startswith('add_user') and not permissions.can_manage_users:
                await self.send_message_with_retry(update.message, "❌ No tienes permiso para gestionar usuarios")
                return
            elif command.startswith('alert') and not permissions.can_manage_alerts:
                await self.send_message_with_retry(update.message, "❌ No tienes permiso para gestionar alertas")
                return
            
            # Notificar al owner si el comando es ejecutado por otro usuario
            user_role = self.user_manager.get_user_role(user_id)
            if user_role != UserRole.OWNER and command not in ['users', 'help', 'start']:
                # Obtener el username desde el registro de usuarios
                users = self.user_manager.list_users()
                user = next((u for u in users if u['id'] == user_id), None)
                notify_username = user['username'] if user else username
                
                await self.notify_owner(
                    f"💻 *Comando:* `{update.message.text}`\n"
                    f"Por: `{notify_username}` ({user_role.value})"
                )
            
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
        user_id = str(update.effective_user.id)
        permissions = self.user_manager.get_user_permissions(user_id)
        
        help_text = "🤖 *Bot - Comandos Disponibles*\n\n"
        
        # Comandos de monitoreo (disponibles para todos)
        help_text += "📊 *Comandos de Monitoreo:*\n"
        help_text += "/info - Información del sistema\n"
        help_text += "/ps - Lista de procesos activos\n"
        help_text += "/net - Estado de la red\n"
        help_text += "/disk - Uso detallado del disco\n\n"
        
        # Comandos de terminal (solo para usuarios con permiso)
        if permissions.can_execute_commands:
            help_text += "📌 *Comandos de Terminal:*\n"
            help_text += "/run - Activar modo terminal\n"
            help_text += "/exit - Desactivar modo terminal\n\n"
        
        # Comandos de alertas (solo para usuarios con permiso)
        if permissions.can_manage_alerts:
            help_text += "⚙️ *Configuración de Alertas:*\n"
            help_text += "/alerts - Gestionar alertas del sistema\n\n"
        
        # Comandos de gestión de usuarios (solo para OWNER)
        if permissions.can_manage_users:
            help_text += "👤 *Gestión de Usuarios:*\n"
            help_text += "/users - Listar usuarios\n"
            help_text += "/add_user - Agregar usuario\n"
            help_text += "/remove_user - Eliminar usuario\n"
            help_text += "/set_role - Cambiar rol de usuario"
        
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
        user_id = update.effective_user.id
        username = update.effective_user.username or "Sin username"
        comando = update.message.text.strip()

        # Verificar si es un comando del bot
        if comando.startswith('/'):
            if not self.modo_terminal:
                # Procesar normalmente a través del manejador de comandos del bot
                return
            else:
                # En modo terminal, no permitir comandos del bot
                await update.message.reply_text(
                    "❌ Los comandos del bot no se pueden ejecutar en modo terminal.",
                    parse_mode='Markdown'
                )
                return

        # Si no estamos en modo terminal y no es un comando, pedir activar el modo
        if not self.modo_terminal:
            await self.send_message_with_retry(
                update.message,
                "❌ Modo terminal no está activo. Usa /run para activarlo.",
                parse_mode='Markdown'
            )
            return
            
        logger.info(f"Comando recibido de {username} (ID: {user_id}): {comando}")
        
        try:
            # Obtener el username desde el registro de usuarios
            users = self.user_manager.list_users()
            user = next((u for u in users if u['id'] == str(user_id)), None)
            notify_username = user['username'] if user else username
            
            # Notificar al owner sobre el comando
            await self.notify_owner(f"💻 `{notify_username}` ejecutó: `{comando}`")
            
            espera_message = await self.send_message_with_retry(
                update.message,
                "⏳ Ejecutando comando..."
            )
            
            output, error = await self.command_executor.execute_command(comando)
            await espera_message.delete()
            
            if error:
                await self.send_message_with_retry(
                    update.message,
                    f"❌ Error: {error}",
                    parse_mode='Markdown'
                )
                # Notificar al owner sobre el error
                await self.notify_owner(f"❌ Error en comando de `{notify_username}`: {error}")
                return
            
            if output:
                # Dividir la salida en chunks si es muy larga
                max_length = 4000  # Límite de Telegram para mensajes
                chunks = [output[i:i + max_length] for i in range(0, len(output), max_length)]
                
                for chunk in chunks:
                    # Escapar caracteres especiales de Markdown
                    chunk = chunk.replace('`', '\\`')
                    await self.send_message_with_retry(
                        update.message,
                        f"`{chunk}`",
                        parse_mode='Markdown'
                    )
                    
                # Notificar al owner sobre el resultado
                await self.notify_owner(f"✅ Comando completado por `{notify_username}`")
            else:
                await self.send_message_with_retry(
                    update.message,
                    "✅ Comando ejecutado con éxito",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            await self.send_message_with_retry(
                update.message,
                f"❌ Error: {str(e)}"
            )

    async def setup_alert_check(self, bot):
        """Configura el bucle de verificación de alertas del sistema"""
        self._bot = bot
        if self._alert_check_task is None:
            self._alert_check_task = asyncio.create_task(self._alert_check_loop())

    async def _alert_check_loop(self):
        """Bucle principal para verificar alertas del sistema"""
        while True:
            try:
                alert = self.alert_system.check_system_resources()
                if alert:
                    await self._send_alert(self._bot, alert)
            except Exception as e:
                logger.error(f"Error en verificación de alertas: {e}")
            await asyncio.sleep(60)  # Verificar cada minuto

    async def _send_alert(self, bot, alert):
        """Envía una alerta al grupo de Telegram"""
        if not TELEGRAM_GROUP:
            return

        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'danger': '🚨'
        }

        alert_text = (
            f"{emoji_map.get(alert.severity, '❗')} *{alert.type.upper()}*\n"
            f"{alert.message}\n"
            f"📅 `{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}`"
        )

        try:
            await bot.send_message(
                chat_id=TELEGRAM_GROUP,
                text=alert_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")

    @validate_access
    async def alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja la configuración de alertas"""
        keyboard = [
            [InlineKeyboardButton("🔒 Seguridad", callback_data="alert_security")],
            [InlineKeyboardButton("💻 CPU", callback_data="alert_cpu")],
            [InlineKeyboardButton("💾 Memoria", callback_data="alert_memory")],
            [InlineKeyboardButton("💿 Disco", callback_data="alert_disk")],
            [InlineKeyboardButton("⚙️ Umbrales", callback_data="alert_thresholds")]
        ]

        alert_status = self.alert_system.get_alert_status()
        status_text = "🔔 *Estado Actual de Alertas*\n\n"
        for alert_type, enabled in alert_status.items():
            status = "✅ Activada" if enabled else "❌ Desactivada"
            status_text += f"• {alert_type.title()}: {status}\n"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_alert_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja las interacciones con los botones de configuración de alertas"""
        query = update.callback_query
        await query.answer()

        if not query.data.startswith("alert_"):
            return

        alert_type = query.data.replace("alert_", "")
        if alert_type == "thresholds":
            thresholds_text = (
                "⚙️ *Configuración de Umbrales*\n\n"
                "Para configurar un umbral, usa:\n"
                "`/threshold <recurso> <valor>`\n\n"
                "Ejemplo:\n"
                "`/threshold cpu 90`\n\n"
                "Recursos disponibles:\n"
                "• cpu\n"
                "• memory\n"
                "• disk"
            )
            await query.edit_message_text(
                text=thresholds_text,
                parse_mode='Markdown'
            )
            return

        # Toggle alert status
        current_status = self.alert_system.get_alert_status()[alert_type]
        new_status = not current_status
        self.alert_system.toggle_alert(alert_type, new_status)

        # Update message
        alert_status = self.alert_system.get_alert_status()
        status_text = "🔔 *Estado Actual de Alertas*\n\n"
        for a_type, enabled in alert_status.items():
            status = "✅ Activada" if enabled else "❌ Desactivada"
            status_text += f"• {a_type.title()}: {status}\n"

        keyboard = [
            [InlineKeyboardButton("🔒 Seguridad", callback_data="alert_security")],
            [InlineKeyboardButton("💻 CPU", callback_data="alert_cpu")],
            [InlineKeyboardButton("💾 Memoria", callback_data="alert_memory")],
            [InlineKeyboardButton("💿 Disco", callback_data="alert_disk")],
            [InlineKeyboardButton("⚙️ Umbrales", callback_data="alert_thresholds")]
        ]

        await query.edit_message_text(
            text=status_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    @validate_access
    async def threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Configura los umbrales de las alertas"""
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(
                "❌ Uso incorrecto. Ejemplo:\n"
                "`/threshold cpu 90`",
                parse_mode='Markdown'
            )
            return

        resource, value = args
        try:
            value = float(value)
            if self.alert_system.set_threshold(resource, value):
                await update.message.reply_text(
                    f"✅ Umbral de {resource} actualizado a {value}%",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Recurso no válido o valor fuera de rango (0-100)",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ El valor debe ser un número",
                parse_mode='Markdown'
            )

    @validate_access
    async def users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista todos los usuarios registrados"""
        users = self.user_manager.list_users()
        if not users:
            await update.message.reply_text(
                "ℹ️ No hay usuarios registrados",
                parse_mode='Markdown'
            )
            return

        message = "📊 *Usuarios Registrados*\n\n"
        for user in users:
            role_emoji = {
                'owner': '👑',  # Corona
                'admin': '🛡️',  # Escudo
                'monitor': '🔍'  # Lupa
            }.get(user['role'], '❓')
            
            message += f"{role_emoji} *{user['username']}*\n"
            message += f"  • ID: `{user['id']}`\n"
            message += f"  • Rol: `{user['role']}`\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    @validate_access
    async def add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Agrega un nuevo usuario"""
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "❌ Uso incorrecto. Ejemplo:\n"
                "`/add_user <user_id> <username> <rol>`\n\n"
                "Roles disponibles:\n"
                "• admin - Acceso total excepto gestión de usuarios\n"
                "• monitor - Solo monitoreo y alertas",
                parse_mode='Markdown'
            )
            return

        user_id, username, role = args
        try:
            role = UserRole(role.lower())
            if role == UserRole.OWNER:
                await update.message.reply_text(
                    "❌ No se puede crear un usuario con rol OWNER",
                    parse_mode='Markdown'
                )
                return

            if self.user_manager.add_user(user_id, username, role):
                await update.message.reply_text(
                    f"✅ Usuario agregado exitosamente:\n"
                    f"ID: `{user_id}`\n"
                    f"Username: `{username}`\n"
                    f"Rol: `{role.value}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Error al agregar usuario",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Rol no válido",
                parse_mode='Markdown'
            )

    @validate_access
    async def remove_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Elimina un usuario"""
        args = context.args
        if len(args) != 1:
            await update.message.reply_text(
                "❌ Uso incorrecto. Ejemplo:\n"
                "`/remove_user <user_id>`",
                parse_mode='Markdown'
            )
            return

        user_id = args[0]
        if self.user_manager.remove_user(user_id):
            await update.message.reply_text(
                f"✅ Usuario eliminado exitosamente",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Error al eliminar usuario (no existe o es OWNER)",
                parse_mode='Markdown'
            )

    @validate_access
    async def set_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cambia el rol de un usuario"""
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(
                "❌ Uso incorrecto. Ejemplo:\n"
                "`/set_role <user_id> <nuevo_rol>`\n\n"
                "Roles disponibles:\n"
                "• admin - Acceso total excepto gestión de usuarios\n"
                "• monitor - Solo monitoreo y alertas",
                parse_mode='Markdown'
            )
            return

        user_id, new_role = args
        try:
            role = UserRole(new_role.lower())
            if role == UserRole.OWNER:
                await update.message.reply_text(
                    "❌ No se puede asignar el rol OWNER",
                    parse_mode='Markdown'
                )
                return

            if self.user_manager.update_user_role(user_id, role):
                # Obtener el username del usuario afectado
                target_user = next((u for u in self.user_manager.list_users() if u['id'] == user_id), None)
                target_username = target_user['username'] if target_user else user_id
                
                success_msg = (f"✅ Rol actualizado exitosamente:\n"
                             f"ID: `{user_id}`\n"
                             f"Usuario: `{target_username}`\n"
                             f"Nuevo rol: `{role.value}`")
                
                await update.message.reply_text(success_msg, parse_mode='Markdown')
                
                # Notificar al owner
                admin_username = update.effective_user.username or "Sin username"
                await self.notify_owner(
                    f"👤 *Cambio de Rol*\n"
                    f"Admin: `{admin_username}`\n"
                    f"Usuario: `{target_username}`\n"
                    f"Nuevo rol: `{role.value}`"
                )
            else:
                await update.message.reply_text(
                    "❌ Error al actualizar rol (usuario no existe o es OWNER)",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Rol no válido",
                parse_mode='Markdown'
            )
        username = update.effective_user.username or "Sin username"
        comando = update.message.text.strip()
        
        logger.info(f"Comando recibido de {username} (ID: {user_id}): {comando}")
        
        try:
            espera_message = await self.send_message_with_retry(
                update.message,
                "⏳ Ejecutando comando..."
            )

            result, error = await self.command_executor.execute_command(comando)
            
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



