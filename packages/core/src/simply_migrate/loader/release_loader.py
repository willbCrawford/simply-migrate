from pathlib import Path

from typing import List

from simply_migrate.models.models import ReleaseFile, TenantConfig

from simply_migrate.loader.load_yaml import (
    _load_yaml,
    _require_fields,
    _require_non_empty,
    _parse_on_error,
    _parse_scripts
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ReleaseConfigError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_release(release_file: Path, tenants_config: List[TenantConfig]) -> ReleaseFile:
    """
    Parse and validate a release YAML file.

    Expected shape::

        version: "1.2.0"
        description: "Add account tiers"
        released_at: "2024-11-01"
        on_error: halt-tenant
        statement_timeout: 60
        lock_timeout: 10
        tenants:                        # optional — omit to target all tenants
          - acme
          - globex
        scripts:
          - path: migrations/V1.2__add_tier.sql
          - path: migrations/V1.3__add_index.sql
            on_error: continue          # per-script override
    """
    raw = _load_yaml(release_file)
    _require_fields(raw, ["version", "scripts"], release_file)
    _require_non_empty(raw, "scripts", release_file)

    return ReleaseFile(
        version=raw["version"],
        description=raw.get("description", ""),
        released_at=raw.get("released_at"),
        on_error=_parse_on_error(value=raw.get("on_error", "halt-tenant"), path=release_file),
        tenants=_resolve_release_tenants(keys=raw.get("tenants"), tenants_config=tenants_config),
        scripts=_parse_scripts(raw_scripts=raw["scripts"]),
        statement_timeout=int(raw.get("statement_timeout", 60)),
        lock_timeout=int(raw.get("lock_timeout", 10)),
    )


def _resolve_release_tenants(
    keys: List[str] | None,
    tenants_config: List[TenantConfig]
):
    # if key is None, return full list of tenants
    if keys is None:
        return tenants_config

    tenant_map = {t.tenant_key: t for t in tenants_config}

    resolved = []
    for key in keys:
        if key not in tenant_map:
            available = ", ".join(tenant_map.keys())
            raise ReleaseConfigError(
                f"Tenant {key!r} not found in tenants file.\n"
                f"Available tenants: {available}"
            )
        resolved.append(tenant_map[key])

    return resolved

