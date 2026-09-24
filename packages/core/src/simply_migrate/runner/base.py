from itertools import chain

import json

from pluggy import PluginManager

from typing import List

from simply_migrate.backend.models import TenantMigrationResult
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.progress_tracker.migration_progress_tracker import MigrationProgressTracker, ProgressTracker
from simply_migrate.runner.encoders import SimplyMigrateEncoder
from simply_migrate.runner.settings import SimplyMigrateRunnerSettings
from simply_migrate.validator.migration_script_validator import MigrationScriptValidator
from simply_migrate.models.models import MigrationScript
from simply_migrate.plugins.enums import SimplyMigrateValidFolders
from simply_migrate.models.models import TenantConfig
from simply_migrate.backend.backend import SimplyMigrateBackend


# TODO: Need to implement searching across the local directory, migrations, data, or hotfix
# TODO: Need to implement migration files
# TODO: Need to implement hotfix files

class MigrationRunner:
    VALID_FOLDERS = [
        SimplyMigrateValidFolders.CURRENT_DIRECTORY,
        SimplyMigrateValidFolders.MIGRATIONS,
        SimplyMigrateValidFolders.DATA,
        SimplyMigrateValidFolders.HOTFIX
    ]

    def __init__(
            self,
            logger: ContextLogger,
            runner_settings: SimplyMigrateRunnerSettings,
            file_plugins: PluginManager,
            migration_callbacks: PluginManager,
            tenants: List[TenantConfig],
            migration_progress_tracker: List[MigrationProgressTracker] = None
    ):
        self.logger = logger
        self.runner_settings = runner_settings
        self.validator = MigrationScriptValidator(
            migrations_dir=runner_settings.migrations_dir,
            dry_run=runner_settings.dry_run,
            logger=self.logger
        )
        self.backend = SimplyMigrateBackend(
            plugin_manager=migration_callbacks.hook,
            logger=self.logger
        )
        self.plugin_manager = file_plugins.hook

        if tenants is None or len(tenants) == 0:
            raise ValueError("No tenants found")
        self._tenants = tenants
        if migration_progress_tracker is None:
            migration_progress_tracker = [ProgressTracker()]

        self.migration_progress_tracker = migration_progress_tracker


    def validate(self) -> List[MigrationScript] | None:
        scripts = self.plugin_manager.get_files(
            path=self.validator.migrations_dir,
            directory=SimplyMigrateValidFolders.CURRENT_DIRECTORY,
            logger=self.logger
        )

        scripts = list(chain.from_iterable(scripts))

        if len(scripts) == 0:
            self.logger.info(f"Did not find any migration scripts to run. Checking other listed directories")
            raise ValueError(f"Could not validate {self.validator.migrations_dir}. Please ensure the directory either "
                             f"has migration sql scripts, or that the directory has "
                             f"{SimplyMigrateValidFolders.MIGRATIONS}, {SimplyMigrateValidFolders.HOTFIX}, or "
                             f"{SimplyMigrateValidFolders.DATA} directories.")

        migration_scripts = self.validator.load_scripts(scripts=scripts)

        if migration_scripts is None:
            self.logger.info("No migration scripts found")
            return None

        return migration_scripts

    def execute_tenant_migration(self, tenants: List[TenantConfig], migration_scripts: List[MigrationScript]) -> List[TenantMigrationResult]:
        raise NotImplementedError

    def write_output(self, data: List[dict]):
        with open(self.runner_settings.output_file, 'w') as f:
            json.dump({"migrations": data}, f, indent=2, cls=SimplyMigrateEncoder)

    def run(self, migration_scripts: List[MigrationScript]) -> List[TenantMigrationResult]:
        if migration_scripts is None:
            self.logger.warning("No migration scripts found... nothing to do")
            return []

        tenants = self._tenants

        migration_results = self.execute_tenant_migration(tenants=tenants, migration_scripts=migration_scripts)

        self.write_output(migration_results)
        self.logger.info(f"{migration_results}")

        return migration_results

