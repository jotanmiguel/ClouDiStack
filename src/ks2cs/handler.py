from __future__ import annotations
import logging
from time import time
from clients.keycloak.client import KeycloakClient
from clients.cloudstack.client import CloudStackClient
from models.keycloak_models import KeycloakUserCreateEvent, _parse_representation
from ks2cs.mapping import decide_cloudstack_role_from_keycloak
from ks2cs.provision_actions import ProvisionResult
from policy.service import PolicyService
from utils.cs_setup.cloudstack_role_setup import CloudStackRoleSetup
from utils.identity import gen_username

log = logging.getLogger("ks2cs.handler")

STUDENT_ROLE_ID    = "c36f7dfb-31bd-11f1-8f49-cec6e5fcc99e"
STAFF_ROLE_ID      = "e7580ffb-8931-4dea-9659-481c7d1d7c71"  # TODO: substituir

# Mapping de role name para role ID
ROLE_NAME_TO_ID = {
    "student": STUDENT_ROLE_ID,
    "staff": STAFF_ROLE_ID,
}


def _normalize_role_name(role_name: str | None) -> str:
    return (role_name or "").strip().lower()


def _resolve_role_id(cs: CloudStackClient, role_name: str | None) -> str | None:
    normalized = _normalize_role_name(role_name)
    if not normalized:
        return None

    role_id = cs.get_role_id_by_name(normalized)
    if role_id:
        return role_id

    return ROLE_NAME_TO_ID.get(normalized)


def _sync_cloudstack_role(kc: KeycloakClient, cs: CloudStackClient, user_id: str) -> dict:
    """Reconcile the CloudStack account role with the current Keycloak state."""
    kc_user = kc.get_user(user_id)
    if not kc_user:
        return {"skipped": True, "reason": "kc_user_not_found"}

    role_name, domain_name, custom_config = decide_cloudstack_role_from_keycloak(kc_user)
    role_id = _resolve_role_id(cs, role_name)
    if not role_id:
        return {"skipped": True, "reason": f"role_not_found:{role_name}"}

    attrs = kc.get_user_attributes(user_id) or {}
    account_id = attrs.get("cloudstackAccountId", [None])[0]
    if not account_id:
        return {"skipped": True, "reason": "no_cs_account_id"}

    account = cs.get_account(account_id)
    if not account:
        return {"skipped": True, "reason": "account_not_found"}

    current_role_id = account.get("roleid") or account.get("roleId")
    if current_role_id == role_id:
        return {
            "skipped": True,
            "reason": "role_unchanged",
            "role": role_name,
            "role_id": role_id,
            "domain": domain_name,
            "tier": custom_config.get("tier", "standard"),
        }

    cs.change_account_role(account_id, role_id)

    kc.set_user_attributes(
        user_id,
        {
            **attrs,
            "cloudstackRole": [role_name],
            "cloudstackRoleId": [role_id],
            "keycloakInternalUpdate": ["true"],
        },
    )

    return {
        "updated": True,
        "account_id": account_id,
        "previous_role_id": current_role_id,
        "role": role_name,
        "role_id": role_id,
        "domain": domain_name,
        "tier": custom_config.get("tier", "standard"),
    }

DOMAIN_GROUP_MAP = {
    "alunos.fc.ul.pt":  "students",
    "di.fc.ul.pt":      "staff",
    "fc.ul.pt":         "staff",
}

DEFAULT_GROUP = "users"

def _resolve_group_from_email(email: str) -> str:
    """
    Decide grupo baseado no domínio do email.

    fc56908@alunos.fc.ul.pt → students
    prof@di.fc.ul.pt        → staff
    unknown@gmail.com       → users (default)
    """
    try:
        domain = email.split("@", 1)[-1].lower().strip()
    except Exception:
        return DEFAULT_GROUP

    # Match exato
    if domain in DOMAIN_GROUP_MAP:
        return DOMAIN_GROUP_MAP[domain]

    # Match parcial — qualquer subdomínio com "alunos"
    if "alunos" in domain:
        return "students"

    return DEFAULT_GROUP

def _is_provisioned(kc: KeycloakClient, user_id: str, flag_attr: str) -> bool:
    attrs = kc.get_user_attributes(user_id) or {}
    v = attrs.get(flag_attr)
    return bool(v and isinstance(v, list) and ( str(v[0]).lower() == "true" or str(v[0]).lower() == "1" or str(v[0]).lower() == "yes" ) )

def _mark_provisioned(kc: KeycloakClient, user_id: str, *, account_id: str, roleid: str, tier: str, cs_user_id: str, **kwargs) -> None:
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
    
def _update_provisioned(kc: KeycloakClient, user_id: str, **kwargs) -> None:
    existing = kc.get_user_attributes(user_id) or {}

    new_attrs = {
        f"cloudstack{k[0].upper()}{k[1:]}": [str(v)]
        for k, v in kwargs.items()
    }

    merged = {**existing, **new_attrs, "keycloakInternalUpdate": ["true"]}

    if existing == merged:
        return

    kc.set_user_attributes(user_id, merged)

# User events

def handle_user_create_event(kc: KeycloakClient,cs: CloudStackClient,event: KeycloakUserCreateEvent,provisioned_attr: str = "cloudstackProvisioned",account_attr: str = "cloudstackAccount",cs_account_id_attr: str = "cloudstackAccountId",cs_user_id_attr: str = "cloudstackUserId",cs_role_attr: str = "cloudstackRole",) -> ProvisionResult | None:

    if _is_provisioned(kc, event.user_id, provisioned_attr):
        log.info("SKIP already provisioned user_id=%s email=%s", event.user_id, event.email)
        return None

    try:
        kc_user = kc.get_user(event.user_id)
        if not kc_user:
            log.error("User not found in Keycloak: %s", event.user_id)
            return None
    except Exception as e:
        log.error("Failed to fetch user from Keycloak: %s", e)
        return None

    # Decidir role baseado nos grupos do Keycloak (muito mais robusto que apenas email)
    # TODO: Review mapping logic
    role_name, domain_name, custom_config = decide_cloudstack_role_from_keycloak(kc_user)
    
    role_id = _resolve_role_id(cs, role_name)
    if not role_id:
        log.error(f"Role '{role_name}' not mapped to role ID")
        return None

    t0 = time()

    try:
        username = event.username or gen_username(event.email)
    except Exception as e:
        log.error(f"No username found and can't be generated: {e}")
        return None

    # 1. Garantir conta no CloudStack
    try:
        acc = cs.get_account_by_name(username)
    except Exception as e:
        log.error(f"Error occurred while fetching account: {e}")
        raise

    changed = False
    if not acc:
        log.info("CREATE account username=%s email=%s role=%s domain=%s", username, event.email, role_name, domain_name)
        result = cs.create_account(
            username=username,
            email=event.email,
            firstname=event.first_name,
            lastname=event.last_name,
            password="",
            role_id=role_id,
            userid=event.user_id,
        )
        account_id = result["account_id"]
        cs_user_id = str(result["user_id"])
        created    = True
    else:
        account_id = acc["id"]
        users      = acc.get("user", [])
        cs_user_id = str(users[0]["id"]) if users else None
        created    = False
        # Atualizar role se for diferente
        current_role_id = acc.get("roleid") or acc.get("roleId")
        if current_role_id != role_id:
            try:
                cs.change_account_role(account_id, role_id)
                log.info("Updated account role account_id=%s old=%s new=%s", account_id, current_role_id, role_id)
                changed = True
            except Exception as e:
                log.error("Failed to update account role account_id=%s: %s", account_id, e)

        log.info("EXISTS account username=%s account_id=%s", username, account_id)

    # 2. Garantir SSO
    if not cs_user_id:
        log.error("CloudStack user ID missing after provisioning account_id=%s", account_id)
        return None

    cs.authorize_saml_sso(cs_user_id)
    log.info("SSO enabled cs_user_id=%s", cs_user_id)

    duration = round(time() - t0, 2)

    # 3. Marcar como provisionado no Keycloak
    _mark_provisioned(
        kc=kc,
        user_id=event.user_id,
        account_id=account_id,
        roleid=role_id,
        tier=custom_config.get("tier", "standard"),
        cs_user_id=cs_user_id,
        internal=True,
    )
    log.info("MARKED_PROVISIONED kc_user_id=%s account_id=%s role=%s tier=%s", event.user_id, account_id, role_name, custom_config.get("tier", "standard"))

    # 4. Atribuir grupo baseado no domínio do email (apenas se não tiver grupos no KC)
    if kc_user.groups:
        log.info("User already has groups in Keycloak: %s — skipping email-based group assignment", kc_user.groups)
    else:
        group_name = _resolve_group_from_email(event.email)
        log.info("User has no groups — resolved group '%s' from email '%s'", group_name, event.email)

        group = kc.get_group_by_name(group_name)
        if not group:
            log.warning("Group '%s' not found in Keycloak — skipping assignment", group_name)
        else:
            try:
                kc.add_user_to_group(event.user_id, group["id"])
                log.info("User %s added to group '%s'", event.user_id, group_name)
            except Exception as e:
                log.error("Failed to add user %s to group '%s': %s", event.user_id, group_name, e)

    # 5. Aplicar quotas
    try:
        policy_svc = PolicyService(kc=kc, cs=cs)
        policy_result = policy_svc.enforce_for_user(event.user_id)
        log.info("POLICY_APPLIED kc_user_id=%s result=%s", event.user_id, policy_result)
    except Exception as e:
        log.error("POLICY_FAILED kc_user_id=%s error=%s", event.user_id, e)

    role_sync_result = _sync_cloudstack_role(kc, cs, event.user_id)
    log.info("ROLE_SYNC kc_user_id=%s result=%s", event.user_id, role_sync_result)

    return ProvisionResult(
        role=role_name,
        username=username,
        email=event.email,
        account_id=account_id,
        user_id=cs_user_id or "",
        created=created,
        changed=changed,
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
        

# Group events    
        
def handle_group_membership_create_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict) -> dict:
    """Processa GROUP_MEMBERSHIP CREATE e aplica quotas do grupo no CloudStack."""

    # TODO: mover funcao para utils e reutilizar no CLI de sync de grupos
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
        role_result = _sync_cloudstack_role(kc, cs, kc_user_id)

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
            "role_result": role_result,
        }

    except Exception as e:
        log.error("Erro ao processar GROUP_MEMBERSHIP CREATE: %s", str(e), exc_info=True)
        return {"handled": False, "error": str(e)}

def handle_group_membership_change_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict, operation: str) -> dict:
    """Processa GROUP_MEMBERSHIP CREATE e DELETE e aplica ou remove quotas do grupo no CloudStack."""
    # Para simplificar, ambos os eventos podem ser tratados da mesma forma, já que a política será reavaliada
    return handle_group_membership_create_event(kc=kc, cs=cs, raw=raw)

def _extract_group_id(raw: dict) -> str | None:
    resource_path = (raw.get("resourcePath") or "").strip("/")
    parts = resource_path.split("/") if resource_path else []

    if len(parts) >= 2 and parts[0] == "groups":
        return parts[1]

    return raw.get("groupId") or raw.get("group_id")


def handle_group_sync_event(*, kc: KeycloakClient, cs: CloudStackClient, raw: dict, dry_run: bool = False) -> dict:
    """Create CloudStack roles from Keycloak groups when a group event is received."""
    group_id = _extract_group_id(raw)
    if not group_id:
        return {"skipped": True, "reason": "no_group_id"}

    group = kc.get_group(group_id)
    if not group:
        rep = _parse_representation(rep=raw.get("representation"))
        if rep:
            group = rep
            group.setdefault("id", group_id)

    if not group:
        return {"skipped": True, "reason": "group_not_found"}

    setup = CloudStackRoleSetup(kc=kc, cs=cs)
    result = setup.sync_group(group=group, dry_run=dry_run)

    return {
        "handled": True,
        "event": "GROUP_SYNC",
        "group_id": group_id,
        "group_name": group.get("name"),
        "result": result,
    }