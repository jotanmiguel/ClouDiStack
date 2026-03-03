from dataclasses import dataclass
import os

from dotenv import load_dotenv

def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None else int(raw)

@dataclass(frozen=True)
class Settings:
    # Keycloak
    kc_server_url: str
    kc_realm: str
    kc_client_id: str
    kc_username: str
    kc_password: str
    kc_verify_tls: bool
    kc_realm_name: str

    # Provisioner
    poll_interval_seconds: int
    state_path: str
    kc_provisioned_attr: str
    kc_account_attr: str

def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        kc_server_url=os.environ["KC_SERVER_URL"],
        kc_realm=os.environ["KC_REALM"],
        kc_client_id=os.getenv("KC_CLIENT_ID", "admin-cli"),
        kc_username=os.environ["KC_USERNAME"],
        kc_password=os.environ["KC_PASSWORD"],
        kc_verify_tls=_get_bool("KC_VERIFY_TLS", True),
        kc_realm_name=os.getenv("KC_REALM_NAME", os.environ["KC_REALM"]),

        poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 5),
        state_path=os.getenv("STATE_PATH", "./state.json"),
        kc_provisioned_attr=os.getenv("KC_PROVISIONED_ATTR", "cloudstackProvisioned"),
        kc_account_attr=os.getenv("KC_ACCOUNT_ATTR", "cloudstackAccount")
    )