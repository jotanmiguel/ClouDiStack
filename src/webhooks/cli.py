"""
ks2cs/webhooks/cli.py

CLI para gerir webhooks do keycloak-events.

Uso:
    python -m ks2cs.webhooks.cli --help
    python -m ks2cs.webhooks.cli -p admin123 list
    python -m ks2cs.webhooks.cli -p admin123 create --url http://10.10.5.52:5000/webhook/keycloak --secret mysecret
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.webhooks.client import WebhookClient

sys.path.insert(0, str(Path(__file__).parents[3]))
load_dotenv()


# ─── Config (.env) ────────────────────────────────────────────────

BASE_URL   = os.getenv("KC_SERVER_URL", "https://10.10.5.52:8443")
REALM      = os.getenv("KC_REALM_NAME", "Cloud-DI")
ADMIN_USER = os.getenv("KC_USERNAME",   "admin")
ADMIN_PASS = os.getenv("KC_PASSWORD",   "")
VERIFY_SSL = os.getenv("KC_VERIFY_TLS", "false").lower() in ("true", "1", "yes")


def build_client(password: str) -> WebhookClient:
    wc = WebhookClient(base_url=BASE_URL, realm=REALM, admin_user=ADMIN_USER, verify_ssl=VERIFY_SSL)
    wc.authenticate(password)
    print("✅ Token received (successfully authenticated)")
    return wc


def main():
    parser = argparse.ArgumentParser(description="Keycloak Webhook Manager — Cloud-DI")
    parser.add_argument("--password", "-p", default=ADMIN_PASS, help="Password Keycloak Admin user")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # list
    sub.add_parser("list", help="List webhooks")

    # create
    p = sub.add_parser("create", help="Create webhook")
    p.add_argument("--url",    required=True)
    p.add_argument("--secret", required=True)
    p.add_argument("--events", default="*", help="Types separated by comma (default: *)")

    # update
    p = sub.add_parser("update", help="Update webhook")
    p.add_argument("--id",     required=True)
    p.add_argument("--url",    required=True)
    p.add_argument("--secret", required=True)
    p.add_argument("--events", default="*")

    # delete
    p = sub.add_parser("delete", help="Delete webhook")
    p.add_argument("--id", required=True)

    # sends
    p = sub.add_parser("sends", help="View send history of a webhook")
    p.add_argument("--id", required=True)

    # resend
    p = sub.add_parser("resend", help="Resend failed payload")
    p.add_argument("--id",     required=True)
    p.add_argument("--sendid", required=True)

    # verify-sig
    p = sub.add_parser("verify-sig", help="Verify HMAC signature of a payload")
    p.add_argument("--payload", required=True)
    p.add_argument("--sig",     required=True)
    p.add_argument("--secret",  required=True)

    args = parser.parse_args()

    # verify-sig não precisa de token
    if args.cmd == "verify-sig":
        ok = WebhookClient.verify_signature(args.payload.encode(), args.sig, args.secret)
        print("✅ Signature valid" if ok else "❌ Signature invalid")
        return

    # todos os outros precisam de autenticação
    password = args.password or input("Keycloak Admin Password: ")
    wc = build_client(password)

    if args.cmd == "list":
        webhooks = wc.list()
        print(f"\n📋 '{REALM}' Webhooks found ({len(webhooks)} encontrados):")
        print(json.dumps(webhooks, indent=2))

    elif args.cmd == "create":
        events = [e.strip() for e in args.events.split(",")]
        wc.create(url=args.url, secret=args.secret, event_types=events)
        print(f"✅ Webhook created → {args.url}")

    elif args.cmd == "update":
        events = [e.strip() for e in args.events.split(",")]
        wc.update(webhook_id=args.id, url=args.url, secret=args.secret, event_types=events)
        print(f"✅ Webhook {args.id} updated → {args.url}")

    elif args.cmd == "delete":
        wc.delete(args.id)
        print(f"🗑️  Webhook {args.id} deleted")

    elif args.cmd == "sends":
        sends = wc.sends(args.id)
        print(f"\n📨 Send History ({len(sends)} records):")
        print(json.dumps(sends, indent=2))

    elif args.cmd == "resend":
        wc.resend(args.id, args.sendid)
        print(f"🔁 Resend sent")


if __name__ == "__main__":
    main()