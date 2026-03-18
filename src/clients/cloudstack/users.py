"""CloudStack user operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from clients.cloudstack.base import CloudStackBaseClient
 
log = logging.getLogger(__name__)
 
 
class CloudStackUsersClient(CloudStackBaseClient):
    """CloudStack user operations."""
    
    def get_user(self, user_id: str) -> Dict[str, Any] | None:
        """Get user by ID."""
        try:
            resp = self._cs.listUsers(id=user_id) or {}
            users = resp.get("user", []) or []
            return users[0] if users else None
        except Exception as e:
            self._handle_error(f"get_user({user_id})", e)
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update user (email, firstname, lastname, etc)."""
        try:
            log.debug(f"Updating user {user_id}")
            self._cs.updateUser(id=user_id, **updates)
            log.info(f"Updated user {user_id}")
        except Exception as e:
            self._handle_error(f"update_user({user_id})", e)