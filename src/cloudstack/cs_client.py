# src/cloudstack/cs_client.py

from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

from cs import CloudStack
from dotenv import load_dotenv
env = load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

class InstrumentedCloudStack(CloudStack):
    """
    Wrapper (composition) around cs.CloudStack.
    Avoids interfering with CloudStack's dynamic __getattr__ handler system.
    """

    def __init__(self, inner: CloudStack):
        self._inner = inner

    def __getattr__(self, name: str):
        original = getattr(self._inner, name)

        if not callable(original):
            return original

        def wrapped(*args, **kwargs):
            t0 = perf_counter()
            try:
                res = original(*args, **kwargs)
                dt = perf_counter() - t0
                print(f"[CS] {name} OK ({dt:.4f}s)")
                return res
            except Exception as ex:
                dt = perf_counter() - t0
                print(f"[CS] {name} FAIL ({dt:.4f}s) -> {ex}")
                raise

        return wrapped

def get_cs() -> CloudStack:
    endpoint = os.getenv("CS_ENDPOINT")
    key = os.getenv("CS_KEY")
    secret = os.getenv("CS_SECRET")

    if not endpoint or not key or not secret:
        raise ValueError("Missing CloudStack credentials in environment variables")

    cs = CloudStack(
        endpoint=endpoint,
        key=key,
        secret=secret,
        timeout=30,
    )

    return InstrumentedCloudStack(cs)