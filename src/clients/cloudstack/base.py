"""Base class for CloudStack HTTP client."""
from __future__ import annotations
import logging
from pathlib import Path
from cs import CloudStack
from dotenv import load_dotenv

from adapters.cloudstack.cs_client import InstrumentedCloudStack
from clients.cloudstack.exceptions import CloudStackClientError
 
log = logging.getLogger(__name__)
 
# Load environment
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)
 
 
class CloudStackBaseClient:
    """Base class for CloudStack HTTP client."""
    
    def __init__(self, config):
        """Initialize CloudStack connection."""
        endpoint = config.cs_endpoint
        key = config.cs_key
        secret = config.cs_secret
        self.entity_id = config.cs_idp_entity_id

        if not endpoint or not key or not secret:
            raise CloudStackClientError(
                "Missing CloudStack credentials: CS_ENDPOINT, CS_KEY, CS_SECRET"
            )
        
        try:
            self._cs = InstrumentedCloudStack(
                CloudStack(
                    endpoint=endpoint,
                    key=key,
                    secret=secret,
                    timeout=30,
                )
            )
            log.info(f"✅ CloudStack connected to {endpoint}")
        except Exception as e:
            log.error(f"Failed to connect to CloudStack: {e}")
            raise CloudStackClientError(f"CloudStack connection failed: {e}")
    
    def _handle_error(self, operation: str, error: Exception) -> None:
        """Centralized error handling."""
        log.error(f"[CS] {operation} failed: {error}")
        raise CloudStackClientError(f"{operation} failed: {error}")
    
    def health_check(self) -> bool:
        """Check if CloudStack is reachable."""
        try:
            self._cs.listZones()
            return True
        except Exception:
            return False