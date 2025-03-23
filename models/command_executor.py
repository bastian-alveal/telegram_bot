import subprocess
import shlex
import os
from utils.logger import logger
from config.config import BLACKLIST_COMMANDS

class CommandExecutor:
    def __init__(self):
        self.current_directory = os.getcwd()

    def execute_command(self, command: str) -> tuple:
        """
        Ejecuta un comando y retorna el resultado y el estado
        """
        try:
            # Validar comando en lista negra
            cmd_base = command.split()[0].lower()
            if cmd_base in BLACKLIST_COMMANDS:
                return None, f"Comando '{cmd_base}' prohibido"

            # Manejar comando cd
            if command.startswith("cd "):
                return self._change_directory(command[3:].strip())

            # Ejecutar comando normal
            cmd_tokens = shlex.split(command)
            result = subprocess.check_output(
                cmd_tokens,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.current_directory
            )
            return result, None

        except subprocess.CalledProcessError as e:
            return None, f"Error ejecutando comando: {e.output}"
        except Exception as e:
            return None, f"Error: {str(e)}"

    def _change_directory(self, new_dir: str) -> tuple:
        """
        Cambia el directorio actual
        """
        try:
            os.chdir(new_dir)
            self.current_directory = os.getcwd()
            return self.current_directory, None
        except Exception as e:
            return None, f"Error cambiando directorio: {str(e)}"

    def get_current_directory(self) -> str:
        return self.current_directory
