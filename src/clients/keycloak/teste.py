# src/test_policy.py
from config.logging import setup_logging
from services.keycloak_service import get_keycloak
from policy.resolver import resolve_quota

setup_logging()
kc = get_keycloak()

# Busca um user real
users = kc.get_users({"username": "teste"})
user_id = users[0].id

# Busca grupos com atributos
groups_raw = kc.get_user_groups(user_id)
group_attrs_list = []
for g in groups_raw:
    full = kc.get_group(g["id"])
    attrs = full.get("attributes") or {} if full else {}
    group_attrs_list.append((g["name"].lower(), attrs))
    print(f"Group: {g['name']} → attrs: {attrs}")

# Resolve quota
user_attrs = kc.get_user_attributes(user_id) or {}
quota = resolve_quota(group_attrs_list=group_attrs_list, user_attrs=user_attrs)
print(f"\nQuota resolvida: {quota}")

# continua no mesmo ficheiro
from services.cloudstack_service import get_cloudstack
from policy.service import PolicyService
import json

cs = get_cloudstack()
svc = PolicyService(kc=kc, cs=cs)

result = svc.enforce_for_user(user_id)
print(json.dumps(result, indent=2, default=str))