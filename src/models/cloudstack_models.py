from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# -------------------------
# User Model
# -------------------------

class CSUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    username: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    created: Optional[str] = None
    state: Optional[str] = None

    account: Optional[str] = None
    accounttype: Optional[int] = None
    usersource: Optional[str] = None

    roleid: Optional[str] = None
    roletype: Optional[str] = None
    rolename: Optional[str] = None

    domainid: Optional[str] = None
    domain: Optional[str] = None
    accountid: Optional[str] = None

    isdefault: Optional[bool] = None
    is2faenabled: Optional[bool] = None
    is2famandated: Optional[bool] = None


# -------------------------
# Account Model
# -------------------------

class CSAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    accounttype: int

    roleid: Optional[str] = None
    roletype: Optional[str] = None
    rolename: Optional[str] = None

    domainid: str
    domain: str
    domainpath: Optional[str] = None

    state: Optional[str] = None
    created: Optional[str] = None

    receivedbytes: Optional[int] = None
    sentbytes: Optional[int] = None
    secondarystoragetotal: Optional[float] = None

    isdefault: Optional[bool] = None
    apikeyaccess: Optional[str] = None

    groups: Optional[List] = None

    user: List[CSUser] = []


# -------------------------
# Root listAccounts Model
# -------------------------

class ListAccountsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    count: int
    account: List[CSAccount]