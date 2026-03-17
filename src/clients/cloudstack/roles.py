"""CloudStack role operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)


class CloudStackRolesClient:
    """CloudStack role operations."""
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles."""
        pass
    
    def get_role(self, role_id: str) -> Dict[str, Any] | None:
        """Get role by ID."""
        pass
    
    def get_role_by_name(self, name: str) -> Dict[str, Any] | None:
        """Get role by name."""
        pass
    
    def list_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """List permissions for a role."""
        pass