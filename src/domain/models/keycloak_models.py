from __future__ import annotations
from dataclasses import dataclass, field
import email
from os import access
from typing import Any, Dict, Optional
import json

@dataclass(frozen=True)
class KeycloakUserCreateEvent:
    """Evento útil para provisionamento (sem dados sensíveis/ruído)."""
    time_ms: int
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    email_verified: bool
    enabled: bool

    @property
    def time(self) -> float:
        """Timestamp em segundos (útil para logs)."""
        return self.time_ms / 1000.0
    
@dataclass(frozen=True)
class KeycloakUser:
    id: str
    emailVerified: bool
    createdTimestamp: int
    enabled: bool
    
    # optional
    email: Optional[str] = None
    username: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    totp: bool = False
    notBefore: Optional[int] = 0
    disableableCredentialTypes: list[str] = field(default_factory=list)
    requiredActions: list[str] = field(default_factory=list)
    access: Dict[str, Any] = field(default_factory=dict)
    
@dataclass(frozen=True)
class KeycloakAdminEvent:
    resource_path: str
    operation_type: str
    resource_type: str
    time_ms: int

# ---------- parsing / normalização ----------

def _norm(s: Any) -> str:
    return (s or "").strip()

def _extract_user_id(resource_path: str) -> str:
    # esperado: "users/<uuid>"
    if not resource_path or not resource_path.startswith("users/"):
        raise ValueError(f"Unexpected resourcePath: {resource_path!r}")
    uid = resource_path.split("/", 1)[1].strip()
    if not uid:
        raise ValueError(f"Empty userId in resourcePath: {resource_path!r}")
    return uid

def _parse_representation(rep: Any) -> Dict[str, Any]:
    if rep is None:
        return {}
    if isinstance(rep, dict):
        return rep
    if isinstance(rep, str):
        rep = rep.strip()
        if not rep:
            return {}
        return json.loads(rep)
    return {}

def event_is_user_create(raw: Dict[str, Any]) -> bool:
    return (raw.get("resourceType") == "USER") and (raw.get("operationType") == "CREATE")

def to_user_create_event(raw: Dict[str, Any]) -> Optional[KeycloakUserCreateEvent]:
    """
    Converte um raw admin event num KeycloakUserCreateEvent.
    Retorna None se não for um CREATE de USER.
    """
    if not event_is_user_create(raw):
        return None

    time_ms = int(raw.get("time") or 0)
    resource_path = _norm(raw.get("resourcePath"))
    user_id = _extract_user_id(resource_path)

    rep = _parse_representation(raw.get("representation"))

    username = _norm(rep.get("username"))
    email = _norm(rep.get("email"))
    first_name = _norm(rep.get("firstName"))
    last_name = _norm(rep.get("lastName"))

    if not email:
        # podes optar por retornar None e depois ir buscar ao KC via get_user(user_id)
        raise ValueError(f"Event for user {user_id} has no email in representation")

    return KeycloakUserCreateEvent(
        time_ms=time_ms,
        user_id=user_id,
        username=username or email,
        email=email,
        first_name=first_name,
        last_name=last_name,
        email_verified=bool(rep.get("emailVerified", False)),
        enabled=bool(rep.get("enabled", True)),
    )