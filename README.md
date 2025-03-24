# Bot de Telegram para Monitoreo de Sistema

Este bot de Telegram proporciona funcionalidades para monitorear y controlar un sistema Linux remotamente a través de Telegram.

## Características

- Monitoreo del sistema (CPU, memoria, disco)
- Información de red
- Lista de procesos activos
- Ejecución de comandos remotos (modo terminal)
- Sistema de alertas configurable
  - Alertas de seguridad para accesos no autorizados
  - Alertas de rendimiento (CPU, memoria, disco)
  - Umbrales configurables
  - Activación/desactivación individual de alertas
- Interfaz de usuario amigable con comandos intuitivos

## Requisitos Previos

- Python 3.8 o superior
- Token de Bot de Telegram (obtenido a través de @BotFather)
- User_ID de Telegram (obtenido a través de @get_id_bot)
- Permisos de administrador en el sistema

## Instalación

1. Clonar o copiar el repositorio:
```bash
cd ~/Desktop
git clone https://github.com/bastian-alveal/telegram_bot.git
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

### Comandos Básicos
- `/start` - Inicia el bot y muestra el menú principal
- `/info` - Muestra información del sistema
- `/ps` - Lista los procesos activos
- `/net` - Muestra el estado de la red
- `/disk` - Muestra información del disco
- `/run` - Activa el modo terminal
- `/exit` - Desactiva el modo terminal

### Comandos de Alertas
- `/alerts` - Muestra el panel de control de alertas
- `/threshold <recurso> <valor>` - Configura el umbral de alerta para un recurso
  - Recursos disponibles: `cpu`, `memory`, `disk`
  - Valor: porcentaje entre 0 y 100
  - Ejemplo: `/threshold cpu 90`

### Comandos de Gestión de Usuarios
- `/users` - Lista todos los usuarios registrados
- `/add_user <id> <username> <rol>` - Agrega un nuevo usuario
  - Roles disponibles: `admin`, `monitor`
  - Ejemplo: `/add_user 123456789 juan monitor`
- `/set_role <id> <rol>` - Cambia el rol de un usuario
  - Ejemplo: `/set_role 123456789 admin`
- `/remove_user <id>` - Elimina un usuario

## Gestión de Usuarios (users.json)

El sistema utiliza un archivo `users.json` para gestionar los usuarios y sus roles. Este archivo:

1. **Creación Automática**:
   - Se crea automáticamente en la carpeta `config/` al iniciar el bot
   - Si no existe, se crea con el usuario owner definido en el `.env`

2. **Estructura**:
```json
{
    "ID_OWNER": {
        "username": "nombre_usuario",
        "role": "owner"
    },
    "ID_USUARIO": {
        "username": "otro_usuario",
        "role": "admin"
    }
}
```

3. **Roles y Permisos**:
   - `owner`: Acceso total (único, no se puede crear otro)
   - `admin`: Todo excepto gestión de usuarios
   - `monitor`: Solo monitoreo y alertas

4. **Notificaciones**:
   - El owner recibe notificaciones de:
     - Comandos ejecutados por otros usuarios
     - Errores en la ejecución de comandos
     - Cambios en roles de usuarios

## Desarrollo y Mejoras

### Agregar Nuevas Funcionalidades

1. **Nuevos Comandos**:
   - Agregar método en `BotController` con el decorador `@validate_access`
   - Registrar el comando en la lista de comandos disponibles
   - Documentar en el README

2. **Nuevos Roles**:
   - Agregar el rol en `UserRole` en `models/user_manager.py`
   - Definir permisos en `_role_permissions` en `UserManager`
   - Actualizar la documentación de roles

3. **Nuevas Alertas**:
   - Agregar tipo de alerta en `AlertSystem`
   - Implementar lógica de verificación
   - Agregar umbrales configurables si es necesario

### Mejoras Sugeridas

1. **Seguridad**:
   - Implementar autenticación de dos factores
   - Agregar logs detallados de acciones de usuarios
   - Mejorar validación de comandos permitidos

2. **Funcionalidad**:
   - Agregar más tipos de alertas (servicios, puertos, etc.)
   - Implementar respaldo automático de configuraciones
   - Agregar gráficos de rendimiento

3. **Usabilidad**:
   - Mejorar mensajes de error
   - Agregar más comandos de ayuda
   - Implementar menús interactivos con botones

## Estructura del Proyecto

```
telegram_bot/
├── config/
│   ├── config.py     # Configuraciones y variables de entorno
│   └── users.json    # Base de datos de usuarios
├── controllers/
│   └── bot_controller.py # Controlador principal del bot
├── models/
│   ├── command_executor.py # Ejecutor de comandos
│   ├── system_info.py    # Modelo para información del sistema
│   └── alert_system.py   # Sistema de alertas y monitoreo
├── utils/
│   └── logger.py         # Configuración de logging
├── views/
│   └── ...              # Vistas y formateadores de mensajes
├── main.py              # Punto de entrada principal
├── requirements.txt     # Dependencias del proyecto
└── README.md           # Esta documentación
```

## Sistema de Usuarios y Roles

El bot implementa un sistema de roles y permisos para gestionar el acceso a las diferentes funcionalidades:

### Roles Disponibles

1. **OWNER** (Dueño)
   - Acceso total al sistema
   - Único rol que puede gestionar usuarios
   - No puede ser eliminado ni modificado
   - Solo puede existir un OWNER

2. **ADMIN** (Administrador)
   - Acceso a comandos de terminal
   - Gestión de alertas
   - Monitoreo del sistema
   - No puede gestionar usuarios

3. **MONITOR** (Monitor)
   - Solo acceso a comandos de monitoreo
   - No puede ejecutar comandos de terminal
   - No puede gestionar alertas ni usuarios

### Comandos de Gestión

- `/users` - Lista todos los usuarios registrados
- `/add_user <user_id> <username> <rol>` - Agrega un nuevo usuario
  - Ejemplo: `/add_user 123456789 juan monitor`
- `/remove_user <user_id>` - Elimina un usuario
  - Ejemplo: `/remove_user 123456789`
- `/set_role <user_id> <nuevo_rol>` - Cambia el rol de un usuario
  - Ejemplo: `/set_role 123456789 admin`

### Persistencia

Los usuarios y sus roles se almacenan en `config/users.json`. Este archivo se crea automáticamente y mantiene la configuración incluso después de reiniciar el bot.

## Sistema de Alertas

El bot incluye un sistema de alertas configurable que monitorea:

1. **Seguridad**
   - Detecta intentos de acceso no autorizados
   - Registra ID y username del usuario

2. **Rendimiento**
   - CPU: Alerta cuando el uso supera el umbral configurado
   - Memoria: Alerta cuando el uso supera el umbral configurado
   - Disco: Alerta cuando el uso supera el umbral configurado

### Configuración

- Usa `/alerts` para acceder al panel de control
- Activa/desactiva alertas individualmente
- Configura umbrales personalizados con `/threshold`
- Las alertas tienen un tiempo de enfriamiento de 5 minutos

### Personalización

Para agregar nuevas alertas:

1. Define la alerta en `models/alert_system.py`
2. Agrega la lógica de detección
3. Registra el tipo de alerta en `AlertSystem.__init__`
4. Actualiza el panel de control en `BotController.alerts`

## Extendiendo el Bot

El bot está diseñado siguiendo el patrón MVC (Modelo-Vista-Controlador) para facilitar su extensión. Aquí hay una guía para agregar nuevas funcionalidades:

### 1. Agregar Nuevos Modelos

1. Crear un nuevo archivo en `models/` siguiendo las convenciones existentes
2. Implementar la lógica de negocio en clases bien definidas
3. Usar tipos estáticos y docstrings para mejor mantenibilidad

Ejemplo:
```python
# models/new_feature.py
from dataclasses import dataclass

@dataclass
class NewFeature:
    name: str
    value: int

class NewFeatureManager:
    def __init__(self):
        self._data = {}

    def add_item(self, name: str, value: int) -> bool:
        # Implementación
        pass
```

### 2. Actualizar el Controlador

1. Importar el nuevo modelo en `controllers/bot_controller.py`
2. Inicializar en el constructor si es necesario
3. Agregar nuevos métodos con el decorador `@validate_access`
4. Implementar la lógica de comando

Ejemplo:
```python
# controllers/bot_controller.py
from models.new_feature import NewFeatureManager

class BotController:
    def __init__(self):
        self.new_feature = NewFeatureManager()

    @validate_access
    async def new_command(self, update, context):
        # Implementación
        pass
```

### 3. Registrar Comandos

1. Agregar el nuevo comando en `main.py`
2. Usar el handler apropiado (CommandHandler, MessageHandler, etc.)

Ejemplo:
```python
# main.py
application.add_handler(
    CommandHandler("new_command", bot_controller.new_command)
)
```

### 4. Documentación

1. Actualizar el README.md con:
   - Descripción de la nueva funcionalidad
   - Nuevos comandos y su uso
   - Ejemplos relevantes
2. Agregar docstrings detallados en el código

### 5. Consideraciones

- Mantener la separación de responsabilidades (MVC)
- Seguir las convenciones de código existentes
- Implementar manejo de errores apropiado
- Agregar logs relevantes
- Considerar la persistencia si es necesaria
- Respetar el sistema de permisos

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
