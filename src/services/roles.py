from __future__ import annotations

from typing import Any, Dict, List, Optional

from cs import CloudStack, CloudStackApiException

from cloudstack.cs_client import get_cs
from ks2cs import teste
from utils.telemetry import instrument

# ---------- helpers ----------

def _find_role(cs: CloudStack, *, role_id: str | None = None, role_name: str | None = None) -> Optional[dict]:
    """
    Find the role by name or id. 

    Args:
        cs (CloudStack): 
        role_id (str | None, optional): role id. Defaults to None.
        role_name (str | None, optional): role name. Defaults to None.

    Raises:
        ValueError: _description_

    Returns:
        Optional[dict]: _description_
    """
    if not role_id and not role_name:
        raise ValueError("Provide role_id or role_name")

    params: Dict[str, Any] = {}
    if role_id:
        params["id"] = role_id
    if role_name:
        params["name"] = role_name

    resp = cs.listRoles(**params) or {}
    roles = resp.get("role", []) or []
    return roles[0] if roles else None

def _list_role_permissions(cs: CloudStack, role_id: str) -> List[dict]:
    # CloudStack usually exposes listRolePermissions(roleid=...)
    resp = cs.listRolePermissions(roleid=role_id) or {}
    return resp.get("rolepermission", []) or resp.get("rolePermission", []) or []

@instrument(label="get_role_id_by_name")
def get_role_id_by_name(cs: CloudStack, role_name: str) -> Optional[str]:
    r = _find_role(cs, role_name=role_name)
    return r["id"] if r else None

@instrument(label="list_accounts_by_role")
def list_accounts_by_role(
    cs: CloudStack,
    role_id: str,
    *,
    domain_id: Optional[str] = None,
    listall: bool = True,
    state: Optional[str] = "enabled",
) -> List[dict]:
    """
    List accounts and filter client-side by roleid because listAccounts DOES NOT support roleid filter.

    role_id: role UUID (API id from listRoles)
    """
    results: List[dict] = []

    while True:
        params: Dict[str, Any] = {
            "details": "min",
        }
        if listall:
            params["listall"] = True
        if domain_id:
            params["domainid"] = domain_id
        if state:
            params["state"] = state

        resp = cs.listAccounts(**params) or {}
        accs = resp.get("account", []) or []

        # filtra aqui
        for a in accs:
            if a.get("roleid") == role_id:
                results.append(a)
                
        break
    return results

def create_role_permission(
    cs: CloudStack,
    *,
    roleid: str,
    rule: str,
    permission: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Wrapper for CloudStack createRolePermission.

    Params (as in the docs screenshot):
      - permission: "allow" or "deny" (required)
      - roleid: role UUID (required)
      - rule: API name or wildcard like "list*" (required)
      - description: optional

    Returns the API response (normalized a bit if needed).
    """
    if not roleid:
        raise ValueError("roleid is required")
    if not rule:
        raise ValueError("rule is required")
    if permission not in {"allow", "deny"}:
        raise ValueError("permission must be 'allow' or 'deny'")

    kwargs: Dict[str, Any] = {
        "roleid": roleid,
        "rule": rule,
        "permission": permission,
    }
    if description:
        kwargs["description"] = description

    try:
        resp = cs.createRolePermission(**kwargs) or {}
    except CloudStackApiException as ex:
        # ex.error usually contains dict like the one you pasted (depends on wrapper)
        err = getattr(ex, "error", None)
        txt = ""
        if isinstance(err, dict):
            txt = err.get("errortext", "") or ""
        else:
            txt = str(ex)

        if "Rule already exists" in txt:
            return {"created": False, "skipped": True, "reason": "already_exists"}
        raise
           
    return resp

def duplicate_role(cs: CloudStack, *, source_role_name: str | None = None, source_role_id: str | None = None, new_role_name: str, description: str | None = None, ispublic: bool = True, forced: bool = False) -> dict:
    
    src = _find_role(cs, role_id=source_role_id, role_name=source_role_name)
    
    if not src:
        raise ValueError("Source role not found")
    
    src_id = src["id"]
    role_type = src.get("type") or src.get("roletype")  # Admin/ResourceAdmin/DomainAdmin/User

    perms = _list_role_permissions(cs, src_id)
    
    dest = _find_role(cs, role_name=new_role_name)
    
    if dest:
        dest_id = dest["id"]
        
        dest_perms = _list_role_permissions(cs, dest_id)
        
        for _, p in enumerate(perms):
            if p in dest_perms:
                print("asdasdasd")
                continue
            create_role_permission(
                cs,
                roleid=dest_id,
                rule=p.get("rule"),
                permission=p.get("permission"),
                description=p.get("description"),
            )
            
        return {"created": False, "updated": True, "reason": "dest_role_already_exists", "dest_role_id": dest["id"]}

    # Build rules map for importRole
    # cs library usually supports passing kwargs like rules[0].rule, etc.
    # We'll create a kwargs dict accordingly.
    kwargs: Dict[str, Any] = {
        "name": new_role_name,
        "ispublic": ispublic,
        "forced": forced,
    }
    if description is not None:
        kwargs["description"] = description
    elif src.get("description"):
        kwargs["description"] = src["description"]

    if role_type:
        kwargs["type"] = role_type

    new_role = cs.createRole(**kwargs)  # create empty role first to get an ID (CloudStack quirk)
    new_role_id = new_role.get("role", {}).get("id")
    if not new_role_id:
        raise ValueError(f"Failed to create new role: {new_role}")
    
    for _, p in enumerate(perms):
        
        create_role_permission(
            cs,
            roleid=new_role_id,
            rule=p.get("rule"),
            permission=p.get("permission"),
            description=p.get("description"),
        )

    role = resp.get("role") or (resp.get("importroleresponse", {}) or {}).get("role")
    if not role:
        return {"created": True, "new_role_name": new_role_name, "rules": i, "raw": resp}

    return {"created": True, "new_role_id": role["id"], "rules": i}

    
if __name__ == "__main__":
    cs = get_cs()
    
    print("List all roles permissions:", _list_role_permissions(cs, role_id="45153dca-dde0-11f0-8032-cec6e5fcc99e"))
    
    print("List accounts with StudentRole:", list_accounts_by_role(cs, "e7580ffb-8931-4dea-9659-481c7d1d7c71"))
    
    print("Create a new permission for StudentRole:", create_role_permission(cs, roleid="e7580ffb-8931-4dea-9659-481c7d1d7c71", rule="listVirtualMachines", permission="allow", description="Allow listing VMs"))
    
    print("Clone StudentRole to StudentRole2:", duplicate_role(cs, source_role_name="User", new_role_name="StudentRole2"))