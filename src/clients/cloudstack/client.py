
"""Main CloudStack HTTP client."""
from __future__ import annotations
import logging
from .accounts import CloudStackAccountsClient
from .users import CloudStackUsersClient
from .roles import CloudStackRolesClient
from .domains import CloudStackDomainsClient
from .sso import CloudStackSSOClient
 
log = logging.getLogger(__name__)
 
 
class CloudStackClient(
    CloudStackAccountsClient,
    CloudStackUsersClient,
    CloudStackRolesClient,
    CloudStackDomainsClient,
    CloudStackSSOClient
):
    """
    Main CloudStack HTTP client.
    Combines accounts, users, roles, domains, and SSO operations.
    """
    
    def __init__(self, config):
        """Initialize CloudStackClient."""
        super().__init__(config)
        log.info(
            "✅ CloudStackClient initialized "
            "(accounts + users + roles + domains + sso)"
        )