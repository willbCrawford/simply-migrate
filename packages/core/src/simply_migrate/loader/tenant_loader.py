from simply_migrate.models.models import TenantsFile, TenantConfig
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.loader.load_yaml import _load_yaml, _parse_all_tenants, _parse_source

from pathlib import Path
from typing import List

class TenantFileNotFoundError(FileNotFoundError):
    pass

class TenantNotFoundError(KeyError):
    pass

class TenantConfigError(ValueError):
    pass

class TenantFileValidator:
    REQUIRED_FIELDS = ("tenant_id", "tenant_name", "connection_string")
    file: TenantsFile

    def __init__(
            self,
            logger: ContextLogger
    ):
        self.logger = logger

    def list_tenant_keys(self, path: Path) -> List[str]:
        """Return all tenant keys defined in the file — useful for --tenant all tab completion."""
        return [t.tenant_key for t in self.file.tenants]

    def load_tenants_file(
            self,
            tenant_key: str | None,
            tenants_file: Path,
    ) -> TenantsFile:
        """
        Parse and validate a tenants.yaml file.

        Expected shape::

            source:
              type: local                   # local | s3 | gcs | azure
              bucket: my-migrations         # s3 / gcs
              region: us-east-1             # s3
              path_prefix: migrations       # s3
              project: my-gcp-project       # gcs
              account_url: https://...      # azure
              container: migrations         # azure

            tenants:
              acme:
                tenant_id: abc123
                tenant_name: Acme Corp
                connection_string: postgresql://user:pass@host/acme_db

              globex:
                tenant_id: def456
                tenant_name: Globex
                connection_string: postgresql://user:pass@host/globex_db
        """
        raw = _load_yaml(path=tenants_file)

        self.file = TenantsFile(
            tenants=_parse_all_tenants(raw, tenants_file),
            source=_parse_source(raw.get("source", {}), tenants_file),
        )

        return self.file

    def resolve_tenants(
            self,
            tenant_key: str | None = None,
            tenant_keys: List[str] = None,
            tenant_id: str | None = None,
            tenant_name: str | None = None,
            connection_string: str | None = None,
    ) -> List[TenantConfig]:
        """
        Unified tenant resolution. Returns a list of TenantConfig in all cases
        so the caller never needs to branch on single vs multiple.

        Precedence:
            CLI args  >  tenants.yaml entry  >  all tenants

        Modes:
            --tenant all                → all tenants in file
            --tenant acme,globex        → specific subset by key
            --tenant acme               → single tenant, with optional CLI overrides
            --tenant-id / --tenant-name / --connection-string only → fully inline
        """
        overrides = {
            k: v for k, v in {
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "connection_string": connection_string,
            }.items() if v is not None
        }

        # -- all tenants --
        if tenant_key == "all":
            if overrides:
                raise TenantConfigError(
                    "Per-field overrides (--tenant-id, --tenant-name, "
                    "--connection-string) cannot be combined with --tenant all."
                )
            return self.file.tenants

        # -- comma-separated subset --
        if tenant_keys:
            if overrides:
                raise TenantConfigError(
                    "Per-field overrides cannot be combined with a tenant list."
                )
            return [self.get_tenant(key) for key in tenant_keys]

        # -- single tenant with optional overrides --
        base: dict = {}

        if tenant_key:
            cfg = self.get_tenant(tenant_key)
            base = {
                "tenant_id": cfg.tenant_id,
                "tenant_name": cfg.tenant_name,
                "connection_string": cfg.connection_string,
            }

        base.update(overrides)

        missing = [f for f in self.REQUIRED_FIELDS if not base.get(f)]
        if missing:
            raise TenantConfigError(
                f"Missing required tenant fields: {missing}\n"
                f"Provide --tenant <key> to load from tenants.yaml, or pass "
                f"--tenant-id / --tenant-name / --connection-string directly."
            )

        return [TenantConfig(**base)]

    def get_tenant(self, tenant_key: str) -> TenantConfig:
        tenant = next(
            (t for t in self.file.tenants if t.tenant_key == tenant_key),
            None
        )

        if tenant is None:
            available = ", ".join(t.tenant_id for t in self.file.tenants)
            raise TenantNotFoundError(
                f"Tenant {tenant_key!r} not found.\n"
                f"Available tenants: {available}"
            )

        return tenant
