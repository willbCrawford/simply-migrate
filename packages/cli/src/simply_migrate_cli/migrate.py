from simply_migrate.app_container.factory import AppContainer
from simply_migrate.loader.migrate import MigrationScriptLoader
from simply_migrate.logging.config import LogLevel, AppEnvironment, ConsoleFormat
from simply_migrate.runner.factory import RunnerContainer
from simply_migrate.runner.settings import SimplyMigrateRunnerSettings

from pathlib import Path

from typing import Annotated

import typer

from rich.console import Console

from simply_migrate.loader.tenant_loader import TenantFileValidator
from simply_migrate.source.factory import build_script_source

from simply_migrate_cli.format.table import create_script_table, create_migration_table
from simply_migrate_cli.progress_tracker.rich_progress_tracker import RichProgressTracker

app = typer.Typer()
console = Console()

@app.command()
def migrate(
    tenants_file: Annotated[
        Path,
        typer.Option(
            exists=True,
            readable=True,
            help="Path to tenants.yaml file."
        )
    ] = Path('tenants.toml'),
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Does not run any sql scripts against tenants. Will output the file to the specified location"
        )
    ] = False,
    validate_only: Annotated[
        bool,
        typer.Option(
            help="Only validates the sql script version files. Does not execute any scripts"
        )
    ] = False,
    version: Annotated[
        str,
        typer.Argument(
            help="Migrates the list of tenants to the specified version. If nothing is supplied it will migrate to the latest version"
        )
    ] = 'latest',
    output_file: Annotated[
        str,
        typer.Option(
            help="Writes the output file to the given path. Normally the output file is written to ./output.json"
        )
    ] = 'output.json',
    migration_dir: Annotated[
        str,
        typer.Option(
            help="Path to the migration folder. By default it will assume you are running in the database migration root directory."
        )
    ] = './',
    tenant_key: Annotated[
        str,
        typer.Option(
            help="Name of tenant to be selected out of tenants_file. By default it will pull all available tenants defined in the file."
        )
    ] = 'all',
    halt_on_error: Annotated[
        bool,
        typer.Option(
            help="If a script fails during a migration, this flag will determine if the entire migration fails or continues."
        )
    ] = False,
    log_level: Annotated[
        LogLevel,
        typer.Option("--log-level")
    ] = LogLevel.INFO,
    environment: Annotated[
        AppEnvironment,
        typer.Option("--environment")
    ] = AppEnvironment.DEVELOPMENT,
    directory: Annotated[
        str,
        typer.Option(
            help="Folder where all the migrations are in."
        )
    ] = ''
):
    """
    Baseline tool to run migrations.
    """
    container = AppContainer.create(
        log_level=log_level,
        environment=environment,
        log_file=True,
        console_format=ConsoleFormat.JSON,
        silent_mode=True
    )
    logger = container.logging.get_logger(namespace="cli", command="migrate")
    logger.info("CLI starting up")

    if tenants_file.is_dir():
        logger.error(f"tenant file is a directory. aborting")
        raise typer.Abort()

    tenant_file_validator = TenantFileValidator(
        logger=logger,
    )

    tenants_file_data = tenant_file_validator.load_tenants_file(
        tenant_key=tenant_key,
        tenants_file=tenants_file,
    )

    source = build_script_source(tenants_file_data.source)

    logger.info(f"Script source: {source.__class__.__name__}")

    loader = MigrationScriptLoader(
        source=source,
        path=".",
        directory=directory,
        version_ceiling=version,
    )

    scripts = loader.load(logger)

    if not scripts:
        logger.warning(f"No scripts found. Aborting.")
        typer.Abort()

    console.print(create_script_table(scripts=scripts))

    tenants_config = tenant_file_validator.resolve_tenants(
        tenant_key=tenant_key,
        tenant_keys=None,
    )

    settings = SimplyMigrateRunnerSettings(
        job_id="local_migration_job",
        version=version,
        migrations_dir=migration_dir,
        output_file=output_file,
        validate_only=validate_only,
        dry_run=dry_run
    )

    migration_progress_tracker = [RichProgressTracker()]

    runner_container = RunnerContainer.create_local_runner(
        logging_container=container.logging,
        runner_settings=settings,
        tenants=tenants_config,
        migration_progress_tracker=migration_progress_tracker
    )

    migration_results = runner_container.runner.run(migration_scripts=scripts)

    console.print(create_migration_table(migration_results=migration_results))

