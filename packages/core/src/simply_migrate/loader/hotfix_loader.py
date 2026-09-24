from dataclasses import dataclass
from pathlib import Path
from typing import List

from simply_migrate.models.models import OnErrorPolicy, ScriptEntry
from simply_migrate.loader.load_yaml import _load_yaml, _require_fields, _require_non_empty, _parse_on_error, \
    _parse_tenants, _parse_scripts


@dataclass
class HotfixFile:
    hotfix:            str
    description:       str
    scripts:           List[ScriptEntry]
    tenants:           List[str]                    # required — no default
    on_error:          OnErrorPolicy       = OnErrorPolicy.HALT
    severity:          str                 = "critical"
    released_at:       str | None          = None
    statement_timeout: int                 = 60
    lock_timeout:      int                 = 10


def load_hotfix(path: Path) -> HotfixFile:
    """
    Parse and validate a hotfix YAML file.

    Expected shape:
        hotfix: "HF-2024-001"
        description: "Backfill missing tier values"
        released_at: "2024-11-15"
        severity: critical
        on_error: halt
        statement_timeout: 60
        lock_timeout: 10
        tenants:                        # required — must name tenants explicitly
          - acme
        scripts:
          - path: hotfixes/scripts/V1.0__backfill_tier.sql
    """
    raw = _load_yaml(path)
    _require_fields(raw, ["hotfix", "scripts", "tenants"], path)
    _require_non_empty(raw, "scripts", path)

    return HotfixFile(
        hotfix=raw["hotfix"],
        description=raw.get("description", ""),
        released_at=raw.get("released_at"),
        severity=raw.get("severity", "critical"),
        on_error=_parse_on_error(raw.get("on_error", "halt"), path),
        tenants=_parse_tenants(raw.get("tenants"), required=True, path=path),
        scripts=_parse_scripts(raw["scripts"]),
        statement_timeout=int(raw.get("statement_timeout", 60)),
        lock_timeout=int(raw.get("lock_timeout", 10)),
    )
