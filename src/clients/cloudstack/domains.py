"""CloudStack domain operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)


class CloudStackDomainsClient:
    """CloudStack domain operations."""
    
    def list_domains(self) -> List[Dict[str, Any]]:
        """List all domains."""
        pass
    
    def get_domain(self, domain_id: str) -> Dict[str, Any] | None:
        """Get domain by ID."""
        pass
    
    def get_domain_by_name(self, name: str) -> Dict[str, Any] | None:
        """Get domain by name."""
        pass