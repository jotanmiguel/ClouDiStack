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

    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type     = event.get("type", "UNKNOWN")
    resource_type  = event.get("resourceType", "")
    operation_type = event.get("operationType", "")
    realm          = event.get("realmId", "")

    log.info(
        "type=%s resourceType=%s operationType=%s realm=%s",
        event_type, resource_type, operation_type, realm,
    )

    result = _route_event(event_type, resource_type, operation_type, event)

    if result is None:
        return JSONResponse(status_code=200, content={"status": "ignored", "type": event_type})

    return JSONResponse(status_code=200, content={"status": "ok", "result": result})

@app.get("/health")
async def health():
    return {"status": "ok", "kc": _kc is not None, "cs": _cs is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook:app", host="0.0.0.0", port=5000, reload=True)