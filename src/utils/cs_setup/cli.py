"""
Uso:
    cd src
    python -m utils.cs_setup.cli
    python -m utils.cs_setup.cli --dry-run
    python -m utils.cs_setup.cli --only-mapped-groups
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack
from services.keycloak_service import get_keycloak
from utils.cs_setup.cloudstack_role_setup import sync_cloudstack_roles_from_keycloak


def main() -> None:
    parser = argparse.ArgumentParser(description="ClouDiStack — CloudStack Role Sync")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument(
        "--only-mapped-groups",
        action="store_true",
        help="Sync only groups declared in ks2cs.mapping.ROLES_MAPPING",
    )
    args = parser.parse_args()

    setup_logging()
    kc = get_keycloak()
    cs = get_cloudstack()

    report = sync_cloudstack_roles_from_keycloak(
        kc=kc,
        cs=cs,
        dry_run=args.dry_run,
        only_mapped_groups=args.only_mapped_groups,
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()