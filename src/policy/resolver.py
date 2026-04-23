from __future__ import annotations
import logging
from typing import List, Tuple, Dict, Any
from .models import QuotaPolicy, BASE_POLICIES

log = logging.getLogger(__name__)

GROUP_PRIORITY = {
    "guests":      0,
    "students":    1,
    "staff":       2,
    "teachers":    2,
    "researchers": 3,
}


def resolve_quota(
    group_attrs_list: List[Tuple[str, Dict[str, Any]]],
    user_attrs: Dict[str, Any] = {},
) -> QuotaPolicy:
    """
    group_attrs_list: [(group_name, {attr_key: [val], ...}), ...]
    user_attrs:       atributos individuais do user (overrides)

    Lógica:
    1. Ordena grupos por prioridade
    2. Grupo de maior prioridade define a quota base via atributos KC
    3. Fallback para BASE_POLICIES se grupo não tiver atributos
    4. Atributos do user sobrescrevem (override individual)
    """
    if not group_attrs_list:
        log.warning("No groups found, defaulting to guest policy")
        return QuotaPolicy(**BASE_POLICIES["guest"].quota.__dict__)

    # Ordena por prioridade — maior primeiro
    sorted_groups = sorted(
        group_attrs_list,
        key=lambda x: GROUP_PRIORITY.get(x[0], 0),
        reverse=True,
    )

    # Tenta construir quota a partir dos atributos do grupo de maior prioridade
    quota = None
    for group_name, attrs in sorted_groups:
        if attrs:
            quota = _quota_from_attrs(attrs, group_name)
            log.info("Quota from group '%s' attributes", group_name)
            break

    if quota is None:
        # Nenhum grupo tem atributos → fallback BASE_POLICIES
        top_group = sorted_groups[0][0]
        fallback = BASE_POLICIES.get(top_group) or BASE_POLICIES["guest"]
        quota = QuotaPolicy(**fallback.quota.__dict__)
        log.warning("No group attributes found, fallback to BASE_POLICIES['%s']", top_group)

    # Overrides individuais do user: {"override_max_vms": ["5"]}
    OVERRIDE_PREFIX = "override_"
    for attr_key, attr_val in user_attrs.items():
        if not attr_key.startswith(OVERRIDE_PREFIX):
            continue
        field_name = attr_key[len(OVERRIDE_PREFIX):]
        value = attr_val[0] if isinstance(attr_val, list) else attr_val
        if hasattr(quota, field_name):
            setattr(quota, field_name, int(value))
            log.info("User override: %s = %s", field_name, value)
        else:
            log.warning("Unknown override field: %s", attr_key)

    return quota


def _quota_from_attrs(attrs: Dict[str, Any], group_name: str) -> QuotaPolicy:
    """Constrói QuotaPolicy a partir dos atributos do grupo Keycloak."""

    def get(key: str, default: int) -> int:
        val = attrs.get(key)
        if isinstance(val, list) and val:
            try:
                return int(val[0])
            except (ValueError, TypeError):
                log.warning("Invalid value for %s in group %s: %s", key, group_name, val)
                return default
        return default

    return QuotaPolicy(
        max_vms               = get("max_vms",               2),
        max_cpu               = get("max_cpu",               2),
        max_ram_mb            = get("max_ram_mb",            2048),
        max_volumes           = get("max_volumes",           4),
        max_snapshots         = get("max_snapshots",         10),
        max_public_ips        = get("max_public_ips",        1),
        max_networks          = get("max_networks",          1),
        max_vpc               = get("max_vpc",               1),
        max_primary_storage   = get("max_primary_storage",   50),
        max_secondary_storage = get("max_secondary_storage", 50),
    )