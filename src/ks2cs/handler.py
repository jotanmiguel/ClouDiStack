# ks2cs/handler.py
from __future__ import annotations
import logging

from cs import CloudStack

from .keycloak_client import KeycloakClient
from models.keycloak_models import KeycloakUserCreateEvent
from .mapping import decide_role_from_email
from .idempotency import is_provisioned, set_provisioned_attrs
from .provision_actions import ProvisionResult
from cloudi.user_ops import create_student

log = logging.getLogger("ks2cs.handler")


def handle_user_create_event(
    *,
    kc: KeycloakClient,
    cs: CloudStack,
    event: KeycloakUserCreateEvent,
    # attrs (configuráveis)
    provisioned_attr: str = "cloudstackProvisioned",
    account_attr: str = "cloudstackAccount",
    cs_account_id_attr: str = "cloudstackAccountId",
    cs_user_id_attr: str = "cloudstackUserId",
    cs_role_attr: str = "cloudstackRole",
) -> ProvisionResult | None:
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
    if role == "student":
        resp = create_student(cs, email=event.email, username=event.username, firstname=event.first_name, lastname=event.last_name)
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

    # 3) marcar no Keycloak (idempotência + info para auditoria)
    user2 = set_provisioned_attrs(
        user,
        flag_attr=provisioned_attr,
        account_attr=account_attr,
        cs_account_id_attr=cs_account_id_attr,
        cs_user_id_attr=cs_user_id_attr,
        cs_role_attr=cs_role_attr,
        username=result.username,
        account_id=result.account_id,
        user_id=result.user_id,
        role=result.role,
    )
    kc.update_user(event.user_id, user2)

    log.info(
        "PROVISIONED role=%s kc_user_id=%s username=%s email=%s cs_account=%s cs_account_id=%s cs_user_id=%s",
        result.role, event.user_id, result.username, result.email, result.username, result.account_id, result.user_id
    )

    return result