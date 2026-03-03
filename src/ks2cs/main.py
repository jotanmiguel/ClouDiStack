import os
import time

from dotenv import load_dotenv
from ks2cs.keycloak_client import KeycloakClient

import cloudstack
import cloudstack.cs_client
import cloudstack.session
from ks2cs.provisioner import Provisioner
from ks2cs.config import load_settings
from ks2cs.logging_conf import setup_logging
from ks2cs.state_store import JsonStateStore


def main() -> None:
    load_dotenv()
    setup_logging()

    s = load_settings()

    kc = KeycloakClient(
        server_url=s.kc_server_url,
        auth_realm=s.kc_realm,
        client_id=s.kc_client_id,
        username=s.kc_username,
        password=s.kc_password,
        verify_tls=s.kc_verify_tls,
        target_realm=s.kc_realm_name,
    )
    
    cs = cloudstack.cs_client.get_cs()

    store = JsonStateStore(s.state_path)

    prov = Provisioner(
        kc=kc,
        cs=cs,
        state_store=store,
        provisioned_attr=s.kc_provisioned_attr,
        account_attr=s.kc_account_attr,
    )

    while True:
        prov.tick()
        time.sleep(s.poll_interval_seconds)
        
if __name__ == "__main__":
    main()