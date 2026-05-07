"""Keycloak event operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List
from keycloak.exceptions import KeycloakError
from .base import KeycloakBaseClient
from .exceptions import KeycloakClientError

log = logging.getLogger(__name__)


class KeycloakEventsClient(KeycloakBaseClient):
    """Keycloak event operations."""
    
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
            self._handle_error("get_admin_events", e)
            return []
        
    def get_user_events(self, user_id: str, query: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Get events for a specific user.
        
        Args:
            user_id: Keycloak user ID
            query: Optional filters like {
                "dateFrom": "2025-03-16",
                "dateTo": "2025-03-17",
                "max": 100
            }
        
        Returns:
            List of events related to the user
        """
        try:
            events = self._admin.get_events(query or {})
            log.debug(f"Got {len(events)} events for user {user_id}")
            return events
        except KeycloakError as e:
            self._handle_error("get_user_events", e)
            return []