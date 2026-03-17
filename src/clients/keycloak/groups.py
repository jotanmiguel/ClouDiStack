"""Keycloak group operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from keycloak.exceptions import KeycloakError
from .base import KeycloakBaseClient
from .exceptions import KeycloakClientError

log = logging.getLogger(__name__)


class KeycloakGroupsClient(KeycloakBaseClient):
    """Keycloak group operations."""
    
    # ============================================================
    # READ OPERATIONS
    # ============================================================
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """
        List all groups in realm.
        
        Returns:
            [
                {"id": "group-uuid", "name": "students", "path": "/students"},
                {"id": "group-uuid", "name": "staff", "path": "/staff"},
                ...
            ]
        """
        try:
            groups = self._admin.get_groups()
            log.debug(f"Listed {len(groups)} groups")
            return groups
        except KeycloakError as e:
            self._handle_error("list_groups", e)
            return []
    
    def get_group_by_name(self, group_name: str) -> Dict[str, Any] | None:
        """Get group by name."""
        try:
            groups = self.list_groups()
            group = next((g for g in groups if g.get("name") == group_name), None)
            if group:
                log.debug(f"Found group {group_name}")
            else:
                log.debug(f"Group {group_name} not found")
            return group
        except Exception:
            return None
    
    def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get groups for a user.
        
        Returns:
            [
                {"id": "group-uuid", "name": "students", "path": "/students"},
                ...
            ]
        """
        try:
            groups = self._admin.get_user_groups(user_id)
            log.debug(f"Got {len(groups)} groups for user {user_id}")
            return groups
        except KeycloakError as e:
            self._handle_error(f"get_user_groups({user_id})", e)
            return []
    
    # ============================================================
    # WRITE OPERATIONS
    # ============================================================
    
    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add user to group."""
        try:
            self._admin.group_user_add(user_id, group_id)
            log.info(f"Added user {user_id} to group {group_id}")
            return True
        except KeycloakError as e:
            self._handle_error(f"add_user_to_group({user_id}, {group_id})", e)
            return False

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove user from group."""
        try:
            self._admin.group_user_remove(user_id, group_id)
            log.info(f"Removed user {user_id} from group {group_id}")
            return True
        except KeycloakError as e:
            self._handle_error(f"remove_user_from_group({user_id}, {group_id})", e)
            return False

    def create_group(self, name: str, path: str = "") -> str | None:
        """
        Create a new group.
        
        Returns:
            Group ID or None if failed
        """
        try:
            group_id = self._admin.create_group({"name": name, "path": path or f"/{name}"})
            log.info(f"Created group {name} (id={group_id})")
            return group_id
        except KeycloakError as e:
            self._handle_error(f"create_group({name})", e)
            return None
        
    def delete_group(self, group_id: str) -> None:
        """Delete a group by ID."""
        try:
            self._admin.delete_group(group_id)
            log.info(f"Deleted group {group_id}")
        except KeycloakError as e:
            self._handle_error(f"delete_group({group_id})", e)