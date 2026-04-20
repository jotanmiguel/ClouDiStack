
"""CloudStack account operations."""
from __future__ import annotations
import logging
import time
from tkinter import N
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
    
    def get_account_by_name(self,account_name: str,domain_id: str = "") -> Dict[str, Any] | None:
        """Get account by name in a domain."""
        try:
            accounts = self.list_accounts(
                filters={"name": account_name}
            )
            return accounts[0] if accounts else None
        except Exception as e:
            self._handle_error(f"get_account_by_name({account_name})", e)
  
    def get_account_by_email(self, email: str) -> Dict[str, Any] | None:
        """Get account by email."""
        try:
            accounts = self.list_accounts(
                filters={"email": email}
            )
            return accounts[0] if accounts else None
        except Exception as e:
            self._handle_error(f"get_account_by_email({email})", e)
            return None
    
    def get_user_id(self, username: str, domain_id: str) -> str | None:
        """Get the user_id for a given username in a domain."""
        try:
            acc = self.get_account_by_name(username, domain_id)
            if not acc:
                return None
            users = acc.get("user", [])
            user = next((u for u in users if u.get("username") == username), None)
            return user["id"] if user else None
        except Exception as e:
            self._handle_error(f"get_user_id({username})", e)
            return None
        
    # ============================================================
    # WRITE OPERATIONS
    # ============================================================
    
    def create_account(
        self,
        username: str,
        email: str,
        firstname: str,
        lastname: str,
        password: str,
        account_type: str = "0",
        role_id: str = "c36f7dfb-31bd-11f1-8f49-cec6e5fcc99e",
        userid: str = ""
    ) -> Dict[str, Any]:
        """Create new account."""
        try:
            log.debug(f"Creating account {username}")
            password = gen_password() if not password else password
            resp = self._cs.createAccount(
                username=username,
                email=email,
                firstname=firstname,
                lastname=lastname,
                password=password,
                accounttype=account_type,
                roleid=role_id,
                userid = userid
            ) or {}
        except Exception as e:
            self._handle_error(f"create_account({username})", e)
            return {}
            
        acct_dict = self._unwrap_account_from_create(resp)
        acc_model = CSAccount.model_validate(acct_dict)
        if acc_model.user:
            log.info(f"Created account {username} (id={acc_model.id}) with user_id={acc_model.user[0].id}")
        
        user_id = acc_model.user[0].id
        
        return {
            "username": username,
            "email": email,
            "account_id": acc_model.id,
            "user_id": user_id,
            "time_duration_s": 0.0,
            "created": True
        }
    
    def update_account(
        self,
        account_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update account role or other account-level fields."""
        try:
            # CloudStack requires account name + domainid even when updating by id
            acc = self.get_account(account_id)
            if not acc:
                raise ValueError(f"Account {account_id} not found")
            
            log.debug(f"Updating account {account_id}")
            self._cs.updateAccount(
                id=account_id,
                account=acc["name"],
                domainid=acc["domainid"],
                **updates
            )
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
            
    def enable_account(self, account_id: str) -> None:
        """Enable previously disabled account."""
        try:
            log.debug(f"Enabling account {account_id}")
            self._cs.enableAccount(id=account_id)
            log.info(f"Enabled account {account_id}")
        except Exception as e:
            self._handle_error(f"enable_account({account_id})", e)
    
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