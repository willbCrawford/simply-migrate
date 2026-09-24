import yaml
from pathlib import Path
from typing import List

from simply_migrate.models.models import OnErrorPolicy, ScriptEntry, SourceConfig, TenantConfig


class SimplyMigrateConfigError(ValueError):
    pass


def _require_non_empty(raw: dict, field: str, path: Path) -> None:
    if not raw.get(field):
        raise SimplyMigrateConfigError(
            f"{path}: '{field}' must contain at least one entry."
        )


def _parse_on_error(value: str, path: Path) -> OnErrorPolicy:
    try:
        return OnErrorPolicy(value)
    except ValueError:
        valid = [p.value for p in OnErrorPolicy]
        raise SimplyMigrateConfigError(
            f"{path}: Invalid on_error value {value!r}. "
            f"Must be one of: {valid}"
        )


def _parse_tenants(
    value,
    required: bool,
    path: Path,
) -> List[str] | None:
    if value is None:
        if required:
            raise SimplyMigrateConfigError(
                f"{path}: 'tenants' is required and must list at least one tenant. "
                f"Hotfixes cannot target all tenants — use a release file instead."
            )
        return None     # release with no tenants = all tenants

    if not isinstance(value, list) or not value:
        raise SimplyMigrateConfigError(
            f"{path}: 'tenants' must be a non-empty list of tenant keys."
        )

    # Guard against numeric tenant keys being parsed as int by PyYAML
    return [str(t) for t in value]

def _parse_scripts(raw_scripts: list[dict]) -> list[ScriptEntry]:
    if not isinstance(raw_scripts, list):
        raise SimplyMigrateConfigError(f"raw_scripts: {raw_scripts!r} is not a list.")

    entries = []
    for s in raw_scripts:
        if "path" not in s:
            raise SimplyMigrateConfigError(f"Script entry missing required 'path' field: {s}")
        on_error = OnErrorPolicy(s["on_error"]) if "on_error" in s else None
        entries.append(ScriptEntry(path=s["path"], on_error=on_error))
    return entries


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Release file not found: {path}")
    with path.open() as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SimplyMigrateConfigError(f"Failed to parse {path}: {e}") from e


def _require_fields(raw: dict, fields: list[str], path: Path) -> None:
    missing = [f for f in fields if f not in raw]
    if missing:
        raise SimplyMigrateConfigError(f"{path} is missing required fields: {missing}")


REQUIRED_TENANT_FIELDS = ("tenant_id", "tenant_name", "connection_string")


def _parse_all_tenants(raw: dict, path: Path) -> List[TenantConfig]:
    tenants_block = raw.get("tenants")

    if not tenants_block or not isinstance(tenants_block, dict):
        raise SimplyMigrateConfigError(
            f"{path} must have a 'tenants' section.\n"
            f"Example:\n"
            f"  tenants:\n"
            f"    acme:\n"
            f"      tenant_id: abc123\n"
            f"      tenant_name: Acme Corp\n"
            f"      connection_string: postgresql://user:pass@host/db"
        )

    return [
        _parse_tenant(key, data, path)
        for key, data in tenants_block.items()
    ]


def _parse_tenant(key: str, data: dict, path: Path) -> TenantConfig:
    if not isinstance(data, dict):
        raise SimplyMigrateConfigError(
            f"{path}: Tenant {key!r} must be a mapping of fields, got {type(data).__name__}."
        )

    missing = [f for f in REQUIRED_TENANT_FIELDS if not data.get(f)]
    if missing:
        raise SimplyMigrateConfigError(
            f"{path}: Tenant {key!r} is missing required fields: {missing}\n"
            f"Each tenant must define: {list(REQUIRED_TENANT_FIELDS)}"
        )

    # Coerce to str — PyYAML parses bare numeric values as int
    return TenantConfig(
        tenant_key=str(key),
        tenant_id=str(data["tenant_id"]),
        tenant_name=str(data["tenant_name"]),
        connection_string=str(data["connection_string"]),
    )


def _parse_source(raw_source: dict, path: Path) -> SourceConfig:
    if not isinstance(raw_source, dict):
        raise SimplyMigrateConfigError(
            f"{path}: 'source' must be a mapping. "
            f"Example:\n  source:\n    type: local"
        )

    valid_types = ("local", "s3", "gcs", "azure")
    source_type = raw_source.get("type", "local")

    if source_type not in valid_types:
        raise SimplyMigrateConfigError(
            f"{path}: Invalid source type {source_type!r}. "
            f"Must be one of: {list(valid_types)}"
        )

    config = SourceConfig(
        type=source_type,
        bucket=raw_source.get("bucket"),
        region=raw_source.get("region", "us-east-1"),
        path_prefix=raw_source.get("path_prefix", ""),
        project=raw_source.get("project"),
        account_url=raw_source.get("account_url"),
        container=raw_source.get("container"),
        options={
            k: v for k, v in raw_source.items()
            if k not in (
                "type", "bucket", "region", "path_prefix",
                "project", "account_url", "container",
            )
        },
    )

    _validate_source_config(config, path)
    return config


def _validate_source_config(config: SourceConfig, path: Path) -> None:
    if config.type == "s3" and not config.bucket:
        raise SimplyMigrateConfigError(
            f"{path}: S3 source requires 'bucket' to be set under 'source'."
        )
    if config.type == "gcs" and not config.bucket:
        raise SimplyMigrateConfigError(
            f"{path}: GCS source requires 'bucket' to be set under 'source'."
        )
    if config.type == "azure":
        if not config.account_url:
            raise SimplyMigrateConfigError(
                f"{path}: Azure source requires 'account_url' to be set under 'source'."
            )
        if not config.container:
            raise SimplyMigrateConfigError(
                f"{path}: Azure source requires 'container' to be set under 'source'."
            )

