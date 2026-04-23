"""Keycloak user operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from keycloak import KeycloakError
from .base import KeycloakBaseClient
from clients.keycloak.exceptions import KeycloakClientError
from models.keycloak_models import KeycloakUser

log = logging.getLogger(__name__)


class KeycloakUsersClient(KeycloakBaseClient):
    """Keycloak user operations."""
    
    # ============================================================
    # READ OPERATIONS
    # ============================================================
    
    def get_user(self, user_id: str) -> KeycloakUser | None:
        try:
            user_data = self._admin.get_user(user_id)
            log.debug(f"Got user {user_id}")

            return KeycloakUser(**user_data)  # ❌ REMOVE chamada extra

        except KeycloakError as e:
            log.error(f"Failed to get user {user_id}: {e}")
            return None
        
    def user_verify_email(self, user_id: str) -> bool:
        """Check if user's email is verified."""
        try:
            user = self.get_user(user_id)
            if user and hasattr(user, "emailVerified"):
                return user.emailVerified
            return False
        except KeycloakClientError:
            return False
        
    def set_email_verified(self, user_id: str, verified: bool) -> bool:
        """Set user's email verified status."""
        try:
            self.update_user(user_id, {"emailVerified": verified})
            log.info(f"Set emailVerified={verified} for user {user_id}")
            return True
        except KeycloakClientError:
            return False
    
    def get_users(self, query: Dict[str, Any] | None = None) -> List[KeycloakUser]:
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
    
    def to_dict(self, user: KeycloakUser) -> Dict[str, Any]:
        """Convert KeycloakUser to dict for API calls."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "enabled": user.enabled,
            "attributes": user.attributes,
        }
    # ============================================================
    # WRITE OPERATIONS
    # ============================================================
    
    def create_user(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        Create a new user.
        
        Args:
            payload: User data, e.g. {
                "username": "joao",
                "email": "joao@example.com"
            }
        """
        try:
            user_id = self._admin.create_user(payload)
            log.info(f"Created user {user_id}")
            self.set_user_enabled(user_id, True)  # Enable user by default
            log.info(f"Enabled user {user_id} by default")
            return user_id
        except KeycloakError as e:
            self._handle_error("create_user", e)
            return None

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
            
    def delete_user(self, user_id: str) -> bool:
        """Delete user by ID."""
        try:
            self._admin.delete_user(user_id)
            log.info(f"Deleted user {user_id}")
            return True
        except KeycloakError as e:
            self._handle_error(f"delete_user({user_id})", e)
            return False
            
    def credentials_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user credentials."""
        try:
            creds = self._admin.get_credentials(user_id)
            log.debug(f"Got credentials for user {user_id}")
            return creds
        except KeycloakError as e:
            self._handle_error(f"credentials_user({user_id})", e)
            return []
    
    def set_user_attributes(self, user_id: str, attributes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Add or update user attributes.

        Keycloak stores attributes as lists!
        """
        try:
            user = self.get_user(user_id)

            payload = {**self.to_dict(user), "attributes": attributes}

            self.update_user(user_id, payload)

            log.info(f"Set attributes for user {user_id}: {list(attributes.keys())}")
            return self.get_user_attributes(user_id)

        except KeycloakError as e:
            self._handle_error(f"set_user_attributes({user_id})", e)
    
    def get_user_attributes(self, user_id: str) -> Dict[str, List[str]]:
        try:
            user_data = self._admin.get_user(user_id)
            return user_data.get("attributes", {}) or {}
        except KeycloakError as e:
            self._handle_error(f"get_user_attributes({user_id})", e)
            return {}
    
    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        """Enable or disable user."""
        try:
            self.update_user(user_id, {"enabled": enabled, "emailVerified": enabled})
            log.info(f"User {user_id} {'enabled' if enabled else 'disabled'}")
            return True
        except KeycloakClientError:
            return False
        
    def set_user_password(self, user_id: str, password: str, temporary: bool = True) -> Dict:
        return super().set_user_password(user_id, password, temporary)