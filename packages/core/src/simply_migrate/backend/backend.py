from datetime import datetime, UTC
import time

from typing import Dict, List

from pluggy import HookRelay

from simply_migrate.backend.execute_scripts import execute_script
from simply_migrate.backend.history import (
    has_script_been_applied,
    compute_checksum,
    record_migration_start,
    record_migration_complete, record_migration_failed
)
from simply_migrate.backend.models import TenantMigrationResult, MigrationStatus
from simply_migrate.backend.database_connection_manager import DatabaseConnectionManager
from simply_migrate.backend.migration_record import MigrationRecord, MigrationRecordStatus
from simply_migrate.backend.system_tables import ensure_migration_history_table
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.plugins.callback_result import CallbackResult
from simply_migrate.plugins.context import CallbackContext

class SimplyMigrateBackend:
    def __init__(
            self,
            plugin_manager: HookRelay,
            logger: ContextLogger
    ):
        self.hooks = plugin_manager
        self.errors = []
        self.logger = logger

    def run_callbacks(self, hook_name: str, context) -> CallbackResult:
        hook = getattr(self.hooks, hook_name)
        results = hook(context=context)

        for result in results:
            if result is None:
                continue

            # enforce return type at runtime
            if not isinstance(result, CallbackResult):
                raise TypeError(
                    f"Hook '{hook_name}' must return a CallbackResult or None, "
                    f"got {type(result).__name__}"
                )

            if not result.success or result.skip_script:
                continue
            else:
                return CallbackResult.fail("something failed... continuing")

        return CallbackResult.ok()

    def run(
        self,
        job_id: str,
        tenant_id: str,
        tenant_name: str,
        scripts: List[Dict],
        version: str,
        dry_run: bool = False,
        connection_string: str = None
    ) -> TenantMigrationResult:
        logger = self.logger.with_context(
            job_id=job_id,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            version=version
        )

        started_at = datetime.now(UTC)

        result = TenantMigrationResult(
            tenant_id=tenant_id,
            status=MigrationStatus.RUNNING,
            scripts_applied=[],
            scripts_skipped=[],
            scripts_failed=[],
            callback_metadata={},
            started_at=started_at.isoformat(),
            duration_seconds=0
        )

        try:
            context = CallbackContext(
                job_id=job_id,
                tenant_id=tenant_id,
                script={},
                scripts=scripts,
                current_script_index=-1,
                metadata={}
            )

            try:
                self.run_callbacks(hook_name="before_tenant", context=context)
            except Exception as e:
                logger.error(f"Before tenant callback failed: {e}")

            if dry_run:
                logger.info(f"DRY RUN: Would apply {len(scripts)} scripts to {tenant_id}")
                result.scripts_applied = [s['filename'] for s in scripts]
                result.status = MigrationStatus.SUCCESS

                return result

            # Apply each script with callbacks
            db_manager = DatabaseConnectionManager(connection_string)
            db_manager_engine = db_manager.create_engine()

            has_history_table_been_created = ensure_migration_history_table(db_manager_engine, logger=logger)

            if not has_history_table_been_created:
                logger.error(f"Encountered an issue creating history table for {tenant_id}")

                result.status = MigrationStatus.FAILED
                result.scripts_failed = [s['filename'] for s in scripts]

                return result

            logger.info(f"scripts: {scripts}")

            for idx, script in enumerate(scripts):
                try:
                    if has_script_been_applied(
                            engine=db_manager_engine,
                            version=script["version"],
                            filename=script["filename"],
                            content=script["content"],
                            logger=logger
                    ):
                        result.scripts_skipped.append(script["filename"])
                        logger.info(f"Skipping already applied script: {script['filename']}")
                        continue
                except ValueError as e:
                    logger.error(f"Error applying script: {e}")

                checksum = compute_checksum(script["content"])

                record = MigrationRecord(
                    version=script["version"],
                    filename=script["filename"],
                    description=script["description"],
                    script_type=script["script_type"],
                    status=MigrationRecordStatus.PENDING,
                    checksum=checksum,
                )

                logger.info(f"Applying {script['filename']} to id: {tenant_id} tenant_name: {tenant_name}")

                # Before script callbacks
                script_context = CallbackContext(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    script=script,
                    scripts=scripts,
                    current_script_index=idx,
                    metadata=context.metadata.copy()
                )

                try:
                    self.run_callbacks(hook_name="before_script", context=script_context)
                except Exception as e:
                    logger.error(f"Before script callback failed: {e}")

                record_id = record_migration_start(
                    engine=db_manager_engine,
                    record=record
                )
                start_time = time.time()

                error_occurred = False

                try:
                    # Execute the script
                    execute_script(engine=db_manager_engine, script_content=script['content'])

                except Exception as e:
                    logger.error(f"Script failed to execute: {e}")
                    execution_time = int((time.time() - start_time) * 1000)

                    record_migration_failed(
                        engine=db_manager_engine,
                        record_id=record_id,
                        error_message=str(e),
                        execution_time=execution_time,
                        logger=logger
                    )

                    result.scripts_failed.append(script["filename"])
                    result.duration_seconds += execution_time

                    raise e

                execution_time = int((time.time() - start_time) * 1000)

                record_migration_complete(
                    engine=db_manager_engine,
                    record_id=record_id,
                    execution_time=execution_time,
                    logger=logger
                )
                result.scripts_applied.append(script["filename"])

                result.duration_seconds += execution_time

                try:
                    self.run_callbacks(hook_name="after_script", context=script_context)
                except Exception as e:
                    logger.error(f"After script callback failed: {e}")

            try:
                self.run_callbacks(hook_name="after_tenant", context=context)
            except Exception as e:
                logger.error(f"After tenant callback failed: {e}")

            result.status = MigrationStatus.SUCCESS
            logger.info(f"Successfully completed migration for {tenant_id}")

        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Migration failed for {tenant_id}: {e}")

        result.completed_at = datetime.now(UTC).isoformat()

        return result
