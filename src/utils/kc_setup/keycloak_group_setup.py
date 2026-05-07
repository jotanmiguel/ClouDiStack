from __future__ import annotations
import logging
from typing import Dict, Any
from clients.keycloak.client import KeycloakClient

log = logging.getLogger(__name__)


GROUP_SCHEMA: Dict[str, Dict[str, Any]] = {
    "students": {
        "attributes": {
            "max_vms":               ["2"],
            "max_cpu":               ["4"],
            "max_ram_mb":            ["4096"],
            "max_volumes":           ["4"],
            "max_snapshots":         ["10"],
            "max_public_ips":        ["1"],
            "max_networks":          ["1"],
            "max_vpc":               ["1"],
            "max_primary_storage":   ["50"],
            "max_secondary_storage": ["50"],
        }
    },
    "staff": {
        "attributes": {
            "max_vms":               ["5"],
            "max_cpu":               ["8"],
            "max_ram_mb":            ["8192"],
            "max_volumes":           ["10"],
            "max_snapshots":         ["20"],
            "max_public_ips":        ["2"],
            "max_networks":          ["3"],
            "max_vpc":               ["2"],
            "max_primary_storage":   ["200"],
            "max_secondary_storage": ["200"],
        }
    },
    "teachers": {
        "attributes": {
            "max_vms":               ["5"],
            "max_cpu":               ["8"],
            "max_ram_mb":            ["8192"],
            "max_volumes":           ["10"],
            "max_snapshots":         ["20"],
            "max_public_ips":        ["2"],
            "max_networks":          ["3"],
            "max_vpc":               ["2"],
            "max_primary_storage":   ["200"],
            "max_secondary_storage": ["200"],
        }
    },
    "researchers": {
        "attributes": {
            "max_vms":               ["10"],
            "max_cpu":               ["32"],
            "max_ram_mb":            ["65536"],
            "max_volumes":           ["20"],
            "max_snapshots":         ["50"],
            "max_public_ips":        ["5"],
            "max_networks":          ["5"],
            "max_vpc":               ["3"],
            "max_primary_storage":   ["500"],
            "max_secondary_storage": ["500"],
        }
    },
    "guests": {
        "attributes": {
            "max_vms":               ["1"],
            "max_cpu":               ["1"],
            "max_ram_mb":            ["1024"],
            "max_volumes":           ["1"],
            "max_snapshots":         ["5"],
            "max_public_ips":        ["0"],
            "max_networks":          ["1"],
            "max_vpc":               ["1"],
            "max_primary_storage":   ["10"],
            "max_secondary_storage": ["10"],
        }
    },
    "users": {
        "attributes": {
            "max_vms":               ["1"],
            "max_cpu":               ["2"],
            "max_ram_mb":            ["2048"],
            "max_volumes":           ["2"],
            "max_snapshots":         ["5"],
            "max_public_ips":        ["0"],
            "max_networks":          ["1"],
            "max_vpc":               ["1"],
            "max_primary_storage":   ["20"],
            "max_secondary_storage": ["20"],
        }
    },
}

class KeycloakGroupSetup:
    """Não herda de nada — recebe cliente já construído."""

    def __init__(self, kc: KeycloakClient):
        self.kc: KeycloakClient = kc

    def run(self, dry_run: bool = False) -> dict:
        report = {
            "created": [],
            "updated": [],
            "skipped": [],
            "errors":  [],
            "dry_run": dry_run,
        }

        existing_groups = {
            g["name"]: g
            for g in (self.kc.list_groups() or [])
        }
    
        for group_name, schema in GROUP_SCHEMA.items():
            try:
                self._ensure_group(
                    group_name=group_name,
                    schema=schema,
                    existing_groups=existing_groups,
                    report=report,
                    dry_run=dry_run,
                )
            except Exception as e:
                log.error("Error processing group %s: %s", group_name, e)
                report["errors"].append({"group": group_name, "error": str(e)})

        log.info(
            "Setup complete — created=%d updated=%d skipped=%d errors=%d",
            len(report["created"]),
            len(report["updated"]),
            len(report["skipped"]),
            len(report["errors"]),
        )
        return report

    def _ensure_group(self, group_name, schema, existing_groups, report, dry_run):
        expected_attrs = schema.get("attributes", {})

        if group_name not in existing_groups:
            log.info("Group '%s' not found → %s", group_name, "SKIP (dry_run)" if dry_run else "CREATE")

            if not dry_run:
                group_id = self.kc.create_group(name=group_name, path=f"/{group_name}")
                print(f"Created group '{group_name}' with ID: {group_id}")
                print(f"Setting attributes for group '{group_name}': {list(expected_attrs.keys())}")
                self._set_group_attributes(group_id, expected_attrs)

            report["created"].append({
                "group": group_name,
                "attributes": list(expected_attrs.keys()),
            })

        else:
            group = existing_groups[group_name]
            group_id = group["id"]
            current_attrs = group.get("attributes") or {}

            missing = {
                k: v for k, v in expected_attrs.items()
                if k not in current_attrs
            }

            if missing:
                log.info("Group '%s' missing attrs %s → %s",
                         group_name, list(missing.keys()), "SKIP (dry_run)" if dry_run else "UPDATE")

                if not dry_run:
                    merged = {**current_attrs, **missing}
                    self._set_group_attributes(group_id, merged)

                report["updated"].append({
                    "group": group_name,
                    "added_attributes": list(missing.keys()),
                })
            else:
                log.debug("Group '%s' OK — no changes needed", group_name)
                report["skipped"].append(group_name)

    def _set_group_attributes(self, group_id: str, attributes: dict) -> None:
        """Atualiza atributos de um grupo via Keycloak Admin API."""
        self.kc.update_group(group_id, {"attributes": attributes})
        log.debug("Set attributes for group %s: %s", group_id, list(attributes.keys()))