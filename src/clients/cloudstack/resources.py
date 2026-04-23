"""CloudStack domain operations."""
from __future__ import annotations
import logging
from traceback import print_tb
from typing import Any, Dict, List
from clients.cloudstack.base import CloudStackBaseClient

 
log = logging.getLogger(__name__)
 
 
class CloudStackResourcesClient(CloudStackBaseClient):
    """CloudStack domain operations."""
    
    # Get resources
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """List all resources."""
        try:
            resp = self._cs.listResourceLimits(listall=True) or {}
            resources = resp.get("resourcelimit", []) or []
            log.debug(f"Listed {len(resources)} resources")
            return resources
        except Exception as e:
            self._handle_error("list_resources", e)
            
    def list_all_resource_limits(self) -> list:
        """List resource limits for ALL accounts across all domains."""
        results = []
        
        accounts = self._cs.listAccounts(listall=True)["account"] or {}
                
        for acc in accounts:
            log.info(f"Getting limits for account {acc['name']} (ID: {acc['id']}) in domain {acc.get('domain', 'N/A')}")
            try:
                resp = self._cs.listResourceLimits(
                    account=acc["name"],
                    domainid=acc["domainid"],
                ) or {}
                limits = resp.get("resourcelimit", []) or []
                results.append({
                    "account": acc["name"],
                    "account_id": acc["id"],
                    "domain": acc.get("domain"),
                    "domainid": acc["domainid"],
                    "limits": {l["resourcetypename"]: l["max"] for l in limits},
                })
            except Exception as e:
                log.error("Failed to get limits for account %s: %s", acc["name"], e)
        
        return results

    def get_resource(self, resource_id: str) -> Dict[str, Any] | None:
        """Get resource by ID."""
        try:
            resp = self._cs.listResourceLimits(id=resource_id) or {}
            resources = resp.get("resourcelimit", []) or []
            return resources[0] if resources else None
        except Exception as e:
            self._handle_error(f"get_resource({resource_id})", e)
 
    # Update resources
    
    def update_resource_limit(self, type: int, account: str, domain: str, max: int) -> bool:
        """Update resource limit."""
        try:
            self._cs.updateResourceLimit(resourcetype=type, account=account, domainid=domain, max=max)
            log.info(f"Updated resource limit of type {type} for account {account} in domain {domain} to {max}")
            return True
        except Exception as e:
            log.error("Failed to update resource limit: %s", e)
            return False
        
    def update_vm_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update VM resource limit."""
        return self.update_resource_limit(type=0, account=account, domain=domain, max=max)
    
    def update_ip_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update IP resource limit."""
        return self.update_resource_limit(type=1, account=account, domain=domain, max=max)
    
    def update_volume_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update Volume resource limit."""
        return self.update_resource_limit(type=2, account=account, domain=domain, max=max)
    
    def update_snapshot_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update Snapshot resource limit."""
        return self.update_resource_limit(type=3, account=account, domain=domain, max=max)
    
    def update_template_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update Template resource limit."""
        return self.update_resource_limit(type=4, account=account, domain=domain, max=max)
    
    def update_project_resource_limit(self, account: str, domain: str, max: int) -> bool:   
        """Update Project resource limit."""
        return self.update_resource_limit(type=5, account=account, domain=domain, max=max)
    
    def update_network_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update guest Network resource limit."""
        return self.update_resource_limit(type=6, account=account, domain=domain, max=max)

    def update_vpc_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update VPC resource limit."""
        return self.update_resource_limit(type=7, account=account, domain=domain, max=max)
    
    def update_cpu_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update CPU resource limit."""
        return self.update_resource_limit(type=8, account=account, domain=domain, max=max)
    
    def update_memory_resource_limit(self, account: str, domain: str, max: int) -> bool:    
        """Update Memory resource limit."""
        return self.update_resource_limit(type=9, account=account, domain=domain, max=max)
    
    def update_primary_storage_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update Primary Storage resource limit."""
        return self.update_resource_limit(type=10, account=account, domain=domain, max=max)
    
    def update_secondary_storage_resource_limit(self, account: str, domain: str, max: int) -> bool:
        """Update Secondary Storage resource limit."""
        return self.update_resource_limit(type=11, account=account, domain=domain, max=max)