"""Base class for Keycloak HTTP client."""
from __future__ import annotations
import logging
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakError
from config.ssl import disable_ssl_warnings
from .exceptions import KeycloakClientError

log = logging.getLogger(__name__)

class KeycloakBaseClient(KeycloakAdmin):
    """Base class for Keycloak HTTP client."""
    
    def __init__(self, config):
        """Initialize connection to Keycloak."""
        log.info(
            "Connecting to Keycloak at %s (realm=%s, user=%s)",
            config.kc_server_url, config.kc_realm, config.kc_username
        )
        
        try:            
            self._conn = KeycloakOpenIDConnection(
                server_url=config.kc_server_url,
                realm_name=config.kc_realm,
                client_id=config.kc_client_id,
                username=config.kc_username,
                password=config.kc_password,
                verify=config.kc_verify_tls,
            )
            
            self._admin = KeycloakAdmin(server_url=config.kc_server_url,
                                         username=config.kc_username,
                                         password=config.kc_password,
                                         realm_name=config.kc_realm,
                                         verify=config.kc_verify_tls)
            self._admin.change_current_realm(config.kc_realm_name)
            
            log.info("✅ Keycloak client ready")
        except Exception as e:
            log.error(f"Failed to initialize Keycloak: {e}")
            raise KeycloakClientError(f"Keycloak connection failed: {e}")
    
    def _handle_error(self, operation: str, error: Exception) -> None:
        """Centralized error handling."""
        log.error(f"[KC] {operation} failed: {error}")
        raise KeycloakClientError(f"{operation} failed: {error}")
    
    def health_check(self) -> bool:
        """Check if Keycloak is reachable."""
        try:
            self._admin.get_groups()
            return True
        except KeycloakError:
            return False