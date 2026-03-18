"""CloudStack role operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from clients.cloudstack.base import CloudStackBaseClient
 
log = logging.getLogger(__name__)
 
 
class CloudStackRolesClient(CloudStackBaseClient):
    """CloudStack role operations."""
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles."""
        try:
            resp = self._cs.listRoles() or {}
            roles = resp.get("role", []) or []
            log.debug(f"Listed {len(roles)} roles")
            return roles
        except Exception as e:
            self._handle_error("list_roles", e)
    
    def get_role(self, role_id: str) -> Dict[str, Any] | None:
        """Get role by ID."""
        try:
            resp = self._cs.listRoles(id=role_id) or {}
            roles = resp.get("role", []) or []
            return roles[0] if roles else None
        except Exception as e:
            self._handle_error(f"get_role({role_id})", e)
    
    def get_role_by_name(self, role_name: str) -> Dict[str, Any] | None:
        """Get role by name."""
        try:
            resp = self._cs.listRoles(name=role_name) or {}
            roles = resp.get("role", []) or []
            return roles[0] if roles else None
        except Exception as e:
            self._handle_error(f"get_role_by_name({role_name})", e)
    
    def list_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """List permissions for a role."""
        try:
            resp = self._cs.listRolePermissions(roleid=role_id) or {}
            perms = resp.get("rolepermission", []) or resp.get("rolePermission", []) or []
            log.debug(f"Listed {len(perms)} permissions for role {role_id}")
            return perms
        except Exception as e:
            self._handle_error(f"list_role_permissions({role_id})", e)
    
    def create_role(
        self,
        name: str,
        description: str = "",
        role_type: str = "User"
    ) -> str | None:
        """Create a new role. Returns role ID."""
        try:
            log.debug(f"Creating role {name}")
            resp = self._cs.createRole(
                name=name,
                description=description,
                type=role_type
            ) or {}
            role = resp.get("role", {})
            role_id = role.get("id")
            if role_id:
                log.info(f"Created role {name} (id={role_id})")
                return role_id
            raise CloudStackClientError(f"Failed to create role {name}")
        except Exception as e:
            self._handle_error(f"create_role({name})", e)