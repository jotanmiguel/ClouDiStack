from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Tipos de recursos CloudStack (updateResourceLimit)
RESOURCE_TYPE_VMS       = 0
RESOURCE_TYPE_PUBLIC_IP = 1
RESOURCE_TYPE_VOLUME    = 2
RESOURCE_TYPE_SNAPSHOT  = 3
RESOURCE_TYPE_TEMPLATE  = 4
RESOURCE_TYPE_NETWORK   = 6
RESOURCE_TYPE_VPC       = 7
RESOURCE_TYPE_CPU       = 8
RESOURCE_TYPE_RAM_MB    = 9
RESOURCE_TYPE_GPU       = 10


@dataclass
class ComputeOffering:
    """Representa um compute offering do CloudStack."""
    name: str
    cpu: int
    ram_mb: int
    offering_id: str = ""   # preenchido após lookup no CloudStack


@dataclass
class QuotaPolicy:
    """Limites de recursos para um role."""
    max_vms: int = 2
    max_volumes: int = 4
    max_snapshots: int = 10
    max_public_ips: int = 1
    max_networks: int = 1
    max_cpu: int = 4
    max_ram_mb: int = 4096
    allowed_offerings: List[str] = field(default_factory=list)  # nomes dos offerings
    max_vpc: int = 1
    max_primary_storage: Optional[int] = None
    max_secondary_storage: Optional[int] = None


@dataclass
class RolePolicy:
    """Política completa para um role base."""
    role: str
    quota: QuotaPolicy
    priority: int = 0   # maior prioridade ganha em caso de conflito


# ─── Políticas base ────────────────────────────────────────────────────────────

BASE_POLICIES: Dict[str, RolePolicy] = {
    "student": RolePolicy(
        role="student",
        priority=1,
        quota=QuotaPolicy(
            max_vms=2,
            max_cpu=2,
            max_ram_mb=2048,
            max_volumes=4,
            max_public_ips=1,
            allowed_offerings=["small", "medium"],
        ),
    ),
    "teacher": RolePolicy(
        role="teacher",
        priority=2,
        quota=QuotaPolicy(
            max_vms=5,
            max_cpu=8,
            max_ram_mb=8192,
            max_volumes=10,
            max_public_ips=2,
            allowed_offerings=["small", "medium", "large"],
        ),
    ),
    "researcher": RolePolicy(
        role="researcher",
        priority=3,
        quota=QuotaPolicy(
            max_vms=10,
            max_cpu=16,
            max_ram_mb=32768,
            max_volumes=20,
            max_public_ips=4,
            allowed_offerings=["small", "medium", "large", "xlarge"],
        ),
    ),
    "staff": RolePolicy(
        role="staff",
        priority=2,
        quota=QuotaPolicy(
            max_vms=5,
            max_cpu=8,
            max_ram_mb=8192,
            max_volumes=10,
            max_public_ips=2,
            allowed_offerings=["small", "medium", "large"],
        ),
    ),
    "guest": RolePolicy(
        role="guest",
        priority=0,
        quota=QuotaPolicy(
            max_vms=1,
            max_cpu=1,
            max_ram_mb=1024,
            max_volumes=1,
            max_public_ips=0,
            allowed_offerings=["small"],
        ),
    ),
}

# ─── Compute Offerings ─────────────────────────────────────────────────────────

COMPUTE_OFFERINGS: Dict[str, ComputeOffering] = {
    "small":  ComputeOffering(name="small",  cpu=1, ram_mb=1024),
    "medium": ComputeOffering(name="medium", cpu=2, ram_mb=4096),
    "large":  ComputeOffering(name="large",  cpu=4, ram_mb=8192),
    "xlarge": ComputeOffering(name="xlarge", cpu=8, ram_mb=16384),
}