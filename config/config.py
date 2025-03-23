import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración del bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_GROUP = os.getenv('TELEGRAM_ADMIN')
ALLOWED_GROUP_ID = os.getenv('ALLOWED_GROUP_ID')

# Configuración de comandos
BLACKLIST_COMMANDS = ["htop", "shutdown"]
MAX_RETRIES = 3

# Configuración del sistema
MAX_WORKERS = 3
