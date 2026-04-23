from __future__ import annotations
import logging
from typing import Any, Dict
from clients.cloudstack.client import CloudStackClient
from .models import (
    QuotaPolicy,
    RESOURCE_TYPE_VMS, RESOURCE_TYPE_VOLUME, RESOURCE_TYPE_SNAPSHOT,
    RESOURCE_TYPE_PUBLIC_IP, RESOURCE_TYPE_NETWORK,
    RESOURCE_TYPE_CPU, RESOURCE_TYPE_RAM_MB,
)

log = logging.getLogger(__name__)

LIMIT_MAP = [
    ("max_vms",               0,  "user_vm"),
    ("max_public_ips",        1,  "public_ip"),
    ("max_volumes",           2,  "volume"),
    ("max_snapshots",         3,  "snapshot"),
    ("max_networks",          6,  "network"),
    ("max_vpc",               7,  "vpc"),
    ("max_cpu",               8,  "cpu"),
    ("max_ram_mb",            9,  "memory"),
    ("max_primary_storage",   10, "primary_storage"),
    ("max_secondary_storage", 11, "secondary_storage"),
]

class PolicyEnforcer:
    """Aplica QuotaPolicy numa account CloudStack."""

    def __init__(self, cs: CloudStackClient):
        self.cs = cs

    def apply(self, account_name: str, account_id: str, domain_id: str, quota: QuotaPolicy) -> dict:
        results = {}
        for field, resource_type, label in LIMIT_MAP:
            value = getattr(quota, field)
            try:
                self.cs._cs.updateResourceLimit(
                    resourcetype=resource_type,
                    max=value,
                    account=account_name,
                    domainid=domain_id,
                )
                results[label] = {"ok": True, "value": value}
            except Exception as e:
                results[label] = {"ok": False, "error": str(e)}
        return results

    def get_current_limits(self, account_name: str, domain_id: str) -> Dict[str, Any]:
        """Lê os limites atuais da conta."""
        try:
            resp = self.cs._cs.listResourceLimits(
                account=account_name,
                domainid=domain_id,
            ) or {}
            limits = resp.get("resourcelimit", []) or []
            return {str(l["resourcetype"]): l.get("max", -1) for l in limits}
        except Exception as e:
            log.error("Failed to get resource limits for %s: %s", account_name, e)
            return {}