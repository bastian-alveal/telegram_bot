import asyncio
import os
import sys
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from controllers.bot_controller import BotController
from config.config import TELEGRAM_TOKEN
from utils.logger import logger
from concurrent.futures import ThreadPoolExecutor

async def start_bot(application, bot_controller):
    """Inicia el bot y envía el mensaje de bienvenida"""
    try:
        # Iniciar el bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True, allowed_updates=['message', 'callback_query'])

        # Inicializar sistema de alertas
        await bot_controller.setup_alert_check(application.bot)

        # Enviar mensaje de bienvenida
        logger.info("Bot iniciado correctamente")
        await bot_controller.send_welcome_message(application.bot)

        # Mantener el bot corriendo indefinidamente
        while True:
            try:
                await asyncio.sleep(60)  # Dormir para no consumir CPU
            except telegram.error.Conflict:
                # Ignorar errores de conflicto
                pass

    except Exception as e:
        logger.error(f"Error iniciando el bot: {e}")
        raise
    finally:
        # Asegurar limpieza al terminar
        if bot_controller._alert_check_task:
            bot_controller._alert_check_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def check_single_instance():
    """Verifica que solo haya una instancia del bot corriendo"""
    pid_file = '/tmp/telegram_bot.pid'
    
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            old_pid = f.read().strip()
            if old_pid and os.path.exists(f'/proc/{old_pid}'):
                logger.error(f'Ya existe una instancia del bot corriendo (PID: {old_pid})')
                sys.exit(1)
    
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def cleanup():
    """Limpia el archivo PID al terminar"""
    try:
        os.remove('/tmp/telegram_bot.pid')
    except:
        pass

def main():
    try:
        # Inicializar el controlador del bot
        bot_controller = BotController()

        # Crear la aplicación
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Registrar manejadores básicos
        application.add_handler(CommandHandler("start", bot_controller.start))
        application.add_handler(CommandHandler("run", bot_controller.run_commands))
        application.add_handler(CommandHandler("exit", bot_controller.exit_commands))
        application.add_handler(CommandHandler("info", bot_controller.info_system))
        
        # Registrar comandos de monitoreo
        application.add_handler(CommandHandler("ps", bot_controller.ps_command))
        application.add_handler(CommandHandler("net", bot_controller.net_command))
        application.add_handler(CommandHandler("disk", bot_controller.disk_command))
        
        # Registrar comandos de alertas
        application.add_handler(CommandHandler("alerts", bot_controller.alerts))
        application.add_handler(CommandHandler("threshold", bot_controller.threshold))
        application.add_handler(CallbackQueryHandler(bot_controller.handle_alert_callback))
        
        # Registrar comandos de gestión de usuarios
        application.add_handler(CommandHandler("users", bot_controller.users))
        application.add_handler(CommandHandler("add_user", bot_controller.add_user))
        application.add_handler(CommandHandler("remove_user", bot_controller.remove_user))
        application.add_handler(CommandHandler("set_role", bot_controller.set_role))
        
        # Manejador de mensajes para comandos de terminal
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_controller.handle_message))

        # Iniciar el bot de forma asíncrona
        asyncio.run(start_bot(application, bot_controller))

    except Exception as e:
        logger.error(f"Error iniciando el bot: {e}")

if __name__ == '__main__':
    main()
