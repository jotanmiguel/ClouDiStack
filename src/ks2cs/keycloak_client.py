from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from typing import Any, Dict, List, Optional
import logging
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from models.keycloak_models import KeycloakAdminEvent, KeycloakUserCreateEvent, to_user_create_event, KeycloakUser

log = logging.getLogger("kc2cs.keycloak")

@dataclass(frozen=True)
class AdminEvent:
    resource_path: str
    operation_type: str
    resource_type: str
    time_ms: int

class KeycloakClient(KeycloakAdmin):
    """
    Autentica num realm (auth_realm, tipicamente master) e opera noutro (target_realm).
    """
    def __init__(self, config):
        log.info("Connecting to Keycloak server at %s with auth_realm=%s and client_id=%s", config.kc_server_url, config.kc_realm, config.kc_client_id)

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

        log.info("KeycloakClient ready. auth_realm=%s target_realm=%s", config.kc_realm, config.kc_realm)
        
    def __getattr__(self, name):
        """
        Forward unknown attributes to KeycloakAdmin.
        """
        return getattr(self._admin, name)
        
    def get_client(self) -> KeycloakAdmin:
        return self._admin