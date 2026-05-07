"""
ks2cs/webhooks/client.py

Cliente para gerir webhooks do keycloak-events (p2-inc).
Pode ser usado programaticamente ou via CLI (cli.py).
"""

from __future__ import annotations

import hmac
import hashlib
import requests
import urllib3
from typing import Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WebhookClient:
    """
    Client for managing Keycloak webhooks.

    Example:
        from ks2cs.webhooks import WebhookClient

        wc = WebhookClient(base_url="https://10.10.5.52:8443", realm="Cloud-DI")
        wc.authenticate(password="admin123")

        wc.create(url="http://10.10.5.52:5000/webhook/keycloak", secret="mysecret")
        wc.list()
    """

    def __init__(
        self,
        base_url: str,
        realm: str,
        admin_user: str = "admin",
        verify_ssl: bool = False,
    ):
        self.base_url   = base_url.rstrip("/")
        self.realm      = realm
        self.admin_user = admin_user
        self.verify_ssl = verify_ssl
        self._token: Optional[str] = None

    # ─── Auth ────────────────────────────────────────────────────────────────

    def authenticate(self, password: str) -> str:
        """Obtém token admin do Keycloak e guarda internamente."""
        url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        r = requests.post(url, data={
            "client_id":  "admin-cli",
            "grant_type": "password",
            "username":   self.admin_user,
            "password":   password,
        }, verify=self.verify_ssl)
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        if not self._token:
            raise RuntimeError("Não autenticado — chama authenticate() primeiro")
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _webhooks_url(self, webhook_id: str = "") -> str:
        base = f"{self.base_url}/realms/{self.realm}/webhooks"
        return f"{base}/{webhook_id}" if webhook_id else base

    # ─── CRUD ────────────────────────────────────────────────────────────────

    def list(self) -> list[dict]:
        """ List all webhooks configured for the realm. """
        r = requests.get(self._webhooks_url(), headers=self._headers(), verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()

    def get(self, webhook_id: str) -> dict:
        """ Get details of a specific webhook by its ID. """
        r = requests.get(self._webhooks_url(webhook_id), headers=self._headers(), verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()

    def create(self,url: str,secret: str,event_types: list[str] | None = None,enabled: bool = True,) -> dict:
        """ Create a new webhook with the given URL, secret, event types, and enabled status. """
        payload = {
            "enabled":    str(enabled).lower(),
            "url":        url,
            "secret":     secret,
            "eventTypes": event_types or ["*"],
        }
        r = requests.post(self._webhooks_url(), headers=self._headers(), json=payload, verify=self.verify_ssl)
        r.raise_for_status()
        return r.json() if r.content else {}

    def update(self,webhook_id: str,url: str,secret: str,event_types: list[str] | None = None,enabled: bool = True,) -> None:
        """ Update an existing webhook. """
        payload = {
            "enabled":    str(enabled).lower(),
            "url":        url,
            "secret":     secret,
            "eventTypes": event_types or ["*"],
        }
        r = requests.put(self._webhooks_url(webhook_id), headers=self._headers(), json=payload, verify=self.verify_ssl)
        r.raise_for_status()

    def delete(self, webhook_id: str) -> None:
        """ Delete a webhook by its ID. """
        r = requests.delete(self._webhooks_url(webhook_id), headers=self._headers(), verify=self.verify_ssl)
        r.raise_for_status()

    # ─── Sends (histórico) ───────────────────────────────────────────────────

    def sends(self, webhook_id: str) -> list[dict]:
        """ List all sends (payload deliveries) for a specific webhook. """
        url = f"{self._webhooks_url(webhook_id)}/sends"
        r = requests.get(url, headers=self._headers(), verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()

    def resend(self, webhook_id: str, send_id: str) -> None:
        """ Resend a specific send (payload delivery) for a webhook. """
        url = f"{self._webhooks_url(webhook_id)}/sends/{send_id}/resend"
        r = requests.post(url, headers=self._headers(), verify=self.verify_ssl)
        r.raise_for_status()

    # ─── Utils ───────────────────────────────────────────────────────────────

    @staticmethod
    def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify the HMAC signature of a received payload."""
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)