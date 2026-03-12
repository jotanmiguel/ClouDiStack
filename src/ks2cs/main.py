import time
from dotenv import get_key, load_dotenv
import cloudstack
from cloudstack.cs_client import get_cs
from ks2cs.config import load_settings
from services.keycloak_service import get_keycloak
from ks2cs.logging_conf import setup_logging
from ks2cs.provisioner import Provisioner
from ks2cs.state_store import JsonStateStore

def main() -> None:
    load_dotenv()
    setup_logging()

    s = load_settings()

    kc = get_keycloak()
    
    cs = get_cs()

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