import os
from cs import CloudStack
from dotenv import load_dotenv

load_dotenv()

def get_cs() -> CloudStack:
    endpoint = os.getenv("CLOUDSTACK_ENDPOINT")
    key = os.getenv("CLOUDSTACK_KEY")
    secret = os.getenv("CLOUDSTACK_SECRET")

    if not endpoint or not key or not secret:
        raise RuntimeError("Faltam variáveis CLOUDSTACK_ENDPOINT/KEY/SECRET no .env")

    return CloudStack(endpoint=endpoint, key=key, secret=secret)
