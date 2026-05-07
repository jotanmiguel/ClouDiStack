"""
Uso:
    cd src
    python -m setup.cli
    python -m setup.cli --dry-run
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from config.logging import setup_logging
from services.keycloak_service import get_keycloak
from utils.kc_setup.keycloak_group_setup import KeycloakGroupSetup


def main():
    parser = argparse.ArgumentParser(description="ClouDiStack — Keycloak Group Setup")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    args = parser.parse_args()

    setup_logging()
    kc = get_keycloak()\

    setup = KeycloakGroupSetup(kc)
    report = setup.run(dry_run=args.dry_run)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()