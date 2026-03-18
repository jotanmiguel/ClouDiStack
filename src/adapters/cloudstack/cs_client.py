from __future__ import annotations
 
import os
import logging
from pathlib import Path
from time import perf_counter
 
from cs import CloudStack
from dotenv import load_dotenv
 
log = logging.getLogger(__name__)
 
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)
 
 
class InstrumentedCloudStack(CloudStack):
    """
    Wrapper around cs.CloudStack that logs all API calls with timing.
    
    Features:
    - Automatic [CS] prefix in logs (from enhanced logging)
    - Duration automatically extracted and displayed
    - Different log levels based on success/failure
    """
 
    def __init__(self, inner: CloudStack):
        self._inner = inner
        log.debug("InstrumentedCloudStack initialized")
 
    def __getattr__(self, name: str):
        """Wrap CloudStack methods with timing and logging."""
        original = getattr(self._inner, name)
 
        if not callable(original):
            return original
 
        def wrapped(*args, **kwargs):
            t0 = perf_counter()
            try:
                res = original(*args, **kwargs)
                dt = perf_counter() - t0
                
                # Log with duration - automatically parsed by enhanced logging!
                # The (XXs) part will be extracted and displayed separately
                log.info(f"{name}() OK ({dt:.4f}s)")
                
                return res
            except Exception as ex:
                dt = perf_counter() - t0
                
                # Error with duration
                log.error(f"{name}() FAIL ({dt:.4f}s): {ex}")
                raise
 
        return wrapped
 
 
def get_cs() -> CloudStack:
    """
    Get CloudStack client.
    
    This function loads credentials from environment variables:
    - CS_ENDPOINT: CloudStack API endpoint (e.g., http://host:8080/client/api)
    - CS_KEY: API key
    - CS_SECRET: Secret key
    
    Returns:
        InstrumentedCloudStack: Wrapped CloudStack client with logging
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    endpoint = os.getenv("CS_ENDPOINT")
    key = os.getenv("CS_KEY")
    secret = os.getenv("CS_SECRET")
 
    if not endpoint or not key or not secret:
        raise ValueError(
            "Missing CloudStack credentials in environment variables. "
            "Please set CS_ENDPOINT, CS_KEY, and CS_SECRET."
        )
 
    cs = CloudStack(
        endpoint=endpoint,
        key=key,
        secret=secret,
        timeout=30,
    )
 
    return InstrumentedCloudStack(cs)