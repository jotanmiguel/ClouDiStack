from clients.cloudstack.client import InstrumentedCloudStack, get_cs
from config.config import load_settings
_cs_instance: InstrumentedCloudStack | None = None


def get_cloudstack() -> InstrumentedCloudStack:
    global _cs_instance

    if _cs_instance is None:
        config = load_settings()
        _cs_instance = get_cs()

    return _cs_instance