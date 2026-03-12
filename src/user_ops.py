from __future__ import annotations

from time import time
from typing import Any, Dict, Optional

from cs import CloudStack
from cloudstack.cs_client import get_cs
from models.cloudstack_models import CSAccount, CSUser, ListAccountsResponse
from utils.identity import gen_password, gen_username

STUDENT_ROLE_ID    = "4eff4f67-dff5-4179-bba8-802d9c7163cc"
STAFF_ROLE_ID      = "4eff4f67-dff5-4179-bba8-802d9c7163cc"  # TODO: substituir pelo ID da role certa
STUDENTS_DOMAIN_ID = "1488a55a-800b-472f-94d7-7273a00a1208"
STAFF_DOMAIN_ID    = "d2fc3766-68f6-4179-a997-b8bc37f9e828"  # TODO: substituir se for domínio diferente
IDP_ENTITY_ID      = "https://10.10.5.52:8443/realms/Cloud-DI"


# ============================================================
# 1) Parsing helpers
# ============================================================

def _parse_list_accounts(resp: Dict[str, Any]) -> ListAccountsResponse:
    data = resp or {}
    if not data:
        data = {"count": 0, "account": []}
    return ListAccountsResponse(**data)


def _unwrap_account_from_create(resp: Dict[str, Any]) -> Dict[str, Any]:
    acct = (resp or {}).get("account")
    if acct:
        return acct
    wrapped = (resp or {}).get("createaccountresponse", {})
    acct = wrapped.get("account")
    if acct:
        return acct
    raise ValueError(f"Unexpected createAccount response keys: {list((resp or {}).keys())}")


# ============================================================
# 2) Queries
# ============================================================

def get_account(cs: CloudStack, account_name: str, domain_id: str) -> Optional[CSAccount]:
    resp = cs.listAccounts(name=account_name, domainid=domain_id, details="min") or {}
    model = _parse_list_accounts(resp)
    return model.account[0] if model.account else None


def get_user_from_account(acc: CSAccount, username: str) -> Optional[CSUser]:
    return next((u for u in acc.user if u.username == username), None)


def get_user_id(cs: CloudStack, username: str, domain_id: str) -> Optional[str]:
    acc = get_account(cs, username, domain_id)
    if not acc:
        return None
    u = get_user_from_account(acc, username)
    return u.id if u else None


def account_exists(cs: CloudStack, email: str, domain_id: str) -> bool:
    username = gen_username(email)
    return get_account(cs, username, domain_id) is not None


def get_roles(cs: CloudStack) -> Dict[str, str]:
    resp = cs.listRoles() or {}
    roles = resp.get("role", []) or []
    return {r["name"]: r["id"] for r in roles}


def get_role_id(cs: CloudStack, role_name: str) -> Optional[str]:
    return get_roles(cs).get(role_name)


def get_role_name(cs: CloudStack, role_id: str) -> Optional[str]:
    for name, rid in get_roles(cs).items():
        if rid == role_id:
            return name
    return None


# ============================================================
# 3) Ensure state
# ============================================================

def ensure_sso_enabled(cs: CloudStack, user_id: str, entity_id: str) -> bool:
    try:
        resp = cs.listUsers(id=user_id) or {}
        users = resp.get("user", []) or []
        u = users[0] if users else {}
        if u.get("samlSsoEnabled") and u.get("samlSsoEntityId") == entity_id:
            return False
    except Exception:
        pass
    cs.authorizeSamlSso(userid=user_id, enable=True, entityid=entity_id)
    return True


def ensure_account_role(cs: CloudStack, account_id: str, role_id: str) -> bool:
    try:
        resp = cs.listAccounts(id=account_id, details="min") or {}
        model = _parse_list_accounts(resp)
        if model.account and model.account[0].roleid == role_id:
            return False
    except Exception:
        pass
    cs.updateAccount(id=account_id, roleid=role_id)
    return True


# ============================================================
# 4) CREATE
# ============================================================

def _create_account(
    cs: CloudStack,
    email: str,
    username: str,
    firstname: str,
    lastname: str,
    domain_id: str,
    role_id: str,
    debug: bool = False,
) -> dict:
    """Base para criar qualquer tipo de conta (student ou staff)."""
    password = gen_password().strip()
    t0 = time()

    resp = cs.createAccount(
        account=username,
        username=username,
        email=email,
        firstname=firstname,
        lastname=lastname,
        password=password,
        domainid=domain_id,
        accounttype="0",
    )

    if debug:
        print("createAccount raw:", resp)

    acct_dict = _unwrap_account_from_create(resp)
    acc_model = CSAccount.model_validate(acct_dict)

    if not acc_model.user:
        raise ValueError("createAccount returned no user list")

    user_id = acc_model.user[0].id

    changed = False
    changed |= ensure_sso_enabled(cs, user_id, IDP_ENTITY_ID)
    changed |= ensure_account_role(cs, acc_model.id, role_id)

    return {
        "username": username,
        "email": email,
        "account_id": acc_model.id,
        "user_id": user_id,
        "time_duration_s": round(time() - t0, 2),
        "created": True,
        "changed": changed,
    }


def create_student(
    cs: CloudStack,
    email: str,
    username: str,
    firstname: str,
    lastname: str,
    debug: bool = False,
) -> dict:
    """Cria uma conta de estudante no CloudStack."""
    return _create_account(
        cs, email, username, firstname, lastname,
        domain_id=STUDENTS_DOMAIN_ID,
        role_id=STUDENT_ROLE_ID,
        debug=debug,
    )


def create_staff(
    cs: CloudStack,
    email: str,
    username: str,
    firstname: str,
    lastname: str,
    debug: bool = False,
) -> dict:
    """Cria uma conta de staff/docente no CloudStack."""
    return _create_account(
        cs, email, username, firstname, lastname,
        domain_id=STAFF_DOMAIN_ID,
        role_id=STAFF_ROLE_ID,
        debug=debug,
    )


# ============================================================
# 5) ENSURE (create or update)
# ============================================================

def ensure_account(
    cs: CloudStack,
    email: str,
    username: str,
    firstname: str,
    lastname: str,
    domain_id: str,
    role_id: str,
    debug: bool = False,
) -> dict:
    """
    Garante que a conta existe e está corretamente configurada.
    Cria se não existir, atualiza SSO e role se necessário.
    """
    start = time()

    acc = get_account(cs, username, domain_id)
    if not acc:
        return _create_account(cs, email, username, firstname, lastname, domain_id, role_id, debug)

    user = get_user_from_account(acc, username)
    user_id = user.id if user else None

    changed = False
    if user_id:
        changed |= ensure_sso_enabled(cs, user_id, IDP_ENTITY_ID)
    changed |= ensure_account_role(cs, acc.id, role_id)

    return {
        "username": username,
        "email": email,
        "account_id": acc.id,
        "user_id": user_id,
        "role": get_role_name(cs, acc.roleid) if acc.roleid else None,
        "time_duration_s": round(time() - start, 2),
        "created": False,
        "changed": changed,
    }


def ensure_student_account(cs, email, username, firstname, lastname, debug=False):
    return ensure_account(cs, email, username, firstname, lastname, STUDENTS_DOMAIN_ID, STUDENT_ROLE_ID, debug)


def ensure_staff_account(cs, email, username, firstname, lastname, debug=False):
    return ensure_account(cs, email, username, firstname, lastname, STAFF_DOMAIN_ID, STAFF_ROLE_ID, debug)


# ============================================================
# 6) UPDATE
# ============================================================

def update_user(
    cs: CloudStack,
    username: str,
    domain_id: str,
    firstname: Optional[str] = None,
    lastname: Optional[str] = None,
    email: Optional[str] = None,
) -> dict:
    """
    Atualiza dados de um utilizador existente no CloudStack.
    Apenas atualiza os campos que forem passados (não None).
    """
    user_id = get_user_id(cs, username, domain_id)
    if not user_id:
        raise ValueError(f"Utilizador '{username}' não encontrado no domínio {domain_id}")

    params: Dict[str, Any] = {"id": user_id}
    if firstname is not None:
        params["firstname"] = firstname
    if lastname is not None:
        params["lastname"] = lastname
    if email is not None:
        params["email"] = email

    if len(params) == 1:
        return {"updated": False, "reason": "no_fields_to_update", "user_id": user_id}

    cs.updateUser(**params)

    return {
        "updated": True,
        "user_id": user_id,
        "username": username,
        "changed_fields": [k for k in ("firstname", "lastname", "email") if k in params],
    }


def update_student(cs, username, **kwargs):
    return update_user(cs, username, STUDENTS_DOMAIN_ID, **kwargs)


def update_staff(cs, username, **kwargs):
    return update_user(cs, username, STAFF_DOMAIN_ID, **kwargs)


# ============================================================
# 7) DISABLE / DELETE
# ============================================================

def disable_account(cs: CloudStack, username: str, domain_id: str) -> dict:
    """
    Desativa a conta de um utilizador no CloudStack (não apaga).
    Usado quando o user é removido do Keycloak — preserva dados.
    """
    acc = get_account(cs, username, domain_id)
    if not acc:
        raise ValueError(f"Conta '{username}' não encontrada no domínio {domain_id}")

    if acc.state == "disabled":
        return {"disabled": False, "reason": "already_disabled", "account_id": acc.id}

    cs.disableAccount(account=username, domainid=domain_id, lock=False)

    return {
        "disabled": True,
        "account_id": acc.id,
        "username": username,
    }


def delete_account(cs: CloudStack, username: str, domain_id: str) -> dict:
    """
    Apaga permanentemente a conta de um utilizador no CloudStack.
    CUIDADO: esta operação é irreversível.
    """
    acc = get_account(cs, username, domain_id)
    if not acc:
        raise ValueError(f"Conta '{username}' não encontrada no domínio {domain_id}")

    cs.deleteAccount(id=acc.id)

    return {
        "deleted": True,
        "account_id": acc.id,
        "username": username,
    }


def disable_student(cs, username):
    return disable_account(cs, username, STUDENTS_DOMAIN_ID)


def disable_staff(cs, username):
    return disable_account(cs, username, STAFF_DOMAIN_ID)


def delete_student(cs, username):
    return delete_account(cs, username, STUDENTS_DOMAIN_ID)


def delete_staff(cs, username):
    return delete_account(cs, username, STAFF_DOMAIN_ID)