import json
import os
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass
from config.config import TELEGRAM_GROUP

class UserRole(Enum):
    OWNER = "owner"      # Usuario principal, acceso total
    ADMIN = "admin"      # Acceso total excepto gestión de usuarios
    MONITOR = "monitor"  # Solo monitoreo y alertas

@dataclass
class UserPermissions:
    can_execute_commands: bool
    can_view_system_info: bool
    can_manage_users: bool
    can_manage_alerts: bool

class UserManager:
    def __init__(self, config_file: str = "config/users.json"):
        self.config_file = config_file
        self.users: Dict[str, Dict] = {}
        self._role_permissions = {
            UserRole.OWNER: UserPermissions(
                can_execute_commands=True,
                can_view_system_info=True,
                can_manage_users=True,
                can_manage_alerts=True
            ),
            UserRole.ADMIN: UserPermissions(
                can_execute_commands=True,
                can_view_system_info=True,
                can_manage_users=False,
                can_manage_alerts=True
            ),
            UserRole.MONITOR: UserPermissions(
                can_execute_commands=False,
                can_view_system_info=True,
                can_manage_users=False,
                can_manage_alerts=False
            )
        }
        self._load_users()
        self._ensure_owner()

    def _ensure_owner(self):
        """Asegura que el usuario principal esté registrado como OWNER"""
        if TELEGRAM_GROUP and TELEGRAM_GROUP not in self.users:
            self.add_user(TELEGRAM_GROUP, "Principal", UserRole.OWNER)

    def _load_users(self):
        """Carga los usuarios desde el archivo de configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.users = {
                        user_id: {
                            'username': info['username'],
                            'role': UserRole(info['role'])
                        }
                        for user_id, info in data.items()
                    }
            except Exception as e:
                print(f"Error loading users: {e}")
                self.users = {}
        else:
            # Crear el directorio si no existe
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            self.users = {}

    def _save_users(self):
        """Guarda los usuarios en el archivo de configuración"""
        try:
            data = {
                user_id: {
                    'username': info['username'],
                    'role': info['role'].value
                }
                for user_id, info in self.users.items()
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving users: {e}")
            return False

    def add_user(self, user_id: str, username: str, role: str | UserRole) -> bool:
        """Agrega un nuevo usuario"""
        # Convertir role a UserRole si es string
        if isinstance(role, str):
            try:
                role = UserRole(role.lower())
            except ValueError:
                return False

        if role == UserRole.OWNER and any(u['role'] == UserRole.OWNER for u in self.users.values()):
            return False  # Solo puede haber un OWNER

        self.users[user_id] = {
            'username': username,
            'role': role
        }
        return self._save_users()

    def remove_user(self, user_id: str) -> bool:
        """Elimina un usuario"""
        if user_id not in self.users:
            return False
        if self.users[user_id]['role'] == UserRole.OWNER:
            return False  # No se puede eliminar al OWNER
        
        del self.users[user_id]
        return self._save_users()

    def get_user_role(self, user_id: str) -> Optional[UserRole]:
        """Obtiene el rol de un usuario"""
        if user_id in self.users:
            return self.users[user_id]['role']
        return None

    def get_user_permissions(self, user_id: str) -> Optional[UserPermissions]:
        """Obtiene los permisos de un usuario"""
        role = self.get_user_role(user_id)
        if role:
            return self._role_permissions[role]
        return None

    def update_user_role(self, user_id: str, new_role: str | UserRole) -> bool:
        """Actualiza el rol de un usuario"""
        if user_id not in self.users:
            return False
        if self.users[user_id]['role'] == UserRole.OWNER:
            return False  # No se puede cambiar el rol del OWNER
            
        # Convertir role a UserRole si es string
        if isinstance(new_role, str):
            try:
                new_role = UserRole(new_role.lower())
            except ValueError:
                return False
                
        if new_role == UserRole.OWNER:
            return False  # No se puede asignar el rol de OWNER
        
        self.users[user_id]['role'] = new_role
        return self._save_users()

    def list_users(self) -> List[Dict]:
        """Lista todos los usuarios con sus roles"""
        return [
            {
                'id': user_id,
                'username': info['username'],
                'role': info['role'].value
            }
            for user_id, info in self.users.items()
        ]
