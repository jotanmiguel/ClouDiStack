"""CloudStack SSO operations."""
from __future__ import annotations
import logging

import cs

log = logging.getLogger(__name__)


class CloudStackSSOClient:
    """CloudStack SSO operations."""
    
    def authorize_saml_sso(
        self,
        user_id: str,
        entity_id: str,
        enable: bool = True
    ) -> None:
        """Enable SAML SSO for a user."""
        log.info(f"{'Enabling' if enable else 'Disabling'} SAML SSO for user {user_id} with entity ID {entity_id}")
        cs.authorizeSamlSso(
            user_id=user_id,
            entity_id=entity_id,
            enable=enable
        )