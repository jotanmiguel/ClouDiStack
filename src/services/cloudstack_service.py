from clients.cloudstack.client import CloudStackClient
from config.config import load_settings
_cs_instance: CloudStackClient | None = None


def get_cloudstack() -> CloudStackClient:
    global _cs_instance

    if _cs_instance is None:
        config = load_settings()
        _cs_instance = CloudStackClient(config)

    return _cs_instance