"""CloudStack user operations."""
from __future__ import annotations
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


class CloudStackUsersClient:
    """CloudStack user operations."""
    
    def get_user(self, user_id: str) -> Dict[str, Any] | None:
        """Get user by ID."""
        pass
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update user."""
        pass