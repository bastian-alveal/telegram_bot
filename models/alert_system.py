from dataclasses import dataclass
from datetime import datetime
import psutil
from typing import Dict, Optional
from config.config import TELEGRAM_GROUP
from utils.logger import logger

@dataclass
class Alert:
    type: str
    message: str
    timestamp: datetime
    severity: str  # 'info', 'warning', 'danger'
    source: str

class AlertSystem:
    def __init__(self):
        self._alerts_enabled = {
            'security': True,
            'cpu': True,
            'memory': True,
            'disk': True
        }
        self._thresholds = {
            'cpu': 80.0,
            'memory': 80.0,
            'disk': 80.0
        }
        self._last_alert_time: Dict[str, datetime] = {}
        self._alert_cooldown = 300  # 5 minutos entre alertas del mismo tipo

    def toggle_alert(self, alert_type: str, enabled: bool) -> bool:
        """Activa o desactiva un tipo de alerta específico"""
        if alert_type in self._alerts_enabled:
            self._alerts_enabled[alert_type] = enabled
            return True
        return False

    def get_alert_status(self) -> Dict[str, bool]:
        """Obtiene el estado actual de todas las alertas"""
        return self._alerts_enabled.copy()

    def set_threshold(self, resource: str, value: float) -> bool:
        """Establece el umbral para un recurso específico"""
        if resource in self._thresholds and 0 <= value <= 100:
            self._thresholds[resource] = value
            return True
        return False

    def _can_send_alert(self, alert_type: str) -> bool:
        """Verifica si se puede enviar una alerta basado en el cooldown"""
        now = datetime.now()
        if alert_type not in self._last_alert_time:
            return True
        
        time_diff = (now - self._last_alert_time[alert_type]).total_seconds()
        return time_diff >= self._alert_cooldown

    def check_unauthorized_access(self, user_id: str, username: str) -> Optional[Alert]:
        """Genera una alerta de seguridad si un usuario no autorizado intenta acceder"""
        if not self._alerts_enabled['security']:
            return None

        if str(user_id) != TELEGRAM_GROUP and self._can_send_alert('security'):
            self._last_alert_time['security'] = datetime.now()
            return Alert(
                type='security',
                message=f"⚠️ *Intento de acceso no autorizado*\nUsuario: `{username}`\nID: `{user_id}`",
                timestamp=datetime.now(),
                severity='danger',
                source='access_control'
            )
        return None

    def check_system_resources(self) -> Optional[Alert]:
        """Verifica los recursos del sistema y genera alertas si es necesario"""
        alerts = []
        now = datetime.now()

        # CPU
        if self._alerts_enabled['cpu'] and self._can_send_alert('cpu'):
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self._thresholds['cpu']:
                self._last_alert_time['cpu'] = now
                alerts.append(Alert(
                    type='cpu',
                    message=f"🔥 *Alerta de CPU*\nUso actual: `{cpu_percent:.1f}%`\nUmbral: `{self._thresholds['cpu']}%`",
                    timestamp=now,
                    severity='warning',
                    source='system_monitor'
                ))

        # Memoria
        if self._alerts_enabled['memory'] and self._can_send_alert('memory'):
            memory = psutil.virtual_memory()
            if memory.percent > self._thresholds['memory']:
                self._last_alert_time['memory'] = now
                alerts.append(Alert(
                    type='memory',
                    message=f"💾 *Alerta de Memoria*\nUso actual: `{memory.percent:.1f}%`\nUmbral: `{self._thresholds['memory']}%`",
                    timestamp=now,
                    severity='warning',
                    source='system_monitor'
                ))

        # Disco
        if self._alerts_enabled['disk'] and self._can_send_alert('disk'):
            disk = psutil.disk_usage('/')
            if disk.percent > self._thresholds['disk']:
                self._last_alert_time['disk'] = now
                alerts.append(Alert(
                    type='disk',
                    message=f"💿 *Alerta de Disco*\nUso actual: `{disk.percent:.1f}%`\nUmbral: `{self._thresholds['disk']}%`",
                    timestamp=now,
                    severity='warning',
                    source='system_monitor'
                ))

        return alerts[0] if alerts else None  # Retorna la primera alerta si hay alguna
