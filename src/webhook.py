#!/usr/bin/env python3
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from services.cloudstack_service import get_cloudstack
from services.keycloak_service import get_keycloak
from config.config import load_settings
from config.logging import setup_logging
from ks2cs.handler import handle_user_create_event, handle_user_delete_event, handle_user_update_event
from ks2cs.mapping import decide_role_from_email
from models.keycloak_models import to_user_create_event
from clients.cloudstack.client import CloudStackClient
from clients.keycloak.client import KeycloakClient
from utils.identity import gen_username

sys.path.insert(0, str(Path(__file__).parent))

setup_logging()
log = logging.getLogger("ks2cs.webhook")

app = FastAPI(title="ClouDiStack Webhook Receiver")

_kc: KeycloakClient | None = None
_cs: CloudStackClient | None = None

@app.on_event("startup")
async def startup():
    global _kc, _cs
    _kc = get_keycloak()
    _cs = get_cloudstack()
    log.info("Keycloak e CloudStack prontos")

# ─── Handlers ──────────────────────────────────────────────────

def _handle_create(raw):
    event = to_user_create_event(raw)
    if not event:
        return {"skipped": True, "reason": "not_parseable"}
    return handle_user_create_event(kc=_kc, cs=_cs, event=event)

def _handle_delete(raw):
    return handle_user_delete_event(kc=_kc, cs=_cs, raw=raw)

def _handle_update(raw):
    return handle_user_update_event(kc=_kc, cs=_cs, raw=raw)

# ─── Router ────────────────────────────────────────────────────

def _route_event(event_type: str, resource_type: str, operation_type: str, raw: dict):
    is_user = resource_type == "USER"

    if event_type == "REGISTER":
        return _handle_create(raw)
    if is_user and operation_type == "CREATE":
        return _handle_create(raw)
    if is_user and operation_type == "DELETE":
        return _handle_delete(raw)
    if is_user and operation_type == "UPDATE":
        return _handle_update(raw)

    return None

# ─── Endpoints ─────────────────────────────────────────────────

@app.post("/webhook/keycloak")
async def keycloak_webhook(request: Request):
    body = await request.body()
    
    if _kc is None or _cs is None:
        raise HTTPException(status_code=500, detail="Clients not initialized")

    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        result = _route_event(
            event.get("type", "UNKNOWN"),
            event.get("resourceType", ""),
            event.get("operationType", ""),
            event
        )

        if result is None:
            return JSONResponse(status_code=200, content={"status": "ignored"})

        return _safe_response(result)

    except Exception as e:
        log.exception("Webhook failed")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

@app.get("/health")
async def health():
    return {"status": "ok", "kc": _kc is not None, "cs": _cs is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook:app", host="0.0.0.0", port=5000, reload=True)
    
# ─── Utils ─────────────────────────────────────────────────────

def _serialize(obj):
    """Converte objetos para algo JSON serializável."""
    if obj is None:
        return None

    # dataclasses
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(obj)

    # objetos com método to_dict()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    # objetos com __dict__
    if hasattr(obj, "__dict__"):
        return vars(obj)

    # fallback
    return str(obj)
    
def _safe_response(result):
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "result": _serialize(result)
        }
    )