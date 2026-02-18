from pydantic import BaseModel, field_validator
from typing import List, Optional


class User(BaseModel):
    id: str
    username: str
    firstname: str
    lastname: str
    email: str
    created: str
    state: str
    account: str
    accounttype: int
    usersource: str
    roleid: str
    roletype: str
    rolename: str
    domainid: str
    domain: str
    accountid: str
    iscallerchilddomain: bool
    isdefault: bool
    is2faenabled: bool
    is2famandated: bool


class Account(BaseModel):
    id: str
    name: str
    accounttype: int
    user: User
    roleid: str
    roletype: str
    rolename: str
    domainid: str
    domain: str
    domainpath: str
    vmlimit: str
    vmtotal: int
    vmavailable: str
    iplimit: str
    iptotal: int
    ipavailable: str
    volumelimit: str
    volumetotal: int
    volumeavailable: str
    snapshotlimit: str
    snapshottotal: int
    snapshotavailable: str
    backuplimit: str
    backuptotal: int
    backupavailable: str
    backupstoragelimit: str
    backupstoragetotal: float
    backupstorageavailable: str
    templatelimit: str
    templatetotal: int
    templateavailable: str
    vmstopped: int
    vmrunning: int
    projectlimit: str
    projecttotal: int
    projectavailable: str
    networklimit: str
    networktotal: int
    networkavailable: str
    vpclimit: str
    vpctotal: int
    vpcavailable: str
    cpulimit: str
    cputotal: int
    cpuavailable: str
    memorylimit: str
    memorytotal: int
    memoryavailable: str
    gpulimit: str
    gputotal: int
    gpuavailable: str
    primarystoragelimit: str
    primarystoragetotal: int
    primarystorageavailable: str
    secondarystoragelimit: str
    secondarystoragetotal: float
    secondarystorageavailable: str
    bucketlimit: str
    buckettotal: int
    bucketavailable: str
    objectstoragelimit: str
    objectstoragetotal: int
    objectstorageavailable: str
    state: str
    created: str
    isdefault: bool
    groups: List
    apikeyaccess: str

    @field_validator("user", mode="before")
    @classmethod
    def extract_single_user(cls, v):
        if isinstance(v, list):
            if not v:
                raise ValueError("user list is empty")
            return v[0]
        return v

class RootModel(BaseModel):
    account: Account
    
