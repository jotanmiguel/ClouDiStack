from __future__ import annotations
import logging
from time import time
from clients.keycloak.client import KeycloakClient
from clients.cloudstack.client import CloudStackClient
from models.keycloak_models import KeycloakUserCreateEvent, _parse_representation
from ks2cs.mapping import decide_role_from_email
from ks2cs.provision_actions import ProvisionResult
from utils.identity import gen_username

log = logging.getLogger("ks2cs.handler")

STUDENTS_DOMAIN_ID = "1488a55a-800b-472f-94d7-7273a00a1208"
STAFF_DOMAIN_ID    = "d2fc3766-68f6-4179-a997-b8bc37f9e828"
STUDENT_ROLE_ID    = "e7580ffb-8931-4dea-9659-481c7d1d7c71"
STAFF_ROLE_ID      = "e7580ffb-8931-4dea-9659-481c7d1d7c71"  # TODO: substituir

def _is_provisioned(kc: KeycloakClient, user_id: str, flag_attr: str) -> bool:
    attrs = kc.get_user_attributes(user_id) or {}
    v = attrs.get(flag_attr)
    return bool(v and isinstance(v, list) and str(v[0]).lower() == "true")

def _mark_provisioned(kc: KeycloakClient,user_id: str,*,flag_attr: str,account_attr: str,cs_account_id_attr: str,cs_user_id_attr: str,cs_role_attr: str,username: str,account_id: str,cs_user_id: str,role: str,) -> None:
    kc.set_user_attributes(user_id, {
        flag_attr:          ["true"],
        account_attr:       [username],
        cs_account_id_attr: [account_id],
        cs_user_id_attr:    [cs_user_id],
        cs_role_attr:       [role],
    })

def handle_user_create_event(*,kc: KeycloakClient,cs: CloudStackClient,event: KeycloakUserCreateEvent,provisioned_attr: str = "cloudstackProvisioned",account_attr: str = "cloudstackAccount",cs_account_id_attr: str = "cloudstackAccountId",cs_user_id_attr: str = "cloudstackUserId",cs_role_attr: str = "cloudstackRole",) -> ProvisionResult | None:

    # 1) idempotência
    if _is_provisioned(kc, event.user_id, provisioned_attr):
        log.info("SKIP already provisioned user_id=%s email=%s", event.user_id, event.email)
        return None

    role = decide_role_from_email(event.email)
    username = gen_username(event.email)

    if role == "student":
        domain_id = STUDENTS_DOMAIN_ID
        role_id   = STUDENT_ROLE_ID
    elif role == "staff":
        domain_id = STAFF_DOMAIN_ID
        role_id   = STAFF_ROLE_ID
    else:
        raise NotImplementedError(f"Role '{role}' not implemented")

    t0 = time()

    # 2) garantir conta no CloudStack
    acc = cs.get_account_by_name(username, domain_id)

    if not acc:
        result = cs.create_account(
            account_name=username,
            username=username,
            email=event.email,
            firstname=event.first_name,
            lastname=event.last_name,
            password="",
            domain_id=domain_id,
            role_id=role_id,
        )
        account_id  = result["account_id"]
        cs_user_id  = result["user_id"]
        created     = True
    else:
        account_id  = acc["id"]
        users       = acc.get("user", [])
        cs_user_id  = users[0]["id"] if users else None
        created     = False

    # 3) garantir SSO
    if cs_user_id:
        cs.authorize_saml_sso(cs_user_id)

    duration = round(time() - t0, 2)

    # 4) escrever resultado de volta no Keycloak
    _mark_provisioned(
        kc, event.user_id,
        flag_attr=provisioned_attr,
        account_attr=account_attr,
        cs_account_id_attr=cs_account_id_attr,
        cs_user_id_attr=cs_user_id_attr,
        cs_role_attr=cs_role_attr,
        username=username,
        account_id=account_id,
        cs_user_id=cs_user_id or "",
        role=role,
    )

    log.info(
        "PROVISIONED role=%s kc_user_id=%s username=%s email=%s account_id=%s user_id=%s",
        role, event.user_id, username, event.email, account_id, cs_user_id,
    )

    return ProvisionResult(
        role=role,
        username=username,
        email=event.email,
        account_id=account_id,
        user_id=cs_user_id or "",
        created=created,
        changed=False,
        time_duration_s=duration,
    )

def handle_user_delete_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    rep = _parse_representation(raw.get("representation"))
    email    = rep.get("email", "")
    username = rep.get("username") or gen_username(email) if email else ""

    if not username:
        return {"skipped": True, "reason": "no_username"}

    role      = decide_role_from_email(email) if email else "student"
    domain_id = STAFF_DOMAIN_ID if role == "staff" else STUDENTS_DOMAIN_ID

    acc = cs.get_account_by_name(username, domain_id)
    if not acc:
        return {"skipped": True, "reason": "account_not_found"}

    cs.disable_account(acc["id"])
    log.info("Desativado: %s (role=%s)", username, role)
    return {"disabled": True, "username": username, "account_id": acc["id"]}

def handle_user_update_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    rep = _parse_representation(raw.get("representation"))
    email     = rep.get("email", "")
    username  = rep.get("username") or gen_username(email) if email else ""
    firstname = rep.get("firstName")
    lastname  = rep.get("lastName")

    if not username:
        return {"skipped": True, "reason": "no_username"}

    updates = {}
    if firstname: updates["firstname"] = firstname
    if lastname:  updates["lastname"]  = lastname
    if email:     updates["email"]     = email

    if not updates:
        return {"skipped": True, "reason": "no_fields_changed"}

    role      = decide_role_from_email(email) if email else "student"
    domain_id = STAFF_DOMAIN_ID if role == "staff" else STUDENTS_DOMAIN_ID

    user_id = cs.get_user_id(username, domain_id)
    if not user_id:
        return {"skipped": True, "reason": "user_not_found"}

    cs.update_user(user_id, updates)
    log.info("Atualizado: %s campos=%s", username, list(updates.keys()))
    return {"updated": True, "username": username, "changed_fields": list(updates.keys())}