# simply_migrate/runner/mixins.py
import json
import datetime
from dataclasses import asdict
from enum import Enum
from typing import List

from simply_migrate.backend.models import MigrationStatus


class SimplyMigrateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class MigrationExecutor:
    """Shared run() logic for local and Celery runners."""

    def write_output(self, data: List[dict]):
        with open(self.runner.output_file, 'w') as f:
            json.dump({"migrations": data}, f, indent=2, cls=SimplyMigrateEncoder)

    def execute_tenant_migration(self, tenant, migration_scripts):
        """Override in subclasses to change dispatch behaviour."""
        return self.backend.run(
            job_id=self.runner.job_id,
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.tenant_name,
            connection_string=tenant.connection_string,
            scripts=[asdict(script) for script in migration_scripts],
            version=self.runner.version
        )

    def run(self):
        tenants = self.get_valid_tenants()
        migration_scripts = self.validate()

        if migration_scripts is None:
            self.logger.warning("No migration scripts found... nothing to do")
            return True

        migration_results = []
        for tenant in tenants:
            try:
                result = self.execute_tenant_migration(tenant, migration_scripts)
                migration_results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to run migration: {e}")

        self.write_output(migration_results)
        self.logger.info(f"{migration_results}")
        return True