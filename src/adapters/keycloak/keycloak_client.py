from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakError

log = logging.getLogger(__name__)


class KeycloakClientError(Exception):
    """Base exception for Keycloak client errors."""
    pass


class KeycloakClient:
    """
    HTTP wrapper para Keycloak Admin API.
    Responsável apenas por comunicar com Keycloak.
    """
    
    def __init__(self, config):
        """Initialize Keycloak connection."""
        log.info(
            "Connecting to Keycloak at %s (realm=%s, user=%s)",
            config.kc_server_url, config.kc_realm, config.kc_username
        )
        
        try:
            self._conn = KeycloakOpenIDConnection(
                server_url=config.kc_server_url,
                realm_name=config.kc_realm,
                client_id=config.kc_client_id,
                username=config.kc_username,
                password=config.kc_password,
                verify=config.kc_verify_tls,
            )
            
            self._admin = KeycloakAdmin(connection=self._conn)
            self._admin.change_current_realm(config.kc_realm_name)
            
            log.info("✅ Keycloak client ready")
        except Exception as e:
            log.error(f"Failed to initialize Keycloak client: {e}")
            raise KeycloakClientError(f"Keycloak connection failed: {e}")
    
    # ============================================================
    # USER READ OPERATIONS
    # ============================================================
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.
        
        Returns:
            {
                "id": "user-uuid",
                "username": "joao",
                "email": "joao@example.com",
                "firstName": "João",
                "lastName": "Silva",
                "enabled": true,
                "emailVerified": false,
                "attributes": {...},
                ...
            }
        """
        try:
            user = self._admin.get_user(user_id)
            log.debug(f"Got user {user_id}")
            return user
        except KeycloakError as e:
            log.error(f"Failed to get user {user_id}: {e}")
            raise KeycloakClientError(f"Get user failed: {e}")
    
    def get_users(self, query: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        List all users (with optional filters).
        
        Args:
            query: Optional filters like {"username": "joao", "email": "joao@example.com"}
        
        Returns:
            List of user objects
        """
        try:
            users = self._admin.get_users(query or {})
            log.debug(f"Got {len(users)} users")
            return users
        except KeycloakError as e:
            log.error(f"Failed to list users: {e}")
            raise KeycloakClientError(f"List users failed: {e}")
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists by username."""
        try:
            users = self.get_users({"username": username})
            exists = len(users) > 0
            log.debug(f"User {username} exists: {exists}")
            return exists
        except KeycloakClientError:
            return False
    
    # ============================================================
    # USER WRITE OPERATIONS
    # ============================================================
    
    def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        """
        Update user (e.g., email, firstName, lastName, attributes).
        
        Args:
            user_id: User UUID
            payload: Dict with fields to update
        
        Example:
            update_user("user-123", {
                "email": "newemail@example.com",
                "firstName": "João",
                "attributes": {
                    "cloudstack_tier": ["premium"]
                }
            })
        """
        try:
            self._admin.update_user(user_id, payload)
            log.info(f"Updated user {user_id}")
        except KeycloakError as e:
            log.error(f"Failed to update user {user_id}: {e}")
            raise KeycloakClientError(f"Update user failed: {e}")
    
    def set_user_attributes(self, user_id: str, attributes: Dict[str, List[str]]) -> None:
        """
        Set user attributes.
        
        Keycloak stores attributes as lists!
        
        Args:
            user_id: User UUID
            attributes: Dict with keys and list values
        
        Example:
            set_user_attributes("user-123", {
                "cloudstack_tier": ["premium"],
                "cloudstack_account_id": ["acc-123"]
            })
        """
        try:
            payload = {"attributes": attributes}
            self._admin.update_user(user_id, payload)
            log.info(f"Set attributes for user {user_id}: {list(attributes.keys())}")
        except KeycloakError as e:
            log.error(f"Failed to set attributes for {user_id}: {e}")
            raise KeycloakClientError(f"Set attributes failed: {e}")
    
    def get_user_attributes(self, user_id: str) -> Dict[str, List[str]]:
        """
        Get user attributes.
        
        Returns:
            {
                "cloudstack_tier": ["standard"],
                "cloudstack_account_id": ["acc-123"],
                ...
            }
        """
        try:
            user = self.get_user(user_id)
            attrs = user.get("attributes", {})
            log.debug(f"Got attributes for user {user_id}")
            return attrs
        except KeycloakClientError:
            raise
    
    # ============================================================
    # GROUP OPERATIONS
    # ============================================================
    
    def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get groups for a user.
        
        Returns:
            [
                {"id": "group-uuid", "name": "students", "path": "/students"},
                {"id": "group-uuid", "name": "special_project", "path": "/special_project"},
                ...
            ]
        """
        try:
            groups = self._admin.get_user_groups(user_id)
            log.debug(f"Got {len(groups)} groups for user {user_id}")
            return groups
        except KeycloakError as e:
            log.error(f"Failed to get groups for {user_id}: {e}")
            raise KeycloakClientError(f"Get user groups failed: {e}")
    
    def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """
        Add user to group.
        
        Args:
            user_id: User UUID
            group_id: Group UUID
        """
        try:
            self._admin.assign_user_to_group(user_id, group_id)
            log.info(f"Added user {user_id} to group {group_id}")
        except KeycloakError as e:
            log.error(f"Failed to add user {user_id} to group {group_id}: {e}")
            raise KeycloakClientError(f"Add user to group failed: {e}")
    
    def remove_user_from_group(self, user_id: str, group_id: str) -> None:
        """Remove user from group."""
        try:
            self._admin.remove_user_from_group(user_id, group_id)
            log.info(f"Removed user {user_id} from group {group_id}")
        except KeycloakError as e:
            log.error(f"Failed to remove user {user_id} from group {group_id}: {e}")
            raise KeycloakClientError(f"Remove user from group failed: {e}")
    
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
            log.debug(f"Got {len(groups)} groups")
            return groups
        except KeycloakError as e:
            log.error(f"Failed to list groups: {e}")
            raise KeycloakClientError(f"List groups failed: {e}")
    
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
        except KeycloakClientError:
            raise
    
    def create_group(self, name: str, path: str = "") -> str:
        """
        Create a new group.
        
        Args:
            name: Group name
            path: Group path (e.g., "/students")
        
        Returns:
            Group ID
        """
        try:
            group_id = self._admin.create_group({"name": name, "path": path or f"/{name}"})
            log.info(f"Created group {name} (id={group_id})")
            return group_id
        except KeycloakError as e:
            log.error(f"Failed to create group {name}: {e}")
            raise KeycloakClientError(f"Create group failed: {e}")
    
    # ============================================================
    # ADMIN EVENTS
    # ============================================================
    
    def get_admin_events(self, query: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Get admin events (user creation, deletion, updates, etc).
        
        Args:
            query: Optional filters like {
                "dateFrom": "2025-03-16",
                "dateTo": "2025-03-17",
                "max": 100
            }
        
        Returns:
            List of events
        """
        try:
            events = self._admin.get_admin_events(query or {})
            log.debug(f"Got {len(events)} admin events")
            return events
        except KeycloakError as e:
            log.error(f"Failed to get admin events: {e}")
            raise KeycloakClientError(f"Get admin events failed: {e}")
    
    # ============================================================
    # UTILITY
    # ============================================================
    
    def health_check(self) -> bool:
        """Check if Keycloak is reachable."""
        try:
            self.list_groups()
            return True
        except KeycloakClientError:
            return False