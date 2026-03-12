#!/usr/bin/env python3
"""
ClouDiStack — Keycloak Webhook Receiver
Recebe eventos do keycloak-events e dispara ações no CloudStack.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))

from cloudstack.cs_client import get_cs
from ks2cs.config import load_settings
from ks2cs.keycloak_client import KeycloakClient
from ks2cs.handler import handle_user_create_event
from ks2cs.mapping import decide_role_from_email
from models.keycloak_models import to_user_create_event
from user_ops import disable_staff, disable_student, update_staff, update_student
from utils.identity import gen_username

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ks2cs.webhook")

app = FastAPI(title="ClouDiStack Webhook Receiver")

_kc = None
_cs = None


@app.on_event("startup")
async def startup():
    global _kc, _cs
    s = load_settings()
    try:
        _kc = KeycloakClient(config=s)
    except TypeError:
        _kc = KeycloakClient(
            server_url=s.kc_server_url,
            auth_realm=s.kc_realm,
            client_id=s.kc_client_id,
            username=s.kc_username,
            password=s.kc_password,
            verify_tls=s.kc_verify_tls,
            target_realm=s.kc_realm_name,
        )
    _cs = get_cs()
    log.info("✅ Keycloak e CloudStack prontos")


# ─── Handlers ────────────────────────────────────────────────────────────────

def _handle_create(raw: dict):
    """Cria o utilizador no CloudStack quando é criado no Keycloak."""
    event = to_user_create_event(raw)
    if not event:
        log.warning("CREATE não parseável: %s", raw)
        return {"skipped": True, "reason": "not_parseable"}

    result = handle_user_create_event(kc=_kc, cs=_cs, event=event)

    if result is None:
        return {"skipped": True, "reason": "already_provisioned"}

    log.info("✅ Criado: %s (%s) role=%s", result.username, result.email, result.role)
    return {
        "provisioned": True,
        "username":    result.username,
        "email":       result.email,
        "account_id":  result.account_id,
        "user_id":     result.user_id,
        "role":        result.role,
        "created":     result.created,
        "changed":     result.changed,
    }


def _handle_delete(raw: dict):
    """
    Desativa a conta no CloudStack quando o user é apagado no Keycloak.
    Usa disable (não delete) para preservar dados — altera para delete_student
    se quiseres apagar permanentemente.
    """
    rep_raw = raw.get("representation", "{}")
    try:
        rep = json.loads(rep_raw) if isinstance(rep_raw, str) else rep_raw
    except Exception:
        rep = {}

    email    = rep.get("email", "")
    username = rep.get("username") or gen_username(email) if email else ""

    if not username:
        details  = raw.get("details", {})
        username = details.get("username", "")

    if not username:
        log.warning("DELETE sem username no payload: %s", raw)
        return {"skipped": True, "reason": "no_username"}

    role = decide_role_from_email(email) if email else "student"

    try:
        if role == "staff":
            result = disable_staff(_cs, username)
        else:
            result = disable_student(_cs, username)

        log.info("🗑️  Desativado: %s (role=%s)", username, role)
        return result

    except ValueError as e:
        log.warning("DELETE ignorado — %s", e)
        return {"skipped": True, "reason": str(e)}


def _handle_update(raw: dict):
    """
    Sincroniza alterações de perfil (nome, email) no CloudStack
    quando o user é atualizado no Keycloak.
    """
    rep_raw = raw.get("representation", "{}")
    try:
        rep = json.loads(rep_raw) if isinstance(rep_raw, str) else rep_raw
    except Exception:
        rep = {}

    email     = rep.get("email", "")
    username  = rep.get("username") or gen_username(email) if email else ""
    firstname = rep.get("firstName")
    lastname  = rep.get("lastName")

    if not username:
        details  = raw.get("details", {})
        username = details.get("username", "")

    if not username:
        log.warning("UPDATE sem username no payload: %s", raw)
        return {"skipped": True, "reason": "no_username"}

    # só atualiza campos que realmente mudaram
    kwargs = {}
    if firstname:
        kwargs["firstname"] = firstname
    if lastname:
        kwargs["lastname"] = lastname
    if email:
        kwargs["email"] = email

    if not kwargs:
        return {"skipped": True, "reason": "no_fields_changed"}

    role = decide_role_from_email(email) if email else "student"

    try:
        if role == "staff":
            result = update_staff(_cs, username, **kwargs)
        else:
            result = update_student(_cs, username, **kwargs)

        log.info("✏️  Atualizado: %s campos=%s", username, list(kwargs.keys()))
        return result

    except ValueError as e:
        log.warning("UPDATE ignorado — %s", e)
        return {"skipped": True, "reason": str(e)}


# ─── Router ──────────────────────────────────────────────────────────────────

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


# ─── Endpoints ───────────────────────────────────────────────────────────────

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
        "📥 type=%s resourceType=%s operationType=%s realm=%s",
        event_type, resource_type, operation_type, realm,
    )

    result = _route_event(event_type, resource_type, operation_type, event)

    if result is None:
        return JSONResponse(status_code=200, content={"status": "ignored", "type": event_type})

    return JSONResponse(status_code=200, content={"status": "ok", "result": result})


@app.get("/health")
async def health():
    return {"status": "ok", "kc": _kc is not None, "cs": _cs is not None}


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook:app", host="0.0.0.0", port=5000, reload=True)