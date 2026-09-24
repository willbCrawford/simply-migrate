from simply_migrate.logging.container import LoggingContainer
from simply_migrate.models.models import TenantConfig
from simply_migrate.plugins.implementation import LocalMigrationFilePlugin
from simply_migrate.plugins.registry import JobCallbackRegistry, MigrationFileRegistry, MigrationCallbackRegistry
from simply_migrate.runner.settings import SimplyMigrateRunnerSettings
from simply_migrate.runner.base import MigrationRunner
from simply_migrate.runner.local import SimplyMigrateLocalRunner
from simply_migrate.progress_tracker.migration_progress_tracker import MigrationProgressTracker, ProgressTracker

from pluggy import PluginManager

from typing import List

def get_plugin_job_spec(plugins: List):
    job_callback = JobCallbackRegistry()

    for plugin in plugins:
        job_callback.register_plugin(plugin)

    return job_callback.pm


def get_plugin_manager_file_spec(plugins: List) -> PluginManager:
    migration_file = MigrationFileRegistry()

    for plugin in plugins:
        migration_file.register_plugin(plugin)

    return migration_file.pm


def get_plugin_manager_migration_callback(plugins: List):
    migration_callback = MigrationCallbackRegistry()

    for plugin in plugins:
        migration_callback.register_plugin(plugin)

    return migration_callback.pm


class RunnerContainer:
    def __init__(
            self,
            runner: MigrationRunner,
    ):
        self.runner = runner

    @classmethod
    def create_local_runner(
            cls,
            logging_container: LoggingContainer,
            runner_settings: SimplyMigrateRunnerSettings,
            tenants: List[TenantConfig],
            migration_progress_tracker: List[MigrationProgressTracker] = None,
            file_plugins=None,
            migration_plugins=None,
            job_plugins=None
    ):
        if job_plugins is None:
            job_plugins = []
        if migration_plugins is None:
            migration_plugins = []
        if file_plugins is None:
            file_plugins = [LocalMigrationFilePlugin()]
        if migration_progress_tracker is None:
            migration_progress_tracker = [ProgressTracker()]

        file_plugins = get_plugin_manager_file_spec(file_plugins)
        migration_plugins = get_plugin_manager_migration_callback(migration_plugins)

        local_runner = SimplyMigrateLocalRunner(
            logger=logging_container.get_logger(job_id=runner_settings.job_id),
            runner_settings=runner_settings,
            file_plugins=file_plugins,
            migration_callbacks=migration_plugins,
            tenants=tenants,
            migration_progress_tracker=migration_progress_tracker
        )

        return cls(runner=local_runner)

