import subprocess
import shlex
import os
import asyncio
from utils.logger import logger
from config.config import BLACKLIST_COMMANDS

class CommandExecutor:
    def __init__(self):
        self.current_directory = os.getcwd()

    async def execute_command(self, command: str) -> tuple[str | None, str | None]:
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
                return await self._change_directory(command[3:].strip())

            # Ejecutar comando normal
            cmd_tokens = shlex.split(command)
            process = await asyncio.create_subprocess_exec(
                *cmd_tokens,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.current_directory
            )

            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return None, stderr.decode() if stderr else "Error ejecutando comando"
                
            return stdout.decode() if stdout else "", None

        except Exception as e:
            return None, f"Error: {str(e)}"

    async def _change_directory(self, new_dir: str) -> tuple[str | None, str | None]:
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
