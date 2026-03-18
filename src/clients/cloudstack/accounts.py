
"""CloudStack account operations."""
from __future__ import annotations
import logging
import time
from typing import Any, Dict, List
from clients.cloudstack.base import CloudStackBaseClient
from domain.models.cloudstack_models import CSAccount, ListAccountsResponse
from utils.identity import gen_password
 
log = logging.getLogger(__name__)
 
 
class CloudStackAccountsClient(CloudStackBaseClient):
    """CloudStack account operations."""
    
    # ============================================================
    # READ OPERATIONS
    # ============================================================
    
    def list_accounts(
        self,
        filters: Dict[str, Any] | None = None,
        listall: bool = True,
        details: str = "min"
    ) -> List[Dict[str, Any]]:
        """List accounts with optional filters."""
        try:
            params: Dict[str, Any] = {
                "details": details,
            }
            if listall:
                params["listall"] = True
            if filters:
                params.update(filters)
            
            resp = self._cs.listAccounts(**params) or {}
            accounts = resp.get("account", []) or []
            log.debug(f"Listed {len(accounts)} accounts")
            return accounts
        except Exception as e:
            self._handle_error("list_accounts", e)
            return {}
    
    def get_account(self, account_id: str) -> Dict[str, Any] | None:
        """Get account by ID."""
        try:
            accounts = self.list_accounts(filters={"id": account_id})
            return accounts[0] if accounts else None
        except Exception as e:
            self._handle_error(f"get_account({account_id})", e)
    
    def get_account_by_name(
        self,
        account_name: str,
        domain_id: str
    ) -> Dict[str, Any] | None:
        """Get account by name in a domain."""
        try:
            accounts = self.list_accounts(
                filters={"name": account_name, "domainid": domain_id}
            )
            return accounts[0] if accounts else None
        except Exception as e:
            self._handle_error(f"get_account_by_name({account_name})", e)
    
    # ============================================================
    # WRITE OPERATIONS
    # ============================================================
    
    def create_account(
        self,
        account_name: str,
        username: str,
        email: str,
        firstname: str,
        lastname: str,
        password: str,
        domain_id: str = "1488a55a-800b-472f-94d7-7273a00a1208",
        account_type: str = "0",
        role_id: str = "4eff4f67-dff5-4179-bba8-802d9c7163cc",
    ) -> Dict[str, Any]:
        """Create new account."""
        try:
            log.debug(f"Creating account {account_name} in domain {domain_id}")
            password = gen_password() if not password else password
            resp = self._cs.createAccount(
                account=account_name,
                username=username,
                email=email,
                firstname=firstname,
                lastname=lastname,
                password=password,
                domainid=domain_id,
                accounttype=account_type,
                roleid=role_id
            ) or {}
        except Exception as e:
            self._handle_error(f"create_account({account_name})", e)
            return {}
            
        acct_dict = self._unwrap_account_from_create(resp)
        acc_model = CSAccount.model_validate(acct_dict)
        if acc_model.user:
            log.info(f"Created account {account_name}")
        
        user_id = acc_model.user[0].id
        
        return {
            "username": username,
            "email": email,
            "account_id": acc_model.id,
            "user_id": user_id,
            "time_duration_s": round(time() - t0, 2),
            "created": True
        }
    
    def update_account(
        self,
        account_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update account."""
        try:
            log.debug(f"Updating account {account_id}")
            self._cs.updateAccount(id=account_id, **updates)
            log.info(f"Updated account {account_id}")
        except Exception as e:
            self._handle_error(f"update_account({account_id})", e)
    
    def disable_account(self, account_id: str) -> None:
        """Disable account (preserves data)."""
        try:
            log.debug(f"Disabling account {account_id}")
            self._cs.disableAccount(id=account_id, lock=False)
            log.info(f"Disabled account {account_id}")
        except Exception as e:
            self._handle_error(f"disable_account({account_id})", e)
    
    def delete_account(self, account_id: str) -> None:
        """Delete account (DESTRUCTIVE)."""
        try:
            log.warning(f"DELETING account {account_id}")
            self._cs.deleteAccount(id=account_id)
            log.info(f"Deleted account {account_id}")
        except Exception as e:
            self._handle_error(f"delete_account({account_id})", e)
            
    def _parse_list_accounts(self, resp: Dict[str, Any]) -> ListAccountsResponse:
        """
        Normalizes listAccounts responses.
        Some wrappers return {} when empty; we convert to count=0/account=[].
        """
        data = resp or {}
        if not data:
            data = {"count": 0, "account": []}
        return ListAccountsResponse(**data)


    def _unwrap_account_from_create(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes createAccount response:
        - {"account": {...}}
        - {"createaccountresponse": {"account": {...}}}
        """
        acct = (resp or {}).get("account")
        if acct:
            return acct

        wrapped = (resp or {}).get("createaccountresponse", {})
        acct = wrapped.get("account")
        if acct:
            return acct

        raise ValueError(f"Unexpected createAccount response keys: {list((resp or {}).keys())}")