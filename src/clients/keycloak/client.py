"""Main Keycloak HTTP client."""
from __future__ import annotations
import logging
from .users import KeycloakUsersClient
from .groups import KeycloakGroupsClient
from .events import KeycloakEventsClient

log = logging.getLogger(__name__)


class KeycloakClient(
    KeycloakUsersClient,
    KeycloakGroupsClient,
    KeycloakEventsClient
):
    """
    Main Keycloak HTTP client.
    Combines users, groups, and events operations.
    """
    
    def __init__(self, config):
        """Initialize."""
        super().__init__(config)
        log.info("✅ KeycloakClient initialized (users + groups + events)")