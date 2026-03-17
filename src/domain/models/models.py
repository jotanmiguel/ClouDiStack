from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============================================================
# ENUMS
# ============================================================

class Tier(str, Enum):
    """Resource tier for users."""
    STANDARD = "standard"
    PREMIUM = "premium"
    ADVANCED = "advanced"


class Role(str, Enum):
    """Role types in CloudStack."""
    STUDENT = "student"
    STAFF = "staff"
    TEACHER = "teacher"
    RESEARCHER = "researcher"
    GUEST = "guest"


class UserState(str, Enum):
    """State of a user in provisioning."""
    PENDING = "pending"
    PROVISIONED = "provisioned"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


# ============================================================
# DOMAIN MODELS
# ============================================================

@dataclass
class Quota:
    """Resource quota for a user."""
    storage_gb: int = 50
    cpu_cores: int = 2
    max_vms: int = 5
    max_networks: int = 1
    
    @staticmethod
    def for_tier(tier: Tier) -> Quota:
        """Return quota based on tier."""
        if tier == Tier.STANDARD:
            return Quota(storage_gb=50, cpu_cores=2, max_vms=5)
        elif tier == Tier.PREMIUM:
            return Quota(storage_gb=200, cpu_cores=4, max_vms=10)
        elif tier == Tier.ADVANCED:
            return Quota(storage_gb=500, cpu_cores=8, max_vms=20)
        raise ValueError(f"Unknown tier: {tier}")


@dataclass
class CustomLimits:
    """Custom overrides for a user."""
    storage_gb: Optional[int] = None
    approved_resources: List[str] = field(default_factory=list)
    notes: str = ""
    
    def merge_with_quota(self, quota: Quota) -> Quota:
        """Merge custom limits into quota."""
        if self.storage_gb:
            quota.storage_gb = self.storage_gb
        return quota


@dataclass
class User:
    """Domain model for a user."""
    keycloak_id: str
    username: str
    email: str
    firstname: str
    lastname: str
    
    # Identity
    groups: List[str] = field(default_factory=list)  # e.g., ["students", "special_project"]
    role: Role = Role.STUDENT
    tier: Tier = Tier.STANDARD
    
    # Provisioning state
    state: UserState = UserState.PENDING
    cloudstack_account_id: Optional[str] = None
    cloudstack_user_id: Optional[str] = None
    
    # Custom settings
    custom_limits: CustomLimits = field(default_factory=CustomLimits)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    provisioned_at: Optional[datetime] = None
    
    # ---- Methods ----
    
    def get_quota(self) -> Quota:
        """Get effective quota (custom + tier-based)."""
        base_quota = Quota.for_tier(self.tier)
        return self.custom_limits.merge_with_quota(base_quota)
    
    def is_provisioned(self) -> bool:
        """Check if user is provisioned in CloudStack."""
        return self.state in [UserState.PROVISIONED, UserState.ACTIVE]
    
    def can_login(self) -> bool:
        """Check if user can login."""
        return self.state == UserState.ACTIVE
    
    def __str__(self) -> str:
        return f"User({self.username}, role={self.role.value}, tier={self.tier.value})"

@dataclass
class KeycloakGroup:
    """Domain model for Keycloak group."""
    group_id: str
    name: str
    path: str
    
    def is_role_group(self) -> bool:
        """Check if this is a role group (students, staff, etc)."""
        return self.name.lower() in ["students", "staff", "teachers", "researchers", "guests"]


# ============================================================
# EXCEPTIONS
# ============================================================

class DomainError(Exception):
    """Base exception for domain errors."""
    pass


class InvalidUserError(DomainError):
    """User data is invalid."""
    pass


class ProvisioningError(DomainError):
    """Error during provisioning."""
    pass


class InvalidTierError(DomainError):
    """Invalid tier specified."""
    pass


class QuotaExceededError(DomainError):
    """User quota exceeded."""
    pass


class UserAlreadyProvisionedError(DomainError):
    """User is already provisioned."""
    pass


class RoleNotFoundError(DomainError):
    """Role not found in CloudStack."""
    pass


class DomainNotFoundError(DomainError):
    """Domain not found in CloudStack."""
    pass


# ============================================================
# EVENTS
# ============================================================

@dataclass
class UserEvent:
    """Base class for user events."""
    keycloak_user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserCreatedEvent(UserEvent):
    """User was created in Keycloak."""
    username: str
    email: str
    firstname: str
    lastname: str


@dataclass
class UserUpdatedEvent(UserEvent):
    """User was updated in Keycloak."""
    changed_fields: Dict[str, Any]


@dataclass
class UserDeletedEvent(UserEvent):
    """User was deleted in Keycloak."""
    username: str


@dataclass
class UserProvisionedEvent(UserEvent):
    """User was provisioned in CloudStack."""
    cloudstack_account_id: str
    role: Role