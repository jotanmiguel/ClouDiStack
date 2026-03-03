from typing import Any, Optional

SSO_STATE_KEYS = (
    "samlSsoEnabled",
    "isSamlSsoEnabled",
    "ssoEnabled",
    "authorizedSamlSso",
    "isSsoEnabled",
)

def _extract_bool(d: dict[str, Any], keys=SSO_STATE_KEYS) -> Optional[bool]:
    for k in keys:
        if k in d:
            v = d[k]
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                if v.lower() in ("true", "yes", "1"):
                    return True
                if v.lower() in ("false", "no", "0"):
                    return False
            if isinstance(v, int):
                return bool(v)
    return None

def ensure_sso_enabled(cs, user_id: str, entity_id: str) -> bool:
    """
    Garante que SAML SSO está ativado para o user no CloudStack.
    Retorna True se fez alteração (ativou agora), False se já estava ativo.
    """
    # 1) Tentar descobrir estado atual
    try:
        resp = cs.listUsers(id=user_id)
        users = (resp or {}).get("user", [])
        user = users[0] if users else {}
        enabled = _extract_bool(user)
    except Exception:
        enabled = None

    # 2) Se sabemos que já está enabled, skip
    if enabled is True:
        return False

    # 3) Caso contrário, ativar (idempotente mesmo que já estivesse)
    cs.authorizeSamlSso(userid=user_id, enable=True, entityid=entity_id)
    return True