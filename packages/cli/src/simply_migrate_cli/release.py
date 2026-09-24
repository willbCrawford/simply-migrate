from simply_migrate.app_container.factory import AppContainer
from simply_migrate.loader.release import ReleaseLoader
from simply_migrate.logging.config import LogLevel, AppEnvironment, ConsoleFormat
from simply_migrate.runner.factory import RunnerContainer
from simply_migrate.runner.settings import SimplyMigrateRunnerSettings

from pathlib import Path

from typing import Annotated

import typer

from simply_migrate.loader.tenant_loader import TenantFileValidator
from simply_migrate.source.factory import build_script_source

app = typer.Typer()

@app.command()
def release(
    release_file: Annotated[
        str,
        typer.Argument(help="Release file"),
    ],
    tenants_file: Annotated[
        Path,
        typer.Option(help="Path to tenants.yaml file"),
    ] = Path("tenants.yaml"),
    log_level: Annotated[
        LogLevel,
        typer.Option("--log-level")
    ] = LogLevel.INFO,
    environment: Annotated[
        AppEnvironment,
        typer.Option("--environment")
    ] = AppEnvironment.DEVELOPMENT,
    dry_run: Annotated[
        bool,
        typer.Option(help="Does not run any sql scripts against tenants."),
    ] = False,
    output_file: Annotated[
        str,
        typer.Option(
            help="Writes the output file to the given path. Normally the output file is written to ./output.json"
        )
    ] = 'output.json',
    validate_only: Annotated[
        bool,
        typer.Option(
            help="Only validates the sql script version files. Does not execute any scripts"
        )
    ] = False
):
    """
    Uses the parameter release_version to find the associated release and parses it to determine the associated
    tenant(s), sql files and apply them in order to the tenants.
    """
    container = AppContainer.create(
        log_level=log_level,
        environment=environment,
        log_file=True,
        console_format=ConsoleFormat.PLAIN,
    )
    logger = container.logging.get_logger(namespace="cli", command="release")
    logger.info("CLI starting up")

    validator = TenantFileValidator(
        logger=logger,
    )

    tenants_file_data = validator.load_tenants_file(
        tenant_key=None,
        tenants_file=tenants_file,
    )

    source = build_script_source(tenants_file_data.source)

    logger.info(f"Script source: {source.__class__.__name__}")

    release_loader = ReleaseLoader(
        source=source,
        release_file=release_file,
        tenants_config=tenants_file_data.tenants,
    )

    tenant_release, migrations = release_loader.load(logger=logger)

    settings = SimplyMigrateRunnerSettings(
        job_id='local_release_job',
        version=tenant_release.version,
        migrations_dir='',
        output_file=output_file,
        validate_only=validate_only,
        dry_run=dry_run
    )

    runner_container = RunnerContainer.create_local_runner(
        logging_container=container.logging,
        runner_settings=settings,
        tenants=tenants_file_data.tenants,
    )

    runner_container.runner.run(migration_scripts=migrations)

