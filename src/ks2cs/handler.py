from __future__ import annotations
import logging
from time import time
from clients.keycloak.client import KeycloakClient
from clients.cloudstack.client import CloudStackClient
from models.keycloak_models import KeycloakUserCreateEvent, _parse_representation
from ks2cs.mapping import decide_role_from_email
from ks2cs.provision_actions import ProvisionResult
from policy.service import PolicyService
from utils.identity import gen_username

log = logging.getLogger("ks2cs.handler")

STUDENT_ROLE_ID    = "c36f7dfb-31bd-11f1-8f49-cec6e5fcc99e"
STAFF_ROLE_ID      = "e7580ffb-8931-4dea-9659-481c7d1d7c71"  # TODO: substituir

def _is_provisioned(kc: KeycloakClient, user_id: str, flag_attr: str) -> bool:
    attrs = kc.get_user_attributes(user_id) or {}
    v = attrs.get(flag_attr)
    return bool(v and isinstance(v, list) and ( str(v[0]).lower() == "true" or str(v[0]).lower() == "1" or str(v[0]).lower() == "yes" ) )

def _mark_provisioned(kc, user_id, *, account_id, roleid, tier, cs_user_id, **kwargs) -> None:
    kc.set_user_attributes(user_id, {
        "cloudstackProvisioned":    ["true"],
        "cloudstackAccountId":      [account_id],
        "cloudstackUserId":         [cs_user_id],
        "cloudstackRoleId":         [roleid],
        "cloudstackTier":           [tier],
        "cloudstackStatus":         ["active"],
        "cloudstackSync":           [str(time())],
        "keycloakInternalUpdate":   ["true"],  # temporária — resetada no próximo evento
    })
    
def _update_provisioned(kc, user_id, **kwargs) -> None:
    existing = kc.get_user_attributes(user_id) or {}

    new_attrs = {
        f"cloudstack{k[0].upper()}{k[1:]}": [str(v)]
        for k, v in kwargs.items()
    }

    merged = {**existing, **new_attrs, "keycloakInternalUpdate": ["true"]}

    if existing == merged:
        return

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
        log.info("CREATE account username=%s email=%s role=%s", username, event.email, role)
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
        log.info("EXISTS account username=%s account_id=%s", username, account_id)
        
    duration = round(time() - t0, 2)
        
    if created:
        log.info("CREATED account_id=%s cs_user_id=%s duration=%ss", account_id, cs_user_id, duration)

    # 3) garantir SSO
    if cs_user_id:
        log.info("SSO enabled cs_user_id=%s", cs_user_id)
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

    log.info("MARKED_PROVISIONED kc_user_id=%s account_id=%s role=%s", event.user_id, account_id, role)


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

def handle_user_update_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    rep = _parse_representation(rep=raw.get("representation"))
    kc_user_id = rep.get("id")

    if not kc_user_id:
        return {"skipped": True, "reason": "no_user_id"}

    attrs = kc.get_user_attributes(kc_user_id) or {}

    # 🔥 lê a flag E reseta imediatamente
    is_internal = attrs.get("keycloakInternalUpdate", ["false"])[0] == "true"
    if is_internal:
        log.debug("SKIP kc_user_id=%s reason=internal_update", kc_user_id)
        kc.set_user_attributes(kc_user_id, {
            **attrs,
            "keycloakInternalUpdate": ["false"]
        })
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
        log.debug("SKIP kc_user_id=%s reason=no_changes", kc_user_id)
        return {"skipped": True, "reason": "no_actual_changes"}

    # 🔑 obter user id do CloudStack (OBRIGATÓRIO)
    cs_user_id = attrs.get("cloudstackUserId", [None])[0]

    if not cs_user_id:
        return {"skipped": True, "reason": "no_cs_user_id"}

    # 🔄 atualizar CloudStack
    cs.update_user(cs_user_id, updates)

    log.info("UPDATE cs_user_id=%s fields=%s", cs_user_id, list(updates.keys()))

    return {
        "updated": True,
        "changed_fields": list(updates.keys())
    }
    
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
        
def handle_group_membership_create_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    """Processa GROUP_MEMBERSHIP CREATE e aplica quotas do grupo no CloudStack."""

    def _extract_ids(payload: dict) -> tuple[str | None, str | None]:
        resource_path = (payload.get("resourcePath") or "").strip("/")
        parts = resource_path.split("/") if resource_path else []

        kc_user_id = None
        group_id = None

        # Formato esperado em admin event:
        # users/<user_id>/groups/<group_id>
        if len(parts) >= 4 and parts[0] == "users" and parts[2] == "groups":
            kc_user_id = parts[1]
            group_id = parts[3]

        # Fallbacks para payloads customizados
        if not kc_user_id:
            kc_user_id = payload.get("userId") or payload.get("user_id")
        if not group_id:
            group_id = payload.get("groupId") or payload.get("group_id")

        return kc_user_id, group_id

    try:
        kc_user_id, group_id = _extract_ids(raw)

        if not kc_user_id:
            log.warning("SKIP group_membership_create reason=no_user_id raw_keys=%s", list(raw.keys()))
            return {"skipped": True, "reason": "no_user_id"}

        service = PolicyService(kc=kc, cs=cs)
        result = service.enforce_for_user(kc_user_id)

        log.info(
            "GROUP_MEMBERSHIP CREATE handled kc_user_id=%s group_id=%s enforced=%s",
            kc_user_id,
            group_id,
            bool(result and result.get("enforced")),
        )

        return {
            "handled": True,
            "event": "GROUP_MEMBERSHIP_CREATE",
            "kc_user_id": kc_user_id,
            "group_id": group_id,
            "result": result,
        }

    except Exception as e:
        log.error("Erro ao processar GROUP_MEMBERSHIP CREATE: %s", str(e), exc_info=True)
        return {"handled": False, "error": str(e)}