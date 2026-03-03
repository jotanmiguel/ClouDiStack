from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from models.keycloak_models import KeycloakUserCreateEvent, to_user_create_event

log = logging.getLogger("kc2cs.keycloak")

@dataclass(frozen=True)
class AdminEvent:
    resource_path: str
    operation_type: str
    resource_type: str
    time_ms: int

class KeycloakClient:
    """
    Autentica num realm (auth_realm, tipicamente master) e opera noutro (target_realm).
    """
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        client_id: str = "admin-cli",
        verify_tls: bool = True,
        auth_realm: str = "master",
        target_realm: Optional[str] = None,
    ):
        # Se não passares target_realm, por defeito opera no mesmo realm do auth.
        target_realm = target_realm or auth_realm

        self.auth_realm = auth_realm
        self.target_realm = target_realm

        self._conn = KeycloakOpenIDConnection(
            server_url=server_url, 
            realm_name=auth_realm, 
            client_id=client_id, 
            username=username, 
            password=password, 
            verify=verify_tls,
            )

        self._admin = KeycloakAdmin(connection=self._conn)

        # 🔥 garante que os endpoints /admin/realms/{realm}/... usam o realm alvo
        self._admin.change_current_realm(self.target_realm)

        log.info("KeycloakClient ready. auth_realm=%s target_realm=%s", self.auth_realm, self.target_realm)


    def get_admin_events(self, query: dict = {}) -> List:
        print("CURRENT REALM:", self._admin.get_current_realm())

        raw_events: List[dict[str, Any]] = self._admin.get_admin_events(query)

        return raw_events
    
    def get_user_create_events(self, max_results: int = 50) -> List[KeycloakUserCreateEvent]:
        raw_events = self._admin.get_admin_events({"max": max_results})

        out: List[KeycloakUserCreateEvent] = []
        for raw in raw_events:
            ev = to_user_create_event(raw)
            if ev:
                out.append(ev)

        # ordena do mais antigo para o mais recente
        out.sort(key=lambda e: e.time_ms)
        return out

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self._admin.get_user(user_id)

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