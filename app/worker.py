from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

import redis

import asyncio

from kombu import Queue
from datetime import datetime
from typing import List, Dict
from dataclasses import asdict
import os

from app.callback.callback_registry import CallbackRegistry
from app.callback.callback_context import CallbackContext
from app.migration_queue.state_management import TenantMigrationResult, MigrationStatus, StateManager, DatabaseConnectionManager

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

app = Celery(__name__)
app.conf.broker_url = REDIS_URL
app.conf.result_backend = REDIS_URL
app.conf.task_track_started = True

# app.config_from_object(Config)

# # Define task queues for different priorities
app.conf.task_routes = {
    'apply_migration_to_tenant': {'queue': 'migrations'},
    'finalize_migration_job': {'queue': 'migrations'},
    'rollback_migration': {'queue': 'rollbacks'},
}

# app.conf.task_queues = (
#     Queue('migrations', routing_key='migrations.#'),
#     Queue('rollbacks', routing_key='rollbacks.#', priority=10),
# )

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

logger = get_task_logger(__name__)

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
state_manager = StateManager(redis_client)

callback_registry = CallbackRegistry()

try:
    callback_file = os.environ['SIMPLY_MIGRATE_CALLBACK_FILE']

    # Load callbacks if file provided
    if callback_file:
        callback_registry.load_from_file(callback_file)
except KeyError as e:
    logger.info(f"Could not load the callback file. Environment variable was never supplied")

print(app.conf)


# TODO: Create logic to store migrations in tenant database and conditionally create tables to store data
@app.task(
    bind=True,
    # soft_time_limit=Config.TASK_SOFT_TIME_LIMIT,
    # time_limit=Config.TASK_TIME_LIMIT,
    # acks_late=Config.TASK_ACKS_LATE,
    # reject_on_worker_lost=Config.TASK_REJECT_ON_WORKER_LOST,
    # autoretry_for=(Exception,),
    # retry_kwargs={'max_retries': 3, 'countdown': 5},
    name="apply_migration_to_tenant"
)
def apply_migration_to_tenant(
        self: Task,
        job_id: str,
        tenant_id: str,
        tenant_name: str,
        user: str,
        password: str,
        database_name: str,
        host: str,
        connection_string: str,
        scripts: List[Dict],
        dry_run: bool = False
) -> Dict:
    """Apply migration scripts to a single tenant with callback support"""
    started_at = datetime.utcnow()
    logger.info(f"🚀 Task received: for tenant: {tenant_id}")
    logger.info(f"Job ID: {job_id}, Scripts: {scripts}, Dry run: {dry_run}")

    result = TenantMigrationResult(
        tenant_id=tenant_id,
        status=MigrationStatus.RUNNING,
        scripts_applied=[],
        scripts_skipped=[],
        callback_metadata={},
        started_at=started_at.isoformat()
    )

    try:
        # Run before_tenant callbacks
        context = CallbackContext(
            job_id=job_id,
            tenant_id=tenant_id,
            script={},
            scripts=scripts,
            current_script_index=-1,
            metadata={}
        )

        callback_result = asyncio.run(callback_registry.run_callbacks(
            callback_registry.before_tenant_callbacks,
            context
        ))

        if not callback_result.success:
            raise Exception(f"Before tenant callback failed: {callback_result.message}")

        result.callback_metadata.update(context.metadata)

        if dry_run:
            logger.info(f"DRY RUN: Would apply {len(scripts)} scripts to {tenant_id}")
            result.scripts_applied = [s['filename'] for s in scripts]
            result.status = MigrationStatus.SUCCESS
        else:
            # Apply each script with callbacks
            db_manager = DatabaseConnectionManager()
            for idx, script in enumerate(scripts):
                logger.info(f"Applying {script['filename']} to {tenant_id}")

                # Before script callbacks
                script_context = CallbackContext(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    script=script,
                    scripts=scripts,
                    current_script_index=idx,
                    metadata=context.metadata.copy()
                )

                callback_result = asyncio.run(callback_registry.run_callbacks(
                    callback_registry.before_script_callbacks,
                    script_context
                ))

                if not callback_result.success:
                    raise Exception(f"Before script callback failed: {callback_result.message}")

                if callback_result.skip_script:
                    logger.info(f"Skipping {script['filename']}: {callback_result.message}")
                    result.scripts_skipped.append(script['filename'])
                    continue

                # Execute the script
                db_manager.execute_script(user, password, database_name, host, connection_string, script['content'])
                result.scripts_applied.append(script['filename'])

                # After script callbacks
                callback_result = asyncio.run(callback_registry.run_callbacks(
                    callback_registry.after_script_callbacks,
                    script_context
                ))

                if not callback_result.success:
                    raise Exception(f"After script callback failed: {callback_result.message}")

                result.callback_metadata.update(script_context.metadata)

                # Update task progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'tenant_id': tenant_id,
                        'scripts_completed': len(result.scripts_applied),
                        'total_scripts': len(scripts)
                    }
                )

            # After tenant callbacks
            callback_result = asyncio.run(callback_registry.run_callbacks(
                callback_registry.after_tenant_callbacks,
                context
            ))

            if not callback_result.success:
                logger.warning(f"After tenant callback failed: {callback_result.message}")

            result.status = MigrationStatus.SUCCESS
            logger.info(f"Successfully completed migration for {tenant_id}")

    except SoftTimeLimitExceeded:
        # result.status = MigrationStatus.FAILED
        result.error_message = "Migration exceeded time limit"
        logger.error(f"Migration timeout for {tenant_id}")

        # Run error callbacks
        # _run_error_callbacks(job_id, tenant_id, result.error_message)

    except Exception as e:
        result.status = MigrationStatus.FAILED
        result.error_message = str(e)
        logger.error(f"Migration failed for {tenant_id}: {e}", exc_info=True)

        # Run error callbacks
        # _run_error_callbacks(job_id, tenant_id, str(e))

    finally:
        completed_at = datetime.utcnow()
        result.completed_at = completed_at.isoformat()
        result.duration_seconds = (completed_at - started_at).total_seconds()

        state_manager.update_tenant_result(job_id, result)

    return asdict(result)


@app.task(
    bind=True,
    name='finalize_migration_job'
)
def finalize_migration_job(self: Task, job_id: str):
    """Callback task that runs after all tenant migrations complete"""
    logger.info(f"Finalizing migration job {job_id}")

    job = state_manager.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    # Run after_job callbacks
    try:
        context = CallbackContext(
            job_id=job_id,
            tenant_id="",
            script={},
            scripts=[],
            current_script_index=-1,
            metadata={
                'total_tenants': job.total_tenants,
                'successful_tenants': job.successful_tenants,
                'failed_tenants': job.failed_tenants
            }
        )
        # callback_registry.run_callbacks(callback_registry.after_job_callbacks, context)
    except Exception as e:
        logger.error(f"After job callback failed: {e}", exc_info=True)

    logger.info(f"Migration job {job_id} completed:")
    logger.info(f"  Total: {job.total_tenants}")
    logger.info(f"  Successful: {job.successful_tenants}")
    logger.info(f"  Failed: {job.failed_tenants}")

    return {
        'job_id': job_id,
        'status': job.status,
        'summary': {
            'total': job.total_tenants,
            'successful': job.successful_tenants,
            'failed': job.failed_tenants
        }
    }


@app.task(
    bind=True,
    name='rollback_migrations'
)
def rollback_migration(job_id: str, tenant_id: str, rollback_scripts: List[Dict]):
    """Rollback migrations for a specific tenant"""
    logger.warning(f"Rolling back migration for tenant {tenant_id} (job: {job_id})")

    try:
        # for script in reversed(rollback_scripts):
        #     db_manager.execute_script(tenant_id, script['content'])

        logger.info(f"Rollback successful for {tenant_id}")
        return {"success": True, "tenant_id": tenant_id}

    except Exception as e:
        logger.error(f"Rollback failed for {tenant_id}: {e}", exc_info=True)
        return {"success": False, "tenant_id": tenant_id, "error": str(e)}

