# Bot de Telegram para Monitoreo de Sistema

Este bot de Telegram proporciona funcionalidades para monitorear y controlar un sistema Linux remotamente a través de Telegram.

## Características

- Monitoreo del sistema (CPU, memoria, disco)
- Información de red
- Lista de procesos activos
- Ejecución de comandos remotos (modo terminal)
- Interfaz de usuario amigable con comandos intuitivos

## Requisitos Previos

- Python 3.8 o superior
- Token de Bot de Telegram (obtenido a través de @BotFather)
- Permisos de administrador en el sistema

## Instalación

1. Clonar o copiar el repositorio:
```bash
cd ~/Desktop
git clone <repositorio> telegram_bot
cd telegram_bot
```

2. Crear y activar un entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear un archivo `.env` en el directorio raíz con:
```
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_ADMIN=tu_id_de_telegram
ALLOWED_GROUP_ID=id_del_grupo_permitido
```

## Configuración del Servicio

1. Copiar el archivo de servicio:
```bash
sudo cp bot-telegram.service /etc/systemd/system/
```

2. Recargar systemd:
```bash
sudo systemctl daemon-reload
```

3. Habilitar el servicio:
```bash
sudo systemctl enable bot-telegram
```

4. Iniciar el servicio:
```bash
sudo systemctl start bot-telegram
```

## Comandos Disponibles

- `/start` - Inicia el bot y muestra el menú principal
- `/info` - Muestra información del sistema
- `/ps` - Lista los procesos activos
- `/net` - Muestra el estado de la red
- `/disk` - Muestra información del disco
- `/run` - Activa el modo terminal
- `/exit` - Desactiva el modo terminal

## Estructura del Proyecto

```
telegram_bot/
├── config/
│   └── config.py         # Configuraciones y variables de entorno
├── controllers/
│   └── bot_controller.py # Controlador principal del bot
├── models/
│   ├── command_executor.py # Ejecutor de comandos
│   └── system_info.py    # Modelo para información del sistema
├── utils/
│   └── logger.py         # Configuración de logging
├── views/
│   └── ...              # Vistas y formateadores de mensajes
├── main.py              # Punto de entrada principal
├── requirements.txt     # Dependencias del proyecto
└── README.md           # Esta documentación
```

## Monitoreo y Logs

Los logs del bot se encuentran en:
- Logs generales: `/var/log/bot-telegram.log`
- Logs de error: `/var/log/bot-telegram.error.log`

Para ver los logs en tiempo real:
```bash
sudo journalctl -fu bot-telegram
```

## Mantenimiento

Para reiniciar el servicio:
```bash
sudo systemctl restart bot-telegram
```

Para detener el servicio:
```bash
sudo systemctl stop bot-telegram
```

Para ver el estado del servicio:
```bash
sudo systemctl status bot-telegram
```
