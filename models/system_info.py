import psutil
import os
from utils.logger import logger
from datetime import datetime

class SystemInfo:
    @staticmethod
    def get_system_info():
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': f"{cpu_percent}%",
                'memory_total': f"{memory.total / (1024**3):.2f}GB",
                'memory_used': f"{memory.used / (1024**3):.2f}GB",
                'memory_percent': f"{memory.percent}%",
                'disk_total': f"{disk.total / (1024**3):.2f}GB",
                'disk_used': f"{disk.used / (1024**3):.2f}GB",
                'disk_percent': f"{disk.percent}%",
                'current_dir': os.getcwd()
            }
        except Exception as e:
            logger.error(f"Error obteniendo información del sistema: {e}")
            return None
