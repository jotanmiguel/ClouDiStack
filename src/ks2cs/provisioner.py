from __future__ import annotations
import logging
from datetime import datetime, timezone

from cs import CloudStack
import cs

from ks2cs.handler import handle_user_create_event
from .keycloak_client import KeycloakClient
from .state_store import JsonStateStore, State

log = logging.getLogger("kc2cs.provisioner")

def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def _is_provisioned(user: dict, provisioned_attr: str) -> bool:
    attrs = user.get("attributes") or {}
    val = attrs.get(provisioned_attr)
    # Keycloak attributes tipicamente dict[str, list[str]]
    return bool(val and isinstance(val, list) and val and str(val[0]).lower() == "true")

def _mark_provisioned(user: dict, provisioned_attr: str, account_attr: str, account_name: str) -> dict:
    attrs = user.get("attributes") or {}
    attrs[provisioned_attr] = ["true"]
    attrs[account_attr] = [account_name]
    user["attributes"] = attrs
    return user

class Provisioner:
    def __init__(
        self,
        kc: KeycloakClient,
        cs: CloudStack,
        state_store: JsonStateStore,
        provisioned_attr: str,
        account_attr: str,
    ):
        self.kc = kc
        self.cs = cs
        self.state_store = state_store
        self.provisioned_attr = provisioned_attr
        self.account_attr = account_attr

    def tick(self) -> None:
        state: State = self.state_store.load()
        start = state.last_time_ms
        end = now_ms()
    
        events = self.kc.get_user_create_events()
        
        print(events)
        
        # garante ordem do mais antigo para o mais recente
        events.sort(key=lambda e: e.time_ms)

        created = 0
        skipped = 0

        for ev in events:
            try:
                handle_user_create_event(kc=self.kc, cs=self.cs, event=ev)
            except Exception:
                log.exception("Failed to provision kc_user_id=%s email=%s", ev.user_id, ev.email)
                        
            user_id = self.kc.extract_user_id(ev.user_id)
            if not user_id:
                continue

            user = self.kc.get_user(user_id)
            email = user.get("email")
            if not email:
                skipped += 1
                continue

            if _is_provisioned(user, self.provisioned_attr):
                skipped += 1
                continue

            username = user.get("username") or email
            first_name = user.get("firstName") or ""
            last_name = user.get("lastName") or ""

            account_name = self.cs.provision_user(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )

            user2 = _mark_provisioned(
                user=user,
                provisioned_attr=self.provisioned_attr,
                account_attr=self.account_attr,
                account_name=account_name,
            )
            self.kc.update_user(user_id=user_id, payload=user2)
            created += 1

        # avança cursor sempre (mesmo sem eventos)
        state.last_time_ms = end
        self.state_store.save(state)

        log.info("Tick done: created=%d skipped=%d window=[%d..%d]", created, skipped, start, end)