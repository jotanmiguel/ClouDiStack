# ks2cs/handler.py
from __future__ import annotations
import logging
from cs import CloudStack
from .keycloak_client import KeycloakClient
from models.keycloak_models import KeycloakUserCreateEvent
from .mapping import decide_role_from_email
from .idempotency import is_provisioned
from .provision_actions import ProvisionResult
from cloudi.user_ops import ensure_student_account

log = logging.getLogger("ks2cs.handler")

def handle_user_create_event(*, kc: KeycloakClient, cs: CloudStack, event: KeycloakUserCreateEvent, provisioned_attr: str = "cloudstackProvisioned", account_attr: str = "cloudstackAccount", cs_account_id_attr: str = "cloudstackAccountId", cs_user_id_attr: str = "cloudstackUserId", cs_role_attr: str = "cloudstackRole") -> ProvisionResult | None:
    """
    Processa um evento CREATE USER:
    - idempotência via atributo no Keycloak
    - cria account/user no CloudStack (student/staff)
    - escreve IDs no Keycloak
    Retorna ProvisionResult se criar/marcar, ou None se skip.
    """
    # 1) carrega user completo (para ver attributes atuais)
    user = kc.get_user(event.user_id)
    
    if is_provisioned(user, provisioned_attr):
        log.info("SKIP already provisioned user_id=%s name=%s email=%s", event.user_id, event.username, event.email)
        return None

    role = decide_role_from_email(event.email)

    # 2) chama CloudStack (por agora só student)
    # TODO Either implement create staff or implement a generic ensure_account_and_user that can handle both roles (and future roles)
    if role == "student":
        resp = ensure_student_account(cs, email=event.email, username=event.username, firstname=event.first_name, lastname=event.last_name)
    else:
        # TODO quando tiveres create_staff
        raise NotImplementedError("create_staff not implemented yet")

    result = ProvisionResult(
        role=role,
        username=resp["username"],
        email=resp["email"],
        account_id=resp["account_id"],
        user_id=resp["user_id"],
        created=bool(resp.get("created", True)),
        changed=bool(resp.get("changed", False)),
        time_duration_s=float(resp.get("time_duration_s", 0.0)),
    )

    log.info(
        "PROVISIONED role=%s kc_user_id=%s username=%s email=%s cs_account=%s cs_account_id=%s cs_user_id=%s",
        result.role, event.user_id, result.username, result.email, result.username, result.account_id, result.user_id
    )

    return result