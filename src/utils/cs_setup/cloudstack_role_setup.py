from __future__ import annotations

import logging
from typing import Any, Dict

from clients.cloudstack.client import CloudStackClient
from clients.cloudstack.exceptions import CloudStackClientError
from clients.keycloak.client import KeycloakClient
from clients.keycloak.exceptions import KeycloakClientError
from ks2cs.mapping import ROLES_MAPPING

log = logging.getLogger(__name__)


# Default permission rules per role (fallback when group doesn't specify)
# These are generic placeholders — adapt to your CloudStack permission ruleset.
DEFAULT_ROLE_PERMISSIONS: Dict[str, list[str]] = {
    "student": [
        "listVms",
        "deployVm",
        "listVolumes",
    ],
    "staff": [
        "listVms",
        "deployVm",
        "destroyVm",
        "createVolume",
        "listVolumes",
    ],
    "teacher": [
        "listVms",
        "deployVm",
        "destroyVm",
        "createVolume",
        "listVolumes",
    ],
    "researcher": [
        "listVms",
        "deployVm",
        "destroyVm",
        "createVolume",
        "listVolumes",
        "manageNetwork",
    ],
    "guest": [
        "listVms",
    ],
    "user": [
        "listVms",
    ],
}


def _normalize_group_name(name: str | None) -> str:
    return (name or "").strip().lower().lstrip("/")


def _role_name_for_group(group_name: str) -> str:
    normalized = _normalize_group_name(group_name)
    mapping = ROLES_MAPPING.get(normalized)
    if mapping and mapping.get("role_name"):
        return str(mapping["role_name"]).strip().lower()
    return normalized.replace(" ", "_")


def _group_description(group: Dict[str, Any]) -> str:
    name = group.get("name") or "unknown"
    path = group.get("path") or f"/{name}"
    attrs = group.get("attributes") or {}
    attr_keys = ", ".join(sorted(attrs.keys())) if attrs else ""
    description = f"Synced from Keycloak group '{name}' ({path})"
    if attr_keys:
        description += f" | attributes: {attr_keys}"
    return description


class CloudStackRoleSetup:
    """Synchronize CloudStack roles from Keycloak groups."""

    def __init__(self, kc: KeycloakClient, cs: CloudStackClient):
        self.kc = kc
        self.cs = cs

    def run(
        self,
        dry_run: bool = False,
        only_mapped_groups: bool = False,
    ) -> dict:
        report = {
            "created": [],
            "skipped": [],
            "errors": [],
            "dry_run": dry_run,
            "only_mapped_groups": only_mapped_groups,
        }

        groups = self.kc.list_groups() or []
        for group in groups:
            try:
                self.sync_group(
                    group=group,
                    report=report,
                    dry_run=dry_run,
                    only_mapped_groups=only_mapped_groups,
                )
            except (CloudStackClientError, KeycloakClientError, ValueError) as exc:
                group_name = group.get("name") or group.get("id") or "unknown"
                log.error("Error syncing group %s: %s", group_name, exc)
                report["errors"].append({"group": group_name, "error": str(exc)})

        log.info(
            "Role sync complete — created=%d skipped=%d errors=%d",
            len(report["created"]),
            len(report["skipped"]),
            len(report["errors"]),
        )
        return report

    def sync_group(
        self,
        group: Dict[str, Any],
        report: dict | None = None,
        dry_run: bool = False,
        only_mapped_groups: bool = False,
    ) -> dict:
        report = report or {"created": [], "skipped": [], "errors": []}

        group_name = group.get("name") or ""
        normalized_group = _normalize_group_name(group_name)
        if not normalized_group:
            report["skipped"].append({"group": group_name, "reason": "empty_group_name"})
            return report

        if only_mapped_groups and normalized_group not in ROLES_MAPPING:
            report["skipped"].append({"group": group_name, "reason": "not_mapped"})
            return report

        role_name = _role_name_for_group(group_name)
        existing = self.cs.get_role_by_name(role_name)
        if existing:
            report["skipped"].append(
                {
                    "group": group_name,
                    "role": role_name,
                    "role_id": existing.get("id"),
                    "reason": "already_exists",
                }
            )
            return report

        description = _group_description(group)
        if dry_run:
            log.info("DRY RUN create role=%s group=%s", role_name, group_name)
            report["created"].append(
                {
                    "group": group_name,
                    "role": role_name,
                    "description": description,
                    "dry_run": True,
                }
            )
            return report

        role_id = self.cs.create_role(
            name=role_name,
            description=description,
            role_type="User",
        )
        created_entry = {
            "group": group_name,
            "role": role_name,
            "role_id": role_id,
            "description": description,
        }

        # Determine permissions to apply: group attribute overrides DEFAULT_ROLE_PERMISSIONS
        attrs = group.get("attributes") or {}
        # support multiple attribute keys for compatibility
        perms_attr = None
        for key in ("cloudstack_permissions", "cs_permissions", "cloudstack_perms", "permissions"):
            if key in attrs:
                perms_attr = attrs.get(key)
                break

        perms_to_apply: list[str] = []
        if perms_attr:
            # Keycloak group attributes are lists; accept comma-separated strings too
            if isinstance(perms_attr, list):
                raw = ",".join(perms_attr)
            else:
                raw = str(perms_attr)
            perms_to_apply = [p.strip() for p in raw.split(",") if p.strip()]
        else:
            # fallback to defaults based on role name
            perms_to_apply = DEFAULT_ROLE_PERMISSIONS.get(role_name, [])

        created_entry["permissions_requested"] = list(perms_to_apply)

        # Apply permissions (unless dry_run)
        assigned = []
        failed = []
        for perm in perms_to_apply:
            try:
                ok = self.cs.assign_permission_to_role(permission=True, role_id=role_id, rule=[perm])
                if ok:
                    assigned.append(perm)
                else:
                    failed.append({"perm": perm, "error": "unknown"})
            except Exception as e:
                log.warning("Failed to assign perm %s to role %s: %s", perm, role_id, e)
                failed.append({"perm": perm, "error": str(e)})

        created_entry["permissions_assigned"] = assigned
        if failed:
            created_entry["permissions_failed"] = failed

        report["created"].append(created_entry)
        return report

    def sync_group_by_id(
        self,
        group_id: str,
        report: dict | None = None,
        dry_run: bool = False,
        only_mapped_groups: bool = False,
    ) -> dict:
        group = self.kc.get_group(group_id)
        if not group:
            report = report or {"created": [], "skipped": [], "errors": []}
            report["skipped"].append({"group_id": group_id, "reason": "group_not_found"})
            return report
        return self.sync_group(
            group=group,
            report=report,
            dry_run=dry_run,
            only_mapped_groups=only_mapped_groups,
        )


def sync_cloudstack_roles_from_keycloak(kc: KeycloakClient,cs: CloudStackClient,dry_run: bool = False,only_mapped_groups: bool = False,) -> dict:
    """Convenience function for CLI and scripts."""
    return CloudStackRoleSetup(kc=kc, cs=cs).run(
        dry_run=dry_run,
        only_mapped_groups=only_mapped_groups,
    )