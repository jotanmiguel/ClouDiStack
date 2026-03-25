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

STUDENT_ROLE_ID    = "7fd5d665-76f2-46a7-9a03-98e0a42985f8"
STAFF_ROLE_ID      = "e7580ffb-8931-4dea-9659-481c7d1d7c71"  # TODO: substituir

def _is_provisioned(kc: KeycloakClient, user_id: str, flag_attr: str) -> bool:
    attrs = kc.get_user_attributes(user_id) or {}
    v = attrs.get(flag_attr)
    return bool(v and isinstance(v, list) and ( str(v[0]).lower() == "true" or str(v[0]).lower() == "1" or str(v[0]).lower() == "yes" ) )

def _mark_provisioned(kc: KeycloakClient,user_id: str,*,account_id: str,roleid: str,tier: str,cs_user_id: str,internal:bool) -> None:
    kc.set_user_attributes(user_id, {
        "cloudstackProvisioned": ["true"],
        "cloudstackAccountId": [account_id],
        "cloudstackUserId": [cs_user_id],  # 🔥 correto
        "cloudstackRoleId": [roleid],
        "cloudstackTier": [tier],
        "cloudstackStatus": ["active"],
        "cloudstackSync": [str(time())],
        "keycloakInternalUpdate": [str(internal)],  # 🔥 garantir flag limpa
    })
    
def _update_provisioned(kc: KeycloakClient, user_id: str, **kwargs) -> None:
    existing = kc.get_user_attributes(user_id) or {}

    new_attrs = {}
    for k, v in kwargs.items():
        print(f"cloudstack{k[0].upper()}{k[1:]}")
        new_attrs[f"cloudstack{k[0].upper()}{k[1:]}"] = [str(v)]

    merged = {**existing, **new_attrs}

    if existing == merged:
        return

    # 🔥 marcar flag APENAS quando necessário
    merged["keycloakInternalUpdate"] = ["true"]

    kc.set_user_attributes(user_id, merged)

def handle_user_create_event(kc: KeycloakClient,cs: CloudStackClient,event: KeycloakUserCreateEvent,provisioned_attr: str = "cloudstackProvisioned",account_attr: str = "cloudstackAccount",cs_account_id_attr: str = "cloudstackAccountId",cs_user_id_attr: str = "cloudstackUserId",cs_role_attr: str = "cloudstackRole",) -> ProvisionResult | None:
    
    if _is_provisioned(kc, event.user_id, provisioned_attr):
        log.info("SKIP already provisioned user_id=%s email=%s", event.user_id, event.email)
        return None

    role = decide_role_from_email(event.email)

    if role == "student":
        role_id   = STUDENT_ROLE_ID
    elif role == "staff":
        role_id   = STAFF_ROLE_ID
    else:
        raise NotImplementedError(f"Role '{role}' not implemented")

    t0 = time()

    try:
        username = event.username or gen_username(event.email)
    except Exception as e:
        log.error(f"No username found and can't be generated: {e}")
        return None

    # 2) garantir conta no CloudStack
    try:
        acc = cs.get_account_by_name(username)
    except Exception as e:
        log.error(f"Error occurred while fetching account: {e}")
        raise

    if not acc:
        result = cs.create_account(
            username=username,
            email=event.email,
            firstname=event.first_name,
            lastname=event.last_name,
            password="",
            role_id=role_id,
            userid=event.user_id,
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
        kc=kc,
        user_id=event.user_id,
        account_id=account_id,
        roleid=role_id,
        tier="default",
        cs_user_id=cs_user_id,
        internal=True,        
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
    details = raw.get("details") or {}
    cs_user_id = details.get("userId")

    if not cs_user_id:
        return {"skipped": True, "reason": "no_user_id"}

    # 🔍 1. descobrir accountId via user
    try:
        user = cs.get_user(cs_user_id)
    except Exception as e:
        return {"skipped": True, "reason": f"user_lookup_failed: {e}"}

    if not user:
        return {"skipped": True, "reason": "user_not_found"}

    account_id = user.get("accountid")
    if not account_id:
        return {"skipped": True, "reason": "no_account_id"}

    try:
        cs.delete_account(account_id)

        log.info(
            "Account apagada account_id=%s cs_user_id=%s",
            account_id,
            cs_user_id,
        )

        return {
            "deleted": True,
            "account_id": account_id,
            "cs_user_id": cs_user_id,
        }

    except Exception as e:
        log.warning("Delete falhou, fallback para disable: %s", e)

        cs.disable_account(account_id)

        return {
            "disabled": True,
            "account_id": account_id,
            "fallback": "delete_failed",
        }

def handle_user_update_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    rep = _parse_representation(rep=raw.get("representation"))
    kc_user_id = rep.get("id")

    if not kc_user_id:
        return {"skipped": True, "reason": "no_user_id"}

    attrs = kc.get_user_attributes(kc_user_id) or {}

    if attrs.get("keycloakInternalUpdate", ["false"])[0] == "true":
        return {"skipped": True, "reason": "internal_update"}

    current_email = attrs.get("email", [None])[0]
    current_firstname = attrs.get("firstname", [None])[0]
    current_lastname = attrs.get("lastname", [None])[0]

    email     = rep.get("email") or current_email
    firstname = rep.get("firstName") or current_firstname
    lastname  = rep.get("lastName") or current_lastname

    updates = {}

    if email != current_email:
        updates["email"] = email

    if firstname != current_firstname:
        updates["firstname"] = firstname

    if lastname != current_lastname:
        updates["lastname"] = lastname

    if not updates:
        return {"skipped": True, "reason": "no_actual_changes"}

    # 🔑 obter user id do CloudStack (OBRIGATÓRIO)
    cs_user_id = attrs.get("cloudstackUserId", [None])[0]

    if not cs_user_id:
        return {"skipped": True, "reason": "no_cs_user_id"}

    # 🔄 atualizar CloudStack
    cs.update_user(cs_user_id, updates)

    # 🏷️ atualizar sync (sem causar loop)
    _update_provisioned(kc, kc_user_id, sync=time())

    log.info(
        "SYNC update kc_user_id=%s cs_user_id=%s fields=%s",
        kc_user_id,
        cs_user_id,
        list(updates.keys())
    )

    return {
        "updated": True,
        "changed_fields": list(updates.keys())
    }