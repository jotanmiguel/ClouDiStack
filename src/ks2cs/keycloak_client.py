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
    


    def get_admin_events(self, query: dict = {}) -> List[KeycloakAdminEvent]:
        raw_events: List[dict[str, Any]] = self._admin.get_admin_events(query)
        return [KeycloakAdminEvent(**ev) for ev in raw_events]

    def get_user_create_events(self, max_results: int | None = None, dateFrom: float = 0, dateTo: float = 0) -> List[KeycloakUserCreateEvent]:
        
        datefrom = pd.to_datetime(dateFrom, unit='ms')
        dateto = pd.to_datetime(dateTo, unit='ms')
        
        if max_results is None:
            log.info("Fetching Keycloak admin events with all results with dateFrom=%s dateTo=%s", datefrom, dateto)
            raw_events = self._admin.get_admin_events({"dateFrom": datefrom, "dateTo": dateto})
        else:
            log.info("Fetching Keycloak admin events with max_results=%d with dateFrom=%s dateTo=%s", max_results, datefrom, dateto)
            raw_events = self._admin.get_admin_events({"dateFrom": datefrom, "dateTo": dateto, "max": max_results})
            
        out: List[KeycloakUserCreateEvent] = []
        for raw in raw_events:
            ev = to_user_create_event(raw)
            if ev:
                out.append(ev)

        # ordena do mais antigo para o mais recente
        out.sort(key=lambda e: e.time_ms)
        return out

    def get_user(self, user_id: str) -> KeycloakUser:
        data = self._admin.get_user(user_id=user_id)
        print(data)
        return KeycloakUser(**data)

    def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        self._admin.update_user(user_id=user_id, payload=payload)
    
    @staticmethod
    def extract_user_id(resource_path: str) -> Optional[str]:
        # normalmente: "users/<uuid>"
        if not resource_path:
            return None
        if resource_path.startswith("users/"):
            return resource_path.split("/", 1)[1].strip() or None
        return None