from __future__ import annotations
import logging
from typing import List, Dict, Any
from src.domain.models import User, Tier, Role, UserState, KeycloakGroup
from src.domain.rules import ProvisioningRules

log = logging.getLogger(__name__)


class KeycloakAdapter:
    """Adapter para integração com Keycloak."""
    
    def __init__(self, keycloak_client):
        """Initialize with actual Keycloak client."""
        self.client = keycloak_client
    
    # ---- Read Operations ----
    
    def get_user(self, user_id: str) -> User:
        """Get user from Keycloak and convert to domain model."""
        try:
            kc_user = self.client.get_user(user_id)
        except Exception as e:
            log.error(f"Failed to get user {user_id} from Keycloak: {e}")
            raise
        
        return self._keycloak_user_to_domain(kc_user)
    
    def get_user_groups(self, user_id: str) -> List[str]:
        """Get groups for a user."""
        try:
            groups_response = self.client.get_user_groups(user_id)
            # Expected: [{"name": "students", "path": "/students"}, ...]
            groups = [g.get("name", "").lower() for g in groups_response]
            return [g for g in groups if g]  # Filter empty
        except Exception as e:
            log.error(f"Failed to get groups for {user_id}: {e}")
            return []
    
    def get_user_tier(self, user_id: str) -> Tier:
        """Get user's tier from attributes."""
        try:
            kc_user = self.client.get_user(user_id)
            attrs = kc_user.get("attributes", {})
            tier_str = self._get_attr(attrs, "cloudstack_tier", "standard")
            return Tier(tier_str)
        except Exception as e:
            log.error(f"Failed to get tier for {user_id}: {e}")
            return Tier.STANDARD
    
    # ---- Write Operations ----
    
    def set_user_tier(self, user_id: str, tier: Tier) -> None:
        """Set user's tier in attributes."""
        try:
            payload = {"attributes": {"cloudstack_tier": [tier.value]}}
            self.client.update_user(user_id, payload)
            log.info(f"Set tier={tier.value} for user {user_id}")
        except Exception as e:
            log.error(f"Failed to set tier for {user_id}: {e}")
            raise
    
    def set_user_provisioned(
        self, 
        user_id: str, 
        account_id: str, 
        account_user_id: str,
        role: Role
    ) -> None:
        """Mark user as provisioned in Keycloak."""
        try:
            attrs = {
                "cloudstackProvisioned": ["true"],
                "cloudstackAccountId": [account_id],
                "cloudstackUserId": [account_user_id],
                "cloudstackRole": [role.value],
            }
            payload = {"attributes": attrs}
            self.client.update_user(user_id, payload)
            log.info(f"Marked user {user_id} as provisioned")
        except Exception as e:
            log.error(f"Failed to mark {user_id} as provisioned: {e}")
            raise
    
    def add_user_to_group(self, user_id: str, group_name: str) -> None:
        """Add user to a group."""
        try:
            # First find the group
            groups = self.client.get_groups()  # Adjust to actual API
            group = next((g for g in groups if g.get("name") == group_name), None)
            
            if not group:
                raise ValueError(f"Group {group_name} not found")
            
            self.client.add_user_to_group(user_id, group["id"])
            log.info(f"Added user {user_id} to group {group_name}")
        except Exception as e:
            log.error(f"Failed to add user {user_id} to group {group_name}: {e}")
            raise
    
    # ---- Helpers ----
    
    def _keycloak_user_to_domain(self, kc_user: Dict[str, Any]) -> User:
        """Convert Keycloak user to domain User."""
        user_id = kc_user.get("id")
        username = kc_user.get("username")
        email = kc_user.get("email", "")
        firstname = kc_user.get("firstName", "")
        lastname = kc_user.get("lastName", "")
        
        # Get groups and decide role
        groups = self.get_user_groups(user_id)
        role = ProvisioningRules.decide_role_from_groups(groups)
        
        # Get tier
        tier = self.get_user_tier(user_id)
        
        # Check if already provisioned
        attrs = kc_user.get("attributes", {})
        is_provisioned = self._get_attr(attrs, "cloudstackProvisioned") == "true"
        
        user = User(
            keycloak_id=user_id,
            username=username,
            email=email,
            firstname=firstname,
            lastname=lastname,
            groups=groups,
            role=role,
            tier=tier,
            state=UserState.PROVISIONED if is_provisioned else UserState.PENDING,
            cloudstack_account_id=self._get_attr(attrs, "cloudstackAccountId"),
            cloudstack_user_id=self._get_attr(attrs, "cloudstackUserId"),
            attributes=attrs,
        )
        
        return user
    
    @staticmethod
    def _get_attr(attrs: Dict[str, Any], key: str, default: str = "") -> str:
        """Extract attribute value (Keycloak stores as lists)."""
        value = attrs.get(key)
        if isinstance(value, list) and value:
            return value[0]
        return default