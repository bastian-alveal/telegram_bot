import asyncio
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
        await application.updater.start_polling()

        # Enviar mensaje de bienvenida
        logger.info("Bot iniciado correctamente")
        await bot_controller.send_welcome_message(application.bot)

        # Mantener el bot corriendo indefinidamente
        while True:
            await asyncio.sleep(60)  # Dormir para no consumir CPU

    except Exception as e:
        logger.error(f"Error iniciando el bot: {e}")
        raise
    finally:
        # Asegurar limpieza al terminar
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

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
        
        # Manejador de mensajes para comandos de terminal
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_controller.handle_message))

        # Iniciar el bot de forma asíncrona
        asyncio.run(start_bot(application, bot_controller))

    except Exception as e:
        logger.error(f"Error iniciando el bot: {e}")

if __name__ == '__main__':
    main()
