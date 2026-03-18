"""CloudStack SSO operations."""
from __future__ import annotations
import logging
from .base import CloudStackBaseClient
 
log = logging.getLogger(__name__)
 
 
class CloudStackSSOClient(CloudStackBaseClient):
    """CloudStack SSO operations."""
    
    def authorize_saml_sso(
        self,
        user_id: str,
        entity_id: str = "https://10.10.5.52:8443/realms/Cloud-DI",
        enable: bool = True
    ) -> None:
        """Enable SAML SSO for a user."""
        try:
            log.info(
                f"{'Enabling' if enable else 'Disabling'} SAML SSO for user {user_id}"
            )
            self._cs.authorizeSamlSso(
                userid=user_id,
                entityid=entity_id,
                enable=enable
            )
            log.info(f"SAML SSO {'enabled' if enable else 'disabled'} for user {user_id}")
        except Exception as e:
            self._handle_error(f"authorize_saml_sso({user_id})", e)