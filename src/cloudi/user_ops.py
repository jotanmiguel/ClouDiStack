from __future__ import annotations
from time import time
from typing import Any, Dict, Optional
from cs import CloudStack
from cloudstack.cs_client import get_cs
from models.cloudstack_models import CSAccount, CSUser, ListAccountsResponse
from utils.identity import gen_password, gen_username

STUDENT_ROLE_ID = "e7580ffb-8931-4dea-9659-481c7d1d7c71"
STUDENTS_DOMAIN_ID = "1488a55a-800b-472f-94d7-7273a00a1208"
IDP_ENTITY_ID = "https://10.10.5.52:8443/realms/Cloud-DI"


# ============================================================
# 1) Parsing helpers
# ============================================================

def _parse_list_accounts(resp: Dict[str, Any]) -> ListAccountsResponse:
    """
    Normalizes listAccounts responses.
    Some wrappers return {} when empty; we convert to count=0/account=[].
    """
    data = resp or {}
    if not data:
        data = {"count": 0, "account": []}
    return ListAccountsResponse(**data)


def _unwrap_account_from_create(resp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes createAccount response:
      - {"account": {...}}
      - {"createaccountresponse": {"account": {...}}}
    """
    acct = (resp or {}).get("account")
    if acct:
        return acct

    wrapped = (resp or {}).get("createaccountresponse", {})
    acct = wrapped.get("account")
    if acct:
        return acct

    raise ValueError(f"Unexpected createAccount response keys: {list((resp or {}).keys())}")


# ============================================================
# 2) Queries (get/exists)
# ============================================================

def get_account(cs: CloudStack, account_name: str, domain_id: str) -> Optional[CSAccount]:
    """
    Returns CSAccount if found, else None.
    """
    resp = cs.listAccounts(name=account_name, domainid=domain_id, details="min") or {}
    model = _parse_list_accounts(resp)
    return model.account[0] if model.account else None


def get_user_from_account(acc: CSAccount, username: str) -> Optional[CSUser]:
    """
    Finds a user inside an account by username.
    """
    return next((u for u in acc.user if u.username == username), None)


def get_user_id(cs: CloudStack, username: str, domain_id: str) -> Optional[str]:
    """
    Fetches user_id by reading listAccounts(name=username).
    Works well with your setup: account per user.
    """
    acc = get_account(cs, username, domain_id)
    if not acc:
        return None

    u = get_user_from_account(acc, username)
    return u.id if u else None


def account_exists(cs: CloudStack, email: str, domain_id: str) -> bool:
    username = gen_username(email)
    return get_account(cs, username, domain_id) is not None


def user_exists(cs: CloudStack, email: str, domain_id: str) -> bool:
    username = gen_username(email)
    return get_user_id(cs, username, domain_id) is not None

def get_roles(cs: CloudStack) -> Dict[str, str]:
    """
    Returns a dict of role_name -> role_id.
    """
    resp = cs.listRoles() or {}
    roles = resp.get("role", []) or []
    return {r["name"]: r["id"] for r in roles}

def get_role_id(cs: CloudStack, role_name: str) -> Optional[str]:
    roles = get_roles(cs)
    return roles.get(role_name)

def get_role_name(cs: CloudStack, role_id: str) -> Optional[str]:
    roles = get_roles(cs)
    for name, rid in roles.items():
        if rid == role_id:
            return name
    return None

def get_all_accounts(cs: CloudStack) -> Dict[str, CSAccount]:
    resp = cs.listAccounts(details="min") or {}
    model = _parse_list_accounts(resp)
    return {acc.id: acc for acc in model.account}

# ============================================================
# 3) Ensure state (SSO / Role)
# ============================================================

def ensure_sso_enabled(cs: CloudStack, user_id: str, entity_id: str) -> bool:
    """
    Ensures SAML SSO is enabled for user.
    Returns True if changed something.
    If we can't detect current state, we enable anyway (idempotent).
    """
    try:
        resp = cs.listUsers(id=user_id) or {}
        users = resp.get("user", []) or []
        u = users[0] if users else {}
        if u.get("samlSsoEnabled") and u.get("samlSsoEntityId") == entity_id:
            return True
    except Exception:
        pass

    cs.authorizeSamlSso(userid=user_id, enable=True, entityid=entity_id)
    return True


def ensure_account_role(cs: CloudStack, account_id: str, role_id: str) -> bool:
    """
    Ensures the account has the required dynamic role (roleid).
    Returns True if changed.
    """
    try:
        resp = cs.listAccounts(id=account_id, details="min") or {}
        model = _parse_list_accounts(resp)

        if model.account and model.account[0].roleid == role_id:
            return False
    except Exception:
        # if we can't detect, we still attempt to update (idempotent)
        pass

    cs.updateAccount(id=account_id, roleid=role_id)
    return True


# ============================================================
# 4) Actions (create + ensure)
# ============================================================

def create_student(cs: CloudStack, email: str, username:str, firstname: str, lastname: str, debug: bool = False) -> dict:
    """
    Creates a student account + initial user, then ensures SSO and student role.
    """
    
    password = gen_password().strip() # the api requires non-empty passwords, this is optional. The keycloak set password is the one that counts for the login.

    t0 = time()

    resp = cs.createAccount(
        account=username,
        username=username,
        email=email,
        firstname=firstname,
        lastname=lastname,
        password=password,
        domainid=STUDENTS_DOMAIN_ID,
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
    changed |= ensure_account_role(cs, acc_model.id, STUDENT_ROLE_ID)

    return {
        "username": username,
        "email": email,
        "account_id": acc_model.id,
        "user_id": user_id,
        "time_duration_s": round(time() - t0, 2),
        "created": True,
        "changed": changed,
    }


def ensure_student_account(cs: CloudStack, email: str, username: str, firstname: str, lastname: str, debug: bool = False) -> dict:
    """
    Ensures student account exists and is correctly configured (SSO + role).
    """
    start = time()
    if "@" not in email:
        raise ValueError(f"Invalid email: {email}")

    acc = get_account(cs, username, STUDENTS_DOMAIN_ID)
    created = False
    if not acc:
        created = True
        return create_student(cs, email, username,firstname, lastname, debug=debug)

    user = get_user_from_account(acc, username)
    user_id = user.id if user else None

    changed = False
    if user_id:
        changed |= ensure_sso_enabled(cs, user_id, IDP_ENTITY_ID)

    # role é na account, deve ser garantida sempre
    changed |= ensure_account_role(cs, acc.id, STUDENT_ROLE_ID)

    end = time()
    return {
        "username": username,
        "email": email,
        "account_id": acc.id,
        "user_id": user_id,
        "role": get_role_name(cs, acc.roleid) if acc.roleid else None,
        "time_duration_s": round(end - start, 2),
        "created": created,
        "changed": changed,
    }


# ============================================================
# 5) Manual run (only here)
# ============================================================

if __name__ == "__main__":
    cs = get_cs()
    
    # get all accounts. Useful to crosscheck with keycloak users. also returns the admin account.
    print(get_all_accounts(cs))