# ks2cs/provision_actions.py
from __future__ import annotations
from dataclasses import dataclass
Role = str

@dataclass(frozen=True)
class ProvisionResult:
    role: Role
    username: str
    email: str
    account_id: str
    user_id: str
    created: bool
    changed: bool
    time_duration_s: float