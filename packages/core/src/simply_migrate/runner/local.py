from typing import List

from dataclasses import asdict

from pluggy import PluginManager

from simply_migrate.backend.models import TenantMigrationResult, MigrationStatus
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.models.models import TenantConfig, MigrationScript
from simply_migrate.runner.base import MigrationRunner
from simply_migrate.runner.settings import SimplyMigrateRunnerSettings


class SimplyMigrateLocalRunner(MigrationRunner):
    """Orchestrates migration execution across tenants"""
    def execute_tenant_migration(self, tenants: List[TenantConfig], migration_scripts: List[MigrationScript]) -> List[TenantMigrationResult]:
        migration_results = []

        [progress_tracker.on_start(total_tenants=len(tenants)) for progress_tracker in self.migration_progress_tracker]

        for tenant in tenants:
            try:
                [
                    progress_tracker.on_tenant_start(tenant_id=tenant.tenant_id, tenant_name=tenant.tenant_name)
                    for progress_tracker in self.migration_progress_tracker
                ]

                result = self.backend.run(
                    job_id=self.runner_settings.job_id,
                    tenant_id=tenant.tenant_id,
                    tenant_name=tenant.tenant_name,
                    connection_string=tenant.connection_string,
                    scripts=[asdict(script) for script in migration_scripts],
                    version=self.runner_settings.version
                )

                [
                    progress_tracker.on_tenant_complete(
                        tenant_id=tenant.tenant_id,
                        tenant_name=tenant.tenant_name,
                        success=result.status == MigrationStatus.SUCCESS
                    )
                    for progress_tracker in self.migration_progress_tracker
                ]

                migration_results.append(result)
            except Exception as e:
                self.logger.error(f"{tenant.tenant_id}: {e}")

        [progress_tracker.on_finish() for progress_tracker in self.migration_progress_tracker]

        return migration_results
