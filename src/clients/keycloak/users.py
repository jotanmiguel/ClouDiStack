"""Keycloak user operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from httpx import get
from keycloak.exceptions import KeycloakError
from .base import KeycloakBaseClient
from .exceptions import KeycloakClientError
from models.keycloak_models import KeycloakUser

log = logging.getLogger(__name__)


class KeycloakUsersClient(KeycloakBaseClient):
    """Keycloak user operations."""
    
    # ============================================================
    # READ OPERATIONS
    # ============================================================
    
    def get_user(self, user_id: str) -> KeycloakUser | None:
        """
        Get user by ID.
        
        Returns:
            KeycloakUser instance or None if not found
        """
        try:
            user_data = self._admin.get_user(user_id)
            log.debug(f"Got user {user_id}")
            return KeycloakUser(**user_data)
        except KeycloakError as e:
            log.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_users(self, query: Dict[str, Any] | None = None) -> List[KeycloakUser]:
        """
        List all users (with optional filters).
        
        Args:
            query: Optional filters like {"username": "joao", "email": "joao@example.com"}
        
        Returns:
            List of KeycloakUser instances
        """
        try:
            log.debug(f"Getting users with query: {query}")
            users_data = self._admin.get_users(query or {})
            log.debug(f"Got {len(users_data)} users")
            return [KeycloakUser(**user_data) for user_data in users_data]
        except KeycloakError as e:
            log.error(f"Failed to get users: {e}")
            return []
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists by username."""
        try:
            users = self.get_users({"username": username})
            exists = len(users) > 0
            log.debug(f"User {username} exists: {exists}")
            return exists
        except Exception:
            return False
    
    # ============================================================
    # WRITE OPERATIONS
    # ============================================================
    
    def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        """
        Update user (email, firstName, lastName, attributes, etc).
        
        Args:
            user_id: User UUID
            payload: Fields to update
        
        Example:
            update_user("user-123", {
                "email": "newemail@example.com",
                "firstName": "João"
            })
        """
        try:
            self._admin.update_user(user_id, payload)
            log.info(f"Updated user {user_id}")
        except KeycloakError as e:
            self._handle_error(f"update_user({user_id})", e)
    
    def set_user_attributes(self, user_id: str, attributes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Add or update user attributes.

        Keycloak stores attributes as lists!
        """
        try:
            current_attributes = self.get_user_attributes(user_id) or {}
            # merge attributes
            merged_attributes = {**current_attributes, **attributes}
            payload = {"attributes": merged_attributes}

            self._admin.update_user(user_id, payload)

            log.info(f"Set attributes for user {user_id}: {list(attributes.keys())}")
            return self.get_user_attributes(user_id)

        except KeycloakError as e:
            self._handle_error(f"set_user_attributes({user_id})", e)
    
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
            if not user:
                log.warning(f"User {user_id} not found")
                return {}
            
            attrs = user.attributes or {}
            log.debug(f"Got attributes for user {user_id}")
            return attrs
        except KeycloakClientError:
            raise
    
    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        """Enable or disable user."""
        try:
            self.update_user(user_id, {"enabled": enabled})
            log.info(f"User {user_id} {'enabled' if enabled else 'disabled'}")
            return True
        except KeycloakClientError:
            return False