from __future__ import annotations
import logging
from clients.keycloak.client import KeycloakClient
from clients.cloudstack.client import CloudStackClient
from .resolver import resolve_quota
from .enforcer import PolicyEnforcer
from ks2cs.mapping import _infer_group_from_email

log = logging.getLogger(__name__)


class PolicyService:
    """Orquestra fetch de roles → resolução de quota → enforcement."""

    def __init__(self, kc: KeycloakClient, cs: CloudStackClient):
        self.kc = kc
        self.cs = cs
        self.enforcer = PolicyEnforcer(cs)

    def enforce_for_user(self, kc_user_id: str) -> dict:
        # 1. Buscar grupos do user
        groups_raw = self.kc.get_user_groups(kc_user_id)
        group_names = [g.get("name", "").lower() for g in groups_raw]
        log.info("User %s groups: %s", kc_user_id, group_names)

        # 2. Buscar atributos de cada grupo individualmente
        group_attrs_list = []
        for g in groups_raw:
            full_group = self.kc.get_group(g["id"])
            attrs = full_group.get("attributes") or {} if full_group else {}
            group_attrs_list.append((g["name"].lower(), attrs))
            log.debug("Group %s attrs: %s", g["name"], attrs)

        # 2b. Se nenhum grupo encontrado, tentar inferir do email (fallback)
        if not group_attrs_list:
            kc_user = self.kc.get_user(kc_user_id)
            if kc_user and hasattr(kc_user, 'email') and kc_user.email:
                inferred_group = _infer_group_from_email(kc_user.email)
                if inferred_group:
                    log.info("No KC groups found for user %s — inferred group '%s' from email '%s'", kc_user_id, inferred_group, kc_user.email)
                    group_attrs_list = [(inferred_group, {})]

        # 3. Buscar atributos do user (overrides individuais)
        user_attrs = self.kc.get_user_attributes(kc_user_id) or {}

        # 4. Resolver quota
        quota = resolve_quota(group_attrs_list, user_attrs=user_attrs)
        log.info("Resolved quota for %s: %s", kc_user_id, quota)

        # 5. Buscar account no CloudStack
        account_id = self._get_attr(user_attrs, "cloudstackAccountId")
        if not account_id:
            log.warning("User %s has no cloudstackAccountId — skipping", kc_user_id)
            return {"skipped": True, "reason": "not_provisioned"}

        account = self.cs.get_account(account_id)
        if not account:
            log.warning("Account %s not found in CloudStack", account_id)
            return {"skipped": True, "reason": "account_not_found"}

        account_name = account["name"]
        domain_id    = account["domainid"]

        # 6. Aplicar quotas
        results = self.enforcer.apply(account_name, account_id, domain_id, quota)

        log.info("Policy enforced for user %s (account %s)", kc_user_id, account_id)

        return {
            "enforced": True,
            "account_name": account_name,
            "kc_user_id": kc_user_id,
            "account_id": account_id,
            "groups": group_names,
            "quota_applied": quota.__dict__,
            "results": results,
            "duration": "TODO",
        }

    @staticmethod
    def _get_attr(attrs: dict, key: str) -> str:
        val = attrs.get(key)
        if isinstance(val, list) and val:
            return val[0]
        return val or ""