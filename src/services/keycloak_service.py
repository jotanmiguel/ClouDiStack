from ks2cs.keycloak_client import KeycloakClient
from ks2cs.config import load_settings
_kc_instance: KeycloakClient | None = None


def get_keycloak() -> KeycloakClient:
    global _kc_instance

    if _kc_instance is None:
        config = load_settings()
        _kc_instance = KeycloakClient(config)

    return _kc_instance