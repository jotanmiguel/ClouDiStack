"""CloudStack role operations."""
from __future__ import annotations
import logging
from traceback import print_tb
from typing import Any, Dict, List, Optional
from clients.cloudstack.base import CloudStackBaseClient
from clients.cloudstack.exceptions import CloudStackClientError
 
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
            return []
    
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
            
    def get_role_id_by_name(self, role_name: str) -> str | None:
        """Get role ID by name."""
        role = self.get_role_by_name(role_name)
        return role.get("id") if role else None
    
    def list_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """List permissions for a role."""
        try:
            resp = self._cs.listRolePermissions(roleid=role_id) or {}
            perms = resp.get("rolepermission", []) or resp.get("rolePermission", []) or []
            log.debug(f"Listed {len(perms)} permissions for role {role_id}")
            return perms
        except Exception as e:
            self._handle_error(f"list_role_permissions({role_id})", e)
            return []
    
    def create_role(self, name: str, description: str = "", role_type: str = "User") -> str | None:
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
            
    def delete_role(self, role_id: str) -> bool:
        """Delete a role by ID."""
        try:
            log.debug(f"Deleting role {role_id}")
            self._cs.deleteRole(id=role_id)
            log.info(f"Deleted role {role_id}")
            return True
        except Exception as e:
            self._handle_error(f"delete_role({role_id})", e)
            return False
        
    def assign_permission_to_role(self, permission: bool, role_id: str, rule: list[str]) -> bool:
        """Assign a permission to a role."""
        try:
            log.debug(f"Assigning permissions to role {role_id}")
            self._cs.createRolePermission(permission=permission, roleid=role_id, rule=rule)
            log.info(f"Assigned permissions to role {role_id}")
            return True
        except Exception as e:
            self._handle_error(f"assign_permission_to_role({role_id})", e)
            return False
        
    def revoke_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Revoke a permission from a role."""
        try:
            log.debug(f"Revoking permission {permission_id} from role {role_id}")
            self._cs.deleteRolePermission(roleid=role_id, permissionid=permission_id)
            log.info(f"Revoked permission {permission_id} from role {role_id}")
            return True
        except Exception as e:
            self._handle_error(f"revoke_permission_from_role({role_id}, {permission_id})", e)
            return False
        
    def duplicate_role(self, source_role_id: str, new_role_name: str, description: str = "") -> str | None:
        """Duplicate an existing role with a new name. Returns new role ID."""
        try:
            log.debug(f"Duplicating role {source_role_id} to {new_role_name}")
            resp = self.create_role(name=new_role_name, description=description)
            new_role_id = resp
            if new_role_id:
                log.info(f"Duplicated role {source_role_id} to {new_role_name} (id={new_role_id})")
                perms = [p for p in self.list_role_permissions(source_role_id)]
                for p in perms:
                    self.assign_permission_to_role(
                        permission=p.get("permission"),
                        role_id=new_role_id,
                        rule=p.get("rule", [])
                    )
                return {
                        "id": new_role_id,
                        "name": new_role_name,
                        "description": description,
                        "permissions": len(perms),
                        "duration": 0, #TODO need to calculate total duration later
                    }
            raise CloudStackClientError(f"Failed to duplicate role {source_role_id}")
        except Exception as e:
            self._handle_error(f"duplicate_role({source_role_id}, {new_role_name})", e)
            return None