from dataclasses import dataclass
from typing import Optional
from cs import CloudStack

@dataclass(frozen=True)
class CSConfig:
    api_url: str
    api_key: str
    secret_key: str
    verify_ssl: bool = True
    timeout: int = 30

_cs_singleton: Optional[CloudStack] = None

def get_cs(config: CSConfig) -> CloudStack:
    """
    Get the singleton CloudStack instance. If it doesn't exist, create it using the provided configuration.

    Args:
        config (CSConfig): CloudStack configuration parameters.

    Returns:
        CloudStack: The singleton CloudStack instance.
    """
    global _cs_singleton
    
    if _cs_singleton is None:
        _cs_singleton = CloudStack(
            endpoint=config.api_url,
            key=config.api_key,
            secret=config.secret_key
        )
        
    return _cs_singleton