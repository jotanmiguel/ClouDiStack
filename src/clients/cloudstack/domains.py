"""CloudStack domain operations."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from clients.cloudstack.base import CloudStackBaseClient
 
log = logging.getLogger(__name__)
 
 
class CloudStackDomainsClient(CloudStackBaseClient):
    """CloudStack domain operations."""
    
    def list_domains(self) -> List[Dict[str, Any]]:
        """List all domains."""
        try:
            resp = self._cs.listDomains() or {}
            domains = resp.get("domain", []) or []
            log.debug(f"Listed {len(domains)} domains")
            return domains
        except Exception as e:
            self._handle_error("list_domains", e)
    
    def get_domain(self, domain_id: str) -> Dict[str, Any] | None:
        """Get domain by ID."""
        try:
            resp = self._cs.listDomains(id=domain_id) or {}
            domains = resp.get("domain", []) or []
            return domains[0] if domains else None
        except Exception as e:
            self._handle_error(f"get_domain({domain_id})", e)
    
    def get_domain_by_name(self, domain_name: str) -> Dict[str, Any] | None:
        """Get domain by name."""
        try:
            resp = self._cs.listDomains(name=domain_name) or {}
            domains = resp.get("domain", []) or []
            return domains[0] if domains else None
        except Exception as e:
            self._handle_error(f"get_domain_by_name({domain_name})", e)
 