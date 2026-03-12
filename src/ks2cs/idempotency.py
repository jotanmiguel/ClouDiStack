# ks2cs/idempotency.py
from __future__ import annotations
from typing import Any, Dict

from models.keycloak_models import KeycloakUser

def is_provisioned(user: KeycloakUser, flag_attr: str = "cloudstackProvisioned") -> bool:
    attrs = user.get("attributes") or {}
    v = attrs.get(flag_attr)
    return bool(v and isinstance(v, list) and v and str(v[0]).lower() == "true")

def set_provisioned_attrs(user: Dict[str, Any],*,flag_attr: str,account_attr: str,cs_account_id_attr: str,cs_user_id_attr: str,cs_role_attr: str,username: str,account_id: str,user_id: str,role: str,) -> Dict[str, Any]:
    attrs = user.get("attributes") or {}
    attrs[flag_attr] = ["true"]
    attrs[account_attr] = [username]
    attrs[cs_account_id_attr] = [account_id]
    attrs[cs_user_id_attr] = [user_id]
    attrs[cs_role_attr] = [role]
    user["attributes"] = attrs
    return user